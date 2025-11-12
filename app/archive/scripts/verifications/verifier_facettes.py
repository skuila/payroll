#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour vérifier les catégories et titres disponibles dans la base
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
    print("  VÉRIFICATION DES CATÉGORIES ET TITRES DISPONIBLES")
    print("=" * 80 + "\n")

    # Vérifier stg_paie_transactions
    print("📋 CATÉGORIES dans paie.stg_paie_transactions:")
    print("-" * 80)
    sql_cat_stg = """
        SELECT DISTINCT categorie_emploi, COUNT(*) as nb
        FROM paie.stg_paie_transactions 
        WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != '' 
        GROUP BY categorie_emploi
        ORDER BY categorie_emploi
        LIMIT 20
    """
    result_cat_stg = provider.repo.run_query(sql_cat_stg)
    if result_cat_stg and isinstance(result_cat_stg, list):
        for row in result_cat_stg:
            print(f"  • {row[0]} ({row[1]} occurrences)")
    else:
        print("  Aucune catégorie trouvée")
    print()

    print("📋 TITRES dans paie.stg_paie_transactions:")
    print("-" * 80)
    sql_title_stg = """
        SELECT DISTINCT titre_emploi, COUNT(*) as nb
        FROM paie.stg_paie_transactions 
        WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != '' 
        GROUP BY titre_emploi
        ORDER BY titre_emploi
        LIMIT 20
    """
    result_title_stg = provider.repo.run_query(sql_title_stg)
    if result_title_stg and isinstance(result_title_stg, list):
        for row in result_title_stg:
            print(f"  • {row[0]} ({row[1]} occurrences)")
    else:
        print("  Aucun titre trouvé")
    print()

    # Vérifier aussi v_employe_profil
    print("📋 CATÉGORIES dans paie.v_employe_profil:")
    print("-" * 80)
    sql_cat_prof = """
        SELECT DISTINCT categorie_emploi, COUNT(*) as nb
        FROM paie.v_employe_profil 
        WHERE categorie_emploi IS NOT NULL AND categorie_emploi != '' 
        GROUP BY categorie_emploi
        ORDER BY categorie_emploi
        LIMIT 20
    """
    result_cat_prof = provider.repo.run_query(sql_cat_prof)
    if result_cat_prof and isinstance(result_cat_prof, list):
        for row in result_cat_prof:
            print(f"  • {row[0]} ({row[1]} occurrences)")
    else:
        print("  Aucune catégorie trouvée")
    print()

    print("📋 TITRES dans paie.v_employe_profil:")
    print("-" * 80)
    sql_title_prof = """
        SELECT DISTINCT titre_emploi, COUNT(*) as nb
        FROM paie.v_employe_profil 
        WHERE titre_emploi IS NOT NULL AND titre_emploi != '' 
        GROUP BY titre_emploi
        ORDER BY titre_emploi
        LIMIT 20
    """
    result_title_prof = provider.repo.run_query(sql_title_prof)
    if result_title_prof and isinstance(result_title_prof, list):
        for row in result_title_prof:
            print(f"  • {row[0]} ({row[1]} occurrences)")
    else:
        print("  Aucun titre trouvé")
    print()

    # Vérifier le nombre total de lignes dans stg_paie_transactions
    print("📊 STATISTIQUES:")
    print("-" * 80)
    sql_stats = """
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT categorie_emploi) as nb_cat_distinctes,
            COUNT(DISTINCT titre_emploi) as nb_titres_distincts,
            COUNT(DISTINCT CASE WHEN categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != '' THEN categorie_emploi END) as nb_cat_non_vides,
            COUNT(DISTINCT CASE WHEN titre_emploi IS NOT NULL AND TRIM(titre_emploi) != '' THEN titre_emploi END) as nb_titres_non_vides
        FROM paie.stg_paie_transactions
    """
    result_stats = provider.repo.run_query(sql_stats)
    if result_stats and isinstance(result_stats, list) and len(result_stats) > 0:
        row = result_stats[0]
        print(f"  Total lignes: {row[0]}")
        print(f"  Catégories distinctes (toutes): {row[1]}")
        print(f"  Titres distincts (tous): {row[2]}")
        print(f"  Catégories distinctes (non vides): {row[3]}")
        print(f"  Titres distincts (non vides): {row[4]}")
    print()

    print("=" * 80)
    print("  ✅ Vérification terminée")
    print("=" * 80 + "\n")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
