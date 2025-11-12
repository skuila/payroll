"""
ARCHIVE: Provider hybride (legacy)

Ce fichier est conservé à titre historique dans `app/tests/legacy/providers/`.
Il contient l'implémentation antérieure du provider hybride qui utilisait
un fallback et un mode offline. Cette implémentation a été retirée du
chemin d'exécution principal pour forcer l'utilisation exclusive de
PostgresProvider (psycopg/DSN strict).

Ne pas importer ce module dans le code actif. Pour restaurer, copier le
contenu dans `app/providers/hybrid_provider.py` (risque: démarrage avec
fallback non souhaité).
"""

"""
Provider hybride permanent - Utilise les vraies données avec fallback intelligent
Source de vérité unique avec données réelles garanties
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import psycopg
from psycopg import OperationalError

logger = logging.getLogger(__name__)


def _get_default_dsn():
    """DSN par défaut depuis config centralisée"""
    from config.config_manager import get_dsn

    return get_dsn()


def _get_dsn() -> str:
    """
    Retourne le DSN PostgreSQL à utiliser pour le provider hybride.
    Priorité: PAYROLL_DSN > DATABASE_URL > valeur par défaut.
    """
    return os.getenv("PAYROLL_DSN") or os.getenv("DATABASE_URL") or _get_default_dsn()


class HybridDataProvider:
    """Provider hybride permanent avec vraies données garanties"""

    def __init__(self):
        self.real_data_cache = {}
        self._load_real_data()

    def _load_real_data(self):
        """Charge les vraies données depuis la base"""
        # Mode hors ligne explicite
        if os.getenv("PAYROLL_FORCE_OFFLINE") == "1":
            logger.warning(
                "PAYROLL_FORCE_OFFLINE=1 → HybridDataProvider en mode hors-ligne."
            )
            self._set_default_data()
            return

        dsn = _get_dsn()
        try:
            with psycopg.connect(dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT 
                            COALESCE(SUM(amount_cents), 0) / 100.0 AS total_amount,
                            COUNT(DISTINCT employee_id) AS nb_employes,
                            COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
                            COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 AS deductions
                        FROM payroll.payroll_transactions
                        WHERE pay_date = '2025-08-28'::date
                        """
                    )
                    row = cur.fetchone()

            if row:
                total_amount = float(row[0] or 0)
                nb_employes = int(row[1] or 0)
                gains_brut = float(row[2] or 0)
                deductions = float(row[3] or 0)

                self.real_data_cache = {
                    "masse_salariale": gains_brut,
                    "nb_employes": nb_employes,
                    "deductions": deductions,
                    "net_moyen": total_amount / nb_employes if nb_employes > 0 else 0,
                    "total_amount": total_amount,
                    "last_updated": datetime.now().isoformat(),
                }

                logger.info("Vraies données chargées: %s", self.real_data_cache)
            else:
                logger.warning("Aucune donnée trouvée dans la base")
                self._set_default_data()

        except OperationalError as e:
            logger.warning(
                "HybridDataProvider: connexion PostgreSQL impossible (%s)", e
            )
            self._set_default_data()
        except Exception as e:
            logger.error("Erreur chargement données: %s", e, exc_info=True)
            self._set_default_data()

    def _set_default_data(self):
        """Données par défaut si erreur"""
        self.real_data_cache = {
            "masse_salariale": 0,
            "nb_employes": 0,
            "deductions": 0,
            "net_moyen": 0,
            "total_amount": 0,
            "last_updated": datetime.now().isoformat(),
        }

    def get_kpis(self, period: Optional[str] = None) -> Dict[str, Any]:
        """Retourne les KPIs avec les vraies données"""
        try:
            # Utiliser les vraies données avec la période demandée
            kpis = self.real_data_cache.copy()
            kpis["period"] = period or "2025-08-28"
            kpis["source"] = "Hybrid_Real_Data"

            logger.info(f"KPIs retournés: {kpis}")
            return kpis

        except Exception as e:
            logger.error(f"Erreur get_kpis: {e}")
            return self._get_fallback_kpis(period)

    def _get_fallback_kpis(self, period: Optional[str] = None) -> Dict[str, Any]:
        """KPIs de fallback en cas d'erreur"""
        return {
            "masse_salariale": 0,
            "nb_employes": 0,
            "deductions": 0,
            "net_moyen": 0,
            "period": period or "N/A",
            "source": "Fallback",
        }

    def refresh_data(self):
        """Rafraîchit les données depuis la base"""
        logger.info("Rafraîchissement des données...")
        self._load_real_data()

    def get_data_info(self) -> Dict[str, Any]:
        """Retourne les informations sur les données"""
        return {
            "cache_size": len(self.real_data_cache),
            "last_updated": self.real_data_cache.get("last_updated"),
            "source": "Hybrid_Real_Data",
            "status": "Active",
        }


# Instance globale permanente
hybrid_provider = HybridDataProvider()


def get_hybrid_provider() -> HybridDataProvider:
    """Retourne l'instance du provider hybride"""
    return hybrid_provider
