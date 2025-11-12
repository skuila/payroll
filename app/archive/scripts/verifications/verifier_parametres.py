#!/usr/bin/env python3
"""
Script pour vérifier les paramètres centralisés dans ref.parameters
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def main():
    print("=" * 60)
    print("🔍 VÉRIFICATION DES PARAMÈTRES CENTRALISÉS")
    print("=" * 60)

    try:
        provider = PostgresProvider()
        repo = provider.repo

        # Vérifier le paramètre part_employeur_taux
        sql = """
            SELECT key, value_num, value_text, updated_at
            FROM ref.parameters
            WHERE key = 'part_employeur_taux'
        """
        rows = repo.run_query(sql)

        if rows:
            row = rows[0]
            taux = row[1] if row[1] is not None else 0.15
            print("\n✅ Paramètre trouvé:")
            print(f"   Clé: {row[0]}")
            print(f"   Valeur numérique: {taux}")
            print(f"   Valeur texte: {row[2] if row[2] else 'N/A'}")
            print(f"   Dernière mise à jour: {row[3] if row[3] else 'N/A'}")
            print("\n💡 Explication:")
            print(
                f"   Ce taux ({taux * 100}%) est utilisé pour calculer la 'part employeur'"
            )
            print("   dans les vues KPI:")
            print(f"   - part_employeur = gains_bruts × {taux}")
            print("   - coût_total = net_à_payer + part_employeur")
            print("\n   Exemple concret:")
            print("   Si gains bruts = 1000 $")
            print(f"   → part_employeur = 1000 × {taux} = {1000 * taux} $")
            print(f"   → coût_total = net + {1000 * taux} $")
        else:
            print("\n❌ Paramètre 'part_employeur_taux' non trouvé!")
            print("   La migration 017 n'a peut-être pas été appliquée correctement.")

        # Vérifier toutes les paramètres
        sql_all = "SELECT key, value_num, value_text FROM ref.parameters ORDER BY key"
        all_params = repo.run_query(sql_all)

        if all_params:
            print("\n📋 Tous les paramètres dans ref.parameters:")
            for p in all_params:
                val = p[1] if p[1] is not None else (p[2] if p[2] else "NULL")
                print(f"   - {p[0]}: {val}")
        else:
            print("\n⚠️ Aucun paramètre dans ref.parameters")

        # Vérifier que les vues KPI utilisent bien ce paramètre
        print("\n🔍 Vérification des vues KPI:")
        sql_check = """
            SELECT 
                periode_paie,
                SUM(gains_brut) as gains_total,
                SUM(part_employeur) as part_employeur_total,
                SUM(cout_total) as cout_total
            FROM paie.v_kpi_mois
            WHERE periode_paie IS NOT NULL
            GROUP BY periode_paie
            ORDER BY periode_paie DESC
            LIMIT 3
        """
        kpi_rows = repo.run_query(sql_check)

        if kpi_rows:
            print("   ✅ Vues KPI fonctionnelles:")
            for kpi in kpi_rows:
                periode = kpi[0]
                gains = kpi[1] or 0
                part_emp = kpi[2] or 0
                cout = kpi[3] or 0

                # Calculer le taux effectif
                taux_effectif = (part_emp / gains * 100) if gains > 0 else 0
                print(f"\n   Période {periode}:")
                print(f"      Gains bruts: {gains:,.2f} $")
                print(f"      Part employeur: {part_emp:,.2f} $")
                print(f"      Taux effectif: {taux_effectif:.2f}%")
                print(f"      Coût total: {cout:,.2f} $")
        else:
            print("   ⚠️ Aucune donnée dans v_kpi_mois")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
