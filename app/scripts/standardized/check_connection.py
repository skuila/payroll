#!/usr/bin/env python3
"""Test de connexion via le module standardisé."""

from __future__ import annotations

try:
    from app.config.connection_standard import mask_dsn, test_connection, get_dsn
except ImportError:  # pragma: no cover
    from config.connection_standard import mask_dsn, test_connection, get_dsn  # type: ignore


def run_check() -> dict:
    dsn = get_dsn()
    result = test_connection()
    result["dsn_masked"] = mask_dsn(dsn)
    return result


def main() -> None:
    result = run_check()
    if result.get("success"):
        print("✅ Connexion réussie")
        print(f"   Utilisateur: {result.get('user')}")
        print(f"   Base: {result.get('database')}")
        print(f"   DSN: {result.get('dsn_masked')}")
    else:
        print("❌ Échec connexion:", result.get("error"))


if __name__ == "__main__":
    main()
