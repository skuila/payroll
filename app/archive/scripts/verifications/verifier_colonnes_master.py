#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
r = p.repo

try:
    # Vérifier les colonnes de imported_payroll_master
    sql_cols = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'payroll' 
          AND table_name = 'imported_payroll_master'
        ORDER BY ordinal_position;
    """
    cols = r.run_query(sql_cols)
    print("Colonnes de payroll.imported_payroll_master:")
    for c in cols:
        print(f"  - {c[0]} ({c[1]})")

    # Chercher Ajarar dans toutes les colonnes possibles
    print("\n" + "=" * 80)
    print("Recherche Ajarar Amin dans imported_payroll_master:")
    print("=" * 80)

    # Essayer différentes variantes de colonnes
    sql_test = """
        SELECT DISTINCT 
            matricule,
            nom_employe,
            categorie_emploi,
            titre_emploi,
            date_paie
        FROM payroll.imported_payroll_master
        WHERE LOWER(nom_employe) LIKE '%%ajarar%%' OR LOWER(nom_employe) LIKE '%%amin%%'
        ORDER BY date_paie DESC;
    """
    result = r.run_query(sql_test)
    print(f"\nRésultats trouvés: {len(result)}")
    for row in result:
        print(f"  Date: {row[4]}")
        print(f"  Matricule: {row[0]}")
        print(f"  Employé: {row[1]}")
        print(f"  Catégorie: {row[2]}")
        print(f"  Titre: {row[3]}")
        print()

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
finally:
    r.close()
