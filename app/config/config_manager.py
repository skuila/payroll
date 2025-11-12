"""
Configuration centralisée et sécurisée pour l'application payroll
Version: utilise le module standardisé de connexion.
"""

from __future__ import annotations

from typing import Dict, Any
from urllib.parse import urlparse

from .connection_standard import get_dsn, get_admin_dsn, mask_dsn


def _parse_dsn(dsn: str) -> Dict[str, Any]:
    parsed = urlparse(dsn)
    if not parsed.scheme:
        raise RuntimeError("DSN invalide: schéma absent")

    return {
        "host": parsed.hostname or "localhost",
        "port": int(parsed.port or 5432),
        "database": (parsed.path or "/payroll_db").lstrip("/"),
        "user": parsed.username or "payroll_unified",
        "password": parsed.password or "",
    }


def get_db_config() -> Dict[str, Any]:
    """Configuration base de données basée sur le standard."""

    app_info = _parse_dsn(get_dsn())

    try:
        admin_info = _parse_dsn(get_admin_dsn())
    except RuntimeError:
        admin_info = {"user": app_info["user"], "password": app_info["password"]}

    return {
        "host": app_info["host"],
        "port": app_info["port"],
        "database": app_info["database"],
        "user": app_info["user"],
        "password": app_info["password"],
        "superuser": admin_info.get("user", app_info["user"]),
        "superuser_password": admin_info.get("password", app_info["password"]),
    }


def get_dsn_for_user(user_type: str = "app") -> str:
    if user_type == "admin":
        return get_admin_dsn()
    return get_dsn()


def get_superuser_dsn() -> str:
    """Compatibilité descendante."""
    return get_dsn_for_user("admin")


def validate_config() -> bool:
    """Valide la configuration actuelle."""
    try:
        config = get_db_config()
    except RuntimeError as exc:
        print(f"❌ Configuration invalide: {exc}")
        return False

    missing = [
        key
        for key in ("host", "port", "database", "user", "password")
        if not config.get(key)
    ]

    if missing:
        print(f"❌ Configuration incomplète. Variables manquantes: {missing}")
        return False

    print(f"✅ Configuration valide: {mask_dsn(get_dsn())}")
    return True


# Alias pour compatibilité descendante
def get_payroll_dsn():
    """Alias pour compatibilité."""
    return get_dsn()
