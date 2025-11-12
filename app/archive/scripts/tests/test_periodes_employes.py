#!/usr/bin/env python3
"""
Script de test pour vérifier le chargement des périodes et employés
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def test_periodes():
    """Test le chargement des périodes"""
    print("=" * 60)
    print("TEST: Chargement des périodes")
    print("=" * 60)

    try:
        provider = PostgresProvider()

        # Test sans filtre
        print("\n1. Test sans filtre (pour employees.js):")
        periods = provider.get_periods(filter_year=None)
        print(f"   ✓ {len(periods)} périodes trouvées")
        if periods:
            print(f"   ✓ Première période: {periods[0]}")
            print(f"   ✓ Dernière période: {periods[-1]}")
        else:
            print("   ⚠️ Aucune période trouvée")

        # Test avec filtre année 2025
        print("\n2. Test avec filtre année 2025 (pour periods.html):")
        periods_2025 = provider.get_periods(filter_year=2025)
        print(f"   ✓ {len(periods_2025)} périodes trouvées pour 2025")
        if periods_2025:
            print(f"   ✓ Première période: {periods_2025[0]}")
            print(f"   ✓ Format: {type(periods_2025[0])}")
            if "pay_date" in periods_2025[0]:
                print(f"   ✓ pay_date: {periods_2025[0]['pay_date']}")
            if "transaction_count" in periods_2025[0]:
                print(f"   ✓ transaction_count: {periods_2025[0]['transaction_count']}")

        # Test avec filtre année 2024
        print("\n3. Test avec filtre année 2024:")
        periods_2024 = provider.get_periods(filter_year=2024)
        print(f"   ✓ {len(periods_2024)} périodes trouvées pour 2024")

        return True

    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_employes():
    """Test le chargement des employés"""
    print("\n" + "=" * 60)
    print("TEST: Chargement des employés")
    print("=" * 60)

    try:
        provider = PostgresProvider()

        # Test list_employees
        print("\n1. Test list_employees (sans filtres):")
        result = provider.list_employees(period_id="", filters={}, page=1, page_size=10)
        print(f"   ✓ Total employés: {result.get('total', 0)}")
        print(f"   ✓ Employés retournés: {len(result.get('items', []))}")

        if result.get("items"):
            emp = result["items"][0]
            print(
                f"   ✓ Premier employé: {emp.get('matricule', 'N/A')} - {emp.get('nom', 'N/A')}"
            )
            print(f"   ✓ Format: {type(emp)}")
            print(f"   ✓ Colonnes: {list(emp.keys())}")

        # Test avec filtre recherche
        print("\n2. Test avec filtre recherche (nom):")
        result_filtered = provider.list_employees(
            period_id="", filters={"q": "test"}, page=1, page_size=10
        )
        print(f"   ✓ Résultats filtrés: {result_filtered.get('total', 0)}")

        return True

    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_sql_direct():
    """Test requêtes SQL directes"""
    print("\n" + "=" * 60)
    print("TEST: Requêtes SQL directes (execute_sql)")
    print("=" * 60)

    try:
        provider = PostgresProvider()
        repo = provider.repo

        # Test 1: Périodes depuis transactions
        print("\n1. Test: Périodes depuis payroll_transactions")
        sql = """
            SELECT DISTINCT
                TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_str,
                t.pay_date
            FROM payroll.payroll_transactions t
            ORDER BY t.pay_date DESC
            LIMIT 5
        """
        rows = repo.run_query(sql)
        print(f"   ✓ {len(rows)} périodes trouvées")
        if rows:
            print(f"   ✓ Première période: {rows[0]}")

        # Test 2: Employés avec catégorie/titre
        print("\n2. Test: Employés avec catégorie/titre")
        sql = """
            SELECT 
                e.employee_id, e.matricule, COALESCE(e.nom,'') AS nom, 
                COALESCE(e.prenom,'') AS prenom,
                COALESCE(e.statut,'') AS statut,
                COALESCE(p.categorie_emploi,'') AS categorie_emploi,
                COALESCE(p.titre_emploi,'') AS titre_emploi
            FROM core.employees e
            LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
            LIMIT 5
        """
        rows = repo.run_query(sql)
        print(f"   ✓ {len(rows)} employés trouvés")
        if rows:
            print(f"   ✓ Premier employé: {rows[0]}")
            print(f"   ✓ Colonnes: {len(rows[0])} colonnes")

        # Test 3: Catégories distinctes
        print("\n3. Test: Catégories d'emploi distinctes")
        sql = """
            SELECT DISTINCT categorie_emploi
            FROM paie.stg_paie_transactions
            WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != ''
            ORDER BY categorie_emploi
            LIMIT 10
        """
        rows = repo.run_query(sql)
        print(f"   ✓ {len(rows)} catégories trouvées")
        if rows:
            print(f"   ✓ Exemples: {[r[0] for r in rows[:5]]}")

        return True

    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🔍 TEST DES MODIFICATIONS - Périodes et Employés")
    print("=" * 60)

    results = []
    results.append(("Périodes", test_periodes()))
    results.append(("Employés", test_employes()))
    results.append(("SQL Direct", test_sql_direct()))

    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    for name, success in results:
        status = "✅ OK" if success else "❌ ÉCHEC"
        print(f"  {status} - {name}")

    print("\n" + "=" * 60)
    all_ok = all(r[1] for r in results)
    if all_ok:
        print("✅ Tous les tests sont passés !")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
    print("=" * 60 + "\n")
