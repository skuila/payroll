#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérification du mapping pour Ajarar Amin
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider


def main():
    print("=" * 80)
    print("VÉRIFICATION MAPPING: Ajarar Amin")
    print("=" * 80)

    provider = PostgresProvider()
    repo = provider.repo

    try:
        # 1. Chercher dans core.employees
        print("\n1. Recherche dans core.employees:")
        sql_emp = """
            SELECT employee_id, matricule_norm, nom_norm, prenom_norm, nom_complet
            FROM core.employees
            WHERE LOWER(nom_norm) LIKE '%ajarar%' OR LOWER(prenom_norm) LIKE '%amin%'
               OR LOWER(nom_complet) LIKE '%ajarar%' OR LOWER(nom_complet) LIKE '%amin%'
            ORDER BY nom_complet;
        """
        employees = repo.run_query(sql_emp)
        if employees:
            for emp in employees:
                print(f"   - {emp}")
                employee_id = emp[0]
                matricule = emp[1]

                # 2. Vérifier dans paie.v_employe_profil
                print(
                    f"\n2. Titre d'emploi dans paie.v_employe_profil (employee_id={employee_id}):"
                )
                sql_profil = """
                    SELECT employee_id, matricule, nom, prenom, categorie_emploi, titre_emploi, occurrences
                    FROM paie.v_employe_profil
                    WHERE employee_id = %(emp_id)s;
                """
                profils = repo.run_query(sql_profil, {"emp_id": employee_id})
                if profils:
                    for p in profils:
                        print(f"   - Catégorie: {p[4]}")
                        print(f"   - Titre: {p[5]}")
                        print(f"   - Occurrences: {p[6]}")
                else:
                    print("   (aucun profil trouvé)")

                # 3. Vérifier dans paie.stg_paie_transactions (source directe)
                print(
                    f"\n3. Données brutes dans paie.stg_paie_transactions (matricule={matricule}):"
                )
                sql_stg = """
                    SELECT DISTINCT 
                        matricule, 
                        nom_prenom,
                        categorie_emploi,
                        titre_emploi,
                        date_paie,
                        COUNT(*) as nb_lignes
                    FROM paie.stg_paie_transactions
                    WHERE matricule = %(mat)s
                    GROUP BY matricule, nom_prenom, categorie_emploi, titre_emploi, date_paie
                    ORDER BY date_paie DESC, titre_emploi;
                """
                stg_data = repo.run_query(sql_stg, {"mat": matricule})
                if stg_data:
                    print(f"   {len(stg_data)} combinaisons distinctes trouvées:")
                    for s in stg_data:
                        print(
                            f"   - Date: {s[4]}, Catégorie: {s[2]}, Titre: {s[3]}, Lignes: {s[5]}"
                        )
                else:
                    print("   (aucune donnée dans stg_paie_transactions)")

                # 4. Vérifier dans payroll.imported_payroll_master (source Excel)
                print(
                    "\n4. Données dans payroll.imported_payroll_master (source Excel):"
                )
                sql_master = """
                    SELECT DISTINCT 
                        "matricule ",
                        "employé ",
                        "Categorie d'emploi",
                        "titre d'emploi",
                        "date de paie ",
                        COUNT(*) as nb_lignes
                    FROM payroll.imported_payroll_master
                    WHERE LOWER("employé ") LIKE '%ajarar%' OR LOWER("employé ") LIKE '%amin%'
                       OR "matricule " = %(mat)s
                    GROUP BY "matricule ", "employé ", "Categorie d'emploi", "titre d'emploi", "date de paie "
                    ORDER BY "date de paie " DESC, "titre d'emploi";
                """
                master_data = repo.run_query(sql_master, {"mat": matricule})
                if master_data:
                    print(f"   {len(master_data)} combinaisons distinctes trouvées:")
                    for m in master_data:
                        print(f"   - Matricule: {m[0]}")
                        print(f"   - Employé: {m[1]}")
                        print(f"   - Date: {m[4]}")
                        print(f"   - Catégorie: {m[2]}")
                        print(f"   - Titre: {m[3]}")
                        print(f"   - Lignes: {m[5]}")
                        print()
                else:
                    print("   (aucune donnée dans imported_payroll_master)")

        # 5. Vérifier le fichier Excel directement
        print("\n" + "=" * 80)
        print("5. Vérification dans le fichier Excel:")
        print("=" * 80)
        excel_path = Path("data/inbox/Classeur1.xlsx")
        if not excel_path.exists():
            excel_path = Path("Classeur1.xlsx")

        if excel_path.exists():
            print(f"   Fichier trouvé: {excel_path}")
            try:
                df = pd.read_excel(excel_path, engine="openpyxl")
                print(f"   Colonnes: {list(df.columns)}")

                # Chercher Ajarar ou Amin
                search_cols = []
                for col in df.columns:
                    if any(
                        term in str(col).lower()
                        for term in ["nom", "employé", "employe", "prenom"]
                    ):
                        search_cols.append(col)

                print(f"   Colonnes de recherche: {search_cols}")

                for col in search_cols:
                    matches = df[
                        df[col]
                        .astype(str)
                        .str.contains("ajarar|amin", case=False, na=False)
                    ]
                    if not matches.empty:
                        print(f"\n   Trouvé dans colonne '{col}':")
                        for idx, row in matches.iterrows():
                            print(f"   Ligne {idx}:")
                            # Afficher toutes les colonnes pertinentes
                            for c in df.columns:
                                val = row[c]
                                if pd.notna(val) and str(val).strip():
                                    if any(
                                        term in str(c).lower()
                                        for term in [
                                            "titre",
                                            "emploi",
                                            "categorie",
                                            "employé",
                                            "nom",
                                        ]
                                    ):
                                        print(f"      {c}: {val}")
            except Exception as e:
                print(f"   ❌ Erreur lecture Excel: {e}")
        else:
            print(f"   ⚠️ Fichier Excel non trouvé: {excel_path}")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
    finally:
        repo.close()


if __name__ == "__main__":
    main()
