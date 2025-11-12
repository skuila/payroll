import sys, traceback

sys.path.insert(0, "app")
try:
    import app.providers.postgres_provider as pg

    print("IMPORT_OK", hasattr(pg, "PostgresProvider"))
except Exception:
    traceback.print_exc()
