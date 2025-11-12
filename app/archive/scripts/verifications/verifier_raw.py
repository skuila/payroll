#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour vérifier les données dans les colonnes _raw
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
    print("  VÉRIFICATION DES DONNÉES RAW")
    print("=" * 80 + "\n")

    # Vérifier les catégories dans les colonnes _raw
    print("📋 CATÉGORIES dans categorie_emploi_raw:")
    print("-" * 80)
    sql_cat_raw = """
        SELECT DISTINCT categorie_emploi_raw, COUNT(*) as nb
        FROM paie.stg_paie_transactions 
        WHERE categorie_emploi_raw IS NOT NULL AND TRIM(categorie_emploi_raw) != '' 
        GROUP BY categorie_emploi_raw
        ORDER BY categorie_emploi_raw
        LIMIT 20
    """
    result_cat_raw = provider.repo.run_query(sql_cat_raw)
    if result_cat_raw and isinstance(result_cat_raw, list):
        for row in result_cat_raw:
            print(f"  • {row[0]} ({row[1]} occurrences)")
    else:
        print("  Aucune catégorie trouvée")
    print()

    print("📋 TITRES dans titre_emploi_raw:")
    print("-" * 80)
    sql_title_raw = """
        SELECT DISTINCT titre_emploi_raw, COUNT(*) as nb
        FROM paie.stg_paie_transactions 
        WHERE titre_emploi_raw IS NOT NULL AND TRIM(titre_emploi_raw) != '' 
        GROUP BY titre_emploi_raw
        ORDER BY titre_emploi_raw
        LIMIT 20
    """
    result_title_raw = provider.repo.run_query(sql_title_raw)
    if result_title_raw and isinstance(result_title_raw, list):
        for row in result_title_raw:
            print(f"  • {row[0]} ({row[1]} occurrences)")
    else:
        print("  Aucun titre trouvé")
    print()

    # Vérifier un échantillon avec les valeurs raw
    print("📋 Échantillon avec valeurs raw:")
    print("-" * 80)
    sql_sample_raw = """
        SELECT 
            categorie_emploi_raw,
            titre_emploi_raw,
            categorie_emploi,
            titre_emploi,
            nom_prenom
        FROM paie.stg_paie_transactions
        WHERE (categorie_emploi_raw IS NOT NULL AND TRIM(categorie_emploi_raw) != '')
           OR (titre_emploi_raw IS NOT NULL AND TRIM(titre_emploi_raw) != '')
        ORDER BY source_file, source_row_number
        LIMIT 5
    """
    result_sample_raw = provider.repo.run_query(sql_sample_raw)
    if result_sample_raw and isinstance(result_sample_raw, list):
        for row in result_sample_raw:
            print(f"  Raw: Cat={repr(row[0])}, Titre={repr(row[1])}")
            print(
                f"  Normalisé: Cat={repr(row[2])}, Titre={repr(row[3])}, Nom={row[4]}"
            )
    else:
        print("  Aucune donnée avec valeurs raw non vides")
    print()

    print("=" * 80)
    print("  ✅ Vérification terminée")
    print("=" * 80 + "\n")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
