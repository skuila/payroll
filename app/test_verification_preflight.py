#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste le script de préflight
"""
import sys
import io
from app.services.data_repo import DataRepository

# Forcer UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from config.config_manager import get_dsn

DSN = get_dsn()

# Lire le script SQL
with open("verification-preflight.sql", "r", encoding="utf-8") as f:
    sql_content = f.read()

# Remplacer les placeholders
sql_content = sql_content.replace("REPLACE_ME_SCHEMA", "payroll")
sql_content = sql_content.replace("REPLACE_ME_TABLE", "imported_payroll_master")

print("=" * 70)
print("EXECUTION DU SCRIPT DE PRÉFLIGHT")
print("=" * 70)
print()

repo = DataRepository(DSN)
try:
    with repo.get_connection() as conn:
        with conn.cursor() as cur:
            # Exécuter le script
            cur.execute(sql_content)
            print("✅ Script exécuté avec succès")
            print("   (Les messages NOTICE apparaîtront ci-dessus si tout est OK)")
except Exception as e:
    print("❌ Erreur lors de l'exécution:")
    print(f"   {str(e)}")
    import traceback

    traceback.print_exc()
finally:
    repo.close()

print()
print("=" * 70)
