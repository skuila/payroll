#!/usr/bin/env python3
"""Script pour vérifier que la migration 020 a bien créé les vues"""
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def verifier_vues():
    """Vérifie que toutes les vues de la migration 020 existent"""
    provider = PostgresProvider()
    repo = provider.repo

    # Liste des vues attendues
    vues_attendues = [
        "paie.v_global_derniere_paie",
        "paie.v_employe_derniere_paie",
        "paie.v_employe_nom_majuscules",
        "paie.v_employe_statut_calcule",
        "paie.v_employes_par_paie",
        "paie.v_employe_dates_paie",
    ]

    print("=" * 70)
    print("🔍 VÉRIFICATION MIGRATION 020")
    print("=" * 70)
    print()

    # Vérifier chaque vue
    sql_check = """
        SELECT schemaname, viewname
        FROM pg_views
        WHERE schemaname = 'paie'
        AND viewname IN (
            'v_global_derniere_paie',
            'v_employe_derniere_paie',
            'v_employe_nom_majuscules',
            'v_employe_statut_calcule',
            'v_employes_par_paie',
            'v_employe_dates_paie'
        )
        ORDER BY viewname;
    """

    try:
        result = repo.run_query(sql_check)

        vues_trouvees = [f"{r[0]}.{r[1]}" for r in result]

        print(f"📊 Vues trouvées dans le schéma 'paie': {len(vues_trouvees)}")
        print()

        for vue in vues_attendues:
            vue_short = vue.split(".")[1]
            if vue in vues_trouvees or any(vue_short in v for v in vues_trouvees):
                print(f"   ✅ {vue}")
            else:
                print(f"   ❌ {vue} - MANQUANTE")

        print()

        # Tester quelques requêtes
        if len(vues_trouvees) > 0:
            print("🧪 Tests de requêtes:")
            print()

            # Test 1: v_global_derniere_paie
            try:
                sql1 = "SELECT * FROM paie.v_global_derniere_paie LIMIT 1;"
                r1 = repo.run_query(sql1)
                if r1:
                    print(f"   ✅ v_global_derniere_paie: {r1[0][0]}")
                else:
                    print("   ⚠️ v_global_derniere_paie: Aucune donnée")
            except Exception as e:
                print(f"   ❌ v_global_derniere_paie: Erreur - {e}")

            # Test 2: v_employe_statut_calcule
            try:
                sql2 = "SELECT COUNT(*) FROM paie.v_employe_statut_calcule;"
                r2 = repo.run_query(sql2)
                if r2:
                    print(f"   ✅ v_employe_statut_calcule: {r2[0][0]} employés")
            except Exception as e:
                print(f"   ❌ v_employe_statut_calcule: Erreur - {e}")

            # Test 3: v_employes_par_paie
            try:
                sql3 = "SELECT COUNT(*) FROM paie.v_employes_par_paie;"
                r3 = repo.run_query(sql3)
                if r3:
                    print(f"   ✅ v_employes_par_paie: {r3[0][0]} lignes")
            except Exception as e:
                print(f"   ❌ v_employes_par_paie: Erreur - {e}")

        print()
        print("=" * 70)

        if len(vues_trouvees) == len(vues_attendues):
            print("✅ TOUTES LES VUES ONT ÉTÉ CRÉÉES AVEC SUCCÈS")
        else:
            print(f"⚠️ {len(vues_trouvees)}/{len(vues_attendues)} vues trouvées")

        print("=" * 70)

    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if hasattr(repo, "pool") and repo.pool:
            repo.pool.close()


if __name__ == "__main__":
    verifier_vues()
