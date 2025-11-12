#!/usr/bin/env python3
"""Run a single CREATE VIEW statement extracted from admin_create_kpi_views.sql
This helper extracts the CREATE OR REPLACE VIEW paie.v_kpi_periode AS ...; block
and runs it with the superuser DSN to diagnose errors cleanly.
"""
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config_manager import get_superuser_dsn
import psycopg

sql_file = Path(__file__).parent / "admin_create_kpi_views.sql"
if not sql_file.exists():
    print(f"File not found: {sql_file}")
    sys.exit(2)

content = sql_file.read_text(encoding="utf-8")
needle = "CREATE OR REPLACE VIEW paie.v_kpi_periode AS"
pos = content.find(needle)
if pos == -1:
    print("CREATE block not found")
    sys.exit(2)

# find the terminating semicolon for this statement
endpos = content.find(";", pos)
if endpos == -1:
    print("Terminating semicolon not found")
    sys.exit(2)

statement = content[pos : endpos + 1]
print("--- Executing extracted CREATE VIEW statement (truncated) ---")
print(statement[:400])

dsn = get_superuser_dsn()
try:
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(statement)
            conn.commit()
    print("OK: statement executed and committed")
    sys.exit(0)
except Exception as e:
    print("ERROR executing statement:\n", e)
    sys.exit(3)
