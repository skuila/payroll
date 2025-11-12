#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour vérifier que les filtres fonctionnent correctement après mise à jour
"""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

try:
    from app.providers.postgres_provider import PostgresProvider

    provider = PostgresProvider()

    if not provider.repo:
        print("❌ Impossible de se connecter à la base de données")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("  VÉRIFICATION DES FILTRES APRÈS MISE À JOUR")
    print("=" * 80 + "\n")

    # Vérifier les catégories disponibles pour les filtres
    print("📋 CATÉGORIES DISPONIBLES POUR LES FILTRES:")
    print("-" * 80)
    sql_cat = """
        SELECT DISTINCT categorie_emploi
        FROM paie.stg_paie_transactions
        WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != ''
        ORDER BY categorie_emploi
    """
    result_cat = provider.repo.run_query(sql_cat)
    if result_cat and isinstance(result_cat, list):
        print(f"  Total: {len(result_cat)} catégories")
        for row in result_cat:
            print(f"  • {row[0]}")
    print()

    # Vérifier les titres disponibles pour les filtres
    print("📋 TITRES DISPONIBLES POUR LES FILTRES:")
    print("-" * 80)
    sql_title = """
        SELECT DISTINCT titre_emploi
        FROM paie.stg_paie_transactions
        WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != ''
        ORDER BY titre_emploi
        LIMIT 20
    """
    result_title = provider.repo.run_query(sql_title)
    if result_title and isinstance(result_title, list):
        print(f"  Total: {len(result_title)} titres affichés (premiers)")
        for row in result_title:
            print(f"  • {row[0]}")
    print()

    # Test de filtrage par catégorie
    print("🔍 TEST FILTRE PAR CATÉGORIE:")
    print("-" * 80)
    sql_test_cat = """
        SELECT 
            COUNT(DISTINCT e.employee_id) as nb_employes
        FROM core.employees e
        LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
        WHERE COALESCE(p.categorie_emploi, '') = 'Enseignant'
    """
    result_test_cat = provider.repo.run_query(sql_test_cat)
    if result_test_cat and isinstance(result_test_cat, list):
        print(f"  Catégorie 'Enseignant': {result_test_cat[0][0]} employé(s)")
    print()

    # Test de filtrage par titre
    print("🔍 TEST FILTRE PAR TITRE:")
    print("-" * 80)
    sql_test_title = """
        SELECT 
            COUNT(DISTINCT e.employee_id) as nb_employes
        FROM core.employees e
        LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
        WHERE COALESCE(p.titre_emploi, '') LIKE '%Enseignant%'
    """
    result_test_title = provider.repo.run_query(sql_test_title)
    if result_test_title and isinstance(result_test_title, list):
        print(f"  Titre contenant 'Enseignant': {result_test_title[0][0]} employé(s)")
    print()

    print("=" * 80)
    print("  ✅ Vérification terminée")
    print("=" * 80 + "\n")
    print("💡 Les filtres devraient maintenant fonctionner dans l'interface web!")
    print("   Ouvrez la page 'Employés' et testez les filtres de catégorie et titre.")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
finally:
    # Fermer proprement le pool
    try:
        if provider and provider.repo:
            provider.repo.close()
    except Exception as _exc:
        pass
    import gc

    gc.collect()
