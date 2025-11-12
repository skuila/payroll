#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour mettre à jour les catégories et titres d'emploi avec une connexion postgres
"""

import sys
import os
import pandas as pd
from pathlib import Path
import psycopg
from psycopg_pool import ConnectionPool

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

try:
    # Connexion directe avec postgres
    from config.config_manager import get_superuser_dsn

    dsn = get_superuser_dsn()

    print("\n" + "=" * 80)
    print("  MISE À JOUR DES CATÉGORIES ET TITRES D'EMPLOI")
    print("=" * 80 + "\n")

    # Lire le fichier Excel
    excel_file = Path("Classeur1.xlsx")
    if not excel_file.exists():
        print(f"❌ Fichier introuvable: {excel_file}")
        sys.exit(1)

    print(f"📖 Lecture du fichier Excel: {excel_file}")
    df = pd.read_excel(excel_file, engine="openpyxl")
    print(f"  OK: {len(df)} lignes lues")

    # Identifier les colonnes
    cat_col = "Categorie d'emploi"
    title_col = "titre d'emploi"
    ligne_col = "N de ligne"

    # Créer un dictionnaire de mapping
    print("\n📊 Préparation des données...")
    mapping = {}
    for idx, row in df.iterrows():
        ligne_num = row.get(ligne_col, idx + 2)
        cat = str(row.get(cat_col, "")).strip() if pd.notna(row.get(cat_col)) else None
        titre = (
            str(row.get(title_col, "")).strip()
            if pd.notna(row.get(title_col))
            else None
        )

        if cat and cat != "" and cat != "nan":
            mapping[(excel_file.name, int(ligne_num))] = (
                cat,
                titre if titre and titre != "nan" else None,
            )

    print(f"  OK: {len(mapping)} entrées préparées")

    # Compter les catégories et titres
    categories = {}
    titres = {}
    for (file, ligne), (cat, titre) in mapping.items():
        categories[cat] = categories.get(cat, 0) + 1
        if titre:
            titres[titre] = titres.get(titre, 0) + 1

    print(f"\n📋 Catégories trouvées: {len(categories)}")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {cat}: {count} lignes")

    print(f"\n📋 Titres trouvés: {len(titres)}")
    for titre, count in sorted(titres.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  • {titre}: {count} lignes")
    if len(titres) > 10:
        print(f"  ... et {len(titres) - 10} autres titres")

    # Connexion à la base avec postgres
    print("\n🔄 Connexion à la base de données...")
    with psycopg.connect(dsn, autocommit=False) as conn:
        print("  OK: Connecté")

        updated_cat = 0
        updated_title = 0

        with conn.cursor() as cur:
            # Utiliser executemany pour les mises à jour par batch
            batch_size = 1000
            items = list(mapping.items())

            for batch_start in range(0, len(items), batch_size):
                batch = items[batch_start : batch_start + batch_size]

                # Préparer les données pour le batch
                cat_updates = []
                title_updates = []

                for (file, ligne), (cat, titre) in batch:
                    if cat:
                        cat_updates.append((cat, file, ligne))
                    if titre:
                        title_updates.append((titre, file, ligne))

                # Mettre à jour les catégories
                if cat_updates:
                    sql_cat = """
                        UPDATE paie.stg_paie_transactions
                        SET categorie_emploi = %s
                        WHERE source_file = %s 
                          AND source_row_number = %s
                          AND (categorie_emploi IS NULL OR TRIM(categorie_emploi) = '')
                    """
                    cur.executemany(sql_cat, cat_updates)
                    updated_cat += cur.rowcount

                # Mettre à jour les titres
                if title_updates:
                    sql_title = """
                        UPDATE paie.stg_paie_transactions
                        SET titre_emploi = %s
                        WHERE source_file = %s 
                          AND source_row_number = %s
                          AND (titre_emploi IS NULL OR TRIM(titre_emploi) = '')
                    """
                    cur.executemany(sql_title, title_updates)
                    updated_title += cur.rowcount

                print(
                    f"  Batch {batch_start // batch_size + 1}: {updated_cat} catégories, {updated_title} titres",
                    end="\r",
                )

            conn.commit()
            print()

    print(f"\nOK: {updated_cat} lignes mises à jour pour categorie_emploi")
    print(f"OK: {updated_title} lignes mises à jour pour titre_emploi")

    # Vérifier les résultats
    print("\n📊 Vérification des résultats:")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    categorie_emploi,
                    COUNT(DISTINCT matricule) as nb_employes,
                    COUNT(*) as nb_lignes
                FROM paie.stg_paie_transactions
                WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != ''
                GROUP BY categorie_emploi
                ORDER BY nb_employes DESC
            """
            )
            results = cur.fetchall()
            print("\n  Catégories:")
            for row in results:
                print(f"    • {row[0]}: {row[1]} employé(s) ({row[2]} lignes)")

            cur.execute(
                """
                SELECT 
                    titre_emploi,
                    COUNT(DISTINCT matricule) as nb_employes,
                    COUNT(*) as nb_lignes
                FROM paie.stg_paie_transactions
                WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != ''
                GROUP BY titre_emploi
                ORDER BY nb_employes DESC
                LIMIT 10
            """
            )
            results = cur.fetchall()
            print("\n  Top 10 titres:")
            for row in results:
                print(f"    • {row[0]}: {row[1]} employé(s) ({row[2]} lignes)")

    print("\n" + "=" * 80)
    print("  ✅ Mise à jour terminée avec succès")
    print("=" * 80 + "\n")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
finally:
    # Nettoyer pour éviter les warnings de fermeture
    import atexit
    import gc

    gc.collect()
