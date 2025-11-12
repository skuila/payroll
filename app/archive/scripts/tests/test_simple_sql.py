"""
Test très simple pour vérifier la requête SQL de base
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def test():
    provider = PostgresProvider()

    # Test simple: compter les transactions pour le 28 août
    date = "2025-08-28"

    print("=" * 70)
    print(f"TEST SIMPLE - Date: {date}")
    print("=" * 70)

    # Test 1: Compter les transactions
    sql1 = f"SELECT COUNT(*) FROM payroll.payroll_transactions WHERE pay_date = DATE '{date}'"
    rows1 = provider.repo.run_query(sql1)
    print(f"\n1. Transactions pour {date}: {rows1[0][0] if rows1 else 0}")

    # Test 2: Compter avec jointure employees
    sql2 = f"""
        SELECT COUNT(*) 
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        WHERE t.pay_date = DATE '{date}'
    """
    rows2 = provider.repo.run_query(sql2)
    print(f"2. Avec jointure employees: {rows2[0][0] if rows2 else 0}")

    # Test 3: Requête simplifiée (sans stg_paie_transactions)
    sql3 = f"""
        SELECT
          e.employee_id,
          e.matricule_norm,
          COALESCE(e.nom_complet, e.nom_norm || ' ' || COALESCE(e.prenom_norm, '')) AS nom_complet,
          SUM(t.amount_cents)::numeric / 100.0 AS amount_paid
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        WHERE t.pay_date = DATE '{date}'
        GROUP BY e.employee_id, e.matricule_norm, e.nom_complet, e.nom_norm, e.prenom_norm
        ORDER BY nom_complet
        LIMIT 5
    """
    rows3 = provider.repo.run_query(sql3)
    print(f"\n3. Requête simplifiée (sans stg): {len(rows3)} résultats")
    for row in rows3:
        print(f"   - {row[0]} | {row[1]} | {row[2][:30]} | ${row[3]:,.2f}")

    # Test 4: Requête complète (avec stg_paie_transactions)
    sql4 = f"""
        SELECT
          e.employee_id,
          e.matricule_norm AS matricule,
          COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')) AS nom_complet,
          MAX(t.pay_date) AS pay_date,
          COALESCE((ARRAY_AGG(s.categorie_emploi ORDER BY s.categorie_emploi NULLS LAST) FILTER (WHERE s.categorie_emploi IS NOT NULL))[1], 'Non défini') AS categorie_emploi,
          COALESCE((ARRAY_AGG(s.titre_emploi ORDER BY s.titre_emploi NULLS LAST) FILTER (WHERE s.titre_emploi IS NOT NULL))[1], 'Non défini') AS titre_emploi,
          CASE 
            WHEN BOOL_OR(s.nom_prenom IS NOT NULL AND s.nom_prenom ~ '[A-Za-z]' AND s.nom_prenom = UPPER(s.nom_prenom)) 
            THEN 'inactif' 
            ELSE 'actif' 
          END AS statut_calcule,
          SUM(t.amount_cents)::numeric / 100.0 AS amount_paid
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        LEFT JOIN paie.stg_paie_transactions s
          ON s.source_file = t.source_file AND s.source_row_number = t.source_row_no
        WHERE t.pay_date = DATE '{date}'
        GROUP BY e.employee_id, e.matricule_norm, e.nom_complet, e.nom_norm, e.prenom_norm
        ORDER BY nom_complet
        LIMIT 5
    """
    try:
        rows4 = provider.repo.run_query(sql4)
        print(f"\n4. Requête complète (avec stg): {len(rows4)} résultats")
        for row in rows4:
            print(
                f"   - ID:{row[0]} | {row[2][:25]} | {row[4][:15]} | {row[6]} | ${row[7]:,.2f}"
            )
    except Exception as e:
        print(f"\n❌ ERREUR requête complète: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)
    print("✅ Test terminé")
    print("=" * 70)


if __name__ == "__main__":
    test()
