#!/usr/bin/env python3
"""Vérifie l'absence de connexions PostgreSQL directes hors liste blanche."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # app/scripts/ -> app/ -> project root

WHITELIST = {
    ROOT / "app" / "config" / "connection_standard.py",
    ROOT / "app" / "services" / "data_repo.py",
    ROOT / "app" / "providers" / "postgres_provider.py",
    ROOT / "app" / "launch_payroll.py",
}

FORBIDDEN_CALLS = {
    "psycopg.connect": re.compile(
        r"\bpsycopg\.(connect|Connection)\s*\(", re.MULTILINE
    ),
    "create_engine": re.compile(r"\bcreate_engine\s*\(", re.MULTILINE),
}

ENV_VARS = (
    "PAYROLL_DSN",
    "DATABASE_URL",
    "PAYROLL_DB_HOST",
    "PAYROLL_DB_PORT",
    "PAYROLL_DB_NAME",
    "PAYROLL_DB_USER",
    "PAYROLL_DB_PASSWORD",
    "PAYROLL_DB_SCHEMA",
)

ENV_CHOICES = "|".join(re.escape(var) for var in ENV_VARS)

ENV_PATTERNS = {
    "os.getenv": re.compile(rf"os\.getenv\(\s*['\"]({ENV_CHOICES})['\"]", re.MULTILINE),
    "os.environ.get": re.compile(
        rf"os\.environ\.get\(\s*['\"]({ENV_CHOICES})['\"]", re.MULTILINE
    ),
    "os.environ[]": re.compile(
        rf"os\.environ\[['\"]({ENV_CHOICES})['\"]\]", re.MULTILINE
    ),
}

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "env",
    "venv",
    "build",
    "dist",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    "legacy_non_standard",
    "archive",
}

SKIP_FILES = {
    Path(__file__).resolve(),
    ROOT / "fix_db_connections.py",
}


def is_whitelisted(path: Path) -> bool:
    try:
        return path.resolve() in WHITELIST
    except FileNotFoundError:
        return False


def scan_file(path: Path) -> list[str]:
    try:
        if path.samefile(__file__):
            return []
    except FileNotFoundError:
        return []

    resolved = path.resolve()
    if resolved in SKIP_FILES:
        return []
    if is_whitelisted(resolved):
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    relative = path.relative_to(ROOT)
    hits: list[str] = []

    for label, pattern in FORBIDDEN_CALLS.items():
        if pattern.search(content):
            hits.append(f"{relative}: utilisation interdite de {label}")

    for label, pattern in ENV_PATTERNS.items():
        if pattern.search(content):
            hits.append(f"{relative}: accès direct aux variables via {label}")

    return hits


def main() -> int:
    violations: list[str] = []

    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        violations.extend(scan_file(path))

    if violations:
        print("❌ Connexions directes non autorisées détectées :", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    print("✅ Aucun accès direct non autorisé détecté.")
    return 0


if __name__ == "main":
    raise RuntimeError(
        "Exécuter ce script via python -m ou python scripts/forbid_direct_db_connect.py"
    )

if __name__ == "__main__":
    sys.exit(main())
