"""
Test pour vérifier quelle est la bonne source pour catégorie et titre d'emploi
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
    print("TEST: Vérification des sources de données")
    print("=" * 70)

    # Test 1: Vérifier si stg_paie_transactions a des données
    print("\n1. Vérification de paie.stg_paie_transactions...")
    sql1 = f"""
        SELECT COUNT(*) 
        FROM paie.stg_paie_transactions 
        WHERE date_paie = DATE '{date}'
    """
    rows1 = provider.repo.run_query(sql1)
    print(
        f"   Lignes dans stg_paie_transactions pour {date}: {rows1[0][0] if rows1 else 0}"
    )

    # Test 2: Vérifier si imported_payroll_master a des données
    print("\n2. Vérification de payroll.imported_payroll_master...")
    sql2 = f"""
        SELECT COUNT(*) 
        FROM payroll.imported_payroll_master 
        WHERE "Date de paie"::date = DATE '{date}'
    """
    try:
        rows2 = provider.repo.run_query(sql2)
        print(
            f"   Lignes dans imported_payroll_master pour {date}: {rows2[0][0] if rows2 else 0}"
        )
    except Exception as e:
        print(f"   Erreur: {e}")

    # Test 3: Vérifier la jointure avec stg_paie_transactions
    print("\n3. Test jointure avec stg_paie_transactions...")
    sql3 = f"""
        SELECT 
          COUNT(*) as total,
          COUNT(DISTINCT s.categorie_emploi) as nb_categories,
          COUNT(DISTINCT s.titre_emploi) as nb_titres
        FROM payroll.payroll_transactions t
        LEFT JOIN paie.stg_paie_transactions s
          ON s.source_file = t.source_file AND s.source_row_number = t.source_row_no
        WHERE t.pay_date = DATE '{date}'
    """
    rows3 = provider.repo.run_query(sql3)
    if rows3:
        print(f"   Total: {rows3[0][0]}")
        print(f"   Catégories distinctes: {rows3[0][1]}")
        print(f"   Titres distincts: {rows3[0][2]}")

    # Test 4: Vérifier la jointure avec imported_payroll_master
    print("\n4. Test jointure avec imported_payroll_master...")
    sql4 = f"""
        SELECT 
          COUNT(*) as total,
          COUNT(DISTINCT m."Catégorie d'emploi") as nb_categories,
          COUNT(DISTINCT m."titre d'emploi") as nb_titres
        FROM payroll.payroll_transactions t
        LEFT JOIN payroll.imported_payroll_master m
          ON m.source_row_number = t.source_row_no
        WHERE t.pay_date = DATE '{date}'
    """
    try:
        rows4 = provider.repo.run_query(sql4)
        if rows4:
            print(f"   Total: {rows4[0][0]}")
            print(f"   Catégories distinctes: {rows4[0][1]}")
            print(f"   Titres distincts: {rows4[0][2]}")
    except Exception as e:
        print(f"   Erreur: {e}")

    # Test 5: Vérifier les colonnes disponibles dans stg_paie_transactions
    print("\n5. Colonnes disponibles dans stg_paie_transactions...")
    sql5 = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'paie' 
          AND table_name = 'stg_paie_transactions'
          AND column_name LIKE '%categorie%' OR column_name LIKE '%titre%'
        ORDER BY column_name
    """
    rows5 = provider.repo.run_query(sql5)
    print(f"   Colonnes trouvées: {[r[0] for r in rows5] if rows5 else 'Aucune'}")

    # Test 6: Exemple de données réelles
    print("\n6. Exemple de données réelles (premières lignes)...")
    sql6 = f"""
        SELECT 
          t.employee_id,
          e.nom_complet,
          s.categorie_emploi,
          s.titre_emploi,
          m."Catégorie d'emploi" as cat_master,
          m."titre d'emploi" as titre_master
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        LEFT JOIN paie.stg_paie_transactions s
          ON s.source_file = t.source_file AND s.source_row_number = t.source_row_no
        LEFT JOIN payroll.imported_payroll_master m
          ON m.source_row_number = t.source_row_no
        WHERE t.pay_date = DATE '{date}'
        LIMIT 5
    """
    try:
        rows6 = provider.repo.run_query(sql6)
        print(f"   Résultats: {len(rows6)}")
        for row in rows6:
            print(
                f"   - {row[1][:25]:<25} | stg_cat: {row[2] or 'NULL':<15} | master_cat: {row[4] or 'NULL'}"
            )
    except Exception as e:
        print(f"   Erreur: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test()
