#!/usr/bin/env python3
import psycopg

from config.config_manager import get_dsn

DSN = get_dsn()
OUTPUT = "net_result.txt"

with open(OUTPUT, "w", encoding="utf-8") as f:
    try:
        conn = psycopg.connect(DSN, connect_timeout=5)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(DISTINCT employee_id),
                   COALESCE(SUM(amount_cents), 0) / 100.0
            FROM payroll.payroll_transactions
        """
        )
        nb_emp, net_total = cur.fetchone()

        f.write("=== Synthèse Salaire Net ===\n")
        f.write(f"Employés distincts : {nb_emp}\n")
        f.write(f"Salaire net total : {net_total:.2f} $\n\n")

        f.write("=== Détail par période ===\n")
        cur.execute(
            """
            SELECT pay_date::date,
                   COALESCE(SUM(amount_cents), 0) / 100.0 AS net
            FROM payroll.payroll_transactions
            GROUP BY pay_date
            ORDER BY pay_date
        """
        )
        for pay_date, net in cur.fetchall():
            f.write(f"{pay_date} : {net:.2f} $\n")

        conn.close()
        f.write("\nStatut : OK\n")
    except Exception as e:
        f.write(f"Statut : ERREUR\n{e}\n")
