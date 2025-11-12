#!/usr/bin/env python3
"""Vérifier la contrainte CHECK sur status dans import_batches."""
import psycopg
import os

# Build connection from environment variables for security
pg_user = os.getenv("PAYROLL_DB_USER", "payroll_unified")
pg_host = os.getenv("PAYROLL_DB_HOST", "localhost")
pg_port = os.getenv("PAYROLL_DB_PORT", "5432")
pg_db = os.getenv("PAYROLL_DB_NAME", "payroll_db")
pg_pw = os.getenv("PAYROLL_DB_PASSWORD") or os.getenv("PGPASSWORD")

conn = psycopg.connect(
    user=pg_user, host=pg_host, port=pg_port, dbname=pg_db, password=pg_pw
)
cur = conn.cursor()

# Get constraint definition
cur.execute(
    """
    SELECT conname, pg_get_constraintdef(oid) 
    FROM pg_constraint 
    WHERE conrelid = 'payroll.import_batches'::regclass 
    AND conname LIKE '%status%'
"""
)

print("Contraintes de statut sur import_batches:")
print("=" * 70)
for name, definition in cur.fetchall():
    print(f"\nNom: {name}")
    print(f"Définition: {definition}")

conn.close()
