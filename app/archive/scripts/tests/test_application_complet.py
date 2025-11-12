#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test complet de l'application - Vérification de tous les composants"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider
import urllib.request
import json
import time


def test_database():
    """Test connexion base de données"""
    print("\n" + "=" * 80)
    print("TEST 1: Connexion Base de Données")
    print("=" * 80)
    try:
        p = PostgresProvider()
        r = p.repo

        # Test simple
        result = r.run_query("SELECT 1 as test")
        if result and result[0][0] == 1:
            print("✅ Base de données: Connectée")
            r.close()
            return True
        else:
            print("❌ Base de données: Erreur de connexion")
            r.close()
            return False
    except Exception as e:
        print(f"❌ Base de données: Erreur - {e}")
        return False


def test_vue_employes():
    """Test vue employés"""
    print("\n" + "=" * 80)
    print("TEST 2: Vue Employés (v_employes_par_periode_liste)")
    print("=" * 80)
    try:
        p = PostgresProvider()
        r = p.repo

        # Test vue
        result = r.run_query(
            """
            SELECT COUNT(*) 
            FROM paie.v_employes_par_periode_liste
            WHERE date_paie = '2025-08-28';
        """
        )
        count = result[0][0] if result else 0
        print(f"✅ Vue employés: {count} lignes pour 2025-08-28")

        # Test Ajarar Amin
        result_ajarar = r.run_query(
            """
            SELECT nom_complet, categorie_emploi, titre_emploi
            FROM paie.v_employes_par_periode_liste
            WHERE LOWER(nom_complet) LIKE '%%ajarar%%'
              AND date_paie = '2025-08-28'
            LIMIT 1;
        """
        )
        if result_ajarar:
            row = result_ajarar[0]
            print("✅ Ajarar Amin trouvé:")
            print(f"   Catégorie: {row[1]}")
            print(f"   Titre: {row[2]}")
            if "Agent" in str(row[2]) and "gestion comptable" in str(row[2]):
                print("✅ Titre correct pour Ajarar Amin")
            else:
                print(
                    f"❌ Titre incorrect: {row[2]} (attendu: Agent(e) de gestion comptable)"
                )
        else:
            print("❌ Ajarar Amin non trouvé dans la vue")

        r.close()
        return True
    except Exception as e:
        print(f"❌ Vue employés: Erreur - {e}")
        import traceback

        traceback.print_exc()
        return False


def test_api():
    """Test API FastAPI"""
    print("\n" + "=" * 80)
    print("TEST 3: API FastAPI")
    print("=" * 80)
    try:
        # Attendre un peu que l'API démarre
        time.sleep(2)

        # Test health check
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:8001/health", timeout=2
            ) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    print("✅ API FastAPI: Accessible")
                    print(f"   Status: {data.get('status', 'N/A')}")
                    return True
        except Exception as e:
            print(f"⚠️ API FastAPI: Non accessible ({e})")
            print("   (Normal si l'API n'est pas démarrée)")
            return False
    except Exception as e:
        print(f"❌ API FastAPI: Erreur - {e}")
        return False


def test_stg_paie_transactions():
    """Test données staging"""
    print("\n" + "=" * 80)
    print("TEST 4: Données Staging (stg_paie_transactions)")
    print("=" * 80)
    try:
        p = PostgresProvider()
        r = p.repo

        # Vérifier Ajarar Amin
        result = r.run_query(
            """
            SELECT DISTINCT
                categorie_emploi,
                titre_emploi,
                COUNT(*) as nb
            FROM paie.stg_paie_transactions
            WHERE matricule = '2364'
              AND date_paie = '2025-08-28'
            GROUP BY categorie_emploi, titre_emploi;
        """
        )

        if result:
            print("✅ Données staging pour Ajarar Amin (matricule 2364):")
            for row in result:
                print(f"   Catégorie: {row[0]}")
                print(f"   Titre: {row[1]}")
                print(f"   Lignes: {row[2]}")
                if (
                    row[1]
                    and "Agent" in str(row[1])
                    and "gestion comptable" in str(row[1])
                ):
                    print("   ✅ Titre correct")
                elif row[1] and row[1] != "None":
                    print(f"   ⚠️ Titre: {row[1]}")
        else:
            print("❌ Aucune donnée trouvée pour Ajarar Amin")

        r.close()
        return True
    except Exception as e:
        print(f"❌ Données staging: Erreur - {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 80)
    print("TESTS COMPLETS DE L'APPLICATION")
    print("=" * 80)

    results = {
        "Base de données": test_database(),
        "Vue employés": test_vue_employes(),
        "API FastAPI": test_api(),
        "Données staging": test_stg_paie_transactions(),
    }

    print("\n" + "=" * 80)
    print("RÉSUMÉ DES TESTS")
    print("=" * 80)
    for test_name, result in results.items():
        status = "✅ OK" if result else "❌ ÉCHEC"
        print(f"{test_name}: {status}")

    print("\n" + "=" * 80)
    if all(results.values()):
        print("✅ TOUS LES TESTS SONT PASSÉS")
    else:
        print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
