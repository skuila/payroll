#!/usr/bin/env python3
"""Check DB connection and return JSON with connection info.

Uses PostgresProvider if available to match application behaviour; falls back to psycopg direct connect.
Outputs JSON to stdout: {ok: bool, user: str, db: str, error: str}
Exit code 0 on success, 1 on failure.
"""
import os, sys, json

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.getcwd(), "app", ".env"))
except Exception:
    pass

# ensure libpq can use PAYROLL_DB_PASSWORD
if os.getenv("PAYROLL_DB_PASSWORD") and not os.getenv("PGPASSWORD"):
    os.environ["PGPASSWORD"] = os.getenv("PAYROLL_DB_PASSWORD")

# Allow explicit override via CLI --dsn for deterministic checks from the harness
DSN = None
try:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", "-d", help="DSN to use for connection", default=None)
    args, _ = parser.parse_known_args()
    DSN = args.dsn
except Exception:
    DSN = None

if not DSN:
    DSN = os.getenv("PAYROLL_DSN") or os.getenv("DATABASE_URL") or os.getenv("PG_DSN")

if not DSN:
    print(json.dumps({"ok": False, "error": "PAYROLL_DSN not set"}))
    sys.exit(1)

# Try to use app PostgresProvider for exact same behaviour
provider = None
try:
    from app.providers.postgres_provider import PostgresProvider

    provider = PostgresProvider(dsn=DSN)
    # provider initialized: get connection info
    info = provider.get_connection_info()
    out = {
        "ok": True if info.get("status") == "connected" else False,
        "user": info.get("user"),
        "db": info.get("database"),
        "host": info.get("host"),
        "app_env": info.get("app_env"),
    }
    print(json.dumps(out))
    # Close pool
    try:
        if getattr(provider, "repo", None) is not None:
            provider.repo.close()
    except Exception:
        pass
    sys.exit(0 if out["ok"] else 1)
except Exception as e:
    # Fallback to direct psycopg connect
    try:
        import psycopg
    except Exception as e2:
        print(json.dumps({"ok": False, "error": f"psycopg missing: {e2}"}))
        sys.exit(1)

    try:
        conn = psycopg.connect(DSN, connect_timeout=5)
        dsn_info = conn.info.get_parameters()
        out = {
            "ok": True,
            "user": dsn_info.get("user"),
            "db": dsn_info.get("dbname"),
            "host": dsn_info.get("host"),
        }
        print(json.dumps(out))
        try:
            conn.close()
        except Exception:
            pass
        sys.exit(0)
    except Exception as e3:
        print(json.dumps({"ok": False, "error": str(e3)}))
        sys.exit(1)
