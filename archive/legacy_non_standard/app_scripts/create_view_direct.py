#!/usr/bin/env python3
"""Directly create paie.v_kpi_periode using the superuser DSN.
This avoids the admin SQL splitting issues.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config_manager import get_superuser_dsn
import psycopg
from dotenv import load_dotenv

# Load environment from app/.env so DSN passwords are available
load_dotenv(Path(__file__).parent.parent / ".env")

create_sql = """
CREATE OR REPLACE VIEW paie.v_kpi_periode AS
SELECT
    TO_CHAR(pay_date, 'YYYY-MM') as periode,
    TO_CHAR(pay_date, 'YYYY-MM') as periode_paie,
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_employeur_pnl,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements
FROM payroll.payroll_transactions
GROUP BY TO_CHAR(pay_date, 'YYYY-MM'), TO_CHAR(pay_date, 'YYYY-MM-DD')
ORDER BY periode, date_paie;
"""

if __name__ == "__main__":
    dsn = get_superuser_dsn()
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(create_sql)
                conn.commit()
        print("OK: paie.v_kpi_periode created")
    except Exception as e:
        print("ERROR creating paie.v_kpi_periode:", e)
        sys.exit(1)
