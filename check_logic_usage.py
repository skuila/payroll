#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérifie l'utilisation du dossier app/logic dans l'application
"""

import re
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path.cwd()
LOGIC_DIR = REPO_ROOT / "app" / "logic"

# Fichiers à exclure
EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "venv", "archive", "app/backups"}
EXCLUDE_FILES = {Path(__file__).name}


def should_skip(path: Path) -> bool:
    """Vérifie si un fichier doit être ignoré"""
    parts = path.parts
    return (
        any(skip_dir in parts for skip_dir in EXCLUDE_DIRS)
        or path.name in EXCLUDE_FILES
    )


def find_logic_files() -> List[Path]:
    """Trouve tous les fichiers dans app/logic"""
    if not LOGIC_DIR.exists():
        return []
    return [
        f for f in LOGIC_DIR.rglob("*.py") if f.is_file() and f.name != "__pycache__"
    ]


def find_references_to_logic() -> Dict[str, List[Dict]]:
    """Trouve toutes les références aux modules logic"""
    logic_files = find_logic_files()
    logic_modules = {f.stem: f for f in logic_files}

    references = {}

    # Rechercher dans tous les fichiers Python
    for py_file in REPO_ROOT.rglob("*.py"):
        if should_skip(py_file) or py_file.parent == LOGIC_DIR:
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        file_refs = []

        # Chercher les imports
        for module_name, module_path in logic_modules.items():
            patterns = [
                rf"from\s+logic\.{module_name}\s+import",
                rf"from\s+app\.logic\.{module_name}\s+import",
                rf"import\s+logic\.{module_name}",
                rf"import\s+app\.logic\.{module_name}",
            ]

            for pattern in patterns:
                if re.search(pattern, content):
                    file_refs.append(
                        {"type": "import", "module": module_name, "pattern": pattern}
                    )
                    break

        # Chercher les fonctions spécifiques
        if "run_basic_audit" in content:
            file_refs.append(
                {"type": "function", "function": "run_basic_audit", "module": "audit"}
            )
        if "compare_periods" in content:
            file_refs.append(
                {"type": "function", "function": "compare_periods", "module": "audit"}
            )
        if "_normalize_period" in content or "_parse_number_safe" in content:
            file_refs.append(
                {
                    "type": "function",
                    "function": "formatting functions",
                    "module": "formatting",
                }
            )
        if "_load_df" in content or "summary" in content:
            file_refs.append(
                {
                    "type": "function",
                    "function": "metrics functions",
                    "module": "metrics",
                }
            )
        if (
            "df_resume_mois" in content
            or "export_excel" in content
            or "export_pdf" in content
        ):
            file_refs.append(
                {
                    "type": "function",
                    "function": "reports functions",
                    "module": "reports",
                }
            )

        if file_refs:
            rel_path = py_file.relative_to(REPO_ROOT)
            references[str(rel_path)] = file_refs

    return references


def main():
    print("=" * 70)
    print("VÉRIFICATION DE L'UTILISATION DU DOSSIER app/logic")
    print("=" * 70)

    # 1. Lister les fichiers dans logic
    logic_files = find_logic_files()
    print("\n=== FICHIERS DANS app/logic ===\n")
    for f in logic_files:
        rel_path = f.relative_to(REPO_ROOT)
        print(f"  - {rel_path}")

    # 2. Trouver les références
    print("\n=== RÉFÉRENCES AUX MODULES logic ===\n")
    references = find_references_to_logic()

    if not references:
        print("  ❌ Aucune référence trouvée - Le dossier logic n'est PAS utilisé")
        return 1

    print(f"  ✅ {len(references)} fichier(s) utilisent les modules logic:\n")

    for file_path, refs in sorted(references.items()):
        print(f"  📄 {file_path}:")
        for ref in refs:
            if ref["type"] == "import":
                print(f"    → Import: {ref['module']}")
            else:
                print(f"    → Fonction: {ref['function']} (module: {ref['module']})")
        print()

    # 3. Résumé par module
    print("\n=== RÉSUMÉ PAR MODULE ===\n")
    modules_used = {}
    for file_path, refs in references.items():
        for ref in refs:
            module = ref.get("module", "unknown")
            if module not in modules_used:
                modules_used[module] = []
            modules_used[module].append(file_path)

    for module, files in sorted(modules_used.items()):
        print(f"  {module}.py: utilisé par {len(files)} fichier(s)")
        for f in files[:3]:  # Afficher max 3 fichiers
            print(f"    - {f}")
        if len(files) > 3:
            print(f"    ... et {len(files) - 3} autre(s)")
        print()

    # 4. Vérifier les imports cassés
    print("\n=== VÉRIFICATION DES IMPORTS CASSÉS ===\n")
    broken_imports = []
    for py_file in REPO_ROOT.rglob("*.py"):
        if should_skip(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            if "logic.kpi_engine" in content or "from logic.kpi_engine" in content:
                broken_imports.append(py_file.relative_to(REPO_ROOT))
        except Exception:
            continue

    if broken_imports:
        print(
            f"  ⚠️  {len(broken_imports)} fichier(s) avec imports cassés (logic.kpi_engine n'existe plus):"
        )
        for f in broken_imports:
            print(f"    - {f}")
    else:
        print("  ✅ Aucun import cassé détecté")

    print("\n" + "=" * 70)
    print("✅ VÉRIFICATION TERMINÉE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
