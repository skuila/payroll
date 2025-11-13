#!/usr/bin/env python3
"""
Test de l'API standardisée connection_standard
===============================================

Ce script teste toutes les fonctions de l'API.
"""

from config.connection_standard import (
    get_dsn,
    get_connection_pool,
    get_connection,
    run_select,
    test_connection,
    mask_dsn,
)

print("=" * 70)
print("TEST API STANDARDISÉE connection_standard")
print("=" * 70)
print()

# Test 1: get_dsn()
print("1. TEST get_dsn():")
try:
    dsn = get_dsn()
    print(f"   ✅ DSN obtenu: {mask_dsn(dsn)}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

print()

# Test 2: test_connection()
print("2. TEST test_connection():")
try:
    result = test_connection()
    if result["success"]:
        print("   ✅ Connexion réussie")
        print(f"   • Utilisateur: {result['user']}")
        print(f"   • Base: {result['database']}")
        print(f"   • Version: {result['version']}")
    else:
        print(f"   ❌ Échec: {result['error']}")
        exit(1)
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

print()

# Test 3: run_select()
print("3. TEST run_select():")
try:
    data = run_select("SELECT 1 AS test, current_user, current_database()")
    print("   ✅ Requête exécutée")
    print(f"   • Résultat: {data}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

print()

# Test 4: get_connection()
print("4. TEST get_connection():")
try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM core.employees")
            count = cur.fetchone()[0]
            print("   ✅ Connexion obtenue du pool")
            print(f"   • Nombre d'employés: {count}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

print()

# Test 5: get_connection_pool()
print("5. TEST get_connection_pool():")
try:
    pool = get_connection_pool()
    print("   ✅ Pool obtenu")
    print(f"   • Type: {type(pool).__name__}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

print()

# Test 6: Requête avec paramètres
print("6. TEST run_select() avec paramètres:")
try:
    data = run_select(
        "SELECT matricule, nom, prenom FROM core.employees WHERE statut = %(statut)s LIMIT 3",
        {"statut": "actif"},
    )
    print("   ✅ Requête avec paramètres exécutée")
    print(f"   • Nombre de résultats: {len(data)}")
    if data:
        print(f"   • Premier employé: {data[0]}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

print()
print("=" * 70)
print("✅ TOUS LES TESTS API PASSENT")
print("=" * 70)
