#!/usr/bin/env python3
"""Test rapide de la méthode get_periods()"""

import json

from dotenv import load_dotenv
from app.providers.postgres_provider import PostgresProvider

load_dotenv()

print("=" * 70)
print("TEST DE get_periods()")
print("=" * 70)
print()

try:
    # Créer le provider
    print("🔄 Création du PostgresProvider...")
    provider = PostgresProvider()
    print("✅ Provider créé")
    print()

    # Tester la requête SQL directement
    print("🔍 Test de la requête SQL...")
    sql = """
    SELECT 
        pay_date,
        COUNT(*) as count
    FROM payroll.payroll_transactions
    GROUP BY pay_date
    ORDER BY pay_date DESC
    """

    repo = provider.repo
    if repo is None:
        raise RuntimeError("Connexion base de données indisponible.")

    result = repo.run_query(sql)
    print(f"📊 Résultat: {len(result) if result else 0} lignes")
    print()

    # Construire la réponse comme dans AppBridge
    periods = []
    if result:
        for row in result:
            period_data = {"pay_date": str(row[0]), "count": row[1]}
            periods.append(period_data)
            print(
                f"  ✅ Période: {period_data['pay_date']} ({period_data['count']} transactions)"
            )

    print()
    response = {"success": True, "periods": periods}
    print("📤 Réponse JSON:")
    print(json.dumps(response, indent=2, ensure_ascii=False))
    print()
    print("=" * 70)
    print("✅ TEST RÉUSSI")
    print("=" * 70)

except Exception as e:
    print(f"❌ ERREUR: {e}")
    import traceback

    traceback.print_exc()
    print()
    print("=" * 70)
    print("❌ TEST ÉCHOUÉ")
    print("=" * 70)
