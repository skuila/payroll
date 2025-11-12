#!/usr/bin/env python3
"""
Script pour vérifier les données part_employeur dans stg_paie_transactions
et pourquoi la jointure ne fonctionne pas
"""
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def main():
    print("=" * 60)
    print("🔍 VÉRIFICATION: Données part_employeur")
    print("=" * 60)

    provider = PostgresProvider()
    repo = provider.repo

    # 1. Vérifier stg_paie_transactions
    print("\n1. Données dans paie.stg_paie_transactions:")
    sql = """
        SELECT 
            COUNT(*) as total,
            COUNT(part_employeur_cents) as avec_valeur,
            COUNT(CASE WHEN part_employeur_cents > 0 THEN 1 END) as avec_valeur_positive,
            SUM(part_employeur_cents) / 100.0 as total_part_employeur,
            AVG(part_employeur_cents) / 100.0 as moyenne_part_employeur
        FROM paie.stg_paie_transactions
    """
    stats = repo.run_query(sql)
    if stats and stats[0]:
        row = stats[0]
        print(f"   ✓ Total lignes: {row[0]}")
        print(f"   ✓ Lignes avec part_employeur_cents: {row[1]}")
        print(f"   ✓ Lignes avec part_employeur > 0: {row[2]}")
        print(
            f"   ✓ Total part employeur: {row[3]:,.2f} $"
            if row[3]
            else "   ⚠️ Total: NULL"
        )
        print(
            f"   ✓ Moyenne part employeur: {row[4]:,.2f} $"
            if row[4]
            else "   ⚠️ Moyenne: NULL"
        )

    # 2. Échantillon de données
    print("\n2. Échantillon de 5 lignes avec part_employeur:")
    sql2 = """
        SELECT 
            source_file,
            source_row_number,
            date_paie,
            matricule,
            montant_cents / 100.0 as montant,
            part_employeur_cents / 100.0 as part_employeur
        FROM paie.stg_paie_transactions
        WHERE part_employeur_cents > 0
        LIMIT 5
    """
    echantillon = repo.run_query(sql2)
    if echantillon:
        for e in echantillon:
            print(
                f"   - {e[0]} | ligne {e[1]} | {e[2]} | {e[3]} | montant: {e[4]:,.2f} $ | part: {e[5]:,.2f} $"
            )
    else:
        print("   ⚠️ Aucune ligne avec part_employeur > 0")

    # 3. Vérifier payroll_transactions
    print("\n3. Données dans payroll.payroll_transactions:")
    sql3 = """
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT source_file) as nb_fichiers,
            COUNT(CASE WHEN source_file IS NOT NULL THEN 1 END) as avec_source_file,
            COUNT(CASE WHEN source_row_no IS NOT NULL THEN 1 END) as avec_source_row
        FROM payroll.payroll_transactions
    """
    stats2 = repo.run_query(sql3)
    if stats2 and stats2[0]:
        row = stats2[0]
        print(f"   ✓ Total transactions: {row[0]}")
        print(f"   ✓ Fichiers distincts: {row[1]}")
        print(f"   ✓ Transactions avec source_file: {row[2]}")
        print(f"   ✓ Transactions avec source_row_no: {row[3]}")

    # 4. Tester la jointure
    print("\n4. Test de jointure payroll_transactions ↔ stg_paie_transactions:")
    sql4 = """
        SELECT 
            COUNT(*) as total_transactions,
            COUNT(s.stg_id) as jointures_reussies,
            SUM(COALESCE(s.part_employeur_cents, 0)) / 100.0 as total_part_employeur_jointure
        FROM payroll.payroll_transactions t
        LEFT JOIN paie.stg_paie_transactions s
          ON t.source_file = s.source_file
         AND t.source_row_no = s.source_row_number
    """
    jointure = repo.run_query(sql4)
    if jointure and jointure[0]:
        row = jointure[0]
        print(f"   ✓ Total transactions: {row[0]}")
        print(f"   ✓ Jointures réussies: {row[1]}")
        print(
            f"   ✓ Part employeur via jointure: {row[2]:,.2f} $"
            if row[2]
            else "   ⚠️ Part: NULL"
        )
        if row[0] > 0:
            taux_jointure = (row[1] / row[0]) * 100
            print(f"   → Taux de jointure: {taux_jointure:.1f}%")

    # 5. Comparer les clés de jointure
    print("\n5. Comparaison des clés de jointure:")
    sql5 = """
        SELECT 
            t.source_file as t_file,
            t.source_row_no as t_row,
            s.source_file as s_file,
            s.source_row_number as s_row,
            s.part_employeur_cents
        FROM payroll.payroll_transactions t
        LEFT JOIN paie.stg_paie_transactions s
          ON t.source_file = s.source_file
         AND t.source_row_no = s.source_row_number
        WHERE t.source_file IS NOT NULL
        LIMIT 5
    """
    comparaison = repo.run_query(sql5)
    if comparaison:
        print("   Échantillon de jointures:")
        for c in comparaison:
            match = "✓" if c[2] else "✗"
            part = f"{c[4]/100.0:.2f} $" if c[4] else "NULL"
            print(f"   {match} t:({c[0]}, {c[1]}) ↔ s:({c[2]}, {c[3]}) | part: {part}")
    else:
        print("   ⚠️ Aucune transaction avec source_file")


if __name__ == "__main__":
    main()
