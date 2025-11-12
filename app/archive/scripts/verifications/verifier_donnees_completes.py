#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifier toutes les sources de données pour Ajarar Amin"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
r = p.repo

try:
    print("=" * 80)
    print("VÉRIFICATION COMPLÈTE DES SOURCES")
    print("=" * 80)

    # 1. Vérifier la vue v_employe_profil
    sql_vue = """
        SELECT * FROM paie.v_employe_profil
        WHERE LOWER(nom) LIKE '%%ajarar%%' OR LOWER(prenom) LIKE '%%amin%%';
    """
    vue_result = r.run_query(sql_vue)
    print("\n1. Vue v_employe_profil:")
    for v in vue_result:
        print(f"   Employee ID: {v[0]}")
        print(f"   Matricule: {v[1]}")
        print(f"   Nom: {v[2]}")
        print(f"   Prénom: {v[3]}")
        print(f"   Catégorie: {v[4]}")
        print(f"   Titre: {v[5]}")
        print(f"   Occurrences: {v[6]}")

    # 2. Vérifier si stg_paie_transactions a des données pour cet employé
    sql_stg = """
        SELECT COUNT(*), 
               COUNT(DISTINCT categorie_emploi) as nb_cat,
               COUNT(DISTINCT titre_emploi) as nb_titres
        FROM paie.stg_paie_transactions
        WHERE matricule = '2364'
          AND (categorie_emploi IS NOT NULL OR titre_emploi IS NOT NULL);
    """
    stg_count = r.run_query(sql_stg)
    print("\n2. Comptage dans stg_paie_transactions (matricule 2364):")
    for sc in stg_count:
        print(f"   Lignes avec cat/titre: {sc[0]}")
        print(f"   Catégories distinctes: {sc[1]}")
        print(f"   Titres distincts: {sc[2]}")

    # 3. Vérifier s'il y a une autre table qui contient ces données
    sql_other = """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema IN ('paie', 'payroll', 'core')
          AND table_name LIKE '%%emploi%%' OR table_name LIKE '%%titre%%'
        ORDER BY table_schema, table_name;
    """
    other_tables = r.run_query(sql_other)
    print("\n3. Tables contenant 'emploi' ou 'titre':")
    for ot in other_tables:
        print(f"   {ot[0]}.{ot[1]}")

except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
finally:
    r.close()
