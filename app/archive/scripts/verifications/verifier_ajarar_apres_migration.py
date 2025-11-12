#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
r = p.repo

try:
    print("=" * 80)
    print("VÉRIFICATION APRÈS MIGRATION 023")
    print("=" * 80)

    # 1. Trouver l'employé
    sql_emp = """
        SELECT employee_id, matricule_norm, nom_complet 
        FROM core.employees 
        WHERE LOWER(nom_complet) LIKE '%%ajarar%%' OR LOWER(nom_complet) LIKE '%%amin%%'
        LIMIT 5;
    """
    emp_result = r.run_query(sql_emp)
    print(f"\n1. Employés trouvés: {len(emp_result)}")
    for e in emp_result:
        print(f"   ID: {e[0]}, Matricule: {e[1]}, Nom: {e[2]}")
        emp_id = e[0]
        matricule = e[1]

        # 2. Vérifier le profil actuel (après migration)
        sql_profil = """
            SELECT categorie_emploi, titre_emploi, occurrences
            FROM paie.v_employe_profil
            WHERE employee_id = %s;
        """
        profil = r.run_query(sql_profil, (emp_id,))
        print("\n2. Profil actuel (v_employe_profil):")
        if profil:
            for p in profil:
                print(f"   Catégorie: {p[0]}")
                print(f"   Titre: {p[1]}")
                print(f"   Occurrences: {p[2]}")
        else:
            print("   (aucun profil trouvé)")

        # 3. Vérifier toutes les dates et titres dans stg
        sql_dates = """
            SELECT DISTINCT 
                date_paie,
                titre_emploi,
                COUNT(*) as nb
            FROM paie.stg_paie_transactions
            WHERE matricule = %s
              AND titre_emploi IS NOT NULL 
              AND TRIM(titre_emploi) <> ''
            GROUP BY date_paie, titre_emploi
            ORDER BY date_paie DESC, titre_emploi;
        """
        dates_titres = r.run_query(sql_dates, (matricule,))
        print("\n3. Titres par date (stg_paie_transactions):")
        for dt in dates_titres:
            print(f"   Date: {dt[0]}, Titre: {dt[1]}, Occurrences: {dt[2]}")

        # 4. Vérifier dans imported_payroll_master (source Excel)
        sql_master = """
            SELECT DISTINCT 
                "date de paie ",
                "titre d'emploi",
                COUNT(*) as nb
            FROM payroll.imported_payroll_master
            WHERE "matricule " = %s
              AND "titre d'emploi" IS NOT NULL
            GROUP BY "date de paie ", "titre d'emploi"
            ORDER BY "date de paie " DESC, "titre d'emploi";
        """
        master_titres = r.run_query(sql_master, (matricule,))
        print("\n4. Titres par date (imported_payroll_master - source Excel):")
        for mt in master_titres:
            print(f"   Date: {mt[0]}, Titre: {mt[1]}, Occurrences: {mt[2]}")

    print("\n" + "=" * 80)
    print("✓ Vérification terminée")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
finally:
    r.close()
