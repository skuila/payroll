#!/usr/bin/env python3
"""Reset passwords for payroll DB users via postgres superuser.

This script will set a unified password for the main DB roles.
It prefers the environment variable NEW_DB_PASSWORD, otherwise defaults to 'aq456*456'.
It also accepts SUPER_DSN env var to connect as superuser; otherwise it will try a reasonable fallback.
"""
import os
import sys
import psycopg
from psycopg import sql

NEW_PW = (
    os.getenv("NEW_DB_PASSWORD")
    or os.getenv("PAYROLL_DB_PASSWORD")
    or os.getenv("PGPASSWORD")
)
SUPER_DSN = os.getenv("SUPER_DSN")

# If SUPER_DSN not provided, we'll connect using individual params and password
# The superuser password will be read from SUPER_DB_PASSWORD or fallback to PAYROLL_DB_PASSWORD
SUPER_DB_PW = (
    os.getenv("SUPER_DB_PASSWORD")
    or os.getenv("PAYROLL_DB_PASSWORD")
    or os.getenv("PGPASSWORD")
)
SUPER_HOST = os.getenv("PAYROLL_DB_HOST", "localhost")
SUPER_PORT = os.getenv("PAYROLL_DB_PORT", "5432")
SUPER_DB = os.getenv("PAYROLL_DB_NAME", "payroll_db")
SUPER_USER = os.getenv("SUPER_DB_USER", "postgres")

print(
    "Réinitialisation des mots de passe DB... (ne pas exposer les mots de passe dans les logs)"
)

try:
    if SUPER_DSN:
        conn = psycopg.connect(SUPER_DSN, autocommit=True)
    else:
        # Use explicit parameters and password from env
        conn = psycopg.connect(
            user=SUPER_USER,
            host=SUPER_HOST,
            port=SUPER_PORT,
            dbname=SUPER_DB,
            password=SUPER_DB_PW,
            autocommit=True,
        )
except Exception as e:
    print(f"❌ Impossible de se connecter en superuser avec le DSN fourni: {e}")
    sys.exit(1)

cur = conn.cursor()

# Roles to update
roles = ["payroll_unified", "payroll_app", "payroll_owner"]
for r in roles:
    try:
        stmt = sql.SQL("ALTER USER {} WITH PASSWORD {};").format(
            sql.Identifier(r), sql.Literal(NEW_PW)
        )
        cur.execute(stmt)
        print(f"OK: Mot de passe mis à jour pour {r}")
    except Exception as e:
        print(f"WARN: Erreur mise à jour {r}: {e}")

conn.close()
print("Opération terminée. Vérifiez les logs DB si nécessaire.")
