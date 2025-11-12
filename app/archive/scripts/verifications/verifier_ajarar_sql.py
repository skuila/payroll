#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
r = p.repo

try:
    print("=== 1. Recherche employé ===")
    sql1 = "SELECT employee_id, matricule_norm, nom_complet FROM core.employees WHERE LOWER(nom_complet) LIKE '%ajarar%' OR LOWER(nom_complet) LIKE '%amin%';"
    emp = r.run_query(sql1)
    print(emp)

    if emp:
        emp_id = emp[0][0]
        mat = emp[0][1]

        print("\n=== 2. Profil actuel (v_employe_profil) ===")
        sql2 = f"SELECT * FROM paie.v_employe_profil WHERE employee_id = '{emp_id}';"
        prof = r.run_query(sql2)
        print(prof)

        print(
            f"\n=== 3. Tous les titres dans stg_paie_transactions (matricule={mat}) ==="
        )
        sql3 = f"SELECT DISTINCT titre_emploi, COUNT(*) as nb FROM paie.stg_paie_transactions WHERE matricule = '{mat}' AND titre_emploi IS NOT NULL GROUP BY titre_emploi ORDER BY nb DESC;"
        titres = r.run_query(sql3)
        for t in titres:
            print(f"  {t[0]}: {t[1]} occurrences")

        print("\n=== 4. Tous les titres dans imported_payroll_master ===")
        sql4 = f'SELECT DISTINCT "titre d\'emploi", COUNT(*) as nb FROM payroll.imported_payroll_master WHERE "matricule " = \'{mat}\' AND "titre d\'emploi" IS NOT NULL GROUP BY "titre d\'emploi" ORDER BY nb DESC;'
        titres_master = r.run_query(sql4)
        for t in titres_master:
            print(f"  {t[0]}: {t[1]} occurrences")

except Exception as e:
    print(f"ERREUR: {e}")
    import traceback

    traceback.print_exc()
finally:
    r.close()
