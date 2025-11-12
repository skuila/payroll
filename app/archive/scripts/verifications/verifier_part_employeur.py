#!/usr/bin/env python3
"""
Script pour vérifier où se trouve la colonne part_employeur dans les données
"""
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def main():
    print("=" * 60)
    print("🔍 VÉRIFICATION: Où se trouve part_employeur?")
    print("=" * 60)

    provider = PostgresProvider()
    repo = provider.repo

    # 1. Vérifier stg_paie_transactions
    print("\n1. Table paie.stg_paie_transactions:")
    sql = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema='paie' AND table_name='stg_paie_transactions' 
        AND column_name LIKE '%%employeur%%'
        ORDER BY ordinal_position
    """
    cols = repo.run_query(sql)
    if cols:
        for c in cols:
            print(f"   ✓ {c[0]} ({c[1]})")

        # Vérifier si des données existent
        sql_count = """
            SELECT COUNT(*), 
                   COUNT(part_employeur_cents) as avec_valeur,
                   SUM(part_employeur_cents) / 100.0 as total_part_employeur
            FROM paie.stg_paie_transactions
        """
        stats = repo.run_query_single(sql_count)
        if stats:
            print("\n   Statistiques:")
            print(f"   - Total lignes: {stats[0]}")
            print(f"   - Lignes avec part_employeur: {stats[1]}")
            print(f"   - Total part employeur: {stats[2]:,.2f} $")
    else:
        print("   ❌ Aucune colonne part_employeur trouvée")

    # 2. Vérifier payroll_transactions
    print("\n2. Table payroll.payroll_transactions:")
    sql2 = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema='payroll' AND table_name='payroll_transactions' 
        AND column_name LIKE '%%employeur%%'
        ORDER BY ordinal_position
    """
    cols2 = repo.run_query(sql2)
    if cols2:
        for c in cols2:
            print(f"   ✓ {c[0]} ({c[1]})")
    else:
        print("   ⚠️ Aucune colonne part_employeur dans payroll_transactions")
        print("   → La part employeur doit être jointe depuis stg_paie_transactions")

    # 3. Vérifier si on peut joindre stg_paie_transactions avec payroll_transactions
    print("\n3. Jointure possible stg_paie_transactions ↔ payroll_transactions:")
    sql3 = """
        SELECT 
            COUNT(*) as total_transactions,
            COUNT(DISTINCT t.source_file || '|' || t.source_row_no::text) as avec_source
        FROM payroll.payroll_transactions t
        WHERE t.source_file IS NOT NULL AND t.source_row_no IS NOT NULL
    """
    join_stats = repo.run_query_single(sql3)
    if join_stats:
        print(
            f"   ✓ Transactions avec source_file/row_no: {join_stats[1]}/{join_stats[0]}"
        )
        print("   → Jointure possible via (source_file, source_row_number)")


if __name__ == "__main__":
    main()
