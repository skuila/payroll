# logic/db_optimizer.py - Optimiseur de base de données PostgreSQL pour KPI
"""
Optimisation de la base de données PostgreSQL:
- Vérification des index pour améliorer les performances
- Accès au cache KPI dans payroll.kpi_snapshot
- Note: Les index sont gérés par les migrations SQL, ce module vérifie leur existence
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Import DataRepository pour PostgreSQL
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.data_repo import DataRepository


class DatabaseOptimizer:
    """Optimiseur de base de données PostgreSQL pour le système KPI"""

    def __init__(self, dsn: Optional[str] = None):
        """Initialise avec DSN PostgreSQL."""

    # Do not hardcode passwords; prefer PAYROLL_DSN and PAYROLL_DB_PASSWORD
    self.dsn = (
        dsn
        or os.getenv("PAYROLL_DSN")
        or os.getenv("DATABASE_URL")
        or "postgresql://payroll_app@localhost:5432/payroll_db"
    )

    def _get_repo(self) -> DataRepository:
        """Retourne une instance DataRepository."""
        return DataRepository(self.dsn, min_size=1, max_size=3)

    def create_indexes(self):
        """
        Vérifie les index PostgreSQL existants.
        Note: Les index sont gérés par les migrations DDL.
        Cette méthode vérifie uniquement leur existence.
        """
        repo = self._get_repo()
        try:
            # Vérifier si la table payroll_transactions existe (table partitionnée)
            rows = repo.run_query(
                """
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'payroll' AND tablename = 'payroll_transactions'
            """,
                fetch_all=True,
            )

            if not rows:
                print("⚠️ Table payroll.payroll_transactions non trouvée")
                print("   Vérifiez que les migrations DDL ont été appliquées")
                return

            # Lister les index existants sur payroll_transactions
            index_rows = repo.run_query(
                """
                SELECT indexname FROM pg_indexes 
                WHERE schemaname = 'payroll' 
                AND tablename LIKE 'payroll_transactions%'
                ORDER BY indexname
            """,
                fetch_all=True,
            )

            if index_rows:
                print("✓ Index PostgreSQL existants:")
                for (idx_name,) in index_rows[:10]:  # Limiter l'affichage
                    print(f"  - {idx_name}")
                if len(index_rows) > 10:
                    print(f"  ... et {len(index_rows) - 10} autres")
            else:
                print("⚠️ Aucun index trouvé sur payroll_transactions")

        except Exception as e:
            print(f"Erreur lors de la vérification des index: {e}")
        finally:
            repo.close()

    def create_cache_table(self):
        """
        Vérifie l'existence de la table payroll.kpi_snapshot.
        Note: Cette table est créée par les migrations DDL.
        """
        repo = self._get_repo()
        try:
            rows = repo.run_query(
                """
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'payroll' AND tablename = 'kpi_snapshot'
            """,
                fetch_all=True,
            )

            if rows:
                print("✓ Table payroll.kpi_snapshot existe")
            else:
                print("⚠️ Table payroll.kpi_snapshot non trouvée")
                print("   Vérifiez que les migrations DDL ont été appliquées")

        except Exception as e:
            print(f"Erreur lors de la vérification de kpi_snapshot: {e}")
        finally:
            repo.close()

    def save_kpi_cache(self, period: str, kpi_data: Dict[str, Any]):
        """
        Sauvegarde les KPI dans payroll.kpi_snapshot.

        Args:
            period: Période au format YYYY-MM
            kpi_data: Dictionnaire avec tous les KPI
        """
        repo = self._get_repo()
        try:
            with repo.get_connection() as conn:
                conn.autocommit = False
                with conn.cursor() as cur:
                    # Générer un UUID pour period_id si nécessaire
                    import uuid

                    period_id = str(uuid.uuid4())
                    timestamp = datetime.now()

                    # PostgreSQL: INSERT ... ON CONFLICT DO UPDATE
                    cur.execute(
                        """
                        INSERT INTO payroll.kpi_snapshot (period, period_id, data, calculated_at, row_count)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (period) DO UPDATE SET
                            data = EXCLUDED.data,
                            calculated_at = EXCLUDED.calculated_at,
                            row_count = EXCLUDED.row_count
                    """,
                        (
                            period,
                            period_id,
                            json.dumps(kpi_data),
                            timestamp,
                            kpi_data.get("nb_employes", 0),
                        ),
                    )
                    conn.commit()

        except Exception as e:
            print(f"Erreur lors de la sauvegarde du cache: {e}")
        finally:
            repo.close()

    def get_kpi_cache(self, period: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les KPI depuis payroll.kpi_snapshot.

        Args:
            period: Période au format YYYY-MM

        Returns:
            Dict avec les KPI ou None si pas en cache
        """
        repo = self._get_repo()
        try:
            row = repo.run_query(
                """
                SELECT data, calculated_at FROM payroll.kpi_snapshot
                WHERE period = %s
            """,
                (period,),
                fetch_one=True,
            )

            if row:
                kpi_json, calc_at = row
                kpi_data = (
                    json.loads(kpi_json) if isinstance(kpi_json, str) else kpi_json
                )

                # Vérifier si le cache est récent (< 1 heure)
                age_hours = (datetime.now() - calc_at).total_seconds() / 3600

                if age_hours < 1.0:
                    return kpi_data
                else:
                    print(f"Cache expiré pour {period} (âge: {age_hours:.1f}h)")
                    return None

            return None

        except Exception as e:
            print(f"Erreur lors de la lecture du cache: {e}")
            return None
        finally:
            repo.close()

    def invalidate_cache(self, period: Optional[str] = None):
        """
        Invalide le cache dans payroll.kpi_snapshot.

        Args:
            period: Période spécifique à invalider (None = tout le cache)
        """
        repo = self._get_repo()
        try:
            with repo.get_connection() as conn:
                conn.autocommit = False
                with conn.cursor() as cur:
                    if period:
                        cur.execute(
                            "DELETE FROM payroll.kpi_snapshot WHERE period = %s",
                            (period,),
                        )
                        print(f"✓ Cache invalidé pour la période {period}")
                    else:
                        cur.execute("DELETE FROM payroll.kpi_snapshot")
                        print("✓ Tout le cache a été invalidé")
                    conn.commit()

        except Exception as e:
            print(f"Erreur lors de l'invalidation du cache: {e}")
        finally:
            repo.close()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Récupère des statistiques sur payroll.kpi_snapshot.

        Returns:
            Dict avec nombre d'entrées, plus ancienne, plus récente
        """
        repo = self._get_repo()
        try:
            # Vérifier si la table existe
            rows = repo.run_query(
                """
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'payroll' AND tablename = 'kpi_snapshot'
            """,
                fetch_all=True,
            )

            if not rows:
                return {"count": 0, "oldest": None, "newest": None}

            row = repo.run_query(
                """
                SELECT 
                    COUNT(*) as count,
                    MIN(calculated_at) as oldest,
                    MAX(calculated_at) as newest
                FROM payroll.kpi_snapshot
            """,
                fetch_one=True,
            )

            if row:
                return {
                    "count": row[0],
                    "oldest": row[1].isoformat() if row[1] else None,
                    "newest": row[2].isoformat() if row[2] else None,
                }

            return {"count": 0, "oldest": None, "newest": None}

        except Exception as e:
            print(f"Erreur lors de la récupération des stats: {e}")
            return {"count": 0, "oldest": None, "newest": None}
        finally:
            repo.close()

    def optimize_database(self):
        """Lance l'optimisation complète de la base de données PostgreSQL"""
        print("🔧 Optimisation de la base de données PostgreSQL...")

        # Vérifier les index
        self.create_indexes()

        # Vérifier la table de cache
        self.create_cache_table()

        # Lancer ANALYZE sur les tables principales (PostgreSQL)
        repo = self._get_repo()
        try:
            with repo.get_connection() as conn:
                conn.autocommit = False
                with conn.cursor() as cur:
                    cur.execute("ANALYZE payroll.payroll_transactions")
                    cur.execute("ANALYZE payroll.imported_payroll_master")
                    cur.execute("ANALYZE core.employees")
                    conn.commit()
            print("✓ Analyse PostgreSQL (ANALYZE) complétée")
        except Exception as e:
            print(f"Erreur lors de l'analyse: {e}")
        finally:
            repo.close()

        print("✅ Optimisation terminée !")


# Instance globale
_optimizer_instance: Optional[DatabaseOptimizer] = None


def get_optimizer() -> DatabaseOptimizer:
    """Retourne l'instance singleton de l'optimiseur"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = DatabaseOptimizer()
    return _optimizer_instance


# API simplifiée
def optimize_database():
    """Lance l'optimisation de la base de données"""
    get_optimizer().optimize_database()


def invalidate_kpi_cache(period: Optional[str] = None):
    """Invalide le cache des KPI"""
    get_optimizer().invalidate_cache(period)


if __name__ == "__main__":
    # Test de l'optimisation
    print("Test de l'optimiseur de base de données")
    optimizer = DatabaseOptimizer()
    optimizer.optimize_database()

    # Afficher les stats du cache
    stats = optimizer.get_cache_stats()
    print("\nStats du cache:")
    print(f"  - Entrées: {stats['count']}")
    print(f"  - Plus ancienne: {stats['oldest']}")
    print(f"  - Plus récente: {stats['newest']}")
