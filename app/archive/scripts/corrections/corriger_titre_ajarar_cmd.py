#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corriger le titre d'emploi pour Ajarar Amin dans stg_paie_transactions"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider


def main():
    p = PostgresProvider()
    r = p.repo
    try:
        print("\n=== CORRECTION TITRE AJARAR AMIN ===")
        print("Matricule: 2364, Date: 2025-08-28\n")
        print("Ancien titre: Technicien(ne) en comptabilité")
        print("Nouveau titre: Agent de la gestion comptable\n")

        # Mettre à jour toutes les lignes de staging pour cet employé cette date
        sql_update = """
            UPDATE paie.stg_paie_transactions
            SET 
                categorie_emploi = 'Professionnel',
                titre_emploi = 'Agent de la gestion comptable',
                categorie_emploi_raw = 'Professionnel',
                titre_emploi_raw = 'Agent de la gestion comptable'
            WHERE matricule = '2364'
              AND date_paie = '2025-08-28';
        """
        r.run_query(sql_update)

        # Vérifier le résultat
        sql_check = """
            SELECT DISTINCT
                categorie_emploi,
                titre_emploi,
                COUNT(*) as nb_lignes
            FROM paie.stg_paie_transactions
            WHERE matricule = '2364'
              AND date_paie = '2025-08-28'
            GROUP BY categorie_emploi, titre_emploi;
        """
        rows = r.run_query(sql_check)
        print("Résultat après correction:")
        for row in rows:
            print(f"  Catégorie: {row[0]}")
            print(f"  Titre: {row[1]}")
            print(f"  Nombre de lignes: {row[2]}")

        print("\n✓ Correction terminée")
        print("\n⚠️ IMPORTANT: Rafraîchissez la page Employés pour voir le changement")
    finally:
        r.close()


if __name__ == "__main__":
    main()
