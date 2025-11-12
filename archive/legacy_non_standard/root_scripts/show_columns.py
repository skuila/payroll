#!/usr/bin/env python3
"""Affiche les colonnes directement depuis PostgreSQL pour les tables principales."""
import psycopg

from config.config_manager import get_dsn

DSN = get_dsn()
TABLES = [
    ("payroll", "imported_payroll_master"),
    ("payroll", "payroll_transactions"),
    ("paie", "stg_paie_transactions"),
    ("core", "employees"),
]

print("=" * 80)
print("COLONNES (depuis PostgreSQL)")
print("=" * 80)

try:
    conn = psycopg.connect(DSN, connect_timeout=5)
    cur = conn.cursor()

    for schema, table in TABLES:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        rows = cur.fetchall()
        print(f"\n{schema}.{table} ({len(rows)} colonnes)")
        print("-" * 60)
        for column_name, data_type in rows:
            print(f"  • {column_name:<35} {data_type}")

    conn.close()
    print("\nStatut : OK")
except Exception as e:
    print("\nStatut : ERREUR")
    print(e)
