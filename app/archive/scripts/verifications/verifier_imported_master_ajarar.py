#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifier les données dans imported_payroll_master pour Ajarar Amin"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider


def main():
    p = PostgresProvider()
    r = p.repo
    try:
        print("\n=== VÉRIFICATION imported_payroll_master ===")
        print("Matricule: 2364, Date: 2025-08-28\n")

        sql = """
            SELECT DISTINCT
                categorie_emploi,
                titre_emploi,
                code_emploi,
                COUNT(*) as nb_lignes,
                MIN(source_row_number) as min_row,
                MAX(source_row_number) as max_row
            FROM payroll.imported_payroll_master
            WHERE matricule = '2364'
              AND date_paie = '2025-08-28'
            GROUP BY categorie_emploi, titre_emploi, code_emploi
            ORDER BY nb_lignes DESC;
        """
        rows = r.run_query(sql)
        print("Données dans imported_payroll_master:")
        for row in rows:
            print(f"  Catégorie: {row[0]}")
            print(f"  Titre: {row[1]}")
            print(f"  Code: {row[2]}")
            print(f"  Nombre de lignes: {row[3]}")
            print(f"  Lignes Excel: {row[4]} à {row[5]}")
            print()

        print("✓ Vérification terminée")
    finally:
        r.close()


if __name__ == "__main__":
    main()
