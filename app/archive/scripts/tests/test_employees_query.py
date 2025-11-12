"""
Script de test pour vérifier les requêtes SQL de la page employees
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def test_sql_for_day(date):
    """Test la requête SQL pour une date donnée"""
    print(f"\n{'='*70}")
    print(f"TEST: Requête SQL pour la date {date}")
    print(f"{'='*70}\n")

    sql = f"""
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
        WHERE t.pay_date = DATE '{date}'
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
        b.matricule,
        b.nom_complet,
        a.derniere_paie_periode AS pay_date,
        a.categorie_emploi,
        a.titre_emploi,
        CASE WHEN a.has_upper_name THEN 'inactif' ELSE 'actif' END AS statut_calcule,
        a.amount_paid
      FROM agg a
      JOIN (
        SELECT DISTINCT employee_id, matricule, nom_complet
        FROM base
      ) b USING (employee_id)
      ORDER BY nom_complet
      LIMIT 10;
    """

    try:
        provider = PostgresProvider()
        rows = provider.repo.run_query(sql)

        print("✅ Requête exécutée avec succès")
        print(f"📊 Nombre de résultats: {len(rows)}")

        if rows:
            print("\n📋 Premiers résultats:")
            print(
                f"{'ID':<8} {'Matricule':<12} {'Nom':<30} {'Date':<12} {'Statut':<8} {'Montant':<12}"
            )
            print("-" * 90)
            for row in rows[:5]:
                emp_id = row[0]
                matricule = row[1] or "-"
                nom = (row[2] or "-")[:28]
                date_paie = str(row[3]) if row[3] else "-"
                statut = row[6] or "-"
                montant = f"${row[7]:,.2f}" if row[7] else "$0.00"
                print(
                    f"{emp_id:<8} {matricule:<12} {nom:<30} {date_paie:<12} {statut:<8} {montant:<12}"
                )
        else:
            print("⚠️ Aucun résultat trouvé")

            # Vérifier si des données existent pour cette date
            print(f"\n🔍 Vérification des données pour {date}:")
            check_sql = f"""
                SELECT COUNT(*) as total_transactions,
                       COUNT(DISTINCT employee_id) as nb_employes
                FROM payroll.payroll_transactions
                WHERE pay_date = DATE '{date}'
            """
            check_rows = provider.repo.run_query(check_sql)
            if check_rows:
                total = check_rows[0][0]
                nb_emp = check_rows[0][1]
                print(f"   Transactions: {total}")
                print(f"   Employés distincts: {nb_emp}")

                if total > 0:
                    print(
                        "\n⚠️ Des transactions existent mais la requête ne retourne rien"
                    )
                    print(
                        "   Vérifiez la jointure avec core.employees et paie.stg_paie_transactions"
                    )

                    # Vérifier la jointure avec employees
                    check_emp_sql = f"""
                        SELECT COUNT(*) 
                        FROM payroll.payroll_transactions t
                        JOIN core.employees e ON e.employee_id = t.employee_id
                        WHERE t.pay_date = DATE '{date}'
                    """
                    check_emp = provider.repo.run_query(check_emp_sql)
                    if check_emp:
                        print(f"   Jointure avec employees: {check_emp[0][0]} lignes")

                    # Vérifier la jointure avec stg_paie_transactions
                    check_stg_sql = f"""
                        SELECT COUNT(*) 
                        FROM payroll.payroll_transactions t
                        LEFT JOIN paie.stg_paie_transactions s
                          ON s.source_file = t.source_file AND s.source_row_number = t.source_row_no
                        WHERE t.pay_date = DATE '{date}'
                    """
                    check_stg = provider.repo.run_query(check_stg_sql)
                    if check_stg:
                        print(
                            f"   Jointure avec stg_paie_transactions: {check_stg[0][0]} lignes"
                        )

        provider.repo.close_pool()
        return rows

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_last_date():
    """Test pour obtenir la dernière date disponible"""
    print(f"\n{'='*70}")
    print("TEST: Dernière date disponible")
    print(f"{'='*70}\n")

    sql = "SELECT MAX(pay_date)::text AS last_date FROM payroll.payroll_transactions"

    try:
        provider = PostgresProvider()
        rows = provider.repo.run_query(sql)

        if rows and rows[0][0]:
            print(f"✅ Dernière date: {rows[0][0]}")
            return rows[0][0]
        else:
            print("⚠️ Aucune date trouvée")
            return None

        provider.repo.close_pool()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("=" * 70)
    print("🔍 TEST DES REQUÊTES SQL - Page Employees")
    print("=" * 70)

    # Test 1: Obtenir la dernière date
    last_date = test_last_date()

    # Test 2: Tester la requête pour cette date
    if last_date:
        test_sql_for_day(last_date)
    else:
        # Essayer avec une date connue
        print("\n⚠️ Aucune date trouvée, test avec 2025-08-28")
        test_sql_for_day("2025-08-28")

    print("\n" + "=" * 70)
    print("✅ Tests terminés")
    print("=" * 70)
