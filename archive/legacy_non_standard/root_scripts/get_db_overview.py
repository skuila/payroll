#!/usr/bin/env python3
"""Résumé complet de la base : tables, KPI, colonnes."""
import psycopg

from config.config_manager import get_dsn

DSN = get_dsn()
OUTPUT = "db_overview.txt"

SECTIONS = [
    ("core", None),
    ("payroll", None),
    ("paie", None),
    ("security", None),
    ("reference", None),
]

with open(OUTPUT, "w", encoding="utf-8") as f:
    try:
        conn = psycopg.connect(DSN, connect_timeout=5)
        cur = conn.cursor()

        f.write("=== INFORMATION DE CONNEXION ===\n")
        cur.execute("SELECT current_database(), current_user")
        db, user = cur.fetchone()
        f.write(f"Base : {db}\nUtilisateur : {user}\n\n")

        f.write("=== KPIs (payroll.payroll_transactions) ===\n")
        cur.execute(
            """
            SELECT COUNT(DISTINCT employee_id),
                   COALESCE(SUM(amount_cents),0)/100.0,
                   COALESCE(SUM(CASE WHEN amount_cents>0 THEN amount_cents ELSE 0 END),0)/100.0,
                   COALESCE(SUM(CASE WHEN amount_cents<0 THEN amount_cents ELSE 0 END),0)/100.0
            FROM payroll.payroll_transactions
        """
        )
        nb_emp, total_net, gains, deductions = cur.fetchone()
        f.write(f"Employés distincts  : {nb_emp}\n")
        f.write(f"Salaire net total   : {total_net:.2f} $\n")
        f.write(f"Gains (positifs)    : {gains:.2f} $\n")
        f.write(f"Déductions (nég.)   : {deductions:.2f} $\n\n")

        f.write("=== LISTE DES TABLES PAR SCHÉMA ===\n")
        cur.execute(
            """
            SELECT schemaname, tablename
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY schemaname, tablename
        """
        )
        tables = cur.fetchall()
        current_schema = None
        for schema, table in tables:
            if schema != current_schema:
                current_schema = schema
                f.write(f"\n[{schema}]\n")
            f.write(f"  - {table}\n")
        f.write("\n")

        f.write("=== COLONNES DES TABLES PRINCIPALES ===\n")
        tables_of_interest = [
            ("core", "employees"),
            ("payroll", "payroll_transactions"),
            ("payroll", "pay_periods"),
            ("payroll", "imported_payroll_master"),
            ("paie", "stg_paie_transactions"),
        ]

        for schema, table in tables_of_interest:
            f.write(f"\nTable {schema}.{table}\n")
            f.write("-" * (len(schema) + len(table) + 8) + "\n")
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """,
                (schema, table),
            )
            rows = cur.fetchall()
            if not rows:
                f.write("  (table introuvable)\n")
                continue
            for column_name, data_type, nullable in rows:
                f.write(
                    f"  • {column_name:<35} {data_type:<20} {'NULL' if nullable=='YES' else 'NOT NULL'}\n"
                )

        conn.close()
        f.write("\nStatut : OK\n")
        print(f"Résultat enregistré dans {OUTPUT}")
    except Exception as e:
        f.write(f"\nStatut : ERREUR\n{e}\n")
        print(f"Erreur : {e}")
