#!/usr/bin/env python3
"""
Script pour vérifier la structure de la table payroll_transactions
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


def check_table_structure():
    """Vérifie la structure de la table payroll_transactions"""
    try:
        print("🔍 VÉRIFICATION DE LA STRUCTURE DE LA TABLE")
        print("=" * 50)

        with psycopg.connect(DSN) as conn:
            with conn.cursor() as cur:
                # Vérifier l'existence de la table
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'payroll' 
                        AND table_name = 'payroll_transactions'
                    )
                """
                )

                table_exists = cur.fetchone()[0]

                if not table_exists:
                    print("❌ Table payroll.payroll_transactions n'existe pas")
                    return False

                print("✅ Table payroll.payroll_transactions existe")

                # Récupérer la structure de la table
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_schema = 'payroll' 
                    AND table_name = 'payroll_transactions'
                    ORDER BY ordinal_position
                """
                )

                columns = cur.fetchall()

                print(f"\n📊 Structure de la table ({len(columns)} colonnes):")
                for col_name, data_type, nullable, default in columns:
                    nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"   - {col_name}: {data_type} {nullable_str}{default_str}")

                # Vérifier les colonnes spécifiques nécessaires
                required_columns = [
                    "employee_id",
                    "pay_date",
                    "amount_cents",
                    "code_paie",
                ]
                missing_columns = []

                existing_columns = [col[0] for col in columns]

                print(f"\n🔍 Vérification des colonnes requises:")
                for req_col in required_columns:
                    if req_col in existing_columns:
                        print(f"   ✅ {req_col}")
                    else:
                        print(f"   ❌ {req_col} - MANQUANTE")
                        missing_columns.append(req_col)

                # Vérifier les données
                cur.execute("SELECT COUNT(*) FROM payroll.payroll_transactions")
                count = cur.fetchone()[0]
                print(f"\n📈 Nombre de lignes: {count}")

                if count > 0:
                    # Échantillon de données
                    cur.execute("SELECT * FROM payroll.payroll_transactions LIMIT 3")
                    sample = cur.fetchall()

                    print(f"\n📋 Échantillon de données:")
                    for i, row in enumerate(sample, 1):
                        print(f"   Ligne {i}: {row}")

                return len(missing_columns) == 0

    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False


def main():
    """Fonction principale"""
    success = check_table_structure()

    if success:
        print("\n✅ Structure de la table correcte")
        return 0
    else:
        print("\n❌ Structure de la table incorrecte")
        print("🔧 Des colonnes sont manquantes")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
