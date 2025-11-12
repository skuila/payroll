#!/usr/bin/env python3
"""Test simple de l'application"""
import sys
import os

# Charger .env
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("TEST APPLICATION PAYROLL")
print("=" * 60)

# 1. Test variables env
print("\n1. VARIABLES D'ENVIRONNEMENT:")
print(f"   PAYROLL_DSN: {'✅ Défini' if os.getenv('PAYROLL_DSN') else '❌ Absent'}")
print(f"   PGPASSWORD: {'✅ Défini' if os.getenv('PGPASSWORD') else '❌ Absent'}")

# 2. Test connexion DB
print("\n2. TEST CONNEXION POSTGRESQL:")
try:
    import psycopg

    dsn = os.getenv("PAYROLL_DSN")
    conn = psycopg.connect(dsn, connect_timeout=5)
    cur = conn.cursor()
    cur.execute("SELECT current_user, current_database()")
    user, db = cur.fetchone()
    print(f"   ✅ Connecté: {user}@{db}")
    conn.close()
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    sys.exit(1)

# 3. Test PyQt6
print("\n3. TEST PYQT6:")
try:
    from PyQt6.QtWidgets import QApplication

    print("   ✅ PyQt6 importé")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    sys.exit(1)

# 4. Test Provider
print("\n4. TEST PROVIDER:")
try:
    from providers.postgres_provider import PostgresProvider

    provider = PostgresProvider(dsn=dsn)
    print("   ✅ Provider initialisé")

    # Test KPI
    kpis = provider.get_kpis()
    print(f"   ✅ KPIs: {kpis.get('nb_employes', 0)} employés")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ TOUS LES TESTS PASSENT - L'APPLICATION PEUT DÉMARRER")
print("=" * 60)
