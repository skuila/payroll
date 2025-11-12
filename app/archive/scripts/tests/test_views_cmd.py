#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de validation des vues:
 - paie.v_employes_par_periode_liste (échantillon, dernière date, cas Ajarar/Amin)
Exécuté via: cmd.exe -> python scripts\\test_views_cmd.py
"""

import sys
from pathlib import Path

# Assurer l'import du package 'providers' depuis la racine du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider


def main():
    p = PostgresProvider()
    r = p.repo
    try:
        print("\n--- TEST 1: Échantillon (5 lignes) ---")
        rows = r.run_query(
            "SELECT nom_complet, categorie_emploi, titre_emploi, date_paie, statut_calcule, amount_paid "
            "FROM paie.v_employes_par_periode_liste "
            "ORDER BY date_paie DESC, nom_complet LIMIT 5;"
        )
        for x in rows:
            print(tuple(x))

        print("\n--- TEST 2: Dernière date et volume du jour ---")
        last = r.run_query(
            "SELECT MAX(date_paie) FROM paie.v_employes_par_periode_liste;"
        )
        last_date = last[0][0] if last and last[0] else None
        print("Dernière date:", last_date)
        if last_date:
            cnt = r.run_query(
                "SELECT COUNT(*) FROM paie.v_employes_par_periode_liste WHERE date_paie=%s;",
                (last_date,),
            )
            print("Lignes ce jour:", cnt[0][0])

        print("\n--- TEST 3: Cas Ajarar / Amin ---")
        aj = r.run_query(
            "SELECT nom_complet, categorie_emploi, titre_emploi, date_paie, amount_paid "
            "FROM paie.v_employes_par_periode_liste "
            "WHERE LOWER(nom_complet) LIKE '%%ajarar%%' OR LOWER(nom_complet) LIKE '%%amin%%' "
            "ORDER BY date_paie DESC LIMIT 3;"
        )
        for x in aj:
            print(tuple(x))

        print("\n✓ Tests terminés.")
    finally:
        r.close()


if __name__ == "__main__":
    main()
