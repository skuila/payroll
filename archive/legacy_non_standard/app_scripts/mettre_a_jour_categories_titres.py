#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour mettre à jour les catégories et titres d'emploi depuis les colonnes RAW
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
    print("  MISE À JOUR DES CATÉGORIES ET TITRES D'EMPLOI")
    print("=" * 80 + "\n")

    # 1. Vérifier les données disponibles dans les colonnes RAW
    print("📊 Vérification des données RAW...")
    sql_check = """
        SELECT 
            COUNT(*) as total_lignes,
            COUNT(DISTINCT categorie_emploi_raw) FILTER (WHERE categorie_emploi_raw IS NOT NULL AND TRIM(categorie_emploi_raw) != '') as nb_cat_raw,
            COUNT(DISTINCT titre_emploi_raw) FILTER (WHERE titre_emploi_raw IS NOT NULL AND TRIM(titre_emploi_raw) != '') as nb_titres_raw
        FROM paie.stg_paie_transactions
    """
    result_check = provider.repo.run_query(sql_check)
    if result_check and isinstance(result_check, list):
        row = result_check[0]
        print(f"  Total lignes: {row[0]}")
        print(f"  Catégories RAW distinctes: {row[1]}")
        print(f"  Titres RAW distincts: {row[2]}")
    print()

    # 2. Mettre à jour categorie_emploi depuis categorie_emploi_raw si manquant
    print("🔄 Mise à jour de categorie_emploi depuis categorie_emploi_raw...")
    sql_update_cat = """
        UPDATE paie.stg_paie_transactions
        SET categorie_emploi = TRIM(categorie_emploi_raw)
        WHERE (categorie_emploi IS NULL OR TRIM(categorie_emploi) = '')
          AND categorie_emploi_raw IS NOT NULL 
          AND TRIM(categorie_emploi_raw) != ''
    """

    # Utiliser run_tx pour exécuter la transaction
    def update_cat(conn):
        with conn.cursor() as cur:
            cur.execute(sql_update_cat)
            return cur.rowcount

    nb_updated_cat = provider.repo.run_tx(update_cat)
    print(f"  OK: {nb_updated_cat} lignes mises à jour")

    # Vérifier après mise à jour
    sql_verify_cat = """
        SELECT COUNT(*) as nb_lignes 
        FROM paie.stg_paie_transactions 
        WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != ''
    """
    result_verify_cat = provider.repo.run_query(sql_verify_cat)
    if result_verify_cat and isinstance(result_verify_cat, list):
        print(f"  Total lignes avec catégorie: {result_verify_cat[0][0]}")
    print()

    # 3. Mettre à jour titre_emploi depuis titre_emploi_raw si manquant
    print("🔄 Mise à jour de titre_emploi depuis titre_emploi_raw...")
    sql_update_title = """
        UPDATE paie.stg_paie_transactions
        SET titre_emploi = TRIM(titre_emploi_raw)
        WHERE (titre_emploi IS NULL OR TRIM(titre_emploi) = '')
          AND titre_emploi_raw IS NOT NULL 
          AND TRIM(titre_emploi_raw) != ''
    """

    def update_title(conn):
        with conn.cursor() as cur:
            cur.execute(sql_update_title)
            return cur.rowcount

    nb_updated_title = provider.repo.run_tx(update_title)
    print(f"  OK: {nb_updated_title} lignes mises à jour")

    # Vérifier après mise à jour
    sql_verify_title = """
        SELECT COUNT(*) as nb_lignes 
        FROM paie.stg_paie_transactions 
        WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != ''
    """
    result_verify_title = provider.repo.run_query(sql_verify_title)
    if result_verify_title and isinstance(result_verify_title, list):
        print(f"  Total lignes avec titre: {result_verify_title[0][0]}")
    print()

    # 4. Afficher les catégories distinctes après mise à jour
    print("📋 Catégories d'emploi après mise à jour:")
    print("-" * 80)
    sql_cat = """
        SELECT 
            categorie_emploi,
            COUNT(DISTINCT matricule) as nb_employes,
            COUNT(*) as nb_lignes
        FROM paie.stg_paie_transactions
        WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != ''
        GROUP BY categorie_emploi
        ORDER BY nb_employes DESC
    """
    result_cat = provider.repo.run_query(sql_cat)
    if result_cat and isinstance(result_cat, list):
        total_emp_cat = sum(row[1] for row in result_cat)
        for row in result_cat:
            pct = (row[1] / total_emp_cat * 100) if total_emp_cat > 0 else 0
            print(f"  • {row[0]}: {row[1]} employé(s) ({row[2]} lignes) - {pct:.1f}%")
    print()

    # 5. Afficher les titres distincts après mise à jour (top 20)
    print("📋 Titres d'emploi après mise à jour (top 20):")
    print("-" * 80)
    sql_title = """
        SELECT 
            titre_emploi,
            COUNT(DISTINCT matricule) as nb_employes,
            COUNT(*) as nb_lignes
        FROM paie.stg_paie_transactions
        WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != ''
        GROUP BY titre_emploi
        ORDER BY nb_employes DESC
        LIMIT 20
    """
    result_title = provider.repo.run_query(sql_title)
    if result_title and isinstance(result_title, list):
        for i, row in enumerate(result_title, 1):
            print(f"  {i:2d}. {row[0]}: {row[1]} employé(s) ({row[2]} lignes)")
    print()

    # 6. Compter les employés par catégorie et titre dans la vue profil (après refresh)
    print("📊 Statistiques dans v_employe_profil (recalculée):")
    print("-" * 80)
    sql_profil = """
        SELECT 
            COALESCE(categorie_emploi, 'Non défini') as categorie,
            COALESCE(titre_emploi, 'Non défini') as titre,
            COUNT(DISTINCT employee_id) as nb_employes
        FROM paie.v_employe_profil
        GROUP BY categorie_emploi, titre_emploi
        ORDER BY nb_employes DESC
        LIMIT 20
    """
    result_profil = provider.repo.run_query(sql_profil)
    if result_profil and isinstance(result_profil, list):
        for row in result_profil:
            print(f"  • {row[0]} / {row[1]}: {row[2]} employé(s)")
    print()

    print("=" * 80)
    print("  ✅ Mise à jour terminée avec succès")
    print("=" * 80 + "\n")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
