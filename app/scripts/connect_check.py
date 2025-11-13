#!/usr/bin/env python3
from config.connection_standard import test_connection

print("=" * 60)
print("TEST DE CONNEXION POSTGRESQL")
print("=" * 60)

result = test_connection()

if result["success"]:
    print(f"Utilisateur : {result['user']}")
    print(f"Base       : {result['database']}")
    print(f"Version    : {result['version']}")
    print("\nStatut : OK")
else:
    print("Statut : ERREUR")
    print(result["error"])
