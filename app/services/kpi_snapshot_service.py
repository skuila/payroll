"""
KPI Snapshot Service: Calcul, invalidation et récupération des KPI par période

Responsabilités:
- Calculer les KPI pour une période donnée depuis payroll_transactions
- Stocker les KPI dans kpi_snapshot (JSONB)
- Invalider (recalculer) les KPI après import
- Fournir les KPI pour l'UI (cartes + tables)

Usage:
    service = KPISnapshotService(repo)
    service.invalidate_and_recalc_kpi('2025-01')
    kpi = service.get_kpi('2025-01')
"""

import logging
import json
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

    def invalidate_and_recalc_kpi(self, period: str) -> dict[str, Any]:
        """
        Invalide et recalcule les KPI pour une période donnée.

        Étapes:
        1. Calculer les KPI depuis payroll_transactions
        2. Supprimer l'ancien snapshot (si existe)
        3. Insérer le nouveau snapshot

        Args:
            period: Période au format YYYY-MM (ex: '2025-01')

        Returns:
            dict avec les KPI calculés
        """
        logger.info(f"Invalidation + recalcul KPI pour période: {period}")

        try:
            # 1. Calculer les KPI
            kpi_data = self._calculate_kpi(period)

            # 2. Upsert dans kpi_snapshot
            self._upsert_snapshot(period, kpi_data)

            logger.info(
                f"OK: KPI recalculés pour {period}: {kpi_data.get('cards', {}).get('nb_employes', 0)} employés"
            )
            return kpi_data

        except Exception as e:
            logger.error(f"Erreur recalcul KPI période {period}: {e}")
            raise

    def get_kpi(self, period: str) -> dict[str, Any]:
        """
        Récupère les KPI pour une période depuis le snapshot.
        Si snapshot inexistant, calcule à la volée.

        Args:
            period: Période au format YYYY-MM (ex: '2025-01')

        Returns:
            dict avec structure:
            {
                "cards": {...},        # KPI cartes (masse salariale, nb employés, etc.)
                "tables": {...},       # KPI tables (anomalies, codes, postes)
                "period": "2025-01",
                "calculated_at": "2025-10-12T14:30:00Z"
            }
        """
        logger.info(f"Récupération KPI pour période: {period}")

        try:
            # Lire le snapshot
            sql = """
            SELECT data, calculated_at
            FROM payroll.kpi_snapshot
            WHERE period = %(period)s
            """
            result = self.repo.run_query(sql, {"period": period}, fetch_one=True)

            if result:
                data = result[0]
                calculated_at = result[1]
                data["calculated_at"] = (
                    calculated_at.isoformat() if calculated_at else None
                )
                data["period"] = period
                data["source"] = "snapshot"
                logger.info(
                    f"OK: KPI snapshot trouvé pour {period} (calculé: {calculated_at})"
                )
                return data
            else:
                # Snapshot inexistant → calculer à la volée
                logger.warning(
                    f"Snapshot KPI inexistant pour {period}, calcul à la volée"
                )
                kpi_data = self._calculate_kpi(period)
                kpi_data["source"] = "on_the_fly"
                return kpi_data

        except Exception as e:
            logger.error(f"Erreur récupération KPI période {period}: {e}")
            raise

    # ========================
    # MÉTHODES INTERNES
    # ========================

    def _calculate_kpi(self, period: str) -> dict[str, Any]:
        """
        Calcule les KPI pour une période depuis payroll_transactions.

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
                "nouveaux_codes": [...]  # Codes apparus cette période
            }
        }
        """
        logger.info(f"Calcul KPI période {period}")

        # 1. KPI CARTES (agrégats globaux)
        cards = self._calculate_cards(period)

        # 2. KPI TABLES (listes détaillées)
        tables = self._calculate_tables(period)

        return {"cards": cards, "tables": tables}

    def _calculate_cards(self, period: str) -> dict[str, Any]:
        """Calcule les KPI cartes (agrégats globaux) - LOGIQUE CORRECTE."""
        sql = """
        SELECT 
            -- Salaire net total (somme simple de tous les montants employé)
            COALESCE(SUM(amount_employee_norm_cents) / 100.0, 0) as salaire_net_total,
            
            -- Masse salariale (montants positifs employé) - pour information
            COALESCE(SUM(CASE WHEN amount_employee_norm_cents > 0 THEN amount_employee_norm_cents ELSE 0 END) / 100.0, 0) as masse_salariale,
            
            -- Déductions (montants négatifs employé) - pour information
            COALESCE(SUM(CASE WHEN amount_employee_norm_cents < 0 THEN amount_employee_norm_cents ELSE 0 END) / 100.0, 0) as deductions,
            
            -- Masse employeur
            COALESCE(SUM(amount_employer_norm_cents) / 100.0, 0) as masse_employeur,
            
            -- Net moyen (salaire net total / nb employés)
            CASE 
                WHEN COUNT(DISTINCT employee_id) > 0 
                THEN (SUM(amount_employee_norm_cents) / 100.0) / COUNT(DISTINCT employee_id)
                ELSE 0
            END as net_moyen,
            
            -- Nombre d'employés distincts
            COUNT(DISTINCT employee_id) as nb_employes,
            
            -- Nombre de transactions
            COUNT(*) as nb_transactions
        
        FROM payroll.payroll_transactions pt
        JOIN payroll.pay_periods pp ON pt.period_id = pp.period_id
        WHERE TO_CHAR(pp.pay_date, 'YYYY-MM') = %(period)s
        """

        result = self.repo.run_query(sql, {"period": period}, fetch_one=True)

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

    def _calculate_tables(self, period: str) -> dict[str, Any]:
        """Calcule les KPI tables (listes détaillées)."""
        tables = {}

        # 1. ANOMALIES (nets négatifs)
        tables["anomalies"] = self._get_anomalies(period)

        # 2. TOP CODES PAY
        tables["codes_top"] = self._get_top_pay_codes(period)

        # 3. TOP POSTES BUDGÉTAIRES
        tables["postes_top"] = self._get_top_budget_posts(period)

        # 4. NOUVEAUX CODES (codes apparus cette période mais pas période précédente)
        # Pour l'instant on retourne liste vide (implémentation future)
        tables["nouveaux_codes"] = []

        return tables

    def _get_anomalies(self, period: str, limit: int = 20) -> list[dict]:
        """Récupère les anomalies (nets négatifs, montants suspects)."""
        sql = """
        SELECT 
            e.matricule,
            e.nom || ' ' || e.prenom as nom_prenom,
            pc.label as code_label,
            pt.amount_employee_norm_cents / 100.0 as montant,
            pp.pay_date::text as date_paie,
            'Net négatif' as type_anomalie
        FROM payroll.payroll_transactions pt
        JOIN core.employees e ON pt.employee_id = e.employee_id
        JOIN core.pay_codes pc ON pt.pay_code = pc.pay_code
        JOIN payroll.pay_periods pp ON pt.period_id = pp.period_id
        WHERE TO_CHAR(pp.pay_date, 'YYYY-MM') = %(period)s
          AND pt.amount_employee_norm_cents < -100000  -- < -1000$ (suspect)
        ORDER BY pt.amount_employee_norm_cents ASC
        LIMIT %(limit)s
        """

        result = self.repo.run_query(sql, {"period": period, "limit": limit})

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

    def _get_top_pay_codes(self, period: str, limit: int = 10) -> list[dict]:
        """Récupère le top N codes de paie par montant."""
        sql = """
        SELECT 
            pc.pay_code,
            pc.label,
            pc.category,
            COUNT(*) as nb_transactions,
            SUM(pt.amount_employee_norm_cents) / 100.0 as total_montant
        FROM payroll.payroll_transactions pt
        JOIN core.pay_codes pc ON pt.pay_code = pc.pay_code
        JOIN payroll.pay_periods pp ON pt.period_id = pp.period_id
        WHERE TO_CHAR(pp.pay_date, 'YYYY-MM') = %(period)s
        GROUP BY pc.pay_code, pc.label, pc.category
        ORDER BY ABS(SUM(pt.amount_employee_norm_cents)) DESC
        LIMIT %(limit)s
        """

        result = self.repo.run_query(sql, {"period": period, "limit": limit})

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

    def _get_top_budget_posts(self, period: str, limit: int = 10) -> list[dict]:
        """Récupère le top N postes budgétaires par montant."""
        sql = """
        SELECT 
            bp.code,
            bp.description,
            COUNT(*) as nb_transactions,
            SUM(pt.amount_employee_norm_cents) / 100.0 as total_montant
        FROM payroll.payroll_transactions pt
        JOIN core.budget_posts bp ON pt.budget_post_id = bp.budget_post_id
        JOIN payroll.pay_periods pp ON pt.period_id = pp.period_id
        WHERE TO_CHAR(pp.pay_date, 'YYYY-MM') = %(period)s
        GROUP BY bp.code, bp.description
        ORDER BY ABS(SUM(pt.amount_employee_norm_cents)) DESC
        LIMIT %(limit)s
        """

        result = self.repo.run_query(sql, {"period": period, "limit": limit})

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

    def _upsert_snapshot(self, period: str, kpi_data: dict) -> None:
        """
        Insert ou update le snapshot KPI dans payroll.kpi_snapshot.

        Args:
            period: Période (ex: '2025-01')
            kpi_data: Données KPI (dict qui sera sérialisé en JSONB)
        """
        sql = """
        INSERT INTO payroll.kpi_snapshot (period, data, calculated_at, row_count)
        VALUES (%(period)s, %(data)s, CURRENT_TIMESTAMP, %(row_count)s)
        ON CONFLICT (period) DO UPDATE SET
            data = EXCLUDED.data,
            calculated_at = EXCLUDED.calculated_at,
            row_count = EXCLUDED.row_count
        """

        row_count = kpi_data.get("cards", {}).get("nb_transactions", 0)

        self.repo.execute_dml(
            sql,
            {"period": period, "data": json.dumps(kpi_data), "row_count": row_count},
        )

        logger.info(
            f"OK: Snapshot KPI upserted pour {period} ({row_count} transactions)"
        )

    def list_periods_with_snapshots(self) -> list[dict]:
        """
        Liste toutes les périodes avec leurs snapshots KPI.

        Returns:
            Liste de dicts avec 'period', 'calculated_at', 'row_count'
        """
        sql = """
        SELECT period, calculated_at, row_count
        FROM payroll.kpi_snapshot
        ORDER BY period DESC
        """

        result = self.repo.run_query(sql)

        periods = []
        if result:
            for row in result:
                periods.append(
                    {
                        "period": row[0],
                        "calculated_at": row[1].isoformat() if row[1] else None,
                        "row_count": int(row[2] or 0),
                    }
                )

        return periods


# ========================================
# HELPER FUNCTIONS
# ========================================


def format_currency(amount: float) -> str:
    """Formate un montant en devise (ex: 1234.56 → '1 234,56 $')."""
    return f"{amount:,.2f} $".replace(",", " ").replace(".", ",")


def format_percent(value: float) -> str:
    """Formate un pourcentage (ex: 0.1234 → '12,34 %')."""
    return f"{value * 100:.2f} %".replace(".", ",")
