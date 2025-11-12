#!/usr/bin/env python3
"""Compte les colonnes par table dans les schémas principaux."""
import psycopg

from config.config_manager import get_dsn

DSN = get_dsn()
SCHEMAS = ("core", "payroll", "paie", "security", "reference")

print("=" * 80)
print("COMPTAGE DES CHAMPS (COLONNES) DANS LA BASE")
print("=" * 80)
print("")

try:
    conn = psycopg.connect(DSN, connect_timeout=5)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT table_schema, table_name, COUNT(*) AS column_count
        FROM information_schema.columns
        WHERE table_schema = ANY(%s)
        GROUP BY table_schema, table_name
        ORDER BY table_schema, table_name
    """,
        (list(SCHEMAS),),
    )

    rows = cur.fetchall()

    total_columns = 0
    current_schema = None

    for schema, table, count in rows:
        if schema != current_schema:
            current_schema = schema
            print(f"[{schema}]")
        print(f"  • {table:<35} {count:>3} colonnes")
        total_columns += count

    print("")
    print(f"Total colonnes (schémas {', '.join(SCHEMAS)}): {total_columns}")

    conn.close()
    print("")
    print("Statut : OK")
except Exception as e:
    print("")
    print("Statut : ERREUR")
    print(e)
