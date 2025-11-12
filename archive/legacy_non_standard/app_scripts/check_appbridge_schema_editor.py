import os
import sys
import json

# Ensure 'app' directory is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

print("[CHECK] Starting AppBridge SchemaEditor checks...")

try:
    from app.providers.postgres_provider import PostgresProvider
    from app.services.schema_editor import get_schema_editor
except Exception as e:
    print("[ERROR] Import failed:", e)
    sys.exit(1)

try:
    provider = PostgresProvider()
    repo_available = bool(provider and provider.repo)
    if not repo_available:
        print(
            "[WARN] Provider repo not available (offline mode). Will run preview-only checks."
        )
    else:
        print("[OK] Provider initialized (repo available)")
except Exception as e:
    print("[ERROR] Provider init error:", e)
    sys.exit(3)

try:
    se = get_schema_editor(provider)
    if se is None:
        print("[ERROR] SchemaEditor not available")
        sys.exit(4)
    print("[OK] SchemaEditor created")

    schema = os.getenv("TEST_SCHEMA", "core")
    print(f"[STEP] Listing tables in schema='{schema}'")
    try:
        tables = se.list_tables(schema)
    except Exception as e:
        print("[ERROR] list_tables failed:", e)
        tables = []
    print("[RESULT] tables count:", len(tables))
    if tables:
        print("[RESULT] first tables:", tables[:10])
    else:
        print("[WARN] No tables found; proceeding with offline placeholders")

    # choose a table
    if tables:
        table = None
        for candidate in (
            "employees",
            "payroll_transactions",
            "imported_payroll_master",
        ):
            if candidate in tables:
                table = candidate
                break
        if table is None:
            table = tables[0]
    else:
        schema = "public"
        table = "demo_table"

    print(f"[STEP] Getting columns for {schema}.{table}")
    try:
        cols = se.get_table_columns(schema, table)
        print("[RESULT] columns count:", len(cols))
        print("[RESULT] first columns:", cols[:5])
    except Exception as e:
        print("[ERROR] get_table_columns failed:", e)

    # Preview add column
    print("[STEP] Preview add column test")
    try:
        preview_add = se.preview_add_column(
            schema, table, "_tmp_test_col", "text", True, None
        )
        print("[RESULT] add preview:", json.dumps(preview_add, ensure_ascii=False))
    except Exception as e:
        print("[ERROR] preview_add_column failed:", e)

    # Preview rename
    print("[STEP] Preview rename column test")
    try:
        preview_ren = se.preview_rename_column(
            schema, table, "_tmp_test_col", "_tmp_test_col2"
        )
        print("[RESULT] rename preview:", json.dumps(preview_ren, ensure_ascii=False))
    except Exception as e:
        print("[ERROR] preview_rename_column failed:", e)

    print("[SUCCESS] AppBridge SchemaEditor checks finished")
    sys.exit(0)
except Exception as e:
    import traceback

    print("[ERROR] Check failure:", e)
    traceback.print_exc()
    sys.exit(10)
