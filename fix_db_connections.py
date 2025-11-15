#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de détection et correction des connexions DB non standard
Remplace psycopg.connect() et os.getenv('PAYROLL_*') par l'API standard
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path.cwd()

# Fichiers whitelistés (ne pas modifier)
WHITELIST = {
    REPO_ROOT / "app" / "config" / "connection_standard.py",
    REPO_ROOT / "app" / "services" / "data_repo.py",
    REPO_ROOT / "app" / "providers" / "postgres_provider.py",
    REPO_ROOT / "app" / "launch_payroll.py",
}

# Dossiers à exclure
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "archive",
    "app/backups",
    "legacy_non_standard",
    ".mypy_cache",
    ".ruff_cache",
}


@dataclass
class Violation:
    file: Path
    line_num: int
    line_content: str
    violation_type: str  # 'psycopg.connect', 'os.getenv', 'create_engine'
    description: str


@dataclass
class Patch:
    file: Path
    old_lines: List[str]
    new_lines: List[str]
    safe: bool
    description: str


def is_whitelisted(path: Path) -> bool:
    """Vérifie si un fichier est whitelisté"""
    try:
        resolved = path.resolve()
        return resolved in WHITELIST
    except FileNotFoundError:
        return False


def should_skip(path: Path) -> bool:
    """Vérifie si un fichier/dossier doit être ignoré"""
    parts = path.parts
    return any(skip_dir in parts for skip_dir in SKIP_DIRS)


def scan_file(path: Path) -> List[Violation]:
    """Scanne un fichier pour détecter les violations"""
    if not path.is_file() or path.suffix != ".py":
        return []

    if is_whitelisted(path) or should_skip(path):
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return []

    violations = []
    lines = content.splitlines()

    # Pattern 1: psycopg.connect
    psycopg_pattern = re.compile(r"\bpsycopg\.connect\s*\(")
    for i, line in enumerate(lines, 1):
        if psycopg_pattern.search(line):
            violations.append(
                Violation(
                    file=path,
                    line_num=i,
                    line_content=line.strip(),
                    violation_type="psycopg.connect",
                    description="Usage direct de psycopg.connect()",
                )
            )

    # Pattern 2: os.getenv('PAYROLL_*')
    env_pattern = re.compile(r"os\.getenv\s*\(\s*['\"]PAYROLL_")
    for i, line in enumerate(lines, 1):
        if env_pattern.search(line):
            violations.append(
                Violation(
                    file=path,
                    line_num=i,
                    line_content=line.strip(),
                    violation_type="os.getenv",
                    description="Lecture directe de variable PAYROLL_*",
                )
            )

    # Pattern 3: os.environ.get('PAYROLL_*')
    environ_pattern = re.compile(r"os\.environ\.get\s*\(\s*['\"]PAYROLL_")
    for i, line in enumerate(lines, 1):
        if environ_pattern.search(line):
            violations.append(
                Violation(
                    file=path,
                    line_num=i,
                    line_content=line.strip(),
                    violation_type="os.environ.get",
                    description="Lecture directe de variable PAYROLL_*",
                )
            )

    # Pattern 4: create_engine
    engine_pattern = re.compile(r"\bcreate_engine\s*\(")
    for i, line in enumerate(lines, 1):
        if engine_pattern.search(line):
            violations.append(
                Violation(
                    file=path,
                    line_num=i,
                    line_content=line.strip(),
                    violation_type="create_engine",
                    description="Usage de create_engine() - REVIEW nécessaire",
                )
            )

    return violations


def generate_patch(file_path: Path, violations: List[Violation]) -> Optional[Patch]:
    """Génère un patch pour un fichier"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return None

    lines = content.splitlines()
    new_lines = lines.copy()
    imports_added = False
    safe = True
    changes = []

    # Vérifier si les imports nécessaires sont déjà présents
    has_import = "from config.connection_standard import" in content

    for violation in violations:
        line_idx = violation.line_num - 1
        if line_idx >= len(new_lines):
            continue

        original_line = new_lines[line_idx]

        if violation.violation_type == "psycopg.connect":
            # Remplacer psycopg.connect() par get_connection()
            # Pattern simple: with psycopg.connect(...) as conn:
            if "with psycopg.connect" in original_line:
                new_line = original_line.replace("psycopg.connect", "get_connection")
                new_lines[line_idx] = new_line
                changes.append(
                    f"Ligne {violation.line_num}: psycopg.connect → get_connection"
                )
            elif "psycopg.connect(" in original_line:
                # Cas plus complexe - nécessite analyse du contexte
                # Pour l'instant, marquer comme REVIEW
                safe = False
                changes.append(
                    f"Ligne {violation.line_num}: psycopg.connect() - REVIEW nécessaire"
                )

        elif violation.violation_type in ("os.getenv", "os.environ.get"):
            # Remplacer os.getenv('PAYROLL_DSN') par get_dsn()
            if "PAYROLL_DSN" in original_line or "DATABASE_URL" in original_line:
                # Extraire la variable
                match = re.search(
                    r"['\"](PAYROLL_DSN|DATABASE_URL)['\"]", original_line
                )
                if match:
                    # Remplacer par get_dsn()
                    new_line = re.sub(
                        r"os\.(getenv|environ\.get)\s*\(\s*['\"]PAYROLL_DSN['\"]\s*\)",
                        "get_dsn()",
                        original_line,
                    )
                    new_line = re.sub(
                        r"os\.(getenv|environ\.get)\s*\(\s*['\"]DATABASE_URL['\"]\s*\)",
                        "get_dsn()",
                        new_line,
                    )
                    if new_line != original_line:
                        new_lines[line_idx] = new_line
                        changes.append(
                            f"Ligne {violation.line_num}: os.getenv('PAYROLL_DSN') → get_dsn()"
                        )
            else:
                # Autres variables PAYROLL_* - marquer comme REVIEW
                safe = False
                changes.append(
                    f"Ligne {violation.line_num}: {violation.violation_type} - REVIEW nécessaire"
                )

        elif violation.violation_type == "create_engine":
            safe = False
            changes.append(
                f"Ligne {violation.line_num}: create_engine() - REVIEW nécessaire"
            )

    # Ajouter les imports nécessaires
    if changes and not has_import:
        # Trouver la position pour insérer l'import
        import_idx = 0
        for i, line in enumerate(new_lines):
            if line.startswith("import ") or line.startswith("from "):
                import_idx = i + 1
            elif line.strip() and not line.strip().startswith("#"):
                break

        # Insérer l'import
        if "get_dsn" in "\n".join(new_lines) or any(
            "PAYROLL_DSN" in c for c in changes
        ):
            new_lines.insert(
                import_idx, "from config.connection_standard import get_dsn"
            )
            imports_added = True

        if "get_connection" in "\n".join(new_lines) or any(
            "psycopg.connect" in c for c in changes
        ):
            if not imports_added:
                new_lines.insert(
                    import_idx, "from config.connection_standard import get_connection"
                )
            else:
                # Modifier la ligne d'import existante
                for i, line in enumerate(new_lines):
                    if line.startswith("from config.connection_standard import"):
                        new_lines[i] = line.rstrip() + ", get_connection"
                        break
            imports_added = True

    if not changes:
        return None

    return Patch(
        file=file_path,
        old_lines=lines,
        new_lines=new_lines,
        safe=safe,
        description="; ".join(changes),
    )


def main():
    print("=" * 70)
    print("DÉTECTION ET CORRECTION DES CONNEXIONS DB NON STANDARD")
    print("=" * 70)

    # 1. Recherche
    print("\n=== 1. RECHERCHE DES VIOLATIONS ===\n")
    all_violations = []

    for py_file in REPO_ROOT.rglob("*.py"):
        if should_skip(py_file):
            continue
        violations = scan_file(py_file)
        all_violations.extend(violations)

    # Grouper par fichier
    violations_by_file: Dict[Path, List[Violation]] = {}
    for v in all_violations:
        if v.file not in violations_by_file:
            violations_by_file[v.file] = []
        violations_by_file[v.file].append(v)

    print(f"Fichiers avec violations: {len(violations_by_file)}")
    print(f"Total violations: {len(all_violations)}\n")

    for file_path, violations in violations_by_file.items():
        rel_path = file_path.relative_to(REPO_ROOT)
        print(f"  {rel_path}:")
        for v in violations:
            print(f"    Ligne {v.line_num}: {v.violation_type} - {v.description}")
            print(f"      {v.line_content[:80]}")

    if not violations_by_file:
        print("✅ Aucune violation détectée!")
        return 0

    # 2. Génération des patches
    print("\n=== 2. GÉNÉRATION DES PATCHES ===\n")
    patches = []
    safe_patches = []
    review_patches = []

    for file_path, violations in violations_by_file.items():
        patch = generate_patch(file_path, violations)
        if patch:
            patches.append(patch)
            if patch.safe:
                safe_patches.append(patch)
            else:
                review_patches.append(patch)

    print(f"Patches générés: {len(patches)}")
    print(f"  - SAFE: {len(safe_patches)}")
    print(f"  - REVIEW: {len(review_patches)}\n")

    # Afficher les patches SAFE
    if safe_patches:
        print("=== PATCHES SAFE ===\n")
        for patch in safe_patches:
            rel_path = patch.file.relative_to(REPO_ROOT)
            print(f"📄 {rel_path}")
            print(f"   {patch.description}\n")
            print("   Diff:")
            # Afficher un diff simple
            for i, (old, new) in enumerate(
                zip(patch.old_lines[:10], patch.new_lines[:10])
            ):
                if old != new:
                    print(f"   -{i + 1}: {old}")
                    print(f"   +{i + 1}: {new}")
            print()

    # Afficher les patches REVIEW
    if review_patches:
        print("=== PATCHES REVIEW (nécessitent vérification manuelle) ===\n")
        for patch in review_patches:
            rel_path = patch.file.relative_to(REPO_ROOT)
            print(f"⚠️  {rel_path}")
            print(f"   {patch.description}\n")

    # 3. Application des patches SAFE
    if safe_patches:
        print("\n=== 3. APPLICATION DES PATCHES SAFE ===\n")
        response = input(
            f"Appliquer {len(safe_patches)} patch(es) SAFE maintenant? (oui/non): "
        )

        if response.lower() in ("oui", "o", "yes", "y"):
            for patch in safe_patches:
                try:
                    patch.file.write_text(
                        "\n".join(patch.new_lines) + "\n", encoding="utf-8"
                    )
                    rel_path = patch.file.relative_to(REPO_ROOT)
                    print(f"✅ Appliqué: {rel_path}")
                except Exception as e:
                    print(f"❌ Erreur lors de l'application de {patch.file}: {e}")
        else:
            print("Application annulée.")
            return 0
    else:
        print("\nAucun patch SAFE à appliquer.")

    print("\n" + "=" * 70)
    print("✅ DÉTECTION TERMINÉE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
