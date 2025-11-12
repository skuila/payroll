# smoke_db_conn.py
# Teste la connexion DB en utilisant app.config.config_manager.get_dsn()
import traceback
import os
import sys

# Ensure project root is on sys.path so `import app` works when script run from anywhere
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from app.config import config_manager

try:
    dsn = config_manager.get_dsn()
    print("DSN:", dsn)
    import psycopg

    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, version();")
            print("OK:", cur.fetchone())
except Exception:
    traceback.print_exc()
    raise
