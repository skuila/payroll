#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifier ce qui est réellement dans le fichier (staging) pour Ajarar Amin"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider


def main():
    p = PostgresProvider()
    r = p.repo
    try:
        print("\n=== VÉRIFICATION FICHIER (stg_paie_transactions) ===")
        print("Matricule: 2364, Date: 2025-08-28\n")

        # Tous les titres/catégories distincts dans le fichier pour cet employé cette date
        sql = """
            SELECT DISTINCT
                categorie_emploi,
                titre_emploi,
                COUNT(*) as nb_lignes,
                source_file,
                MIN(source_row_number) as premiere_ligne,
                MAX(source_row_number) as derniere_ligne
            FROM paie.stg_paie_transactions
            WHERE matricule = '2364'
              AND date_paie = '2025-08-28'
            GROUP BY categorie_emploi, titre_emploi, source_file
            ORDER BY nb_lignes DESC;
        """
        rows = r.run_query(sql)
        print("Titres/catégories dans le fichier (staging):")
        for row in rows:
            print(f"  Catégorie: {row[0]}")
            print(f"  Titre: {row[1]}")
            print(f"  Nombre de lignes: {row[2]}")
            print(f"  Fichier: {row[3]}")
            print(f"  Lignes Excel: {row[4]} à {row[5]}")
            print()

        # Vérifier aussi les valeurs RAW (brutes)
        sql_raw = """
            SELECT DISTINCT
                categorie_emploi_raw,
                titre_emploi_raw,
                COUNT(*) as nb
            FROM paie.stg_paie_transactions
            WHERE matricule = '2364'
              AND date_paie = '2025-08-28'
            GROUP BY categorie_emploi_raw, titre_emploi_raw
            ORDER BY nb DESC;
        """
        rows_raw = r.run_query(sql_raw)
        print("\nValeurs RAW (brutes) dans le fichier:")
        for row in rows_raw:
            print(f"  Catégorie RAW: {row[0]}")
            print(f"  Titre RAW: {row[1]}")
            print(f"  Nombre: {row[2]}")
            print()

        print("✓ Vérification terminée")
    finally:
        r.close()


if __name__ == "__main__":
    main()
