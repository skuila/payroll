#!/usr/bin/env python3
"""
Script anti-régression - Connexions PostgreSQL
===============================================

Ce script vérifie qu'aucune connexion directe n'existe en dehors
de la liste blanche.

Usage:
    python scripts/forbid_direct_db_connect.py

Exit codes:
    0: Aucune violation
    1: Violations détectées

Auteur: Système de standardisation
Date: 2025-11-11
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

# Liste blanche (fichiers autorisés)
WHITELIST_FILES = [
    "config/connection_standard.py",
    "services/data_repo.py",
    "providers/postgres_provider.py",
    "launch_payroll.py",
]

# Patterns interdits
FORBIDDEN_PATTERNS = {
    "psycopg_connect": {
        "pattern": r"psycopg\.connect\(",
        "message": "Connexion directe psycopg.connect() interdite. Utiliser get_connection_pool() ou get_connection()",
    },
    "create_engine": {
        "pattern": r"create_engine\(",
        "message": "create_engine() interdit. Utiliser get_connection_pool()",
    },
    "os_getenv_payroll_dsn": {
        "pattern": r'os\.getenv\([\'"]PAYROLL_DSN[\'"]\)',
        "message": "Lecture directe de PAYROLL_DSN interdite. Utiliser get_dsn()",
    },
    "os_getenv_database_url": {
        "pattern": r'os\.getenv\([\'"]DATABASE_URL[\'"]\)',
        "message": "Lecture directe de DATABASE_URL interdite. Utiliser get_dsn()",
    },
    "os_getenv_payroll_db": {
        "pattern": r'os\.getenv\([\'"]PAYROLL_DB_(HOST|PORT|NAME|USER|PASSWORD)[\'"]\)',
        "message": "Lecture directe de PAYROLL_DB_* interdite. Utiliser get_dsn()",
    },
}

# Dossiers à ignorer
IGNORE_DIRS = [
    "__pycache__",
    ".git",
    "venv",
    "env",
    "node_modules",
    ".pytest_cache",
    "archive",
    "_cleanup_report",
    "tests/legacy",
]

# ============================================================================
# FONCTIONS
# ============================================================================


def is_whitelisted(file_path: Path, root: Path) -> bool:
    """Vérifie si un fichier est dans la liste blanche."""
    try:
        rel_path = file_path.relative_to(root).as_posix()
        return any(wl in rel_path for wl in WHITELIST_FILES)
    except ValueError:
        return False


def should_ignore(file_path: Path) -> bool:
    """Vérifie si un fichier doit être ignoré."""
    return any(ignore_dir in file_path.parts for ignore_dir in IGNORE_DIRS)


def scan_file(file_path: Path) -> List[Tuple[str, int, str]]:
    """
    Scanne un fichier pour détecter les violations.

    Returns:
        Liste de (pattern_name, line_number, line_content)
    """
    violations = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for pattern_name, config in FORBIDDEN_PATTERNS.items():
            pattern = config["pattern"]

            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    violations.append((pattern_name, line_num, line.strip()))

    except Exception as e:
        print(f"⚠️  Erreur lecture {file_path}: {e}", file=sys.stderr)

    return violations


def scan_repository(root_path: Path) -> Dict[str, List[Tuple[str, int, str]]]:
    """
    Scanne tout le dépôt pour trouver les violations.

    Returns:
        Dict[file_path, violations]
    """
    results = {}

    for py_file in root_path.rglob("*.py"):
        # Ignorer certains dossiers
        if should_ignore(py_file):
            continue

        # Vérifier la liste blanche
        if is_whitelisted(py_file, root_path):
            continue

        violations = scan_file(py_file)
        if violations:
            rel_path = py_file.relative_to(root_path).as_posix()
            results[rel_path] = violations

    return results


def print_report(results: Dict[str, List[Tuple[str, int, str]]]) -> None:
    """Affiche le rapport des violations."""
    if not results:
        print("✅ AUCUNE VIOLATION DÉTECTÉE")
        print("")
        print("Tous les fichiers utilisent l'API standardisée connection_standard.py")
        return

    print("❌ VIOLATIONS DÉTECTÉES")
    print("=" * 80)
    print("")

    total_violations = sum(len(v) for v in results.values())
    print(f"📊 {len(results)} fichiers avec {total_violations} violations")
    print("")

    for file_path in sorted(results.keys()):
        violations = results[file_path]
        print(f"📄 {file_path}")

        for pattern_name, line_num, line_content in violations:
            message = FORBIDDEN_PATTERNS[pattern_name]["message"]
            print(f"   Ligne {line_num}: {pattern_name}")
            print(f"   → {line_content[:70]}...")
            print(f"   ⚠️  {message}")
            print("")

    print("=" * 80)
    print("ACTIONS REQUISES:")
    print("=" * 80)
    print("")
    print("1. Remplacer psycopg.connect() par:")
    print("   from config.connection_standard import get_connection")
    print("   with get_connection() as conn:")
    print("       ...")
    print("")
    print("2. Remplacer create_engine() par:")
    print("   from config.connection_standard import get_connection_pool")
    print("   pool = get_connection_pool()")
    print("")
    print("3. Remplacer os.getenv('PAYROLL_*') par:")
    print("   from config.connection_standard import get_dsn")
    print("   dsn = get_dsn()")
    print("")
    print("4. Consulter: app/guides/CONNEXION_STANDARDISEE.md")
    print("")


def main() -> int:
    """Point d'entrée principal."""
    print("🔍 Vérification des connexions standardisées...")
    print("")

    # Déterminer la racine
    script_path = Path(__file__).resolve()
    root = script_path.parents[2] / "app"  # APP/app/scripts/forbid_direct_db_connect.py

    if not root.exists():
        print(f"❌ Erreur: Racine introuvable: {root}", file=sys.stderr)
        return 1

    print(f"📁 Racine: {root}")
    print("")

    # Scanner
    results = scan_repository(root)

    # Afficher le rapport
    print_report(results)

    # Code de sortie
    if results:
        print("❌ ÉCHEC: Des violations ont été détectées")
        return 1
    else:
        print("✅ SUCCÈS: Aucune violation")
        return 0


if __name__ == "__main__":
    sys.exit(main())
