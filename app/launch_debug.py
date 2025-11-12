#!/usr/bin/env python3
"""Lanceur avec logs détaillés pour diagnostic"""
import sys
import os
from pathlib import Path

from config.connection_standard import get_dsn, mask_dsn, test_connection

print("=" * 70)
print("LANCEMENT APPLICATION PAYROLL - MODE DEBUG")
print("=" * 70)

# 1. Configuration PYTHONPATH
app_root = Path(__file__).parent.parent.absolute()
print("\n1. Configuration PYTHONPATH:")
print(f"   Root: {app_root}")
sys.path.insert(0, str(app_root))
print("   ✅ PYTHONPATH configuré")

# 2. Chargement .env
print("\n2. Chargement .env:")
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"   ✅ .env chargé: {env_file}")
    else:
        print(f"   ⚠️  .env absent: {env_file}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

# 3. Vérification variables
print("\n3. Variables d'environnement:")
try:
    dsn = get_dsn()
    print(f"   ✅ DSN standard: {mask_dsn(dsn)}")
except RuntimeError as exc:
    print(f"   ❌ DSN indisponible: {exc}")
    sys.exit(1)

# 4. Test connexion DB
print("\n4. Test connexion PostgreSQL:")
result = test_connection()
if result.get("success"):
    print(f"   ✅ Connecté: {result.get('user')}@{result.get('database')}")
else:
    print(f"   ❌ Erreur: {result.get('error')}")
    sys.exit(1)

# 5. Import Provider
print("\n5. Import Provider:")
try:
    print("   ✅ Provider importé")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# 6. Lancement PyQt6
print("\n6. Lancement interface PyQt6:")
try:
    from PyQt6.QtWidgets import QApplication

    print("   ✅ PyQt6 importé")

    # Créer application
    app = QApplication(sys.argv)
    print("   ✅ QApplication créée")

    # Importer et créer fenêtre principale
    print("\n7. Chargement MainWindow...")
    os.chdir(Path(__file__).parent)  # S'assurer d'être dans app/

    # Import du fichier principal
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "payroll_main", "payroll_app_qt_Version4.py"
    )
    payroll_module = importlib.util.module_from_spec(spec)

    print("   ✅ Module chargé, exécution...")
    spec.loader.exec_module(payroll_module)

except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
