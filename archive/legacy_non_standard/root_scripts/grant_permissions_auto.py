#!/usr/bin/env python3
"""Accorde automatiquement les permissions DELETE à payroll_unified"""

import os
import psycopg

print("=" * 70)
print("ACCORD DES PERMISSIONS DELETE")
print("=" * 70)
print()

# Utiliser les credentials postgres depuis l'environnement ou demander
pg_password = os.getenv("POSTGRES_PASSWORD", "aq456*456")  # Mot de passe par défaut

try:
    # Se connecter en tant que postgres (superuser)
    dsn = f"postgresql://postgres:{pg_password}@localhost:5432/payroll_db"

    print("🔄 Connexion en tant que postgres...")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            print("✅ Connecté")
            print()

            # Accorder DELETE sur core.employees
            print("🔧 Accord des permissions DELETE sur core.employees...")
            cur.execute("GRANT DELETE ON TABLE core.employees TO payroll_unified")
            conn.commit()
            print("✅ DELETE accordé sur core.employees")

            # Accorder DELETE sur payroll.pay_periods
            print("🔧 Accord des permissions DELETE sur payroll.pay_periods...")
            cur.execute("GRANT DELETE ON TABLE payroll.pay_periods TO payroll_unified")
            conn.commit()
            print("✅ DELETE accordé sur payroll.pay_periods")

            # Vérifier les permissions
            print()
            print("📋 Vérification des permissions:")
            cur.execute(
                """
                SELECT table_schema, table_name, privilege_type
                FROM information_schema.table_privileges
                WHERE grantee = 'payroll_unified'
                AND privilege_type = 'DELETE'
                ORDER BY table_schema, table_name
            """
            )

            for row in cur.fetchall():
                print(f"  ✅ {row[0]}.{row[1]} : {row[2]}")

    print()
    print("=" * 70)
    print("✅ PERMISSIONS ACCORDÉES AVEC SUCCÈS")
    print("=" * 70)

except Exception as e:
    print(f"❌ Erreur: {e}")
    print()
    print("💡 Si l'erreur est liée au mot de passe postgres:")
    print("   Modifiez pg_password dans le script ou définissez POSTGRES_PASSWORD")
    print()
    print("=" * 70)
    print("❌ ÉCHEC")
    print("=" * 70)
