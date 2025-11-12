import os
import sys
import json

# Ensure 'app' directory is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

print("[TEST] Starting SchemaEditor smoke test...")

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
    if repo_available:
        schema = os.getenv("TEST_SCHEMA", "core")
        print(f"[STEP] Listing tables in schema='{schema}'")
        tables = se.list_tables(schema)
        print("[RESULT] tables:", tables[:10])
        if not tables:
            print("[WARN] No tables found, switching to 'public'")
            schema = "public"
            tables = se.list_tables(schema)
            print("[RESULT] tables(public):", tables[:10])

        # Pick a table to inspect
        table = None
        for candidate in (
            "employees",
            "payroll_transactions",
            "imported_payroll_master",
        ):
            if candidate in tables:
                table = candidate
                break
        if table is None and tables:
            table = tables[0]
        if not table:
            print("[ERROR] No table available to inspect")
            sys.exit(5)

        print(f"[STEP] Getting columns for {schema}.{table}")
        cols = se.get_table_columns(schema, table)
        print("[RESULT] columns count:", len(cols))
        print("[RESULT] first columns:", cols[:5])
    else:
        # Offline defaults for previews
        schema = "public"
        table = "demo_table"
        print(
            f"[INFO] Offline mode: using placeholders {schema}.{table} for preview checks"
        )

    # Preview add column
    print("[STEP] Preview add column test")
    preview_add = se.preview_add_column(
        schema, table, "_tmp_test_col", "text", True, None
    )
    print("[RESULT] add preview:", json.dumps(preview_add, ensure_ascii=False))

    # Preview rename (use the same temp name just for SQL generation)
    print("[STEP] Preview rename column test")
    preview_ren = se.preview_rename_column(
        schema, table, "_tmp_test_col", "_tmp_test_col2"
    )
    print("[RESULT] rename preview:", json.dumps(preview_ren, ensure_ascii=False))

    print("[SUCCESS] SchemaEditor smoke test finished")
    sys.exit(0)
except Exception as e:
    import traceback

    print("[ERROR] Test failure:", e)
    traceback.print_exc()
    sys.exit(10)
