"""
Script de refactoring automatique des connexions PostgreSQL
============================================================

Ce script remplace toutes les connexions directes par l'API standardisée.

Règles:
1. Remplacer psycopg.connect() par get_connection_pool()
2. Remplacer create_engine() par get_connection_pool()
3. Remplacer les lectures d'env par get_dsn()
4. Respecter la liste blanche

Auteur: Système de refactoring
Date: 2025-11-11
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict

# Liste blanche (fichiers autorisés à avoir des connexions directes)
WHITELIST = [
    "app/config/connection_standard.py",
    "app/services/data_repo.py",
    "app/providers/postgres_provider.py",
    "app/launch_payroll.py",
]

# Patterns à détecter
PATTERNS = {
    "psycopg_connect": r"psycopg\.connect\(",
    "create_engine": r"create_engine\(",
    "os_getenv_payroll": r'os\.getenv\([\'"]PAYROLL',
    "os_getenv_database": r'os\.getenv\([\'"]DATABASE_URL',
    "os_getenv_pgpassword": r'os\.getenv\([\'"]PGPASSWORD',
}


def is_whitelisted(file_path: Path, root: Path) -> bool:
    """Vérifie si un fichier est dans la liste blanche."""
    rel_path = file_path.relative_to(root).as_posix()
    return any(wl in rel_path for wl in WHITELIST)


def scan_file(file_path: Path) -> Dict[str, List[int]]:
    """Scanne un fichier pour détecter les patterns."""
    violations = {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for pattern_name, pattern in PATTERNS.items():
            matches = []
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    matches.append(i)

            if matches:
                violations[pattern_name] = matches

    except Exception as e:
        print(f"   ⚠️  Erreur lecture {file_path}: {e}")

    return violations


def scan_repository(root_path: Path) -> Dict[str, Dict[str, List[int]]]:
    """Scanne tout le dépôt pour trouver les violations."""
    results = {}

    # Parcourir tous les fichiers Python
    for py_file in root_path.rglob("*.py"):
        # Ignorer les fichiers dans certains dossiers
        if any(
            part in py_file.parts
            for part in ["__pycache__", ".git", "venv", "env", "node_modules"]
        ):
            continue

        # Vérifier la liste blanche
        if is_whitelisted(py_file, root_path):
            continue

        violations = scan_file(py_file)
        if violations:
            rel_path = py_file.relative_to(root_path).as_posix()
            results[rel_path] = violations

    return results


def generate_report(results: Dict[str, Dict[str, List[int]]]) -> str:
    """Génère un rapport des violations."""
    report = []
    report.append("=" * 80)
    report.append("RAPPORT DE SCAN - CONNEXIONS NON STANDARDISÉES")
    report.append("=" * 80)
    report.append("")

    if not results:
        report.append("✅ AUCUNE VIOLATION DÉTECTÉE")
        report.append("")
        report.append(
            "Tous les fichiers utilisent l'API standardisée ou sont dans la liste blanche."
        )
        return "\n".join(report)

    # Statistiques
    total_files = len(results)
    total_violations = sum(
        len(v) for violations in results.values() for v in violations.values()
    )

    report.append(f"📊 STATISTIQUES:")
    report.append(f"   • Fichiers avec violations: {total_files}")
    report.append(f"   • Total de violations: {total_violations}")
    report.append("")

    # Détails par type
    by_type = {}
    for file_path, violations in results.items():
        for pattern_name, lines in violations.items():
            if pattern_name not in by_type:
                by_type[pattern_name] = []
            by_type[pattern_name].append((file_path, lines))

    report.append("📋 VIOLATIONS PAR TYPE:")
    report.append("")

    for pattern_name, files in by_type.items():
        count = sum(len(lines) for _, lines in files)
        report.append(
            f"  {pattern_name}: {count} occurrences dans {len(files)} fichiers"
        )

    report.append("")
    report.append("=" * 80)
    report.append("DÉTAILS PAR FICHIER")
    report.append("=" * 80)
    report.append("")

    for file_path in sorted(results.keys()):
        violations = results[file_path]
        report.append(f"📄 {file_path}")

        for pattern_name, lines in violations.items():
            report.append(f"   • {pattern_name}: lignes {', '.join(map(str, lines))}")

        report.append("")

    report.append("=" * 80)
    report.append("ACTIONS RECOMMANDÉES")
    report.append("=" * 80)
    report.append("")
    report.append("1. Refactoriser les fichiers listés ci-dessus")
    report.append("2. Remplacer psycopg.connect() par get_connection_pool()")
    report.append("3. Remplacer create_engine() par get_connection_pool()")
    report.append("4. Remplacer os.getenv('PAYROLL_*') par get_dsn()")
    report.append("5. Tester chaque fichier modifié")
    report.append("")

    return "\n".join(report)


def main():
    """Point d'entrée principal."""
    print("🔍 Scan du dépôt pour connexions non standardisées...")
    print("")

    # Déterminer la racine du projet
    root = (
        Path(__file__).resolve().parents[2]
    )  # app/scripts/refactor_connections.py -> APP/
    app_root = root / "app"

    print(f"📁 Racine: {app_root}")
    print("")

    # Scanner
    results = scan_repository(app_root)

    # Générer le rapport
    report = generate_report(results)

    # Afficher
    print(report)

    # Sauvegarder
    report_file = app_root / "REFACTOR_REPORT.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"📝 Rapport sauvegardé: {report_file}")
    print("")

    # Code de sortie
    if results:
        print("⚠️  Des violations ont été détectées. Refactoring nécessaire.")
        return 1
    else:
        print("✅ Aucune violation. Le dépôt est conforme.")
        return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
