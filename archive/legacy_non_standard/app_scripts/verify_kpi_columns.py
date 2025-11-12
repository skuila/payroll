#!/usr/bin/env python3
"""
Script de vérification des colonnes dans toutes les vues v_kpi_*
Vérifie que toutes les vues respectent le contrat de colonnes harmonisé.
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

# Configuration de connexion — éviter les secrets en dur
DSN = (
    os.getenv("DATABASE_URL")
    or os.getenv("PAYROLL_DSN")
    or (
        f"postgresql://{os.getenv('PAYROLL_DB_USER','payroll_app')}:"
        f"{os.getenv('PAYROLL_DB_PASSWORD','__SET_AT_DEPLOY__')}@"
        f"{os.getenv('PAYROLL_DB_HOST','localhost')}:{os.getenv('PAYROLL_DB_PORT','5432')}/"
        f"{os.getenv('PAYROLL_DB_NAME','payroll_db')}"
    )
)

if "__SET_AT_DEPLOY__" in DSN:
    print(
        "WARNING: PAYROLL_DB_PASSWORD non configuré dans l'environnement — vérifiez .env ou variables CI"
    )

# Contrat de colonnes obligatoires
REQUIRED_COLUMNS = [
    "periode",
    "gains_brut",
    "deductions_net",
    "net_a_payer",
    "part_employeur",
    "cout_total",
    "cash_out_total",
    "nb_employes",
    "ajustements_gains",
    "deductions_brutes",
    "remboursements",
]

# Vues à vérifier
KPI_VIEWS = [
    "paie.v_kpi_periode",
    "paie.v_kpi_par_categorie_emploi",
    "paie.v_kpi_par_code_paie",
    "paie.v_kpi_par_poste_budgetaire",
    "paie.v_kpi_par_employe_periode",
    "paie.v_kpi_temps_mensuel",
    "paie.v_kpi_temps_annuel",
]


def check_view_columns(conn, view_name):
    """Vérifie les colonnes d'une vue spécifique"""
    try:
        with conn.cursor() as cur:
            # Récupérer les colonnes de la vue
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """,
                (view_name.split(".")[0], view_name.split(".")[1]),
            )

            columns = {
                row[0]: {"type": row[1], "nullable": row[2]} for row in cur.fetchall()
            }

            print(f"\n📊 Vérification de {view_name}:")
            print(f"   Colonnes trouvées: {len(columns)}")

            # Vérifier les colonnes obligatoires
            missing_columns = []
            for col in REQUIRED_COLUMNS:
                if col not in columns:
                    missing_columns.append(col)
                else:
                    print(f"   ✅ {col}: {columns[col]['type']}")

            if missing_columns:
                print(f"   ❌ Colonnes manquantes: {missing_columns}")
                return False
            else:
                print(f"   ✅ Toutes les colonnes obligatoires présentes")
                return True

    except Exception as e:
        print(f"   ❌ Erreur lors de la vérification: {e}")
        return False


def check_view_data_sample(conn, view_name):
    """Vérifie qu'il y a des données dans la vue"""
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {view_name}")
            count = cur.fetchone()[0]

            if count > 0:
                print(f"   ✅ Données présentes: {count} lignes")
                return True
            else:
                print(f"   WARN:  Aucune donnée dans la vue")
                return False

    except Exception as e:
        print(f"   ❌ Erreur lors du comptage: {e}")
        return False


def check_view_periods(conn, view_name):
    """Vérifie les périodes disponibles dans la vue"""
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT 
                    MIN(periode) as periode_min,
                    MAX(periode) as periode_max,
                    COUNT(DISTINCT periode) as nb_periodes
                FROM {view_name}
            """
            )

            result = cur.fetchone()
            if result and result[0]:
                print(
                    f"   📅 Périodes: {result[0]} → {result[1]} ({result[2]} périodes)"
                )
                return True
            else:
                print(f"   WARN:  Aucune période trouvée")
                return False

    except Exception as e:
        print(f"   ❌ Erreur lors de la vérification des périodes: {e}")
        return False


def main():
    """Fonction principale de vérification"""
    print("🔍 VÉRIFICATION DES VUES KPI - CONTRAT DE COLONNES")
    print("=" * 60)

    try:
        with psycopg.connect(DSN) as conn:
            print(f"✅ Connexion à la base de données réussie")

            all_views_ok = True

            for view_name in KPI_VIEWS:
                # Vérifier l'existence de la vue
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.views 
                            WHERE table_schema = %s AND table_name = %s
                        )
                    """,
                        (view_name.split(".")[0], view_name.split(".")[1]),
                    )

                    if not cur.fetchone()[0]:
                        print(f"\n❌ Vue {view_name} n'existe pas")
                        all_views_ok = False
                        continue

                # Vérifier les colonnes
                columns_ok = check_view_columns(conn, view_name)

                # Vérifier les données
                data_ok = check_view_data_sample(conn, view_name)

                # Vérifier les périodes
                periods_ok = check_view_periods(conn, view_name)

                if not (columns_ok and data_ok and periods_ok):
                    all_views_ok = False

            print("\n" + "=" * 60)
            if all_views_ok:
                print("🎉 TOUTES LES VUES RESPECTENT LE CONTRAT DE COLONNES")
                print("✅ Système KPI harmonisé et opérationnel")
                return 0
            else:
                print("❌ CERTAINES VUES NE RESPECTENT PAS LE CONTRAT")
                print("🔧 Exécutez le script harmonize_kpi_views.sql pour corriger")
                return 1

    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
