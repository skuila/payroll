#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
r = p.repo

try:
    print("=" * 80)
    print("VÉRIFICATION SOURCE TITRE D'EMPLOI")
    print("=" * 80)

    # Vérifier dans stg_paie_transactions pour Ajarar Amin (matricule 2364)
    sql_stg = """
        SELECT 
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
        ORDER BY date_paie DESC
        LIMIT 5;
    """
    stg_result = r.run_query(sql_stg)
    print("\n1. Données dans stg_paie_transactions (matricule 2364):")
    print(f"   {len(stg_result)} lignes trouvées")
    for row in stg_result:
        print(f"\n   Fichier source: {row[0]}")
        print(f"   Ligne source: {row[1]}")
        print(f"   Date: {row[2]}")
        print(f"   Matricule: {row[3]}")
        print(f"   Nom: {row[4]}")
        print(f"   Catégorie (nettoyée): {row[5]}")
        print(f"   Titre (nettoyé): {row[6]}")
        print(f"   Catégorie (raw): {row[7]}")
        print(f"   Titre (raw): {row[8]}")

    # Vérifier s'il y a une vue ou fonction qui remplit ces colonnes
    print("\n" + "=" * 80)
    print("2. Vérification si une vue/fonction remplit categorie_emploi/titre_emploi")
    print("=" * 80)

    sql_views = """
        SELECT 
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'paie'
          AND table_name = 'stg_paie_transactions'
          AND (column_name LIKE '%%categorie%%' OR column_name LIKE '%%titre%%')
        ORDER BY ordinal_position;
    """
    cols = r.run_query(sql_views)
    print("\nColonnes categorie/titre dans stg_paie_transactions:")
    for c in cols:
        print(f"  - {c[0]}.{c[1]} ({c[2]})")

except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
finally:
    r.close()
