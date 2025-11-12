#!/usr/bin/env python3
"""Query KPIs from PostgreSQL for acceptance tests.

Outputs JSON to stdout with keys: total_net, nb_employees, avg_net_per_employee, batch_id

Behavior:
 - Reads PAYROLL_DSN from environment or from .env in repo root (using python-dotenv if available)
 - Finds the latest completed batch in payroll.import_batches (fallback: use all transactions)
 - Computes totals over payroll.payroll_transactions for that batch
"""
import os
import json
import sys

try:
    # prefer python-dotenv if available to load .env
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.getcwd(), "app", ".env"))
except Exception:
    # silent fallback if python-dotenv missing
    pass

# If a PAYROLL_DB_PASSWORD is provided, set PGPASSWORD so libpq/psycopg can use it
if os.getenv("PAYROLL_DB_PASSWORD") and not os.getenv("PGPASSWORD"):
    os.environ["PGPASSWORD"] = os.getenv("PAYROLL_DB_PASSWORD")

DSN = os.getenv("PAYROLL_DSN") or os.getenv("DATABASE_URL") or os.getenv("PG_DSN")
if not DSN:
    print(json.dumps({"error": "PAYROLL_DSN not found in environment or .env"}))
    sys.exit(2)

try:
    import psycopg
except Exception as e:
    print(json.dumps({"error": f"psycopg not available: {e}"}))
    sys.exit(3)


def query_latest_batch(conn):
    sql = """
        SELECT batch_id
        FROM payroll.import_batches
        WHERE status = 'completed'
        ORDER BY COALESCE(completed_at, now()) DESC, batch_id DESC
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r else None


def compute_kpis_for_batch(conn, batch_id=None):
    """
    Return a rich KPI dict comparable to app/_cleanup_report/kpi_summary.py
    If batch_id is provided we filter by import_batch_id, otherwise fallback to the
    latest pay_date present in payroll.payroll_transactions.
    """
    use_batch = batch_id is not None
    params = (batch_id,) if use_batch else None

    # Determine the WHERE clause for transactions
    if use_batch:
        where_clause = "t.import_batch_id = %s"
    else:
        # find latest pay_date
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(pay_date) FROM payroll.payroll_transactions")
            r = cur.fetchone()
            latest_date = r[0] if r else None
        if latest_date is None:
            # no data
            return {}
        where_clause = "t.pay_date = %s"
        params = (latest_date,)

    kpi = {}
    with conn.cursor() as cur:
        # Batch metadata if available
        if use_batch:
            cur.execute(
                "SELECT filename, total_rows, valid_rows, invalid_rows, new_employees FROM payroll.import_batches WHERE batch_id = %s",
                (batch_id,),
            )
            meta = cur.fetchone()
            if meta:
                kpi["input"] = meta[0]
                kpi["total_lines"] = int(meta[1] or 0)
                kpi["valid_lines"] = int(meta[2] or 0)
                kpi["rejected_lines"] = int(meta[3] or 0)
                kpi["new_employees"] = int(meta[4] or 0)
            else:
                kpi["input"] = None

        # Totals
        sql_tot = f"SELECT COUNT(*) AS total_lines, COALESCE(SUM(t.amount_cents),0) AS total_net_cents, COUNT(DISTINCT t.employee_id) AS nb_employees FROM payroll.payroll_transactions t WHERE {where_clause}"
        cur.execute(sql_tot, params)
        tr = cur.fetchone()
        total_lines = int(tr[0] or 0)
        total_net_cents = int(tr[1] or 0)
        nb_employees = int(tr[2] or 0)

        kpi["total_lines"] = kpi.get("total_lines", total_lines)
        kpi["total_net_cents"] = total_net_cents
        kpi["total_net"] = round(total_net_cents / 100.0, 2)
        kpi["nb_employees"] = nb_employees
        kpi["avg_net_per_employee"] = round(
            (kpi["total_net"] / nb_employees) if nb_employees > 0 else 0.0, 2
        )

        # By code
        sql_code = f"SELECT t.pay_code, COUNT(*) AS cnt, COALESCE(SUM(t.amount_cents),0)/100.0 AS total_net FROM payroll.payroll_transactions t WHERE {where_clause} GROUP BY t.pay_code ORDER BY ABS(SUM(t.amount_cents)) DESC"
        cur.execute(sql_code, params)
        rows_code = cur.fetchall() or []
        by_code = {}
        for r in rows_code:
            code = r[0] or "UNKNOWN"
            by_code[str(code)] = {
                "count": int(r[1] or 0),
                "total_net": float(r[2] or 0.0),
            }
        kpi["by_code"] = by_code

        # By period (pay_date)
        sql_period = f"SELECT TO_CHAR(t.pay_date,'YYYY-MM-DD') AS pd, COUNT(*) AS cnt, COALESCE(SUM(t.amount_cents),0)/100.0 AS net FROM payroll.payroll_transactions t WHERE {where_clause} GROUP BY pd ORDER BY pd"
        cur.execute(sql_period, params)
        rows_period = cur.fetchall() or []
        by_period = {
            r[0]: {"count": int(r[1] or 0), "net": float(r[2] or 0.0)}
            for r in rows_period
        }
        kpi["by_period"] = by_period

        # Top employees (limit 10)
        sql_top = f"""
            SELECT COALESCE(e.matricule_norm, '') AS matricule, COALESCE(e.nom_complet, '') AS nom_complet,
                   COUNT(*) AS cnt, COALESCE(SUM(t.amount_cents),0)/100.0 AS net
            FROM payroll.payroll_transactions t
            LEFT JOIN core.employees e ON t.employee_id = e.employee_id
            WHERE {where_clause}
            GROUP BY COALESCE(e.matricule_norm, ''), COALESCE(e.nom_complet, '')
            ORDER BY net DESC
            LIMIT 10
        """
        cur.execute(sql_top, params)
        rows_top = cur.fetchall() or []
        top_emps = []
        for r in rows_top:
            top_emps.append(
                {
                    "matricule": r[0],
                    "nom_prenom": r[1],
                    "count": int(r[2] or 0),
                    "net": float(r[3] or 0.0),
                }
            )
        kpi["top_employees"] = top_emps

    return kpi


def main():
    # Try to reuse the PostgresProvider logic (preferred) so the same connection
    # checks and pool initialization are used as in the application. If that
    # fails (import error or runtime), fall back to a direct psycopg connection.
    provider = None
    conn = None
    try:
        try:
            from app.providers.postgres_provider import PostgresProvider

            provider = PostgresProvider(dsn=DSN)
        except Exception:
            provider = None

        if provider is not None and getattr(provider, "repo", None) is not None:
            # Use a connection from the provider's pool
            with provider.repo.get_connection() as conn:
                try:
                    batch_id = query_latest_batch(conn)
                except Exception:
                    batch_id = None

                try:
                    kpi = compute_kpis_for_batch(conn, batch_id)
                    if not kpi:
                        print(
                            json.dumps(
                                {"error": "No transactions found to compute KPIs"}
                            )
                        )
                        return 6
                    kpi["batch_id"] = batch_id
                    print(json.dumps(kpi, ensure_ascii=False))
                    return 0
                except Exception as e:
                    print(json.dumps({"error": f"Query failed: {e}"}))
                    return 5

        # Fallback: direct connection using psycopg
        try:
            conn = psycopg.connect(DSN)
        except Exception as e:
            print(json.dumps({"error": f"Connection failed: {e}"}))
            sys.exit(4)

        try:
            try:
                batch_id = query_latest_batch(conn)
            except Exception:
                batch_id = None

            kpi = compute_kpis_for_batch(conn, batch_id)
            if not kpi:
                print(json.dumps({"error": "No transactions found to compute KPIs"}))
                return 6
            kpi["batch_id"] = batch_id
            print(json.dumps(kpi, ensure_ascii=False))
            return 0
        except Exception as e:
            print(json.dumps({"error": f"Query failed: {e}"}))
            return 5
        finally:
            try:
                conn.close()
            except Exception:
                pass
    finally:
        # ensure provider pool is closed if initialized
        try:
            if provider is not None and getattr(provider, "repo", None) is not None:
                provider.repo.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
