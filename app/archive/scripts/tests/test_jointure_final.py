#!/usr/bin/env python3
"""
Test de jointure pour trouver part_employeur
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
r = p.repo

print("=" * 60)
print("TEST JOINTURE PART EMPLOYEUR")
print("=" * 60)

# Test 1: payroll_transactions → imported_payroll_master
print("\n1. Jointure payroll_transactions → imported_payroll_master:")
sql1 = """
    SELECT 
        COUNT(*) as total,
        COUNT(m.id) as avec_imported,
        SUM(COALESCE(m.part_employeur, 0)) as total_part
    FROM payroll.payroll_transactions t
    LEFT JOIN payroll.imported_payroll_master m
      ON t.source_row_no = m.source_row_number
    LIMIT 5
"""
r1 = r.run_query(sql1)
if r1:
    print(f"   Total transactions: {r1[0][0]}")
    print(f"   Jointures réussies: {r1[0][1]}")
    print(
        f"   Total part employeur: {r1[0][2]:,.2f} $" if r1[0][2] else "   Total: NULL"
    )

# Test 2: Vérifier colonnes dans imported_payroll_master
print("\n2. Échantillon imported_payroll_master:")
sql2 = """
    SELECT 
        source_row_number,
        part_employeur,
        "part employeur "
    FROM payroll.imported_payroll_master
    WHERE part_employeur > 0 OR "part employeur " IS NOT NULL
    LIMIT 3
"""
try:
    r2 = r.run_query(sql2)
    if r2:
        for row in r2:
            print(
                f"   Row {row[0]}: part_employeur={row[1]}, 'part employeur '={row[2]}"
            )
except Exception as e:
    print(f"   Erreur: {e}")
