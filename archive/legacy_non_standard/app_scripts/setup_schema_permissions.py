#!/usr/bin/env python3
"""
Script pour créer le schéma paie et accorder les droits nécessaires
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


def setup_schema_and_permissions():
    """Crée le schéma paie et accorde les droits nécessaires"""
    try:
        print("🔧 CONFIGURATION DU SCHÉMA ET DES DROITS")
        print("=" * 50)

        with psycopg.connect(DSN) as conn:
            with conn.cursor() as cur:
                # 1. Créer le schéma paie s'il n'existe pas
                print("📁 Création du schéma paie...")
                cur.execute("CREATE SCHEMA IF NOT EXISTS paie")
                print("   ✅ Schéma paie créé")

                # 2. Accorder les droits sur le schéma
                print("🔐 Configuration des droits...")

                # Droits sur le schéma
                cur.execute("GRANT USAGE ON SCHEMA paie TO payroll_app")
                cur.execute("GRANT CREATE ON SCHEMA paie TO payroll_app")
                print("   ✅ Droits sur le schéma accordés")

                # Droits sur les tables existantes
                cur.execute(
                    "GRANT SELECT ON ALL TABLES IN SCHEMA payroll TO payroll_app"
                )
                cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA paie TO payroll_app")
                print("   ✅ Droits de lecture accordés")

                # Droits par défaut pour les futures tables
                cur.execute(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA paie GRANT SELECT ON TABLES TO payroll_app"
                )
                cur.execute(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA payroll GRANT SELECT ON TABLES TO payroll_app"
                )
                print("   ✅ Droits par défaut configurés")

                conn.commit()

                # 3. Vérifier que le schéma existe
                cur.execute(
                    """
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name = 'paie'
                """
                )

                schema_exists = cur.fetchone()
                if schema_exists:
                    print("   ✅ Schéma paie vérifié")
                else:
                    print("   ❌ Schéma paie non trouvé")
                    return False

                return True

    except Exception as e:
        print(f"❌ Erreur lors de la configuration: {e}")
        return False


def main():
    """Fonction principale"""
    success = setup_schema_and_permissions()

    if success:
        print("\n🎉 CONFIGURATION TERMINÉE AVEC SUCCÈS")
        print("✅ Schéma paie créé")
        print("✅ Droits accordés à payroll_app")
        print("✅ Configuration prête pour l'harmonisation")
        return 0
    else:
        print("\n❌ ÉCHEC DE LA CONFIGURATION")
        print("🔧 Vérifiez les droits de l'utilisateur payroll_app")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
