#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour tester et compter les employés par catégorie et titre d'emploi
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
    print("  COMPTAGE DES EMPLOYÉS PAR CATÉGORIE ET TITRE D'EMPLOI")
    print("=" * 80 + "\n")

    # 1. Chercher dans toutes les tables/vues possibles
    print("🔍 RECHERCHE DES SOURCES DE DONNÉES...")
    print("-" * 80)

    # Test 1: paie.v_employe_profil (vue consolidée)
    print("\n📊 SOURCE 1: paie.v_employe_profil")
    print("-" * 80)
    sql_profil = """
        SELECT 
            COALESCE(categorie_emploi, 'Non défini') as categorie,
            COALESCE(titre_emploi, 'Non défini') as titre,
            COUNT(DISTINCT employee_id) as nb_employes
        FROM paie.v_employe_profil
        GROUP BY categorie_emploi, titre_emploi
        ORDER BY nb_employes DESC, categorie, titre
    """
    result_profil = provider.repo.run_query(sql_profil)
    if result_profil and isinstance(result_profil, list):
        print(f"  Total combinaisons: {len(result_profil)}")
        for row in result_profil[:10]:  # Afficher les 10 premiers
            print(f"  • {row[0]} / {row[1]}: {row[2]} employé(s)")
    print()

    # Test 2: paie.stg_paie_transactions (colonnes normalisées)
    print("📊 SOURCE 2: paie.stg_paie_transactions (colonnes normalisées)")
    print("-" * 80)
    sql_stg_norm = """
        SELECT 
            COALESCE(categorie_emploi, 'Non défini') as categorie,
            COALESCE(titre_emploi, 'Non défini') as titre,
            COUNT(DISTINCT matricule) as nb_employes
        FROM paie.stg_paie_transactions
        WHERE matricule IS NOT NULL AND TRIM(matricule) != ''
        GROUP BY categorie_emploi, titre_emploi
        ORDER BY nb_employes DESC, categorie, titre
        LIMIT 20
    """
    result_stg_norm = provider.repo.run_query(sql_stg_norm)
    if result_stg_norm and isinstance(result_stg_norm, list):
        print(f"  Total combinaisons: {len(result_stg_norm)}")
        for row in result_stg_norm:
            print(f"  • {row[0]} / {row[1]}: {row[2]} employé(s)")
    print()

    # Test 3: paie.stg_paie_transactions (colonnes raw)
    print("📊 SOURCE 3: paie.stg_paie_transactions (colonnes raw)")
    print("-" * 80)
    sql_stg_raw = """
        SELECT 
            COALESCE(categorie_emploi_raw, 'Non défini') as categorie,
            COALESCE(titre_emploi_raw, 'Non défini') as titre,
            COUNT(DISTINCT matricule_raw) as nb_employes
        FROM paie.stg_paie_transactions
        WHERE matricule_raw IS NOT NULL AND TRIM(matricule_raw) != ''
        GROUP BY categorie_emploi_raw, titre_emploi_raw
        ORDER BY nb_employes DESC, categorie, titre
        LIMIT 20
    """
    result_stg_raw = provider.repo.run_query(sql_stg_raw)
    if result_stg_raw and isinstance(result_stg_raw, list):
        print(f"  Total combinaisons: {len(result_stg_raw)}")
        for row in result_stg_raw:
            print(f"  • {row[0]} / {row[1]}: {row[2]} employé(s)")
    print()

    # Test 4: payroll.payroll_transactions jointe avec stg_paie_transactions
    print("📊 SOURCE 4: payroll.payroll_transactions + paie.stg_paie_transactions")
    print("-" * 80)
    sql_trans = """
        SELECT 
            COALESCE(s.categorie_emploi, 'Non défini') as categorie,
            COALESCE(s.titre_emploi, 'Non défini') as titre,
            COUNT(DISTINCT t.employee_id) as nb_employes
        FROM payroll.payroll_transactions t
        LEFT JOIN paie.stg_paie_transactions s 
            ON t.source_file = s.source_file 
            AND t.source_row_no = s.source_row_number
        GROUP BY s.categorie_emploi, s.titre_emploi
        ORDER BY nb_employes DESC, categorie, titre
        LIMIT 20
    """
    result_trans = provider.repo.run_query(sql_trans)
    if result_trans and isinstance(result_trans, list):
        print(f"  Total combinaisons: {len(result_trans)}")
        for row in result_trans:
            print(f"  • {row[0]} / {row[1]}: {row[2]} employé(s)")
    print()

    # Test 5: payroll.imported_payroll_master
    print("📊 SOURCE 5: payroll.imported_payroll_master")
    print("-" * 80)
    sql_ipm = """
        SELECT 
            COALESCE(categorie_emploi, 'Non défini') as categorie,
            COALESCE(titre_emploi, 'Non défini') as titre,
            COUNT(DISTINCT matricule) as nb_employes
        FROM payroll.imported_payroll_master
        WHERE matricule IS NOT NULL AND TRIM(matricule) != ''
        GROUP BY categorie_emploi, titre_emploi
        ORDER BY nb_employes DESC, categorie, titre
        LIMIT 20
    """
    result_ipm = provider.repo.run_query(sql_ipm)
    if result_ipm and isinstance(result_ipm, list):
        print(f"  Total combinaisons: {len(result_ipm)}")
        for row in result_ipm:
            print(f"  • {row[0]} / {row[1]}: {row[2]} employé(s)")
    print()

    # RÉSUMÉ: Compter par catégorie seule
    print("📋 RÉSUMÉ PAR CATÉGORIE D'EMPLOI")
    print("-" * 80)
    sql_cat_summary = """
        SELECT 
            COALESCE(p.categorie_emploi, 'Non défini') as categorie,
            COUNT(DISTINCT e.employee_id) as nb_employes
        FROM core.employees e
        LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
        GROUP BY p.categorie_emploi
        ORDER BY nb_employes DESC
    """
    result_cat_summary = provider.repo.run_query(sql_cat_summary)
    if result_cat_summary and isinstance(result_cat_summary, list):
        total_cat = sum(row[1] for row in result_cat_summary)
        print(f"  Total employés: {total_cat}")
        for row in result_cat_summary:
            pct = (row[1] / total_cat * 100) if total_cat > 0 else 0
            print(f"  • {row[0]}: {row[1]} employé(s) ({pct:.1f}%)")
    print()

    # RÉSUMÉ: Compter par titre seul
    print("📋 RÉSUMÉ PAR TITRE D'EMPLOI")
    print("-" * 80)
    sql_title_summary = """
        SELECT 
            COALESCE(p.titre_emploi, 'Non défini') as titre,
            COUNT(DISTINCT e.employee_id) as nb_employes
        FROM core.employees e
        LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
        GROUP BY p.titre_emploi
        ORDER BY nb_employes DESC
    """
    result_title_summary = provider.repo.run_query(sql_title_summary)
    if result_title_summary and isinstance(result_title_summary, list):
        total_title = sum(row[1] for row in result_title_summary)
        print(f"  Total employés: {total_title}")
        for row in result_title_summary:
            pct = (row[1] / total_title * 100) if total_title > 0 else 0
            print(f"  • {row[0]}: {row[1]} employé(s) ({pct:.1f}%)")
    print()

    # RÉSUMÉ: Combinaison catégorie + titre
    print("📋 RÉSUMÉ PAR COMBINAISON CATÉGORIE + TITRE")
    print("-" * 80)
    sql_combo = """
        SELECT 
            COALESCE(p.categorie_emploi, 'Non défini') as categorie,
            COALESCE(p.titre_emploi, 'Non défini') as titre,
            COUNT(DISTINCT e.employee_id) as nb_employes
        FROM core.employees e
        LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
        GROUP BY p.categorie_emploi, p.titre_emploi
        ORDER BY nb_employes DESC, categorie, titre
    """
    result_combo = provider.repo.run_query(sql_combo)
    if result_combo and isinstance(result_combo, list):
        total_combo = sum(row[2] for row in result_combo)
        print(f"  Total employés: {total_combo}")
        print(f"  Total combinaisons: {len(result_combo)}")
        print()
        print("  Top 20 combinaisons:")
        for i, row in enumerate(result_combo[:20], 1):
            pct = (row[2] / total_combo * 100) if total_combo > 0 else 0
            print(f"  {i:2d}. {row[0]} / {row[1]}: {row[2]} employé(s) ({pct:.1f}%)")
    print()

    print("=" * 80)
    print("  ✅ Analyse terminée")
    print("=" * 80 + "\n")

    # Fermer proprement le pool
    if provider and provider.repo:
        try:
            provider.repo.close()
        except:
            pass

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
finally:
    # Nettoyer pour éviter les warnings de fermeture
    import gc

    gc.collect()
