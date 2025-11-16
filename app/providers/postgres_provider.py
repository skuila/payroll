# providers/postgres_provider.py
"""Provider PostgreSQL avec pool de connexions - VERSION POST-MIGRATION
Version: 3.0.0 (Référentiel Employés)
Architecture: core.employees (DIM) + payroll.payroll_transactions (FACT)
"""

import logging
import os
import re
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import OperationalError

from .data_provider import AbstractDataProvider

if TYPE_CHECKING:
    from app.services.data_repo import DataRepository

# NOTE: we avoid mutating sys.path here to prevent duplicate-module issues during
import atexit
import builtins

# static analysis (mypy). Import the package-qualified module instead.
from app.services.data_repo import DataRepository


def _safe_print(*args, **kwargs):
    """Print wrapper that avoids encoding errors on Windows consoles.

    Falls back to writing UTF-8 bytes to stdout.buffer if the normal
    print call raises an encoding error.
    """
    try:
        builtins.print(*args, **kwargs)
    except Exception:
        try:
            text = " ".join(str(a) for a in args)
            # Ensure newline handling
            end = kwargs.get("end", "\n")
            out = text + end
            # Use the console encoding if available to avoid mojibake
            enc = getattr(sys.stdout, "encoding", None) or "utf-8"
            b = out.encode(enc, errors="replace")
            try:
                sys.stdout.buffer.write(b)
                sys.stdout.buffer.flush()
            except Exception:
                try:
                    sys.stdout.write(out)
                    sys.stdout.flush()
                except Exception:
                    pass
        except Exception:
            pass


# Try to force stdout/stderr to UTF-8 on Python 3.7+ to avoid Windows cp1252 issues
try:
    _reconf_out = getattr(sys.stdout, "reconfigure", None)
    if callable(_reconf_out):
        _reconf_out(encoding="utf-8", errors="replace")
    _reconf_err = getattr(sys.stderr, "reconfigure", None)
    if callable(_reconf_err):
        _reconf_err(encoding="utf-8", errors="replace")
except Exception:
    # Not critical; continue with _safe_print fallback
    pass

# Configuration environnement
APP_ENV = os.getenv("APP_ENV", "development")
USE_COPY = os.getenv("USE_COPY", "0") == "1"


def _mask_dsn(dsn: str) -> str:
    """Masque le mot de passe dans le DSN"""
    if not dsn:
        return ""
    # Try URL parse (handles url-encoded passwords)
    try:
        parts = urlsplit(dsn)
        if parts.scheme and (parts.hostname or parts.netloc):
            user = parts.username or ""
            if parts.password:
                # rebuild netloc with masked password
                host = parts.hostname or ""
                port = f":{parts.port}" if parts.port else ""
                netloc = f"{user}:***@{host}{port}" if user else f"{host}{port}"
                return urlunsplit(
                    (parts.scheme, netloc, parts.path, parts.query, parts.fragment)
                )
    except Exception:
        pass

    # Fallback: mask conninfo style password=XXX
    try:
        return re.sub(r"(password\s*=\s*)([^\s]+)", r"\1***", dsn, flags=re.IGNORECASE)
    except Exception:
        return dsn


def _has_password_in_dsn(dsn: str) -> bool:
    """Détecte si une DSN contient un mot de passe (format URL ou conninfo)."""
    if not dsn:
        return False
    # Try URL style first
    try:
        parts = urlsplit(dsn)
        if parts.password:
            return True
    except Exception:
        # ignore and fallback to conninfo detection
        pass

    # conninfo style: password=...
    try:
        if re.search(r"\bpassword\s*=\s*[^\s]+", dsn, flags=re.IGNORECASE):
            return True
    except Exception:
        pass

    return False


class PostgresProvider(AbstractDataProvider):
    """
    Provider PostgreSQL avec architecture dimension/fait.
    Version 3.0.0: Post-migration référentiel employés

    Tables utilisées:
        - core.employees (dimension)
        - payroll.payroll_transactions (fait)
        - payroll.import_batches (traçabilité)
    """

    repo: "DataRepository"

    def __init__(self, dsn: Optional[str] = None):
        """Initialise le provider PostgreSQL.

        - N'utilise aucune logique de fallback.
        - En cas d'échec de connexion, l'exception est levée vers l'appelant.
        """
        logger = logging.getLogger(__name__)

        # Priorité: paramètre > PAYROLL_DSN > DATABASE_URL
        self.dsn = dsn or os.getenv("PAYROLL_DSN") or os.getenv("DATABASE_URL")

        # Interdire le mode offline/fallback: DSN requis
        if not self.dsn:
            raise RuntimeError(
                "Aucun DSN valide fourni. Utilisez --dsn ou PAYROLL_DSN avec mot de passe."
            )

        # PAYROLL_FORCE_OFFLINE should not be used in this strict mode
        if os.getenv("PAYROLL_FORCE_OFFLINE") == "1":
            raise RuntimeError(
                "PAYROLL_FORCE_OFFLINE=1 n'est pas autorisé: le provider PostgreSQL est obligatoire."
            )

        # Vérifier présence mot de passe dans DSN ou via PGPASSWORD
        if (
            not _has_password_in_dsn(self.dsn)
            and not os.getenv("PGPASSWORD")
            and not os.getenv("PAYROLL_DB_PASSWORD")
        ):
            raise RuntimeError(
                "Aucun mot de passe fourni dans le DSN et PGPASSWORD/PAYROLL_DB_PASSWORD absent."
            )

        # Test de connexion unique et rapide
        try:
            test_conn = psycopg.connect(self.dsn, connect_timeout=5)
            test_conn.close()
        except OperationalError as e:
            logger.error(f"Échec connexion PostgreSQL: {e}")
            # Re-raise to force the caller to handle failure
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors du test de connexion PostgreSQL: {e}")
            raise

        # Initialiser le DataRepository (pool)
        try:
            self.repo = DataRepository(self.dsn, min_size=2, max_size=10)
            self._configure_connection_defaults()

            # Register close at exit
            def _close_repo_safe(r: Optional["DataRepository"] = self.repo) -> None:
                try:
                    if r is not None and hasattr(r, "close"):
                        r.close()
                except Exception:
                    pass

            try:
                atexit.register(_close_repo_safe)
            except Exception:
                pass

            # Log unique de succès (masquer mot de passe)
            dsn_display = _mask_dsn(self.dsn)
            conn_info = self.get_connection_info()
            logger.info(
                f"SUCCESS: Connexion PostgreSQL établie (app={dsn_display}, db={conn_info.get('database', 'N/A')}, user={conn_info.get('user', 'N/A')})"
            )
        except Exception:
            logger.exception(
                "Erreur lors de l'initialisation du DataRepository PostgreSQL"
            )
            raise

    def _configure_connection_defaults(self) -> None:
        """Configure les paramètres par défaut sur chaque connexion du pool"""
        if self.repo is None:
            return

        try:
            with self.repo.get_connection() as conn:
                with conn.cursor() as cur:
                    # Fixer timezone pour cohérence (America/Toronto pour Québec)
                    cur.execute("SET TIME ZONE 'America/Toronto';")
                    # Fixer format de date ISO
                    cur.execute("SET datestyle TO ISO, YMD;")
                    # Fixer search_path par défaut
                    cur.execute(
                        "SET search_path TO payroll, core, reference, security, public;"
                    )
                conn.commit()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Impossible de configurer les paramètres de connexion: {e}")

    def get_kpis(self, pay_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les KPI depuis la nouvelle structure référentiel.

        Architecture: core.employees (DIM) + payroll.payroll_transactions (FACT)

        Args:
            pay_date: Date de paie exacte au format YYYY-MM-DD (ex: '2025-08-28')
                     Si None, utilise la dernière date de paie disponible

        Returns:
            Dict avec: salaire_net_total, masse_salariale, nb_employes, deductions, net_moyen, pay_date
        """
        if not self.repo:
            return self._mock_kpis(pay_date)
        assert self.repo is not None

        try:
            # Si pas de date fournie, récupérer la dernière date de paie
            if not pay_date:
                sql_last_date = """
                SELECT MAX(pay_date)::text
                FROM payroll.payroll_transactions
                """
                result_last = self.repo.run_query(sql_last_date, fetch_one=True)
                if result_last and result_last[0]:
                    pay_date = result_last[0]
                else:
                    return self._mock_kpis(None)

            # Normaliser la date (accepter DD/MM/YYYY ou YYYY-MM-DD)
            pay_date_str = self._normalize_pay_date(pay_date)
            if not pay_date_str:
                return self._mock_kpis(pay_date)

            # 1) Essayer de lire le snapshot KPI
            try:
                snapshot_row = self.repo.run_query(
                    """
                    SELECT data
                    FROM payroll.kpi_snapshot
                    WHERE period = %(pay_date)s
                    """,
                    {"pay_date": pay_date_str},
                    fetch_one=True,
                )
                if snapshot_row and snapshot_row[0]:
                    snapshot = snapshot_row[0]
                    cards = snapshot.get("cards", {})
                    tables = snapshot.get("tables", {})
                    return {
                        "salaire_net_total": float(cards.get("salaire_net_total", 0.0)),
                        "masse_salariale": float(cards.get("masse_salariale", 0.0)),
                        "nb_employes": int(cards.get("nb_employes", 0) or 0),
                        "deductions": float(cards.get("deductions", 0.0)),
                        "net_moyen": float(cards.get("net_moyen", 0.0)),
                        "pay_date": pay_date_str,
                        "period": pay_date_str,
                        "source": snapshot.get("source", "kpi_snapshot"),
                        "tables": tables,
                    }
            except Exception:
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Impossible de lire kpi_snapshot, calcul live", exc_info=True
                )

            # Requête sur nouvelle structure (core.employees + payroll.payroll_transactions)
            # Utiliser TO_DATE pour garantir le format correct
            sql = """
            SELECT
              -- Salaire net total (tous montants)
              COALESCE(SUM(t.amount_cents), 0) / 100.0 AS salaire_net_total,
              -- Masse salariale (montants positifs)
              COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS masse,
              -- Employés uniques (amount_cents <> 0 par construction de la table)
              COUNT(DISTINCT t.employee_id) AS nb_employes_uniques,
              -- Déductions (montants négatifs)
              COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions
            FROM payroll.payroll_transactions t
            WHERE t.pay_date = %(pay_date)s::date
            """

            result = self.repo.run_query(sql, {"pay_date": pay_date_str})

            if result and len(result) > 0:
                row = result[0]
                salaire_net_total = float(row[0] or 0)
                masse = float(row[1] or 0)
                nb_emp = int(row[2] or 0)
                deductions = float(row[3] or 0)

                return {
                    "salaire_net_total": salaire_net_total,
                    "masse_salariale": masse,
                    "nb_employes": nb_emp,  # Employés uniques depuis référentiel
                    "deductions": deductions,
                    "net_moyen": salaire_net_total / nb_emp if nb_emp > 0 else 0,
                    "pay_date": pay_date_str,
                    "period": pay_date_str,  # Compatibilité avec code existant
                    "source": "transactions_live",  # Calcul en direct
                }
            else:
                return self._mock_kpis(pay_date_str)

        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Erreur get_kpis PostgreSQL")
            return self._mock_kpis(pay_date)

    def get_latest_pay_date(self) -> Optional[Dict[str, str]]:
        """
        Retourne la dernière date de paie disponible (transactions > imported).

        Returns:
            {"pay_date": "YYYY-MM-DD", "source": "transactions|imported"} | None
        """
        if not self.repo:
            return None

        try:
            result_tx = self.repo.run_query(
                "SELECT MAX(pay_date)::text FROM payroll.payroll_transactions",
                fetch_one=True,
            )
            if result_tx and result_tx[0]:
                return {"pay_date": result_tx[0], "source": "transactions"}

            result_imported = self.repo.run_query(
                "SELECT MAX(date_paie)::text FROM payroll.imported_payroll_master",
                fetch_one=True,
            )
            if result_imported and result_imported[0]:
                return {"pay_date": result_imported[0], "source": "imported"}

            return None
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Erreur get_latest_pay_date")
            return None

    def _mock_kpis(self, pay_date: Optional[str]) -> Dict[str, Any]:
        """Fallback mock data si erreur"""
        return {
            "masse_salariale": 0,
            "nb_employes": 0,
            "deductions": 0,
            "salaire_net_total": 0,
            "net_moyen": 0,
            "pay_date": pay_date or "2025-08-28",
            "period": pay_date or "2025-08-28",  # Compatibilité
            "source": "mock_fallback",
        }

    @staticmethod
    def _normalize_pay_date(date_str: Optional[str]) -> Optional[str]:
        """
        Normalise une date de paie au format YYYY-MM-DD.

        Formats acceptés:
        - YYYY-MM-DD (ex: '2025-08-28')
        - DD/MM/YYYY (ex: '28/08/2025')
        - DD-MM-YYYY (ex: '28-08-2025')

        Returns:
            Date au format YYYY-MM-DD ou None si format invalide
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        # Déjà au format YYYY-MM-DD
        if len(date_str) == 10 and date_str.count("-") == 2:
            try:
                # Valider que c'est une date valide
                from datetime import datetime

                datetime.strptime(date_str, "%Y-%m-%d")
                return date_str
            except ValueError:
                return None

        # Format DD/MM/YYYY
        if "/" in date_str and len(date_str.split("/")) == 3:
            try:
                from datetime import datetime

                parts = date_str.split("/")
                if len(parts[0]) == 2 and len(parts[1]) == 2 and len(parts[2]) == 4:
                    dt = datetime.strptime(date_str, "%d/%m/%Y")
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Format DD-MM-YYYY
        if "-" in date_str and len(date_str.split("-")) == 3:
            try:
                from datetime import datetime

                parts = date_str.split("-")
                if len(parts[0]) == 2 and len(parts[1]) == 2 and len(parts[2]) == 4:
                    dt = datetime.strptime(date_str, "%d-%m-%Y")
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        return None

    @staticmethod
    def _parse_pay_date_input(pay_date: Optional[str]) -> Optional[str]:
        """
        Normalise une date de paie au format YYYY-MM-DD.

        Args:
            pay_date: Date de paie dans différents formats

        Returns:
            Date au format YYYY-MM-DD ou None si format invalide
        """
        return PostgresProvider._normalize_pay_date(pay_date)

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value) if value is not None else 0.0
        except Exception:
            return 0.0

    def get_kpi_details(self, pay_date: Optional[str]) -> Dict[str, Any]:
        """
        Retourne les détails KPI sans passer par l'API FastAPI.

        Args:
            pay_date: Date de paie exacte au format YYYY-MM-DD (ex: '2025-08-28')
        """
        empty = {
            "codes_paie": [],
            "postes_budgetaires": [],
            "categories_emploi": [],
            "pay_date": pay_date or "N/A",
            "period": pay_date or "N/A",  # Compatibilité
            "source": "database",
        }

        if not self.repo:
            return empty
        assert self.repo is not None

        # Normaliser la date de paie
        pay_date_normalized = self._normalize_pay_date(pay_date) if pay_date else None
        if not pay_date_normalized:
            return empty

        params = {"pay_date": pay_date_normalized}

        try:
            # Codes de paie - utiliser date_paie au lieu de periode
            sql_codes = """
                SELECT 
                    date_paie::text AS date_paie,
                    code_paie,
                    libelle_paie,
                    categorie_paie,
                    montant_total,
                    nb_transactions
                FROM payroll.v_kpi_par_code_paie
                WHERE date_paie = %(pay_date)s::date
                ORDER BY ABS(montant_total) DESC
            """
            codes_rows = self.repo.run_query(sql_codes, params) or []
            codes = [
                {
                    "pay_date": row[0],
                    "code_paie": row[1],
                    "libelle_code": row[2],
                    "categorie_paie": row[3],
                    "montant_total": self._safe_float(row[4]),
                    "nb_lignes": int(row[5] or 0),
                }
                for row in codes_rows
            ]

            # Postes budgétaires - utiliser date_paie au lieu de periode
            sql_postes = """
                SELECT 
                    date_paie::text AS date_paie,
                    poste_budgetaire,
                    libelle_poste,
                    nb_employes,
                    cout_total,
                    gains_brut,
                    deductions_totales,
                    net_a_payer
                FROM payroll.v_kpi_par_poste_budgetaire
                WHERE date_paie = %(pay_date)s::date
                ORDER BY cout_total DESC
            """
            postes_rows = self.repo.run_query(sql_postes, params) or []
            postes = [
                {
                    "pay_date": row[0],
                    "poste_budgetaire": row[1],
                    "libelle_poste": row[2],
                    "nb_employes": int(row[3] or 0),
                    "cout_total_employeur": self._safe_float(row[4]),
                    "gains_brut": self._safe_float(row[5]),
                    "deductions_net": self._safe_float(row[6]),
                    "net_a_payer": self._safe_float(row[7]),
                }
                for row in postes_rows
            ]

            # Catégories d'emploi - utiliser date_paie au lieu de periode
            sql_categories = """
                SELECT 
                    date_paie::text AS date_paie,
                    categorie_emploi,
                    nb_employes,
                    gains_brut,
                    deductions_totales,
                    net_a_payer,
                    part_employeur,
                    cout_total
                FROM payroll.v_kpi_par_categorie_emploi
                WHERE date_paie = %(pay_date)s::date
                ORDER BY cout_total DESC
            """
            categories_rows = self.repo.run_query(sql_categories, params) or []
            categories = [
                {
                    "pay_date": row[0],
                    "categorie_emploi": row[1],
                    "nb_employes": int(row[2] or 0),
                    "gains_brut": self._safe_float(row[3]),
                    "deductions_employe": self._safe_float(row[4]),
                    "net": self._safe_float(row[5]),
                    "part_employeur": self._safe_float(row[6]),
                    "cout_total_employeur": self._safe_float(row[7]),
                }
                for row in categories_rows
            ]

            return {
                "codes_paie": codes,
                "postes_budgetaires": postes,
                "categories_emploi": categories,
                "pay_date": pay_date_normalized,
                "period": pay_date_normalized,  # Compatibilité
                "source": "database",
            }
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Erreur get_kpi_details")
            return empty

    def get_dashboard_charts(self, pay_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Séries de graphiques pour le dashboard (dernières 30 dates).
        """
        if not self.repo:
            return {}
        try:
            pay_date_str = self._normalize_pay_date(pay_date) if pay_date else None
            sql = """
            WITH ordered AS (
                SELECT 
                    t.pay_date::text AS pay_date,
                    SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) / 100.0 AS gains,
                    SUM(t.amount_cents) / 100.0 AS net,
                    COUNT(*) AS tx
                FROM payroll.payroll_transactions t
                WHERE (%(pay_date)s::date IS NULL OR t.pay_date <= %(pay_date)s::date)
                GROUP BY t.pay_date
                ORDER BY t.pay_date DESC
                LIMIT 30
            )
            SELECT * FROM ordered ORDER BY pay_date ASC
            """
            rows = self.repo.run_query(sql, {"pay_date": pay_date_str})
            if not rows:
                return {}

            labels = [row[0] for row in rows]
            gains = [float(row[1] or 0) for row in rows]
            net = [float(row[2] or 0) for row in rows]
            tx = [int(row[3] or 0) for row in rows]

            category_reference_date = pay_date_str or (labels[-1] if labels else None)
            category_labels: List[str] = []
            category_values: List[int] = []
            if category_reference_date:
                sql_categories = """
                SELECT 
                    COALESCE(NULLIF(categorie_emploi, ''), 'Non classé') AS categorie,
                    SUM(nb_employes) AS nb_membres
                FROM payroll.v_emp_categories
                WHERE date_paie = %(pay_date)s::date
                GROUP BY 1
                ORDER BY nb_membres DESC
                """
                try:
                    cat_rows = self.repo.run_query(
                        sql_categories, {"pay_date": category_reference_date}
                    )
                    if cat_rows:
                        category_labels = [row[0] for row in cat_rows]
                        category_values = [int(row[1] or 0) for row in cat_rows]
                except Exception as cat_err:
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        "Impossible d'accéder à payroll.v_emp_categories (exécuter app/migration/analytics_emp_categories.sql avec un superuser) : %s",
                        cat_err,
                    )

            return {
                "revenue": {
                    "labels": labels,
                    "values": gains,
                    "name": "Masse salariale",
                },
                "active": {"labels": labels, "values": tx, "name": "Transactions"},
                "net": {"labels": labels, "values": net, "name": "Salaire net"},
                "purchases": {"labels": labels, "values": tx, "name": "Transactions"},
                "categories": {
                    "labels": category_labels,
                    "values": category_values,
                    "name": "Catégorie d'emploi",
                },
            }
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Erreur get_dashboard_charts")
            return {}

    def get_table(
        self, offset: int = 0, limit: int = 50, filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Récupère les données paginées depuis la nouvelle structure.

        Architecture: JOIN payroll.payroll_transactions + core.employees
        """
        if not self.repo:
            return self._mock_table(offset, limit, filters)
        assert self.repo is not None

        try:
            # Validation des paramètres
            limit = min(limit, 100)  # Max 100 lignes par requête
            offset = max(0, offset)
            filters = filters or {}

            pay_date_filter = filters.get(
                "pay_date", filters.get("period", "")
            )  # Compatibilité
            matricule_filter = filters.get("matricule", "")
            categorie_filter = filters.get("categorie", "")

            # Normaliser la date de paie si fournie
            pay_date_normalized = None
            if pay_date_filter:
                pay_date_normalized = self._normalize_pay_date(pay_date_filter)

            # Requête sur nouvelle structure
            sql = """
            SELECT 
                e.matricule_norm,
                e.nom_complet AS nom,
                t.pay_date::text AS date_paie,
                t.pay_code AS categorie,
                t.amount_cents / 100.0 AS montant
            FROM payroll.payroll_transactions t
            JOIN core.employees e ON t.employee_id = e.employee_id
            WHERE 1=1
                AND (%(pay_date)s::date IS NULL OR t.pay_date = %(pay_date)s::date)
                AND (%(matricule)s = '' OR e.matricule_norm = %(matricule)s)
                AND (%(categorie)s = '' OR t.pay_code ILIKE '%%' || %(categorie)s || '%%')
            ORDER BY t.pay_date DESC, e.matricule_norm
            LIMIT %(limit)s OFFSET %(offset)s
            """

            # Requête count pour pagination
            sql_count = """
            SELECT COUNT(*) AS total
            FROM payroll.payroll_transactions t
            JOIN core.employees e ON t.employee_id = e.employee_id
            WHERE 1=1
                AND (%(pay_date)s::date IS NULL OR t.pay_date = %(pay_date)s::date)
                AND (%(matricule)s = '' OR e.matricule_norm = %(matricule)s)
                AND (%(categorie)s = '' OR t.pay_code ILIKE '%%' || %(categorie)s || '%%')
            """

            params = {
                "pay_date": pay_date_normalized,
                "matricule": matricule_filter,
                "categorie": categorie_filter,
                "limit": limit,
                "offset": offset,
            }

            # Exécuter les requêtes
            rows_result = self.repo.run_query(sql, params)
            count_result = self.repo.run_query(sql_count, params)

            total = int(count_result[0][0]) if count_result else 0

            # Formater les résultats
            rows = []
            if rows_result:
                for row in rows_result:
                    rows.append(
                        {
                            "matricule": row[0] or "N/A",
                            "nom": row[1] or "N/A",
                            "date_paie": row[2] or "",
                            "categorie": row[3] or "N/A",
                            "montant": float(row[4] or 0),
                        }
                    )

            return {
                "rows": rows,
                "total": total,
                "offset": offset,
                "limit": limit,
                "source": "referentiel_employees",
            }

        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Erreur get_table PostgreSQL")
            return self._mock_table(offset, limit, filters)

    def _mock_table(self, offset, limit, filters):
        """Fallback mock data si erreur"""
        return {
            "rows": [],
            "total": 0,
            "offset": offset,
            "limit": limit,
            "source": "mock_fallback_empty",
        }

    def get_employees_list(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Récupère la liste des employés du référentiel.

        NOUVELLE MÉTHODE (post-migration)

        Args:
            filters: {'statut': 'actif', 'search': 'dupont'}

        Returns:
            Dict avec liste employés et total
        """
        if not self.repo:
            return {"employees": [], "total": 0}
        assert self.repo is not None

        try:
            filters = filters or {}
            statut_filter = filters.get("statut", "actif")
            search_filter = filters.get("search", "")

            sql = """
            SELECT 
                employee_id,
                employee_key,
                matricule_norm,
                nom_norm,
                prenom_norm,
                nom_complet,
                statut,
                TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at,
                TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI:SS') AS updated_at
            FROM core.employees
            WHERE statut = %(statut)s
              AND (%(search)s = '' OR 
                   nom_norm ILIKE '%%' || %(search)s || '%%' OR
                   prenom_norm ILIKE '%%' || %(search)s || '%%' OR
                   matricule_norm ILIKE '%%' || %(search)s || '%%')
            ORDER BY nom_norm, prenom_norm
            """

            result = self.repo.run_query(
                sql, {"statut": statut_filter, "search": search_filter}
            )

            employees = []
            if result:
                for row in result:
                    employees.append(
                        {
                            "employee_id": row[0],
                            "employee_key": row[1],
                            "matricule": row[2] or "",
                            "nom": row[3] or "",
                            "prenom": row[4] or "",
                            "nom_complet": row[5] or "",
                            "statut": row[6] or "",
                            "created_at": row[7] or "",
                            "updated_at": row[8] or "",
                        }
                    )

            return {
                "employees": employees,
                "total": len(employees),
                "source": "referentiel_employees",
            }

        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Erreur get_employees_list")
            return {"employees": [], "total": 0}

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Retourne les informations de connexion effectives.
        Version 3.0: Ajout architecture info

        Returns:
            dict avec 'dsn_masked', 'user', 'host', 'database', 'port', 'status', etc.
        """
        if not self.repo:
            return {
                "status": "disconnected",
                "message": "Repository non initialisé",
                "app_env": APP_ENV,
            }

        try:
            with self.repo.get_connection() as conn:
                # Récupérer les paramètres de connexion (psycopg3)
                dsn_info = conn.info.get_parameters()

                # Récupérer timezone active (avec fallback)
                timezone = "America/Toronto"  # Défaut
                try:
                    with conn.cursor() as cur:
                        cur.execute("SHOW timezone;")
                        result = cur.fetchone()
                        if result:
                            timezone = result[0]
                except Exception as tz_err:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Impossible de récupérer timezone: {tz_err}")

                # Masquer le mot de passe dans le DSN
                dsn_masked = _mask_dsn(self.dsn or "")

                return {
                    "status": "connected",
                    "dsn_masked": dsn_masked,
                    "user": dsn_info.get("user", "N/A"),
                    "host": dsn_info.get("host", "N/A"),
                    "database": dsn_info.get("dbname", "N/A"),
                    "port": dsn_info.get("port", "N/A"),
                    "app_env": APP_ENV,
                    "timezone": timezone,
                    "use_copy": USE_COPY,
                    "architecture": "referentiel_v3",
                }
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception("Erreur get_connection_info")
            return {"status": "error", "message": str(e), "app_env": APP_ENV}

    # ========================================================================
    # GESTION NOUVEAUX EMPLOYÉS (par fichier/batch)
    # ========================================================================

    def get_all_pay_dates(self) -> list:
        """
        Liste toutes les dates de paie (fichiers importés).

        Returns:
            [
                {'pay_date': '2025-08-28', 'filename': 'Classeur_aout.xlsx', 'batch_id': 3},
                {'pay_date': '2025-07-31', 'filename': 'Classeur_juillet.xlsx', 'batch_id': 2},
                ...
            ]
        """
        sql = """
            SELECT DISTINCT
                t.pay_date,
                ib.filename,
                ib.batch_id
            FROM payroll.payroll_transactions t
            JOIN payroll.import_batches ib ON t.batch_id = ib.batch_id
            WHERE ib.status = 'completed'
            ORDER BY t.pay_date DESC
        """
        rows = self.repo.run_query(sql)
        return [
            {
                "pay_date": r[0].isoformat() if r[0] else None,
                "filename": r[1],
                "batch_id": r[2],
            }
            for r in rows
        ]

    def get_employee_stats_by_date(self, pay_date: str) -> dict:
        """
        Stats nouveaux employés pour une date de paie (fichier).
        Règle métier: 1 période = 1 fichier = 1 date exacte
        Nouveau = matricule > max(matricule du batch précédent)

        Args:
            pay_date: Format YYYY-MM-DD (ex: "2025-08-28")

        Returns:
            {
                'batch_id': 3,
                'pay_date': '2025-08-28',
                'filename': 'Classeur_aout.xlsx',
                'total': 295,
                'nouveaux': 6,
                'anciens': 289,
                'max_precedent': 2000,
                'max_actuel': 2006,
                'date_precedente': '2025-07-31',
                'liste_nouveaux': '2001, 2002, 2003, 2004, 2005, 2006'
            }
        """
        sql = "SELECT * FROM payroll.get_stats_nouveaux_date(%s::DATE)"
        row = self.repo.run_query(sql, (pay_date,), fetch_one=True)

        if not row:
            return {
                "pay_date": pay_date,
                "total": 0,
                "nouveaux": 0,
                "anciens": 0,
                "max_precedent": None,
                "max_actuel": None,
                "date_precedente": None,
                "liste_nouveaux": None,
            }

        return {
            "batch_id": row[0],
            "pay_date": row[1].isoformat() if row[1] else pay_date,
            "filename": row[2],
            "total": row[3] or 0,
            "nouveaux": row[4] or 0,
            "anciens": row[5] or 0,
            "max_precedent": row[6],
            "max_actuel": row[7],
            "date_precedente": row[8].isoformat() if row[8] else None,
            "liste_nouveaux": row[9],
        }

    def get_nouveaux_employes_by_date(self, pay_date: str) -> list:
        """
        Liste des nouveaux employés pour une date de paie.

        Args:
            pay_date: Format YYYY-MM-DD (ex: "2025-08-28")

        Returns:
            [
                {
                    'matricule': '2001',
                    'nom_complet': 'Abdou, Anis',
                    'max_precedent': 2000,
                    'est_nouveau': True
                },
                ...
            ]
        """
        sql = """
            SELECT 
                matricule_norm,
                nom_norm || ', ' || COALESCE(prenom_norm, '') as nom_complet,
                max_precedent,
                est_nouveau
            FROM payroll.v_nouveaux_par_batch
            WHERE pay_date = %s::DATE
            AND est_nouveau = TRUE
            ORDER BY matricule_int ASC
        """

        rows = self.repo.run_query(sql, (pay_date,))
        return [
            {
                "matricule": r[0],
                "nom_complet": r[1],
                "max_precedent": r[2],
                "est_nouveau": r[3],
            }
            for r in rows
        ]

    def get_employees_for_date(self, pay_date: str) -> list:
        """
        Liste TOUS les employés d'une date avec indicateur nouveau/ancien.

        Args:
            pay_date: Format YYYY-MM-DD (ex: "2025-08-28")

        Returns:
            [
                {
                    'matricule': '2001',
                    'nom_complet': 'Abdou, Anis',
                    'est_nouveau': True,
                    'statut': 'actif'
                },
                ...
            ]
        """
        sql = """
            SELECT 
                matricule_norm,
                nom_norm || ', ' || COALESCE(prenom_norm, '') as nom_complet,
                est_nouveau
            FROM payroll.v_nouveaux_par_batch
            WHERE pay_date = %s::DATE
            ORDER BY est_nouveau DESC, matricule_int ASC
        """
        rows = self.repo.run_query(sql, (pay_date,))
        return [
            {
                "matricule": r[0],
                "nom_complet": r[1],
                "est_nouveau": r[2],
                "statut": "actif",
            }
            for r in rows
        ]

    # ========================================================================
    # API EMPLOYEES PAGE (AppBridge via QWebChannel)
    # ========================================================================

    def get_periods(self, filter_year: Optional[int] = None) -> list:
        """
        Liste toutes les périodes depuis payroll.pay_periods (si remplie) ou payroll_transactions (fallback).

        Args:
            filter_year: Optionnel, filtre par année (ex: 2025)

        Returns:
            Si filter_year fourni (pour periods.html):
            [
                {
                    'period_id': str,
                    'pay_date': str (YYYY-MM-DD),
                    'pay_day': int,
                    'pay_month': int,
                    'pay_year': int,
                    'period_seq_in_year': int,
                    'status': str,
                    'closed_by': str or None,
                    'transaction_count': int
                },
                ...
            ]

            Sinon (pour employees.js):
            [
                {'id': period_id, 'label': date_str, 'date': date_str},
                ...
            ]
        """
        # Essayer d'abord payroll.pay_periods
        try:
            if filter_year:
                # Format détaillé pour periods.html
                sql = """
                    SELECT 
                        period_id::text,
                        pay_date::text,
                        pay_day,
                        pay_month,
                        pay_year,
                        period_seq_in_year,
                        status,
                        closed_by::text,
                        (SELECT COUNT(*) FROM payroll.payroll_transactions WHERE period_id = pp.period_id) as transaction_count
                    FROM payroll.pay_periods pp
                    WHERE pay_year = %(year)s
                    ORDER BY pay_date DESC
                """
                rows = self.repo.run_query(sql, {"year": filter_year})
                if rows:
                    return [
                        {
                            "period_id": r[0],
                            "pay_date": r[1],
                            "pay_day": r[2],
                            "pay_month": r[3],
                            "pay_year": r[4],
                            "period_seq_in_year": r[5],
                            "status": r[6],
                            "closed_by": r[7],
                            "transaction_count": r[8] or 0,
                        }
                        for r in rows
                    ]
            else:
                # Format simplifié pour employees.js
                sql = """
                    SELECT period_id::text, TO_CHAR(pay_date, 'YYYY-MM-DD') AS date_str
                    FROM payroll.pay_periods
                    ORDER BY pay_date DESC
                    LIMIT 100
                """
                rows = self.repo.run_query(sql)
                if rows:
                    return [{"id": r[0], "label": r[1], "date": r[1]} for r in rows]
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Erreur lecture payroll.pay_periods, fallback sur transactions: %s", e
            )

        # Fallback: utiliser payroll_transactions si pay_periods vide ou inexistant
        if filter_year:
            # Format détaillé depuis transactions
            sql = """
                SELECT 
                    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS pay_date,
                    EXTRACT(DAY FROM t.pay_date)::int AS pay_day,
                    EXTRACT(MONTH FROM t.pay_date)::int AS pay_month,
                    EXTRACT(YEAR FROM t.pay_date)::int AS pay_year,
                    COUNT(*)::int AS transaction_count
                FROM payroll.payroll_transactions t
                WHERE EXTRACT(YEAR FROM t.pay_date) = %(year)s
                GROUP BY t.pay_date
                ORDER BY t.pay_date DESC
            """
            rows = self.repo.run_query(sql, {"year": filter_year})
            return [
                {
                    "period_id": f"auto-{r[0]}",
                    "pay_date": r[0],
                    "pay_day": r[1],
                    "pay_month": r[2],
                    "pay_year": r[3],
                    "period_seq_in_year": 0,  # Non calculable depuis transactions seul
                    "status": "ouverte",
                    "closed_by": None,
                    "transaction_count": r[4] or 0,
                }
                for r in rows
            ]
        else:
            # Format simplifié depuis transactions
            sql = """
                SELECT DISTINCT
                    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_str,
                    t.pay_date
                FROM payroll.payroll_transactions t
                ORDER BY t.pay_date DESC
                LIMIT 100
            """
            rows = self.repo.run_query(sql)
            return [{"id": r[0], "label": r[0], "date": r[0]} for r in rows]

    def get_kpi(self, period_id: str) -> dict:
        """
        Calcule les KPI pour une période donnée.

        Args:
            period_id: Date au format YYYY-MM-DD

        Returns:
            {
                'total': int,      # Effectif total
                'nouveaux': int,   # Nouveaux recrus
                'sorties': int,    # Employés sortis
                'churn': float,    # Taux de rotation (%)
                'prev': str        # Date période précédente
            }
        """
        sql = """
            WITH base AS (
                SELECT
                    v.employee_id,
                    v.est_nouveau,
                    v.pay_date,
                    v.date_precedente,
                    CASE WHEN e.statut = 'inactif' THEN TRUE ELSE FALSE END AS is_left
                FROM payroll.v_nouveaux_par_batch v
                JOIN core.employees e ON e.employee_id = v.employee_id
                WHERE v.pay_date = %s::DATE
            ),
            current_period AS (
                SELECT
                    COUNT(DISTINCT employee_id) AS total,
                    COUNT(DISTINCT employee_id) FILTER (WHERE est_nouveau = TRUE) AS nouveaux,
                    COUNT(DISTINCT employee_id) FILTER (WHERE is_left = TRUE) AS sorties,
                    MAX(date_precedente) AS prev_date
                FROM base
            )
            SELECT 
                total,
                nouveaux,
                sorties,
                CASE 
                    WHEN total > 0 THEN ROUND((sorties::NUMERIC / total * 100), 2)
                    ELSE 0
                END as churn,
                prev_date
            FROM current_period
        """

        row = self.repo.run_query(sql, (period_id,), fetch_one=True)

        if not row:
            return {"total": 0, "nouveaux": 0, "sorties": 0, "churn": 0.0, "prev": None}

        return {
            "total": row[0] or 0,
            "nouveaux": row[1] or 0,
            "sorties": row[2] or 0,
            "churn": float(row[3]) if row[3] else 0.0,
            "prev": row[4].isoformat() if row[4] else None,
        }

    def list_employees(
        self, period_id: str, filters: dict, page: int, page_size: int
    ) -> dict:
        """
        Liste les employés avec filtres et pagination (accents ignorés).
        """
        if not self.repo:
            return {"items": [], "total": 0}

        try:
            page = max(1, int(page))
            page_size = min(100, max(1, int(page_size)))
        except Exception:
            page, page_size = 1, 10

        offset = (page - 1) * page_size
        params = []
        where = ["1=1"]

        q = (filters or {}).get("q")
        if q:
            params += [q, q]
            where.append(
                """
                (
                  unaccent(lower(e.nom_complet)) LIKE unaccent(lower('%%' || %s || '%%'))
                  OR e.matricule_norm ILIKE '%%' || %s || '%%'
                )
            """
            )

        status = (filters or {}).get("status")
        if status:
            params.append(status)
            where.append("e.statut = %s")

        where_sql = " AND ".join(where)

        sql_base = f"""
            FROM core.employees e
            LEFT JOIN LATERAL (
                SELECT MAX(t.pay_date) AS last_pay_date
                FROM payroll.payroll_transactions t
                WHERE t.employee_id = e.employee_id
            ) act ON true
            WHERE {where_sql}
        """

        total = self.repo.run_query(
            f"SELECT COUNT(*) {sql_base}", tuple(params), fetch_one=True
        )[0]

        rows = (
            self.repo.run_query(
                f"""
            SELECT
                e.employee_id,
                COALESCE(e.matricule_norm, '') AS matricule,
                COALESCE(e.nom_complet, '') AS nom,
                '' AS dept,
                COALESCE(e.statut, 'actif') AS statut,
                COALESCE(act.last_pay_date, NULL) AS last_pay_date
            {sql_base}
            ORDER BY unaccent(lower(e.nom_complet)) ASC, e.employee_id ASC
            LIMIT %s OFFSET %s
        """,
                tuple(params) + (page_size, offset),
                fetch_all=True,
            )
            or []
        )

        items = []
        for r in rows:
            items.append(
                {
                    "employee_id": r[0],
                    "matricule": r[1],
                    "nom": r[2],
                    "dept": r[3],
                    "statut": r[4],
                    "last_pay_date": (r[5].isoformat() if r[5] else None),
                }
            )

        return {"items": items, "total": int(total)}

    def get_employee_detail(self, employee_id: int) -> dict:
        """
        Détails d'un employé avec historique.

        Args:
            employee_id: ID employé

        Returns:
            {
                'employee_id': int,
                'matricule': str,
                'nom': str,
                'dept': str,
                'statut': str,
                'type': str,
                'historique': [
                    {'mois': str, 'statut': str, 'type': str, 'changements': str},
                    ...
                ]
            }
        """
        # Info employé
        sql_emp = """
            SELECT 
                employee_id,
                matricule_norm,
                nom_norm || COALESCE(', ' || prenom_norm, '') as nom_complet,
                statut
            FROM core.employees
            WHERE employee_id = %s
        """

        emp_row = self.repo.run_query(sql_emp, (employee_id,), fetch_one=True)

        if not emp_row:
            return {
                "employee_id": employee_id,
                "matricule": "",
                "nom": "Employé introuvable",
                "dept": "",
                "statut": "",
                "type": "",
                "historique": [],
            }

        # Historique (dernières périodes)
        sql_hist = """
            SELECT DISTINCT
                v.pay_date,
                CASE WHEN v.est_nouveau THEN 'new' ELSE 'old' END as type,
                'Présent' as changements
            FROM payroll.v_nouveaux_par_batch v
            WHERE v.employee_id = %s
            ORDER BY v.pay_date DESC
            LIMIT 10
        """

        hist_rows = self.repo.run_query(sql_hist, (employee_id,))

        historique = [
            {
                "mois": r[0].isoformat() if r[0] else "",
                "statut": emp_row[3],
                "type": r[1],
                "changements": r[2],
            }
            for r in hist_rows
        ]

        return {
            "employee_id": emp_row[0],
            "matricule": emp_row[1],
            "nom": emp_row[2],
            "dept": "",  # Pas encore dans schema
            "statut": emp_row[3],
            "type": historique[0]["type"] if historique else "old",
            "historique": historique,
        }

    def export(self, export_type: str, payload: dict) -> dict:
        """
        Génère un export (Excel/PDF).

        Args:
            export_type: 'excel_view'|'excel_pack'|'pdf_period'|'pdf_employee'|'excel_employee'
            payload: Paramètres export (period, filters, employee_id, etc.)

        Returns:
            {'path': str}  # Chemin fichier généré
        """
        import os
        from datetime import datetime

        # Répertoire exports
        export_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(export_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Placeholder - à implémenter selon besoin réel
        filename_map = {
            "excel_view": f"employees_view_{timestamp}.xlsx",
            "excel_pack": f"employees_pack_{timestamp}.xlsx",
            "pdf_period": f"period_{timestamp}.pdf",
            "pdf_employee": f"employee_{payload.get('employee_id', 'unknown')}_{timestamp}.pdf",
            "excel_employee": f"employee_{payload.get('employee_id', 'unknown')}_{timestamp}.xlsx",
        }

        filename = filename_map.get(export_type, f"export_{timestamp}.xlsx")
        filepath = os.path.join(export_dir, filename)

        # Créer fichier placeholder
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Export {export_type}\n")
            f.write(f"Payload: {payload}\n")
            f.write(f"Généré le: {datetime.now().isoformat()}\n")

        logger = logging.getLogger(__name__)
        logger.info("Export créé: %s", filepath)

        return {"path": filepath}

    def close(self):
        """Ferme le pool de connexions"""
        if self.repo and hasattr(self.repo, "close"):
            try:
                self.repo.close()
                logging.getLogger(__name__).info("DataRepository fermé")
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "Erreur fermeture DataRepository: %s", e
                )
