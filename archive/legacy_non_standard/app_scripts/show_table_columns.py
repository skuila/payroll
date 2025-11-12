import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

schema = os.getenv("TEST_SCHEMA", "public")
table = os.getenv("TEST_TABLE", "")
if not table:
    print("[ERROR] Please set TEST_TABLE to the target table name")
    sys.exit(2)

try:
    from app.providers.postgres_provider import PostgresProvider
    from app.services.schema_editor import get_schema_editor
except Exception as e:
    print("[ERROR] Import failed:", e)
    sys.exit(1)

provider = PostgresProvider()
if not provider or not provider.repo:
    print("[ERROR] Provider repo not available (need DB connection)")
    sys.exit(3)

se = get_schema_editor(provider)
cols = se.get_table_columns(schema, table)
print(
    json.dumps(
        {"schema": schema, "table": table, "columns": cols},
        ensure_ascii=False,
        indent=2,
    )
)
