#!/usr/bin/env python3
"""
Script pour vérifier les vues existantes et adapter l'API
"""

import sys
import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Propagate PAYROLL_DB_PASSWORD into PGPASSWORD for libpq/psycopg compatibility
try:
    if os.getenv("PAYROLL_DB_PASSWORD") and not os.getenv("PGPASSWORD"):
        os.environ["PGPASSWORD"] = os.getenv("PAYROLL_DB_PASSWORD")
except Exception:
    pass

# Configuration de connexion
from config.config_manager import get_dsn

DSN = get_dsn()


def check_existing_views():
    """Vérifie les vues existantes"""
    try:
        print("🔍 VÉRIFICATION DES VUES EXISTANTES")
        print("=" * 50)

        with psycopg.connect(DSN) as conn:
            with conn.cursor() as cur:
                # Vérifier toutes les vues disponibles
                cur.execute(
                    """
                    SELECT table_schema, table_name, table_type
                    FROM information_schema.tables 
                    WHERE table_type = 'VIEW'
                    ORDER BY table_schema, table_name
                """
                )

                views = cur.fetchall()

                print(f"📊 Vues disponibles ({len(views)}):")
                for schema, name, table_type in views:
                    print(f"   {schema}.{name}")

                # Vérifier les vues KPI spécifiques
                kpi_views = [v for v in views if "kpi" in v[1].lower()]

                print(f"\n📈 Vues KPI trouvées ({len(kpi_views)}):")
                for schema, name, table_type in kpi_views:
                    print(f"   ✅ {schema}.{name}")

                # Vérifier les tables disponibles
                cur.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables 
                    WHERE table_type = 'BASE TABLE'
                    AND table_schema IN ('payroll', 'public')
                    ORDER BY table_schema, table_name
                """
                )

                tables = cur.fetchall()

                print(f"\n📋 Tables disponibles ({len(tables)}):")
                for schema, name in tables:
                    print(f"   {schema}.{name}")

                # Test direct sur la table principale
                print(f"\n🧪 Test direct sur payroll.payroll_transactions:")
                cur.execute(
                    """
                    SELECT 
                        TO_CHAR(pay_date, 'YYYY-MM') as periode,
                        COUNT(*) as nb_lignes,
                        COUNT(DISTINCT employee_id) as nb_employes,
                        SUM(amount_cents) / 100.0 as total_amount
                    FROM payroll.payroll_transactions
                    GROUP BY TO_CHAR(pay_date, 'YYYY-MM')
                    ORDER BY periode
                    LIMIT 5
                """
                )

                results = cur.fetchall()
                print(f"   📊 Données par période:")
                for row in results:
                    print(
                        f"      {row[0]}: {row[1]} lignes, {row[2]} employés, {row[3]:,.2f}€"
                    )

                return len(kpi_views) > 0

    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False


def main():
    """Fonction principale"""
    success = check_existing_views()

    if success:
        print("\n✅ VUES KPI DISPONIBLES")
        print("🎯 L'API peut utiliser les vues existantes")
        return 0
    else:
        print("\nWARN:  AUCUNE VUE KPI TROUVÉE")
        print("🔧 L'API devra utiliser des requêtes directes")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
