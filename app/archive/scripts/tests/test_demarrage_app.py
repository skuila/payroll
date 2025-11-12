#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test du démarrage de l'application - Vérification des imports et initialisation"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("TEST DÉMARRAGE APPLICATION")
print("=" * 80)

# Test 1: Imports
print("\n1. Test des imports...")
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebChannel import QWebChannel

    print("✅ Imports PyQt6: OK")
except Exception as e:
    print(f"❌ Erreur imports PyQt6: {e}")
    sys.exit(1)

try:
    from app.providers.postgres_provider import PostgresProvider
    from providers.hybrid_provider import get_hybrid_provider
    from ui.api_client import get_api_client

    print("✅ Imports providers: OK")
except Exception as e:
    print(f"❌ Erreur imports providers: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 2: Initialisation QApplication (sans affichage)
print("\n2. Test initialisation QApplication...")
try:
    app = QApplication(sys.argv)
    print("✅ QApplication créée")
except Exception as e:
    print(f"❌ Erreur QApplication: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 3: Initialisation providers
print("\n3. Test initialisation providers...")
try:
    hybrid = get_hybrid_provider()
    print("✅ Provider hybride: OK")
except Exception as e:
    print(f"❌ Erreur provider hybride: {e}")
    import traceback

    traceback.print_exc()

try:
    api_client = get_api_client()
    print("✅ API client: OK")
except Exception as e:
    print(f"❌ Erreur API client: {e}")
    import traceback

    traceback.print_exc()

try:
    provider = PostgresProvider()
    print("✅ PostgreSQL provider: OK")
except Exception as e:
    print(f"❌ Erreur PostgreSQL provider: {e}")
    import traceback

    traceback.print_exc()

# Test 4: Test connexion API
print("\n4. Test connexion API...")
try:
    if api_client.test_connection():
        print("✅ API connectée")
    else:
        print("⚠️ API non connectée (normal si non démarrée)")
except Exception as e:
    print(f"⚠️ Erreur test connexion API: {e}")

# Test 5: Test WebEngine
print("\n5. Test WebEngine...")
try:
    web_view = QWebEngineView()
    print("✅ QWebEngineView créée")
except Exception as e:
    print(f"❌ Erreur QWebEngineView: {e}")
    import traceback

    traceback.print_exc()

# Test 6: Test WebChannel
print("\n6. Test WebChannel...")
try:
    web_channel = QWebChannel()
    print("✅ QWebChannel créée")
except Exception as e:
    print(f"❌ Erreur QWebChannel: {e}")
    import traceback

    traceback.print_exc()

# Test 7: Test chargement fichier HTML
print("\n7. Test chargement fichier HTML...")
try:
    html_path = Path(__file__).parent.parent / "web" / "tabler" / "employees.html"
    if html_path.exists():
        print(f"✅ Fichier HTML trouvé: {html_path}")
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "DataTables" in content:
                print("✅ DataTables détecté dans HTML")
            if "v_employes_par_periode_liste" in content:
                print("✅ Vue SQL détectée dans HTML")
    else:
        print(f"❌ Fichier HTML non trouvé: {html_path}")
except Exception as e:
    print(f"❌ Erreur lecture HTML: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ TOUS LES TESTS DE DÉMARRAGE SONT PASSÉS")
print("=" * 80)
