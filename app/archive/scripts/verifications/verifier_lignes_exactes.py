#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifier les lignes exactes avec titre d'emploi"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
r = p.repo

try:
    print("=" * 80)
    print("LIGNES EXACTES AVEC TITRE D'EMPLOI")
    print("=" * 80)

    sql = """
        SELECT 
            stg_id,
            source_file,
            source_row_number,
            date_paie,
            matricule,
            nom_prenom,
            categorie_emploi,
            titre_emploi,
            categorie_emploi_raw,
            titre_emploi_raw
        FROM paie.stg_paie_transactions
        WHERE matricule = '2364'
          AND (categorie_emploi IS NOT NULL OR titre_emploi IS NOT NULL)
        ORDER BY date_paie DESC, stg_id;
    """
    result = r.run_query(sql)
    print(f"\n{len(result)} lignes avec catégorie/titre:")
    for row in result:
        print(f"\n  STG ID: {row[0]}")
        print(f"  Fichier: {row[1]}")
        print(f"  Ligne source: {row[2]}")
        print(f"  Date: {row[3]}")
        print(f"  Matricule: {row[4]}")
        print(f"  Nom: {row[5]}")
        print(f"  Catégorie (nettoyée): {row[6]}")
        print(f"  Titre (nettoyé): {row[7]}")
        print(f"  Catégorie (raw): {row[8]}")
        print(f"  Titre (raw): {row[9]}")

    print("\n" + "=" * 80)
    print("RECOMMANDATION:")
    print("=" * 80)
    print("Si le titre dans le fichier Excel est 'agent de la gestion comptable'")
    print("mais que la base affiche 'Technicien(ne) en comptabilité', il faut:")
    print("1. Vérifier le fichier Excel directement (lignes mentionnées ci-dessus)")
    print("2. Si le fichier Excel est correct, réimporter le fichier")
    print("3. Ou corriger manuellement dans stg_paie_transactions")

except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
finally:
    r.close()
