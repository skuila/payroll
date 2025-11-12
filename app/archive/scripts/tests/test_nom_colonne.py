#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
r = p.repo
# Test direct avec une requête simple
sql = 'SELECT "part employeur " FROM payroll.imported_payroll_master LIMIT 1'
try:
    result = r.run_query(sql)
    print("✓ Colonne trouvée: 'part employeur ' (avec espace)")
    if result and result[0]:
        print(f"  Valeur exemple: {result[0][0]}")
except Exception as e:
    print(f"❌ Erreur: {e}")
