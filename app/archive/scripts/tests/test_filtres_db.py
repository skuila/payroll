#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification des filtres et catégorisation par titre d'emploi
"""

import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
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
    print("  VÉRIFICATION DES FILTRES ET CATÉGORISATION PAR TITRE D'EMPLOI")
    print("=" * 80 + "\n")

    # 1. Liste des titres d'emploi disponibles
    print("📋 TITRES D'EMPLOI DISPONIBLES:")
    print("-" * 80)
    sql_titres = """
        SELECT DISTINCT titre_emploi 
        FROM paie.v_employe_profil 
        WHERE titre_emploi IS NOT NULL 
        ORDER BY titre_emploi
    """
    result_titres = provider.repo.run_query(sql_titres)
    if result_titres and isinstance(result_titres, list):
        for row in result_titres:
            print(f"  • {row[0]}")
    else:
        print("  Aucun titre d'emploi trouvé")
    print()

    # 2. Catégorisation par titre d'emploi (ordre alphabétique)
    print("📊 CATÉGORISATION PAR TITRE D'EMPLOI:")
    print("-" * 80)
    sql_cat = """
        SELECT 
            titre_emploi,
            categorie_emploi,
            COUNT(*) as nb_employes
        FROM paie.v_employe_profil 
        WHERE categorie_emploi IS NOT NULL AND titre_emploi IS NOT NULL 
        GROUP BY titre_emploi, categorie_emploi 
        ORDER BY titre_emploi, nb_employes DESC
    """
    result_cat = provider.repo.run_query(sql_cat)
    if result_cat and isinstance(result_cat, list):
        current_titre = None
        for row in result_cat:
            titre, categorie, nb = row[0], row[1], row[2]
            if titre != current_titre:
                if current_titre is not None:
                    print()
                print(f"  📌 {titre}:")
                current_titre = titre
            print(f"      └─ {categorie}: {nb} employé(s)")
        print()
    else:
        print("  Aucune catégorisation trouvée")
    print()

    # 3. Test filtres: employés avec catégorie et titre (10 premiers)
    print("👥 EMPLOYÉS AVEC CATÉGORIE ET TITRE (10 premiers):")
    print("-" * 80)
    sql_emp = """
        SELECT 
            e.employee_id,
            e.matricule,
            e.nom,
            e.prenom,
            COALESCE(p.categorie_emploi, 'N/A') AS categorie_emploi,
            COALESCE(p.titre_emploi, 'N/A') AS titre_emploi,
            e.statut
        FROM core.employees e
        LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
        ORDER BY p.titre_emploi NULLS LAST, e.nom
        LIMIT 10
    """
    result_emp = provider.repo.run_query(sql_emp)
    if result_emp and isinstance(result_emp, list):
        print(
            f"{'Matricule':<12} {'Nom':<20} {'Catégorie':<25} {'Titre':<30} {'Statut'}"
        )
        print("-" * 100)
        for row in result_emp:
            emp_id, matricule, nom, prenom, categorie, titre, statut = row
            nom_complet = f"{nom} {prenom}".strip()
            print(
                f"{matricule or 'N/A':<12} {nom_complet:<20} {categorie:<25} {titre:<30} {statut}"
            )
    else:
        print("  Aucun employé trouvé")
    print()

    # 4. Test filtre par catégorie (exemple)
    print("🔍 TEST FILTRE PAR CATÉGORIE (première catégorie disponible):")
    print("-" * 80)
    sql_test_cat = """
        SELECT DISTINCT categorie_emploi 
        FROM paie.v_employe_profil 
        WHERE categorie_emploi IS NOT NULL 
        ORDER BY categorie_emploi 
        LIMIT 1
    """
    result_test_cat = provider.repo.run_query(sql_test_cat)
    if (
        result_test_cat
        and isinstance(result_test_cat, list)
        and len(result_test_cat) > 0
    ):
        test_categorie = result_test_cat[0][0]
        print(f"  Filtre: Catégorie = '{test_categorie}'")
        sql_filtre = """
            SELECT 
                e.matricule,
                e.nom,
                e.prenom,
                p.categorie_emploi,
                p.titre_emploi
            FROM core.employees e
            LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
            WHERE COALESCE(p.categorie_emploi, '') = %(cat)s
            ORDER BY p.titre_emploi, e.nom
            LIMIT 5
        """
        result_filtre = provider.repo.run_query(sql_filtre, {"cat": test_categorie})
        if result_filtre and isinstance(result_filtre, list):
            print(f"  Résultats trouvés: {len(result_filtre)} employé(s)")
            for row in result_filtre:
                matricule, nom, prenom, cat, titre = row
                nom_complet = f"{nom} {prenom}".strip()
                print(f"    • {matricule} - {nom_complet} ({cat} / {titre})")
        else:
            print("  Aucun résultat avec ce filtre")
    print()

    # 5. Test filtre par titre (exemple)
    print("🔍 TEST FILTRE PAR TITRE (premier titre disponible):")
    print("-" * 80)
    sql_test_titre = """
        SELECT DISTINCT titre_emploi 
        FROM paie.v_employe_profil 
        WHERE titre_emploi IS NOT NULL 
        ORDER BY titre_emploi 
        LIMIT 1
    """
    result_test_titre = provider.repo.run_query(sql_test_titre)
    if (
        result_test_titre
        and isinstance(result_test_titre, list)
        and len(result_test_titre) > 0
    ):
        test_titre = result_test_titre[0][0]
        print(f"  Filtre: Titre = '{test_titre}'")
        sql_filtre_titre = """
            SELECT 
                e.matricule,
                e.nom,
                e.prenom,
                p.categorie_emploi,
                p.titre_emploi
            FROM core.employees e
            LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
            WHERE COALESCE(p.titre_emploi, '') = %(titre)s
            ORDER BY e.nom
            LIMIT 5
        """
        result_filtre_titre = provider.repo.run_query(
            sql_filtre_titre, {"titre": test_titre}
        )
        if result_filtre_titre and isinstance(result_filtre_titre, list):
            print(f"  Résultats trouvés: {len(result_filtre_titre)} employé(s)")
            for row in result_filtre_titre:
                matricule, nom, prenom, cat, titre = row
                nom_complet = f"{nom} {prenom}".strip()
                print(f"    • {matricule} - {nom_complet} ({cat} / {titre})")
        else:
            print("  Aucun résultat avec ce filtre")
    print()

    print("=" * 80)
    print("  ✅ Vérification terminée")
    print("=" * 80 + "\n")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
