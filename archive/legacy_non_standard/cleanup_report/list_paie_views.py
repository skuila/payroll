import psycopg
import os

d = os.environ.get("DATABASE_URL") or os.environ.get("PAYROLL_DSN")
print("DSN=", d)
if not d:
    raise SystemExit("No DSN found in env")
with psycopg.connect(d) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_schema, table_name FROM information_schema.views WHERE table_schema='paie' ORDER BY table_name"
        )
        rows = cur.fetchall()
        print("paie views:", [r[1] for r in rows])
