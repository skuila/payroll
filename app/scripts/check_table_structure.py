#!/usr/bin/env python3
"""Vérifie la structure de payroll_transactions"""

from dotenv import load_dotenv

load_dotenv()

from config.connection_standard import run_select

print("=" * 70)
print("STRUCTURE DE payroll.payroll_transactions")
print("=" * 70)
print()

sql = """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_schema = 'payroll' 
AND table_name = 'payroll_transactions'
ORDER BY ordinal_position
"""

cols = run_select(sql)

if cols:
    print(f"✅ Table trouvée avec {len(cols)} colonnes:")
    print()
    for col in cols:
        nullable = "NULL" if col[2] == "YES" else "NOT NULL"
        print(f"  • {col[0]:30} {col[1]:20} {nullable}")
else:
    print("❌ Table non trouvée")

print()
print("=" * 70)
