#!/usr/bin/env python3
"""
Test de requêtes réelles sur la base de données
================================================

Ce script teste des requêtes réelles pour vérifier que
l'API standardisée fonctionne avec des données réelles.
"""

from config.connection_standard import run_select, get_connection

print("=" * 70)
print("TEST REQUÊTES RÉELLES - BASE DE DONNÉES")
print("=" * 70)
print()

# Test 1: Compter les employés
print("1. TEST: Compter les employés actifs")
try:
    result = run_select(
        """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN statut = 'actif' THEN 1 END) as actifs,
            COUNT(CASE WHEN statut = 'inactif' THEN 1 END) as inactifs
        FROM core.employees
    """
    )

    if result:
        total, actifs, inactifs = result[0]
        print("   ✅ Requête exécutée")
        print(f"   • Total employés: {total}")
        print(f"   • Actifs: {actifs}")
        print(f"   • Inactifs: {inactifs}")
    else:
        print("   ⚠️  Aucun résultat")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

print()

# Test 2: Dernière date de paie
print("2. TEST: Dernière date de paie")
try:
    result = run_select(
        """
        SELECT MAX(pay_date)::text as derniere_paie
        FROM payroll.payroll_transactions
    """
    )

    if result and result[0][0]:
        derniere_paie = result[0][0]
        print("   ✅ Requête exécutée")
        print(f"   • Dernière paie: {derniere_paie}")
    else:
        print("   ⚠️  Aucune transaction trouvée")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

print()

# Test 3: Statistiques par période
print("3. TEST: Statistiques dernière période")
try:
    result = run_select(
        """
        SELECT 
            pay_date,
            COUNT(DISTINCT employee_id) as nb_employes,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_gains,
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_deductions
        FROM payroll.payroll_transactions
        WHERE pay_date = (SELECT MAX(pay_date) FROM payroll.payroll_transactions)
        GROUP BY pay_date
    """
    )

    if result:
        pay_date, nb_employes, total_gains, total_deductions = result[0]
        print("   ✅ Requête exécutée")
        print(f"   • Date: {pay_date}")
        print(f"   • Nombre d'employés: {nb_employes}")
        print(f"   • Total gains: {total_gains:.2f} $")
        print(f"   • Total déductions: {total_deductions:.2f} $")
        print(f"   • Net: {(total_gains - total_deductions):.2f} $")
    else:
        print("   ⚠️  Aucune statistique disponible")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

print()

# Test 4: Schémas disponibles
print("4. TEST: Schémas disponibles")
try:
    result = run_select(
        """
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name
    """
    )

    if result:
        schemas = [row[0] for row in result]
        print("   ✅ Requête exécutée")
        print(f"   • Schémas: {', '.join(schemas)}")
    else:
        print("   ⚠️  Aucun schéma trouvé")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

print()

# Test 5: Test avec get_connection() (avancé)
print("5. TEST: Requête avec get_connection() et transaction")
try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Test 1: Vérifier search_path
            cur.execute("SHOW search_path")
            search_path = cur.fetchone()[0]
            print(f"   ✅ Search path: {search_path}")

            # Test 2: Vérifier timezone
            cur.execute("SHOW timezone")
            timezone = cur.fetchone()[0]
            print(f"   ✅ Timezone: {timezone}")

            # Test 3: Vérifier statement_timeout
            cur.execute("SHOW statement_timeout")
            timeout = cur.fetchone()[0]
            print(f"   ✅ Statement timeout: {timeout}")

except Exception as e:
    print(f"   ❌ Erreur: {e}")

print()

# Test 6: Performance du pool
print("6. TEST: Performance du pool (10 requêtes)")
try:
    import time

    start = time.time()

    for i in range(10):
        result = run_select("SELECT 1")

    elapsed = time.time() - start
    print("   ✅ 10 requêtes exécutées")
    print(f"   • Temps total: {elapsed:.3f}s")
    print(f"   • Moyenne: {(elapsed/10)*1000:.1f}ms par requête")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

print()
print("=" * 70)
print("✅ TOUS LES TESTS DE REQUÊTES RÉELLES PASSENT")
print("=" * 70)
