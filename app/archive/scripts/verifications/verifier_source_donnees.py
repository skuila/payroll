#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour vérifier où sont stockées les catégories et titres
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
    print("  RECHERCHE DES CATÉGORIES ET TITRES DANS TOUTES LES TABLES")
    print("=" * 80 + "\n")

    # Vérifier imported_payroll_master
    print("📋 Vérification payroll.imported_payroll_master:")
    print("-" * 80)
    sql_check_cols = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'payroll' 
        AND table_name = 'imported_payroll_master'
        AND (column_name LIKE '%%categorie%%' OR column_name LIKE '%%titre%%')
        ORDER BY column_name
    """
    result_cols = provider.repo.run_query(sql_check_cols)
    if result_cols and isinstance(result_cols, list):
        for row in result_cols:
            print(f"  • {row[0]} ({row[1]})")
    print()

    # Vérifier les données dans imported_payroll_master
    sql_cat_ipm = """
        SELECT DISTINCT categorie_emploi, COUNT(*) as nb
        FROM payroll.imported_payroll_master 
        WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != '' 
        GROUP BY categorie_emploi
        ORDER BY categorie_emploi
        LIMIT 10
    """
    result_cat_ipm = provider.repo.run_query(sql_cat_ipm)
    if result_cat_ipm and isinstance(result_cat_ipm, list) and len(result_cat_ipm) > 0:
        print("  Catégories trouvées:")
        for row in result_cat_ipm:
            print(f"    • {row[0]} ({row[1]} occurrences)")
    else:
        print("  Aucune catégorie non vide trouvée")

    sql_title_ipm = """
        SELECT DISTINCT titre_emploi, COUNT(*) as nb
        FROM payroll.imported_payroll_master 
        WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != '' 
        GROUP BY titre_emploi
        ORDER BY titre_emploi
        LIMIT 10
    """
    result_title_ipm = provider.repo.run_query(sql_title_ipm)
    if (
        result_title_ipm
        and isinstance(result_title_ipm, list)
        and len(result_title_ipm) > 0
    ):
        print("  Titres trouvés:")
        for row in result_title_ipm:
            print(f"    • {row[0]} ({row[1]} occurrences)")
    else:
        print("  Aucun titre non vide trouvé")
    print()

    # Vérifier les colonnes de stg_paie_transactions
    print("📋 Colonnes de paie.stg_paie_transactions:")
    print("-" * 80)
    sql_stg_cols = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'paie' 
        AND table_name = 'stg_paie_transactions'
        ORDER BY ordinal_position
    """
    result_stg_cols = provider.repo.run_query(sql_stg_cols)
    if result_stg_cols and isinstance(result_stg_cols, list):
        for row in result_stg_cols:
            print(f"  • {row[0]} ({row[1]})")
    print()

    # Vérifier un échantillon de données de stg_paie_transactions
    print(
        "📋 Échantillon de données de paie.stg_paie_transactions (5 premières lignes):"
    )
    print("-" * 80)
    sql_sample = """
        SELECT 
            source_file,
            source_row_number,
            categorie_emploi,
            titre_emploi,
            nom_prenom
        FROM paie.stg_paie_transactions
        ORDER BY source_file, source_row_number
        LIMIT 5
    """
    result_sample = provider.repo.run_query(sql_sample)
    if result_sample and isinstance(result_sample, list):
        for row in result_sample:
            print(f"  Fichier: {row[0]}, Ligne: {row[1]}")
            print(
                f"    Catégorie: {repr(row[2])}, Titre: {repr(row[3])}, Nom: {row[4]}"
            )
    print()

    print("=" * 80)
    print("  ✅ Vérification terminée")
    print("=" * 80 + "\n")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
