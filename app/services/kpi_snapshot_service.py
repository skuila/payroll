"""
KPI Snapshot Service: Calcul, invalidation et récupération des KPI par date de paie

Responsabilités:
- Calculer les KPI pour une date de paie donnée depuis payroll_transactions
- Stocker les KPI dans kpi_snapshot (JSONB)
- Invalider (recalculer) les KPI après import
- Fournir les KPI pour l'UI (cartes + tables)

Usage:
    service = KPISnapshotService(repo)
    service.invalidate_and_recalc_kpi('2025-08-28')  # Date exacte YYYY-MM-DD
    kpi = service.get_kpi('2025-08-28')
"""

import json
import logging
from typing import Any

from app.services.data_repo import DataRepository

logger = logging.getLogger(__name__)


class KPISnapshotService:
    """Service pour gestion des KPI snapshots (calcul, invalidation, récupération)."""

    def __init__(self, repo: DataRepository):
        """
        Initialise le service KPI.

        Args:
            repo: Instance de DataRepository configurée
        """
        self.repo = repo

    # ========================
    # POINT D'ENTRÉE PRINCIPAL
    # ========================

    def invalidate_and_recalc_kpi(self, pay_date: str) -> dict[str, Any]:
        """
        Invalide et recalcule les KPI pour une date de paie donnée.

        Étapes:
        1. Calculer les KPI depuis payroll_transactions
        2. Supprimer l'ancien snapshot (si existe)
        3. Insérer le nouveau snapshot

        Args:
            pay_date: Date de paie au format YYYY-MM-DD (ex: '2025-08-28')

        Returns:
            dict avec les KPI calculés
        """
        logger.info(f"Invalidation + recalcul KPI pour date de paie: {pay_date}")

        try:
            # 1. Calculer les KPI
            kpi_data = self._calculate_kpi(pay_date)

            # 2. Upsert dans kpi_snapshot
            self._upsert_snapshot(pay_date, kpi_data)

            logger.info(
                f"OK: KPI recalculés pour {pay_date}: {kpi_data.get('cards', {}).get('nb_employes', 0)} employés"
            )
            return kpi_data

        except Exception as e:
            logger.error(f"Erreur recalcul KPI date de paie {pay_date}: {e}")
            raise

    def get_kpi(self, pay_date: str) -> dict[str, Any]:
        """
        Récupère les KPI pour une date de paie depuis le snapshot.
        Si snapshot inexistant, calcule à la volée.

        Args:
            pay_date: Date de paie au format YYYY-MM-DD (ex: '2025-08-28')

        Returns:
            dict avec structure:
            {
                "cards": {...},        # KPI cartes (masse salariale, nb employés, etc.)
                "tables": {...},       # KPI tables (anomalies, codes, postes)
                "pay_date": "2025-08-28",
                "calculated_at": "2025-10-12T14:30:00Z"
            }
        """
        logger.info(f"Récupération KPI pour date de paie: {pay_date}")

        try:
            # Lire le snapshot
            sql = """
            SELECT data, calculated_at
            FROM payroll.kpi_snapshot
            WHERE period = %(pay_date)s
            """
            result = self.repo.run_query(sql, {"pay_date": pay_date}, fetch_one=True)

            if result:
                data = result[0]
                calculated_at = result[1]
                data["calculated_at"] = (
                    calculated_at.isoformat() if calculated_at else None
                )
                data["pay_date"] = pay_date
                data["source"] = "snapshot"
                logger.info(
                    f"OK: KPI snapshot trouvé pour {pay_date} (calculé: {calculated_at})"
                )
                return data
            else:
                # Snapshot inexistant → calculer à la volée
                logger.warning(
                    f"Snapshot KPI inexistant pour {pay_date}, calcul à la volée"
                )
                kpi_data = self._calculate_kpi(pay_date)
                kpi_data["source"] = "on_the_fly"
                return kpi_data

        except Exception as e:
            logger.error(f"Erreur récupération KPI date de paie {pay_date}: {e}")
            raise

    # ========================
    # MÉTHODES INTERNES
    # ========================

    def _calculate_kpi(self, pay_date: str) -> dict[str, Any]:
        """
        Calcule les KPI pour une date de paie précise depuis payroll_transactions.

        Structure retournée:
        {
            "cards": {
                "masse_salariale": 125000.50,
                "nb_employes": 45,
                "deductions": -25000.00,
                "net_moyen": 2777.78,
                "masse_employeur": 30000.00
            },
            "tables": {
                "anomalies": [...],      # Nets négatifs, codes sensibles, etc.
                "codes_top": [...],      # Top 10 codes par montant
                "postes_top": [...],     # Top 10 postes budgétaires
                "nouveaux_codes": [...]  # Codes apparus cette date de paie
            }
        }
        """
        logger.info(f"Calcul KPI date de paie {pay_date}")

        # 1. KPI CARTES (agrégats globaux)
        cards = self._calculate_cards(pay_date)

        # 2. KPI TABLES (listes détaillées)
        tables = self._calculate_tables(pay_date)

        return {"cards": cards, "tables": tables, "source": "kpi_snapshot"}

    def _calculate_cards(self, pay_date: str) -> dict[str, Any]:
        """Calcule les KPI cartes (agrégats globaux) - LOGIQUE CORRECTE."""
        # Le paramètre pay_date est une date exacte au format 'YYYY-MM-DD' (ex: '2025-08-28')
        sql = """
        SELECT 
            COALESCE(SUM(pt.amount_cents) / 100.0, 0) AS salaire_net_total,
            COALESCE(SUM(CASE WHEN pt.amount_cents > 0 THEN pt.amount_cents ELSE 0 END) / 100.0, 0) AS masse_salariale,
            COALESCE(SUM(CASE WHEN pt.amount_cents < 0 THEN pt.amount_cents ELSE 0 END) / 100.0, 0) AS deductions,
            0.0 AS masse_employeur,
            CASE 
                WHEN COUNT(DISTINCT pt.employee_id) > 0
                THEN (SUM(pt.amount_cents) / 100.0) / COUNT(DISTINCT pt.employee_id)
                ELSE 0
            END AS net_moyen,
            COUNT(DISTINCT pt.employee_id) AS nb_employes,
            COUNT(*) AS nb_transactions
        FROM payroll.payroll_transactions pt
        WHERE pt.pay_date = %(pay_date)s::date
        """

        result = self.repo.run_query(sql, {"pay_date": pay_date}, fetch_one=True)

        if result:
            return {
                "salaire_net_total": float(
                    result[0] or 0
                ),  # Somme simple de tous les montants
                "masse_salariale": float(result[1] or 0),  # Montants positifs (info)
                "deductions": float(result[2] or 0),  # Montants négatifs (info)
                "masse_employeur": float(result[3] or 0),
                "net_moyen": float(result[4] or 0),
                "nb_employes": int(result[5] or 0),
                "nb_transactions": int(result[6] or 0),
            }
        else:
            return {
                "salaire_net_total": 0.0,
                "masse_salariale": 0.0,
                "deductions": 0.0,
                "masse_employeur": 0.0,
                "net_moyen": 0.0,
                "nb_employes": 0,
                "nb_transactions": 0,
            }

    def _calculate_tables(self, pay_date: str) -> dict[str, Any]:
        """Calcule les KPI tables (listes détaillées)."""
        tables = {}

        # 1. ANOMALIES (nets négatifs)
        tables["anomalies"] = self._get_anomalies(pay_date)

        # 2. TOP CODES PAY
        tables["codes_top"] = self._get_top_pay_codes(pay_date)

        # 3. TOP POSTES BUDGÉTAIRES
        tables["postes_top"] = self._get_top_budget_posts(pay_date)

        # 4. NOUVEAUX CODES (codes apparus cette date de paie mais pas date précédente)
        # Pour l'instant on retourne liste vide (implémentation future)
        tables["nouveaux_codes"] = []

        return tables

    def _get_anomalies(self, pay_date: str, limit: int = 20) -> list[dict]:
        """Récupère les anomalies (nets négatifs, montants suspects)."""
        sql = """
        SELECT 
            COALESCE(e.matricule, pt.employee_id::text) AS matricule,
            COALESCE(e.nom || ' ' || e.prenom, 'N/A') AS nom_prenom,
            COALESCE(pc.label, pt.pay_code) AS code_label,
            pt.amount_cents / 100.0 AS montant,
            pt.pay_date::text AS date_paie,
            'Net négatif' AS type_anomalie
        FROM payroll.payroll_transactions pt
        LEFT JOIN core.employees e ON pt.employee_id = e.employee_id
        LEFT JOIN core.pay_codes pc ON pt.pay_code = pc.pay_code
        WHERE pt.pay_date = %(pay_date)s::date
          AND pt.amount_cents < -100000
        ORDER BY pt.amount_cents ASC
        LIMIT %(limit)s
        """

        result = self.repo.run_query(sql, {"pay_date": pay_date, "limit": limit})

        anomalies = []
        if result:
            for row in result:
                anomalies.append(
                    {
                        "matricule": row[0],
                        "nom": row[1],
                        "code": row[2],
                        "montant": float(row[3] or 0),
                        "date": row[4],
                        "type": row[5],
                    }
                )

        return anomalies

    def _get_top_pay_codes(self, pay_date: str, limit: int = 10) -> list[dict]:
        """Récupère le top N codes de paie par montant."""
        sql = """
        SELECT 
            COALESCE(pc.pay_code, pt.pay_code) AS pay_code,
            COALESCE(pc.label, pt.pay_code) AS label,
            COALESCE(pc.category, 'Inconnu') AS category,
            COUNT(*) AS nb_transactions,
            SUM(pt.amount_cents) / 100.0 AS total_montant
        FROM payroll.payroll_transactions pt
        LEFT JOIN core.pay_codes pc ON pt.pay_code = pc.pay_code
        WHERE pt.pay_date = %(pay_date)s::date
        GROUP BY COALESCE(pc.pay_code, pt.pay_code), COALESCE(pc.label, pt.pay_code), COALESCE(pc.category, 'Inconnu')
        ORDER BY ABS(SUM(pt.amount_cents)) DESC
        LIMIT %(limit)s
        """

        result = self.repo.run_query(sql, {"pay_date": pay_date, "limit": limit})

        codes = []
        if result:
            for row in result:
                codes.append(
                    {
                        "code": row[0],
                        "label": row[1],
                        "category": row[2],
                        "nb_transactions": int(row[3] or 0),
                        "total_montant": float(row[4] or 0),
                    }
                )

        return codes

    def _get_top_budget_posts(self, pay_date: str, limit: int = 10) -> list[dict]:
        """Récupère le top N postes budgétaires par montant."""
        # Note: payroll_transactions n'a pas budget_post_id directement
        # On utilise imported_payroll_master qui a cette information
        # Colonnes réelles: description_poste_budgetaire, montant_employe
        sql = """
        SELECT 
            ipm.poste_budgetaire AS code,
            COALESCE(ipm.description_poste_budgetaire, ipm.poste_budgetaire) AS description,
            COUNT(*) as nb_transactions,
            SUM(ipm.montant_employe) as total_montant
        FROM payroll.imported_payroll_master ipm
        WHERE ipm.date_paie = %(pay_date)s::date
          AND ipm.poste_budgetaire IS NOT NULL
          AND ipm.poste_budgetaire != ''
        GROUP BY ipm.poste_budgetaire, COALESCE(ipm.description_poste_budgetaire, ipm.poste_budgetaire)
        ORDER BY ABS(SUM(ipm.montant_employe)) DESC
        LIMIT %(limit)s
        """

        try:
            result = self.repo.run_query(sql, {"pay_date": pay_date, "limit": limit})
        except Exception as e:
            logger.warning(f"Erreur récupération top postes budgétaires: {e}")
            return []

        postes = []
        if result:
            for row in result:
                postes.append(
                    {
                        "code": row[0],
                        "description": row[1] or "",
                        "nb_transactions": int(row[2] or 0),
                        "total_montant": float(row[3] or 0),
                    }
                )

        return postes

    def _upsert_snapshot(self, pay_date: str, kpi_data: dict) -> None:
        """
        Insert ou update le snapshot KPI dans payroll.kpi_snapshot.

        Args:
            pay_date: Date de paie au format YYYY-MM-DD (ex: '2025-08-28')
            kpi_data: Données KPI (dict qui sera sérialisé en JSONB)
        """
        sql = """
        INSERT INTO payroll.kpi_snapshot (period, data, calculated_at, row_count)
        VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
        ON CONFLICT (period) DO UPDATE SET
            data = EXCLUDED.data,
            calculated_at = EXCLUDED.calculated_at,
            row_count = EXCLUDED.row_count
        """

        row_count = kpi_data.get("cards", {}).get("nb_transactions", 0)

        try:
            self.repo.execute_dml(sql, (pay_date, json.dumps(kpi_data), row_count))
            logger.info(
                f"OK: Snapshot KPI upserted pour {pay_date} ({row_count} transactions)"
            )
        except Exception as e:
            # Si erreur de droits, on log mais on ne fait pas échouer le calcul
            logger.warning(
                f"⚠️ Impossible de sauvegarder snapshot KPI pour {pay_date} (droits insuffisants?): {e}"
            )
            logger.info(
                "Les KPI ont été calculés avec succès mais n'ont pas été sauvegardés dans kpi_snapshot"
            )

    def list_pay_dates_with_snapshots(self) -> list[dict]:
        """
        Liste toutes les dates de paie avec leurs snapshots KPI.

        Returns:
            Liste de dicts avec 'pay_date', 'calculated_at', 'row_count'
        """
        sql = """
        SELECT period, calculated_at, row_count
        FROM payroll.kpi_snapshot
        ORDER BY period DESC
        """

        result = self.repo.run_query(sql)

        pay_dates = []
        if result:
            for row in result:
                pay_dates.append(
                    {
                        "pay_date": row[
                            0
                        ],  # period contient la date de paie YYYY-MM-DD
                        "calculated_at": row[1].isoformat() if row[1] else None,
                        "row_count": int(row[2] or 0),
                    }
                )

        return pay_dates


# ========================================
# HELPER FUNCTIONS
# ========================================


def format_currency(amount: float) -> str:
    """Formate un montant en devise (ex: 1234.56 → '1 234,56 $')."""
    return f"{amount:,.2f} $".replace(",", " ").replace(".", ",")


def format_percent(value: float) -> str:
    """Formate un pourcentage (ex: 0.1234 → '12,34 %')."""
    return f"{value * 100:.2f} %".replace(".", ",")
