#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour vérifier où sont les données et créer le script SQL de mise à jour
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
    print("  VÉRIFICATION DES SOURCES DE DONNÉES")
    print("=" * 80 + "\n")

    # Vérifier imported_payroll_master
    print("📊 Vérification payroll.imported_payroll_master:")
    print("-" * 80)
    sql_check_ipm = """
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT categorie_emploi) FILTER (WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != '') as nb_cat,
            COUNT(DISTINCT titre_emploi) FILTER (WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != '') as nb_titres
        FROM payroll.imported_payroll_master
    """
    result_ipm = provider.repo.run_query(sql_check_ipm)
    if result_ipm and isinstance(result_ipm, list):
        row = result_ipm[0]
        print(f"  Total lignes: {row[0]}")
        print(f"  Catégories distinctes: {row[1]}")
        print(f"  Titres distincts: {row[2]}")

        if row[1] > 0 or row[2] > 0:
            print("\n  ✓ Données trouvées dans imported_payroll_master!")

            # Afficher les catégories
            sql_cat_ipm = """
                SELECT DISTINCT categorie_emploi, COUNT(*) as nb
                FROM payroll.imported_payroll_master
                WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != ''
                GROUP BY categorie_emploi
                ORDER BY nb DESC
            """
            result_cat_ipm = provider.repo.run_query(sql_cat_ipm)
            if result_cat_ipm and isinstance(result_cat_ipm, list):
                print("\n  Catégories dans imported_payroll_master:")
                for r in result_cat_ipm:
                    print(f"    • {r[0]}: {r[1]} lignes")

            # Afficher quelques titres
            sql_title_ipm = """
                SELECT DISTINCT titre_emploi, COUNT(*) as nb
                FROM payroll.imported_payroll_master
                WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != ''
                GROUP BY titre_emploi
                ORDER BY nb DESC
                LIMIT 10
            """
            result_title_ipm = provider.repo.run_query(sql_title_ipm)
            if result_title_ipm and isinstance(result_title_ipm, list):
                print("\n  Titres dans imported_payroll_master (top 10):")
                for r in result_title_ipm:
                    print(f"    • {r[0]}: {r[1]} lignes")
        else:
            print("  ⚠️ Aucune donnée de catégorie/titre trouvée")
    print()

    # Vérifier la relation entre imported_payroll_master et stg_paie_transactions
    print("🔗 Vérification de la relation entre les tables:")
    print("-" * 80)
    sql_relation = """
        SELECT 
            COUNT(*) as total_stg,
            COUNT(DISTINCT s.source_file) as nb_fichiers_stg,
            COUNT(DISTINCT i.source_file) as nb_fichiers_ipm
        FROM paie.stg_paie_transactions s
        LEFT JOIN payroll.imported_payroll_master i 
            ON s.source_file = i.source_file 
            AND s.source_row_number = i.source_row_number
    """
    result_relation = provider.repo.run_query(sql_relation)
    if result_relation and isinstance(result_relation, list):
        row = result_relation[0]
        print(f"  Lignes dans stg_paie_transactions: {row[0]}")
        print(f"  Fichiers dans stg: {row[1]}")
        print(f"  Fichiers correspondants dans ipm: {row[2]}")
    print()

    print("=" * 80)
    print("  ✅ Vérification terminée")
    print("=" * 80 + "\n")

    # Si les données sont dans imported_payroll_master, créer le script SQL
    if (
        result_ipm
        and isinstance(result_ipm, list)
        and (result_ipm[0][1] > 0 or result_ipm[0][2] > 0)
    ):
        print("📝 Création du script SQL de mise à jour...")
        sql_script = """
-- =============================================================================
-- Mise à jour des catégories et titres d'emploi depuis imported_payroll_master
-- À exécuter avec le rôle postgres
-- =============================================================================

\\set ON_ERROR_STOP on
SET client_min_messages TO NOTICE;

\\echo ''
\\echo '========================================================================='
\\echo 'Mise à jour des catégories et titres d''emploi'
\\echo '========================================================================='
\\echo ''

-- Mettre à jour stg_paie_transactions depuis imported_payroll_master
UPDATE paie.stg_paie_transactions s
SET 
    categorie_emploi = TRIM(i.categorie_emploi),
    titre_emploi = TRIM(i.titre_emploi)
FROM payroll.imported_payroll_master i
WHERE s.source_file = i.source_file 
  AND s.source_row_number = i.n_de_ligne
  AND i.categorie_emploi IS NOT NULL 
  AND TRIM(i.categorie_emploi) != ''
  AND (s.categorie_emploi IS NULL OR TRIM(s.categorie_emploi) = '');

\\echo '✓ Catégories mises à jour'

UPDATE paie.stg_paie_transactions s
SET titre_emploi = TRIM(i.titre_emploi)
FROM payroll.imported_payroll_master i
WHERE s.source_file = i.source_file 
  AND s.source_row_number = i.n_de_ligne
  AND i.titre_emploi IS NOT NULL 
  AND TRIM(i.titre_emploi) != ''
  AND (s.titre_emploi IS NULL OR TRIM(s.titre_emploi) = '');

\\echo '✓ Titres mis à jour'

-- Vérifier les résultats
\\echo ''
\\echo '📊 Résultats:'
SELECT 
    categorie_emploi,
    COUNT(DISTINCT matricule) as nb_employes,
    COUNT(*) as nb_lignes
FROM paie.stg_paie_transactions
WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != ''
GROUP BY categorie_emploi
ORDER BY nb_employes DESC;

\\echo ''
\\echo '========================================================================='
\\echo '✅ Mise à jour terminée'
\\echo '========================================================================='
"""

        script_path = Path("migration/016_mise_a_jour_categories_titres.sql")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(sql_script)

        print(f"  ✓ Script créé: {script_path}")
        print("\n  Pour exécuter ce script, utilisez:")
        print(
            "  psql -h localhost -U postgres -d payroll_db -f migration/016_mise_a_jour_categories_titres.sql"
        )

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
