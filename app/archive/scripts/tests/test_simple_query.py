"""
Test simple pour vérifier la requête SQL de base
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def test_simple():
    provider = PostgresProvider()

    # Test 1: Vérifier les dates disponibles
    print("=" * 70)
    print("TEST 1: Dates disponibles")
    print("=" * 70)
    sql1 = "SELECT DISTINCT pay_date FROM payroll.payroll_transactions ORDER BY pay_date DESC LIMIT 5"
    rows1 = provider.repo.run_query(sql1)
    print(f"Dates trouvées: {len(rows1)}")
    for row in rows1:
        print(f"  - {row[0]}")

    if not rows1:
        print("❌ Aucune date trouvée dans payroll_transactions!")
        provider.repo.close_pool()
        return

    test_date = str(rows1[0][0])
    print(f"\nUtilisation de la date: {test_date}")

    # Test 2: Vérifier les transactions pour cette date
    print("\n" + "=" * 70)
    print("TEST 2: Transactions pour cette date")
    print("=" * 70)
    sql2 = f"SELECT COUNT(*) FROM payroll.payroll_transactions WHERE pay_date = DATE '{test_date}'"
    rows2 = provider.repo.run_query(sql2)
    print(f"Nombre de transactions: {rows2[0][0] if rows2 else 0}")

    # Test 3: Vérifier la jointure avec employees
    print("\n" + "=" * 70)
    print("TEST 3: Jointure avec employees")
    print("=" * 70)
    sql3 = f"""
        SELECT COUNT(*) 
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        WHERE t.pay_date = DATE '{test_date}'
    """
    rows3 = provider.repo.run_query(sql3)
    print(f"Transactions avec employees: {rows3[0][0] if rows3 else 0}")

    # Test 4: Vérifier la jointure avec stg_paie_transactions
    print("\n" + "=" * 70)
    print("TEST 4: Jointure avec stg_paie_transactions")
    print("=" * 70)
    sql4 = f"""
        SELECT COUNT(*) 
        FROM payroll.payroll_transactions t
        LEFT JOIN paie.stg_paie_transactions s
          ON s.source_file = t.source_file AND s.source_row_number = t.source_row_no
        WHERE t.pay_date = DATE '{test_date}'
    """
    rows4 = provider.repo.run_query(sql4)
    print(f"Transactions avec stg: {rows4[0][0] if rows4 else 0}")

    # Test 5: Requête complète simplifiée
    print("\n" + "=" * 70)
    print("TEST 5: Requête complète (premiers résultats)")
    print("=" * 70)
    sql5 = f"""
        SELECT
          e.employee_id,
          e.matricule_norm AS matricule,
          COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')) AS nom_complet,
          t.pay_date,
          SUM(t.amount_cents)::numeric / 100.0 AS amount_paid
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        WHERE t.pay_date = DATE '{test_date}'
        GROUP BY e.employee_id, e.matricule_norm, e.nom_complet, e.nom_norm, e.prenom_norm, t.pay_date
        ORDER BY nom_complet
        LIMIT 5
    """
    rows5 = provider.repo.run_query(sql5)
    print(f"Résultats: {len(rows5)}")
    for row in rows5:
        print(f"  - {row[0]} | {row[1]} | {row[2]} | {row[4]}")

    # Test 6: Requête avec CTE (comme dans le code)
    print("\n" + "=" * 70)
    print("TEST 6: Requête avec CTE (comme dans api-client.js)")
    print("=" * 70)
    sql6 = f"""
      WITH base AS (
        SELECT
          e.employee_id,
          e.matricule_norm AS matricule,
          COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')) AS nom_complet,
          t.pay_date,
          t.amount_cents,
          s.categorie_emploi,
          s.titre_emploi,
          s.nom_prenom
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        LEFT JOIN paie.stg_paie_transactions s
          ON s.source_file = t.source_file AND s.source_row_number = t.source_row_no
        WHERE t.pay_date = DATE '{test_date}'
      ),
      agg AS (
        SELECT
          employee_id,
          MAX(pay_date) AS derniere_paie_periode,
          SUM(amount_cents)::numeric / 100.0 AS amount_paid,
          (ARRAY_AGG(categorie_emploi ORDER BY categorie_emploi NULLS LAST))[1] AS categorie_emploi,
          (ARRAY_AGG(titre_emploi ORDER BY titre_emploi NULLS LAST))[1] AS titre_emploi,
          BOOL_OR(
            nom_prenom IS NOT NULL
            AND nom_prenom ~ '[A-Za-z]'
            AND nom_prenom = UPPER(nom_prenom)
          ) AS has_upper_name
        FROM base
        GROUP BY employee_id
      )
      SELECT
        a.employee_id,
        MAX(b.matricule) AS matricule,
        MAX(b.nom_complet) AS nom_complet,
        a.derniere_paie_periode AS pay_date,
        a.categorie_emploi,
        a.titre_emploi,
        CASE WHEN a.has_upper_name THEN 'inactif' ELSE 'actif' END AS statut_calcule,
        a.amount_paid
      FROM agg a
      JOIN base b ON b.employee_id = a.employee_id
      GROUP BY a.employee_id, a.derniere_paie_periode, a.categorie_emploi, a.titre_emploi, a.has_upper_name, a.amount_paid
      ORDER BY MAX(b.nom_complet)
      LIMIT 5
    """
    try:
        rows6 = provider.repo.run_query(sql6)
        print(f"✅ Résultats: {len(rows6)}")
        for row in rows6:
            print(f"  - ID:{row[0]} | {row[2]} | {row[6]} | ${row[7]}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback

        traceback.print_exc()

    provider.repo.close_pool()


if __name__ == "__main__":
    test_simple()
