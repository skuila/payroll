#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic: titres du fichier vs sommes de gains (référentiel) pour un employé/date.
Exécution (cmd.exe):
  python scripts\\diag_titre_ajarar_cmd.py 2364 2025-08-28
  (Param1 = matricule, Param2 = date de paie YYYY-MM-DD; défauts: 2364, 2025-08-28)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider


def main():
    matricule = sys.argv[1] if len(sys.argv) > 1 else "2364"
    pay_date = sys.argv[2] if len(sys.argv) > 2 else "2025-08-28"
    p = PostgresProvider()
    r = p.repo
    try:
        print(f"\n=== DIAG: matricule={matricule}, date={pay_date} ===")
        # 1) Titres par somme de gains (montants positifs uniquement)
        sql_pos = """
        SELECT 
          COALESCE(NULLIF(TRIM(s.titre_emploi), ''), 'Non défini') AS titre_emploi,
          COALESCE(NULLIF(TRIM(s.categorie_emploi), ''), 'Non défini') AS categorie_emploi,
          SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) / 100.0 AS total_gains_pos,
          COUNT(*) AS nb_lignes
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        LEFT JOIN paie.stg_paie_transactions s
          ON s.matricule = e.matricule_norm
         AND s.date_paie = t.pay_date
        WHERE e.matricule_norm = %s
          AND t.pay_date = %s::date
        GROUP BY 1,2
        ORDER BY total_gains_pos DESC NULLS LAST, titre_emploi;
        """
        rows = r.run_query(sql_pos, (matricule, pay_date))
        print("\n-- Sommes de gains par titre (montants positifs) --")
        for row in rows:
            print(
                f"  Titre={row[0]} | Cat={row[1]} | Gains+={row[2]} | Lignes={row[3]}"
            )

        # 2) Détail par code de paie (pour voir les types)
        sql_codes = """
        SELECT 
          t.pay_code,
          COALESCE(pc.pay_code_type, 'NULL') AS type,
          SUM(t.amount_cents) FILTER (WHERE t.amount_cents > 0) / 100.0 AS montant_pos,
          SUM(t.amount_cents) FILTER (WHERE t.amount_cents < 0) / 100.0 AS montant_neg,
          COUNT(*) AS nb
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        LEFT JOIN reference.pay_codes pc ON pc.pay_code = t.pay_code
        WHERE e.matricule_norm = %s
          AND t.pay_date = %s::date
        GROUP BY t.pay_code, COALESCE(pc.pay_code_type, 'NULL')
        ORDER BY montant_pos DESC NULLS LAST, t.pay_code;
        """
        codes = r.run_query(sql_codes, (matricule, pay_date))
        print("\n-- Détail par code de paie (types référentiel) --")
        for c in codes:
            print(f"  code={c[0]} | type={c[1]} | +={c[2]} | -={c[3]} | n={c[4]}")

        # 3) Titres distincts présents dans le fichier (staging) pour ce jour
        sql_titres = """
        SELECT DISTINCT 
          COALESCE(NULLIF(TRIM(titre_emploi), ''), 'Non défini') AS titre_emploi,
          COALESCE(NULLIF(TRIM(categorie_emploi), ''), 'Non défini') AS categorie_emploi
        FROM paie.stg_paie_transactions
        WHERE matricule = %s AND date_paie = %s::date
        ORDER BY 1;
        """
        titres = r.run_query(sql_titres, (matricule, pay_date))
        print("\n-- Titres présents dans le fichier (staging) ce jour --")
        for trow in titres:
            print(f"  Titre={trow[0]} | Cat={trow[1]}")

        print("\n✓ Diagnostic terminé.")
    finally:
        r.close()


if __name__ == "__main__":
    main()
