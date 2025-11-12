"""
Debug de la jointure pour comprendre pourquoi elle ne fonctionne pas
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def test():
    provider = PostgresProvider()
    date = "2025-08-28"

    print("=" * 70)
    print("DEBUG: Pourquoi la jointure ne fonctionne pas?")
    print("=" * 70)

    # Test 1: Vérifier les valeurs de source_file dans payroll_transactions
    print("\n1. Valeurs de source_file dans payroll_transactions...")
    sql1 = f"""
        SELECT DISTINCT source_file, COUNT(*) as cnt
        FROM payroll.payroll_transactions
        WHERE pay_date = DATE '{date}'
        GROUP BY source_file
        LIMIT 5
    """
    rows1 = provider.repo.run_query(sql1)
    print("   Fichiers sources dans payroll_transactions:")
    for row in rows1:
        print(f"     - '{row[0]}': {row[1]} transactions")

    # Test 2: Vérifier les valeurs de source_file dans stg_paie_transactions
    print("\n2. Valeurs de source_file dans stg_paie_transactions...")
    sql2 = f"""
        SELECT DISTINCT source_file, COUNT(*) as cnt
        FROM paie.stg_paie_transactions
        WHERE date_paie = DATE '{date}'
        GROUP BY source_file
        LIMIT 5
    """
    rows2 = provider.repo.run_query(sql2)
    print("   Fichiers sources dans stg_paie_transactions:")
    for row in rows2:
        print(f"     - '{row[0]}': {row[1]} lignes")

    # Test 3: Vérifier si les source_row_no correspondent
    print("\n3. Test de correspondance source_row_no...")
    sql3 = f"""
        SELECT 
          t.source_file as t_file,
          t.source_row_no as t_row,
          s.source_file as s_file,
          s.source_row_number as s_row,
          s.categorie_emploi,
          s.titre_emploi
        FROM payroll.payroll_transactions t
        LEFT JOIN paie.stg_paie_transactions s
          ON s.source_file = t.source_file AND s.source_row_number = t.source_row_no
        WHERE t.pay_date = DATE '{date}'
        LIMIT 10
    """
    rows3 = provider.repo.run_query(sql3)
    print("   Exemples de jointure:")
    matched = 0
    for row in rows3:
        if row[2] is not None:  # s_file n'est pas NULL
            matched += 1
            print(
                f"     ✅ Match: t_file='{row[0]}' t_row={row[1]} | s_file='{row[2]}' s_row={row[3]} | cat={row[4] or 'NULL'}"
            )
        else:
            print(f"     ❌ Pas de match: t_file='{row[0]}' t_row={row[1]}")
    print(f"   Total matchés: {matched}/{len(rows3)}")

    # Test 4: Vérifier si on peut utiliser imported_payroll_master à la place
    print("\n4. Test avec imported_payroll_master...")
    sql4 = f"""
        SELECT 
          t.source_row_no,
          m."Catégorie d'emploi" as cat,
          m."titre d'emploi" as titre
        FROM payroll.payroll_transactions t
        LEFT JOIN payroll.imported_payroll_master m
          ON m.source_row_number = t.source_row_no
        WHERE t.pay_date = DATE '{date}'
          AND t.source_row_no IS NOT NULL
        LIMIT 10
    """
    try:
        rows4 = provider.repo.run_query(sql4)
        matched_master = sum(1 for r in rows4 if r[1] is not None)
        print(f"   Matchés avec imported_payroll_master: {matched_master}/{len(rows4)}")
        if rows4 and rows4[0][1]:
            print(f"   Exemple: cat='{rows4[0][1]}', titre='{rows4[0][2]}'")
    except Exception as e:
        print(f"   Erreur: {e}")

    # Test 5: Vérifier les colonnes de imported_payroll_master
    print("\n5. Colonnes disponibles dans imported_payroll_master...")
    sql5 = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'payroll' 
          AND table_name = 'imported_payroll_master'
          AND (column_name ILIKE '%categorie%' OR column_name ILIKE '%titre%' OR column_name ILIKE '%emploi%')
        ORDER BY column_name
    """
    rows5 = provider.repo.run_query(sql5)
    print(f"   Colonnes trouvées: {[r[0] for r in rows5] if rows5 else 'Aucune'}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test()
