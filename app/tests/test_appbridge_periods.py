#!/usr/bin/env python3
"""Test automatisé de AppBridge.get_periods() comme dans l'application"""

import sys
import json
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Charger .env AVANT tout
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("TEST AUTOMATISÉ DE AppBridge.get_periods()")
print("=" * 80)
print()


# Simuler l'environnement de l'application
class FakeMainWindow:
    """Fausse fenêtre principale pour le test"""

    pass


try:
    # Importer AppBridge comme dans l'application
    print("🔄 Import de AppBridge...")
    from payroll_app_qt_Version4 import AppBridge

    print("✅ AppBridge importé")
    print()

    # Créer une instance de AppBridge
    print("🔄 Création de AppBridge...")
    fake_window = FakeMainWindow()
    bridge = AppBridge(fake_window)
    print("✅ AppBridge créé")
    print()

    # Appeler get_periods() comme le ferait JavaScript
    print("=" * 80)
    print("APPEL DE get_periods() (comme JavaScript)")
    print("=" * 80)
    print()

    result_json = bridge.get_periods()

    print()
    print("=" * 80)
    print("RÉSULTAT BRUT (JSON string)")
    print("=" * 80)
    print(result_json)
    print()

    # Parser le JSON comme le ferait JavaScript
    print("=" * 80)
    print("RÉSULTAT PARSÉ (objet Python)")
    print("=" * 80)
    result = json.loads(result_json)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()

    # Vérifier le résultat
    print("=" * 80)
    print("ANALYSE DU RÉSULTAT")
    print("=" * 80)
    print()

    if result.get("success"):
        print("✅ success = True")
        periods = result.get("periods", [])
        print(f"✅ Nombre de périodes: {len(periods)}")
        print()

        if periods:
            print("📋 LISTE DES PÉRIODES:")
            for i, period in enumerate(periods, 1):
                print(f"  {i}. {period['pay_date']} ({period['count']} transactions)")
            print()
            print("=" * 80)
            print("✅ TEST RÉUSSI - Les périodes sont disponibles !")
            print("=" * 80)
        else:
            print("⚠️ Aucune période dans la liste")
            print()
            print("=" * 80)
            print("⚠️ TEST PARTIELLEMENT RÉUSSI - Pas de périodes")
            print("=" * 80)
    else:
        print("❌ success = False")
        error = result.get("error", "Erreur inconnue")
        print(f"❌ Erreur: {error}")
        print()
        print("=" * 80)
        print("❌ TEST ÉCHOUÉ")
        print("=" * 80)

except Exception as e:
    print()
    print("=" * 80)
    print("❌ ERREUR LORS DU TEST")
    print("=" * 80)
    print(f"Erreur: {e}")
    print()
    import traceback

    traceback.print_exc()
    print()
    print("=" * 80)
    print("❌ TEST ÉCHOUÉ")
    print("=" * 80)
