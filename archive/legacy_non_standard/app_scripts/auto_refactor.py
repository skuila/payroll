"""
Script de refactoring automatique - Connexions PostgreSQL
==========================================================

Ce script refactorise automatiquement les fichiers pour utiliser
l'API standardisée connection_standard.py

Auteur: Système de refactoring
Date: 2025-11-11
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Liste blanche
WHITELIST = [
    "connection_standard.py",
    "data_repo.py",
    "postgres_provider.py",
    "launch_payroll.py",
]


def is_whitelisted(file_path: Path) -> bool:
    """Vérifie si un fichier est dans la liste blanche."""
    return any(wl in file_path.name for wl in WHITELIST)


def refactor_file(file_path: Path) -> Tuple[bool, str]:
    """
    Refactorise un fichier pour utiliser l'API standardisée.

    Returns:
        (modified, message)
    """
    if is_whitelisted(file_path):
        return False, "Fichier dans la liste blanche"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        modified = False

        # 1. Ajouter l'import si nécessaire
        if "psycopg.connect(" in content or "create_engine(" in content:
            if "from config.connection_standard import" not in content:
                # Trouver la section d'imports
                import_section_end = 0
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        import_section_end = i + 1

                # Insérer l'import
                if import_section_end > 0:
                    lines.insert(
                        import_section_end,
                        "from config.connection_standard import get_connection_pool, get_dsn, run_select",
                    )
                    content = "\n".join(lines)
                    modified = True

        # 2. Remplacer psycopg.connect() simple
        # Pattern: conn = psycopg.connect(DSN, ...)
        pattern1 = r"(\w+)\s*=\s*psycopg\.connect\([^)]+\)"
        if re.search(pattern1, content):
            # Remplacer par pool
            content = re.sub(
                pattern1,
                r"pool = get_connection_pool()\n    \1 = pool.pool.getconn()",
                content,
            )
            modified = True

        # 3. Remplacer with psycopg.connect()
        # Pattern: with psycopg.connect(...) as conn:
        pattern2 = r"with\s+psycopg\.connect\([^)]+\)\s+as\s+(\w+):"
        if re.search(pattern2, content):
            content = re.sub(
                pattern2,
                r"pool = get_connection_pool()\n    with pool.pool.connection() as \1:",
                content,
            )
            modified = True

        # 4. Remplacer construction DSN manuelle
        # Pattern: DSN = os.getenv('PAYROLL_DSN') or ...
        pattern3 = r'DSN\s*=\s*os\.getenv\([\'"]PAYROLL_DSN[\'"]\)[^\n]+'
        if re.search(pattern3, content):
            content = re.sub(pattern3, "DSN = get_dsn()", content)
            modified = True

        # 5. Remplacer create_engine()
        pattern4 = r"engine\s*=\s*create_engine\([^)]+\)"
        if re.search(pattern4, content):
            content = re.sub(
                pattern4,
                "# REFACTOR: Utiliser get_connection_pool() au lieu de create_engine()\npool = get_connection_pool()",
                content,
            )
            modified = True

        if modified:
            # Sauvegarder
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, "Refactorisé avec succès"
        else:
            return False, "Aucune modification nécessaire"

    except Exception as e:
        return False, f"Erreur: {e}"


def main():
    """Point d'entrée principal."""
    print("🔧 Refactoring automatique des connexions...")
    print("")

    root = Path(__file__).resolve().parents[2] / "app"

    # Fichiers à refactoriser (liste prioritaire)
    priority_files = [
        "connect_check.py",
        "calc_net.py",
        "count_columns.py",
        "show_columns.py",
        "get_db_overview.py",
        "export_employees_json.py",
        "analyser_code_paie_pour_categories.py",
    ]

    stats = {"modified": 0, "skipped": 0, "errors": 0}

    for filename in priority_files:
        file_path = root / filename
        if not file_path.exists():
            continue

        print(f"📄 {filename}... ", end="")
        modified, message = refactor_file(file_path)

        if modified:
            print(f"✅ {message}")
            stats["modified"] += 1
        else:
            print(f"⏭️  {message}")
            stats["skipped"] += 1

    print("")
    print("=" * 60)
    print(f"✅ Modifiés: {stats['modified']}")
    print(f"⏭️  Ignorés: {stats['skipped']}")
    print(f"❌ Erreurs: {stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
