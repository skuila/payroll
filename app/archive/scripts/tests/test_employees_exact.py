"""
Test exact qui simule le comportement du code JavaScript
"""

import sys
from pathlib import Path
import json

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def test_exact_simulation():
    """Simule exactement ce que fait le code JavaScript"""
    print("=" * 70)
    print("TEST EXACT - Simulation du code JavaScript")
    print("=" * 70)

    provider = PostgresProvider()

    # Étape 1: Obtenir la dernière date (comme getLastPayDate)
    print("\n1. Obtention de la dernière date...")
    sql_last_date = (
        "SELECT MAX(pay_date)::text AS last_date FROM payroll.payroll_transactions"
    )
    rows_last = provider.repo.run_query(sql_last_date)
    if rows_last and rows_last[0][0]:
        test_date = rows_last[0][0]
        print(f"   ✅ Dernière date: {test_date}")
    else:
        test_date = "2025-08-28"
        print(f"   ⚠️ Aucune date trouvée, utilisation de: {test_date}")

    # Étape 2: Exécuter la requête SQL exacte (comme sqlForDay)
    print(f"\n2. Exécution de la requête SQL pour {test_date}...")
    sql = f"""
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
      WHERE t.pay_date = DATE '{test_date}'
      GROUP BY e.employee_id, e.matricule_norm, e.nom_complet, e.nom_norm, e.prenom_norm
      ORDER BY nom_complet
    """

    try:
        rows = provider.repo.run_query(sql)
        print(f"   ✅ Requête exécutée: {len(rows)} lignes retournées")

        # Étape 3: Simuler le format de retour de execute_sql (comme toArray)
        print("\n3. Simulation du format execute_sql...")
        result_json = json.dumps({"rows": rows})
        print(f"   Format JSON: {len(result_json)} caractères")

        # Étape 4: Parser comme le fait toArray
        parsed = json.loads(result_json)
        if parsed and parsed.get("rows") and isinstance(parsed["rows"], list):
            rows_array = parsed["rows"]
            print(f"   ✅ Format rows trouvé: {len(rows_array)} lignes")
        else:
            print(f"   ❌ Format non reconnu: {parsed}")
            provider.repo.close_pool()
            return

        # Étape 5: Simuler rowsToObjects
        print("\n4. Conversion en objets (rowsToObjects)...")
        columns = [
            "employee_id",
            "matricule",
            "nom_complet",
            "pay_date",
            "categorie_emploi",
            "titre_emploi",
            "statut_calcule",
            "amount_paid",
        ]
        objects = []

        for row_idx, row in enumerate(rows_array):
            if not isinstance(row, (list, tuple)):
                print(f"   ❌ Ligne {row_idx} n'est pas un tableau: {row}")
                continue

            obj = {}
            for col_idx, col_name in enumerate(columns):
                if col_idx < len(row):
                    obj[col_name] = row[col_idx]
                else:
                    obj[col_name] = None

            objects.append(obj)

        print(f"   ✅ {len(objects)} objets créés")

        # Étape 6: Afficher les résultats
        print("\n5. Résultats finaux:")
        print("-" * 100)
        print(
            f"{'ID':<8} {'Matricule':<12} {'Nom':<30} {'Catégorie':<20} {'Statut':<8} {'Montant':<12}"
        )
        print("-" * 100)

        for obj in objects[:10]:  # Afficher les 10 premiers
            emp_id = obj.get("employee_id", "-")
            matricule = str(obj.get("matricule", "-"))[:12]
            nom = str(obj.get("nom_complet", "-"))[:28]
            categorie = str(obj.get("categorie_emploi", "-"))[:18]
            statut = str(obj.get("statut_calcule", "-"))
            montant = (
                f"${obj.get('amount_paid', 0):,.2f}"
                if obj.get("amount_paid")
                else "$0.00"
            )

            print(
                f"{emp_id:<8} {matricule:<12} {nom:<30} {categorie:<20} {statut:<8} {montant:<12}"
            )

        if len(objects) > 10:
            print(f"... et {len(objects) - 10} autres employés")

        # Étape 7: Vérifier les KPIs
        print("\n6. Calcul des KPIs (comme updateSummary)...")
        total = len(objects)
        actifs = sum(
            1 for o in objects if str(o.get("statut_calcule", "")).lower() == "actif"
        )
        inactifs = total - actifs
        total_pay = sum(float(o.get("amount_paid", 0) or 0) for o in objects)

        print(f"   Total employés: {total}")
        print(f"   Actifs: {actifs}")
        print(f"   Inactifs: {inactifs}")
        print(f"   Total payé: ${total_pay:,.2f}")

        if total == 0:
            print("\n❌ PROBLÈME: Aucun employé trouvé!")
            print("\n   Vérifications supplémentaires:")

            # Vérifier si des transactions existent
            check_sql = f"SELECT COUNT(*) FROM payroll.payroll_transactions WHERE pay_date = DATE '{test_date}'"
            check_rows = provider.repo.run_query(check_sql)
            if check_rows:
                print(f"   - Transactions pour {test_date}: {check_rows[0][0]}")

            # Vérifier la jointure avec employees
            check_emp = f"""
                SELECT COUNT(*) 
                FROM payroll.payroll_transactions t
                JOIN core.employees e ON e.employee_id = t.employee_id
                WHERE t.pay_date = DATE '{test_date}'
            """
            check_emp_rows = provider.repo.run_query(check_emp)
            if check_emp_rows:
                print(f"   - Jointure avec employees: {check_emp_rows[0][0]}")
        else:
            print("\n✅ SUCCÈS: Les données sont disponibles!")

    except Exception as e:
        print(f"\n❌ ERREUR lors de l'exécution: {e}")
        import traceback

        traceback.print_exc()

    provider.repo.close_pool()


if __name__ == "__main__":
    test_exact_simulation()
