#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de nettoyage complet du dépôt
Supprime les fichiers UI/Qt inutiles et nettoie les fichiers .bak
S'arrête avant push pour validation manuelle
"""

import filecmp
import fnmatch
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Configuration
REPO_ROOT = Path.cwd()
EXCLUDE_DIRS = {".git", "__pycache__", "archive/legacy_non_standard"}
EXCLUDE_PATTERNS = ["archive/legacy_non_standard/**"]

# Patterns de fichiers à supprimer
UI_QT_PATTERNS = [
    "app/ui/**/*theme*",
    "app/ui/**/*Theme*",
    "app/ui/**/*selector*",
    "app/ui/*selector*",
    "app/ui/themes/**",
    "app/ui/*overlays*",
    "app/config/theme_manager.py",
    "app/logic/insights.py",
]

BACKUP_PATTERNS = [
    "**/*.bak",
    "**/*.bak.auto",
    "**/RAPPORT_*.txt",
    "strict_ruff_output.txt",
    "top20_files.txt",
    "tmp*",
    "*.diff",
    "*.patch",
    "app/archive/**",
    "app/backups/**",
    "archive/**",
]

# Patterns pour .gitignore
GITIGNORE_PATTERNS = [
    "*.bak",
    "*.bak.auto",
    "RAPPORT_*.txt",
    "strict_ruff_output.txt",
    "top20_files.txt",
    "tmp*",
    "*.diff",
    "*.patch",
    "app/archive/",
    "app/backups/",
    "archive/",
]


class FileCandidate:
    """Représente un fichier candidat à la suppression"""

    def __init__(self, path: Path):
        self.path = path
        self.size = path.stat().st_size if path.exists() else 0
        self.mtime = path.stat().st_mtime if path.exists() else 0
        self.references: List[str] = []
        self.safe_to_remove = False
        self.reason = ""

    def __repr__(self):
        return f"FileCandidate({self.path}, safe={self.safe_to_remove}, refs={len(self.references)})"


def run_cmd(
    cmd: List[str], check: bool = False, capture_output: bool = True
) -> Tuple[int, str, str]:
    """Exécute une commande et retourne (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_current_branch() -> str:
    """Récupère la branche Git courante"""
    exit_code, stdout, _ = run_cmd(["git", "branch", "--show-current"])
    if exit_code == 0:
        return stdout.strip()
    return ""


def create_backup_branch() -> str:
    """Crée une branche de sauvegarde"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    branch_name = f"backup/cleanup-{timestamp}"
    exit_code, _, _ = run_cmd(["git", "branch", branch_name], check=False)
    if exit_code == 0:
        print(f"✓ Branche de sauvegarde créée : {branch_name}")
        return branch_name
    else:
        print(f"⚠ Impossible de créer la branche de sauvegarde")
        return ""


def create_archive() -> Optional[Path]:
    """Crée une archive des dossiers ciblés"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    temp_dir = Path(os.environ.get("TEMP", "C:/temp"))
    temp_dir.mkdir(parents=True, exist_ok=True)

    archive_path = temp_dir / f"backup_cleanup_{timestamp}.zip"

    dirs_to_archive = [
        "app/ui",
        "app/config",
        "app/logic",
        "app/archive",
        "app/backups",
    ]

    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for dir_path in dirs_to_archive:
                full_path = REPO_ROOT / dir_path
                if full_path.exists():
                    if full_path.is_file():
                        zipf.write(full_path, dir_path)
                    else:
                        for root, dirs, files in os.walk(full_path):
                            # Exclure __pycache__ et .git
                            dirs[:] = [
                                d for d in dirs if d not in {".git", "__pycache__"}
                            ]
                            for file in files:
                                file_path = Path(root) / file
                                arcname = file_path.relative_to(REPO_ROOT)
                                zipf.write(file_path, arcname)

        print(f"✓ Archive créée : {archive_path}")
        return archive_path
    except Exception as e:
        print(f"✗ Erreur lors de la création de l'archive : {e}")
        return None


def find_files_by_patterns(patterns: List[str]) -> Set[Path]:
    """Trouve tous les fichiers correspondant aux patterns"""
    found_files = set()

    for pattern in patterns:
        # Convertir le pattern en glob
        if pattern.endswith("/**"):
            # Dossier entier
            base_dir = pattern[:-3]
            base_path = REPO_ROOT / base_dir
            if base_path.exists() and base_path.is_dir():
                try:
                    for path in base_path.rglob("*"):
                        if path.is_file():
                            path_str = str(path).replace("\\", "/")
                            if "archive/legacy_non_standard" not in path_str:
                                found_files.add(path)
                except Exception:
                    pass
            continue

        # Patterns avec wildcards
        if "*" in pattern:
            # Convertir en glob
            if pattern.startswith("**/"):
                glob_pattern = pattern
            elif pattern.startswith("app/"):
                # Chercher dans app/ spécifiquement
                base_path = REPO_ROOT / "app"
                if base_path.exists():
                    try:
                        for path in base_path.rglob(pattern[4:]):  # Enlever "app/"
                            if path.is_file():
                                path_str = str(path).replace("\\", "/")
                                if "archive/legacy_non_standard" not in path_str:
                                    found_files.add(path)
                    except Exception:
                        pass
                continue
            else:
                glob_pattern = f"**/{pattern}"
        else:
            # Pattern exact
            exact_path = REPO_ROOT / pattern
            if exact_path.exists() and exact_path.is_file():
                found_files.add(exact_path)
            continue

        # Recherche avec glob
        try:
            for path in REPO_ROOT.rglob(glob_pattern):
                # Vérifier les exclusions
                should_exclude = False
                path_str = str(path).replace("\\", "/")
                path_parts = path.parts

                for exclude_dir in EXCLUDE_DIRS:
                    if exclude_dir in path_parts:
                        should_exclude = True
                        break

                if "archive/legacy_non_standard" in path_str:
                    should_exclude = True

                if not should_exclude and path.is_file():
                    # Vérification du pattern
                    if "*" in pattern:
                        # Pattern matching avec fnmatch
                        pattern_normalized = pattern.replace("\\", "/")
                        path_normalized = str(path.relative_to(REPO_ROOT)).replace(
                            "\\", "/"
                        )
                        if fnmatch.fnmatch(
                            path_normalized.lower(), pattern_normalized.lower()
                        ):
                            found_files.add(path)
                    else:
                        found_files.add(path)
        except Exception as e:
            print(f"  ⚠ Erreur avec le pattern {pattern}: {e}")
            continue

    return found_files


def find_references_fast(
    file_path: Path, repo_root: Path, code_files_cache: List[Path]
) -> List[str]:
    """Trouve les références à un fichier dans le dépôt (version optimisée)"""
    references = []

    # Obtenir le nom de base sans extension
    base_name = file_path.stem
    file_name = file_path.name
    relative_path = file_path.relative_to(repo_root)
    relative_path_str = str(relative_path).replace("\\", "/")

    # Patterns de recherche simplifiés
    search_terms = [base_name, file_name, relative_path_str]

    # Rechercher uniquement dans les fichiers Python (plus rapide)
    for code_file in code_files_cache:
        if code_file == file_path:
            continue

        if len(references) >= 5:  # Limiter à 5 références
            break

        try:
            # Lire seulement les premières lignes pour détecter les imports
            with open(code_file, "r", encoding="utf-8", errors="ignore") as f:
                # Lire par chunks pour être plus rapide
                content = f.read(8192)  # Lire seulement les 8 premiers KB

                # Recherche rapide
                content_lower = content.lower()
                for term in search_terms:
                    if term.lower() in content_lower:
                        # Vérification plus précise avec le terme exact
                        if (
                            f"import {base_name}" in content
                            or f"from {base_name}" in content
                            or f'"{file_name}"' in content
                            or f"'{file_name}'" in content
                            or relative_path_str in content
                        ):
                            references.append(f"{code_file.relative_to(repo_root)}")
                            break
        except Exception:
            continue

    return references


def inventory_candidates() -> Dict[str, List[FileCandidate]]:
    """Inventorie tous les fichiers candidats (version optimisée)"""
    candidates = {"ui_qt": [], "backups": [], "pyqt_files": []}

    print("\n=== INVENTAIRE DES FICHIERS CANDIDATS ===\n")

    # Pré-calculer la liste des fichiers Python (une seule fois)
    print("Préparation du cache des fichiers Python...")
    code_files_cache = []
    for file_path in REPO_ROOT.rglob("*.py"):
        path_str = str(file_path).replace("\\", "/")
        if "archive/" not in path_str and "app/backups/" not in path_str:
            code_files_cache.append(file_path)
    print(f"  {len(code_files_cache)} fichiers Python indexés")

    # Fichiers UI/Qt
    print("Recherche des fichiers UI/Qt...")
    ui_qt_files = find_files_by_patterns(UI_QT_PATTERNS)
    print(f"  {len(ui_qt_files)} fichiers trouvés")

    for i, file_path in enumerate(ui_qt_files, 1):
        if i % 10 == 0:
            print(f"  Vérification {i}/{len(ui_qt_files)}...")
        candidate = FileCandidate(file_path)
        candidate.references = find_references_fast(
            file_path, REPO_ROOT, code_files_cache
        )

        if not candidate.references:
            candidate.safe_to_remove = True
            candidate.reason = "Aucune référence trouvée"
        else:
            candidate.reason = f"Référencé dans {len(candidate.references)} fichier(s)"

        candidates["ui_qt"].append(candidate)

    # Fichiers de backup
    print("Recherche des fichiers de backup...")
    backup_files = find_files_by_patterns(BACKUP_PATTERNS)
    print(f"  {len(backup_files)} fichiers trouvés")

    for file_path in backup_files:
        candidate = FileCandidate(file_path)
        # Les fichiers .bak sont toujours candidats, on les traitera différemment
        candidate.safe_to_remove = True
        candidate.reason = "Fichier de backup"
        candidates["backups"].append(candidate)

    # Fichiers contenant PyQt/QtWidgets (recherche optimisée)
    print("Recherche de fichiers PyQt/QtWidgets...")
    pyqt_files = set()
    for file_path in code_files_cache:
        try:
            # Lire seulement le début du fichier pour détecter les imports
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(2048)  # Lire seulement les 2 premiers KB
                if "PyQt" in content or "QtWidgets" in content:
                    pyqt_files.add(file_path)
        except Exception:
            continue

    print(f"  {len(pyqt_files)} fichiers trouvés")

    for i, file_path in enumerate(pyqt_files, 1):
        if i % 10 == 0:
            print(f"  Vérification {i}/{len(pyqt_files)}...")
        candidate = FileCandidate(file_path)
        candidate.references = find_references_fast(
            file_path, REPO_ROOT, code_files_cache
        )

        if not candidate.references:
            candidate.safe_to_remove = True
            candidate.reason = "Aucune référence trouvée"
        else:
            candidate.reason = f"Référencé dans {len(candidate.references)} fichier(s)"

        candidates["pyqt_files"].append(candidate)

    return candidates


def process_bak_files(backup_candidates: List[FileCandidate]) -> Dict[str, List[Path]]:
    """Traite les fichiers .bak de manière intelligente"""
    actions = {
        "remove": [],  # Identiques à l'original
        "archive_old": [],  # Plus anciens que l'original
        "replace": [],  # Plus récents que l'original (remplacer l'original)
        "archive_orphan": [],  # Pas d'original correspondant
    }

    print("\n=== TRAITEMENT DES FICHIERS .bak ===\n")

    for candidate in backup_candidates:
        bak_path = candidate.path

        if not bak_path.name.endswith((".bak", ".bak.auto", ".backup")):
            continue

        # Trouver le fichier original
        original_path = bak_path.parent / bak_path.stem

        if original_path.exists():
            # Comparer les fichiers
            try:
                if filecmp.cmp(bak_path, original_path, shallow=False):
                    # Identiques -> supprimer le .bak
                    actions["remove"].append(bak_path)
                    print(f"  ✓ {bak_path.name} identique à l'original -> SUPPRESSION")
                else:
                    # Différents -> comparer les dates
                    bak_mtime = bak_path.stat().st_mtime
                    orig_mtime = original_path.stat().st_mtime

                    if bak_mtime < orig_mtime:
                        # .bak plus ancien -> archiver
                        actions["archive_old"].append(bak_path)
                        print(f"  → {bak_path.name} plus ancien -> ARCHIVAGE")
                    else:
                        # .bak plus récent -> remplacer l'original
                        actions["replace"].append((bak_path, original_path))
                        print(
                            f"  ⚠ {bak_path.name} plus récent -> REMPLACEMENT (ATTENTION!)"
                        )
            except Exception as e:
                print(f"  ✗ Erreur lors de la comparaison de {bak_path}: {e}")
                actions["archive_orphan"].append(bak_path)
        else:
            # Pas d'original -> archiver
            actions["archive_orphan"].append(bak_path)
            print(f"  → {bak_path.name} orphelin -> ARCHIVAGE")

    return actions


def archive_path(target_path: Path, archive_base: Path) -> Path:
    """Crée le chemin d'archivage pour un fichier"""
    relative = target_path.relative_to(REPO_ROOT)
    archive_path = archive_base / relative
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    return archive_path


def execute_cleanup(
    candidates: Dict[str, List[FileCandidate]],
    bak_actions: Dict[str, List],
) -> bool:
    """Exécute le nettoyage"""
    print("\n=== EXÉCUTION DU NETTOYAGE ===\n")

    archive_dir = REPO_ROOT / "archive" / "legacy_non_standard" / "backups"
    archive_dir.mkdir(parents=True, exist_ok=True)

    success = True

    # 1. Supprimer les fichiers sûrs
    safe_to_remove = []
    for category in ["ui_qt", "pyqt_files"]:
        for candidate in candidates[category]:
            if candidate.safe_to_remove:
                safe_to_remove.append(candidate.path)

    print(f"Suppression de {len(safe_to_remove)} fichiers sûrs...")
    for file_path in safe_to_remove:
        try:
            # Vérifier si le fichier est tracké par Git
            exit_code, _, _ = run_cmd(
                ["git", "ls-files", "--error-unmatch", str(file_path)], check=False
            )

            if exit_code == 0:
                # Tracké -> git rm
                exit_code, _, err = run_cmd(
                    ["git", "rm", "-f", str(file_path)], check=False
                )
                if exit_code == 0:
                    print(f"  ✓ Supprimé (git): {file_path.relative_to(REPO_ROOT)}")
                else:
                    print(
                        f"  ✗ Erreur git rm: {file_path.relative_to(REPO_ROOT)} - {err}"
                    )
                    success = False
            else:
                # Non tracké -> rm
                if file_path.exists():
                    file_path.unlink()
                    print(f"  ✓ Supprimé: {file_path.relative_to(REPO_ROOT)}")
        except Exception as e:
            print(f"  ✗ Erreur: {file_path.relative_to(REPO_ROOT)} - {e}")
            success = False

    # 2. Traiter les fichiers .bak
    print(f"\nTraitement des fichiers .bak...")

    # Supprimer les identiques
    for bak_path in bak_actions["remove"]:
        try:
            exit_code, _, _ = run_cmd(
                ["git", "ls-files", "--error-unmatch", str(bak_path)], check=False
            )
            if exit_code == 0:
                run_cmd(["git", "rm", "-f", str(bak_path)], check=False)
            else:
                if bak_path.exists():
                    bak_path.unlink()
            print(f"  ✓ Supprimé: {bak_path.relative_to(REPO_ROOT)}")
        except Exception as e:
            print(f"  ✗ Erreur: {bak_path.relative_to(REPO_ROOT)} - {e}")
            success = False

    # Archiver les anciens/orphelins
    for bak_path in bak_actions["archive_old"] + bak_actions["archive_orphan"]:
        try:
            archive_target = archive_path(bak_path, archive_dir)
            archive_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(bak_path), str(archive_target))
            print(
                f"  → Archivé: {bak_path.relative_to(REPO_ROOT)} -> {archive_target.relative_to(REPO_ROOT)}"
            )
        except Exception as e:
            print(f"  ✗ Erreur archivage: {bak_path.relative_to(REPO_ROOT)} - {e}")
            success = False

    # Remplacer les originaux par les .bak plus récents
    for bak_path, orig_path in bak_actions["replace"]:
        try:
            # Sauvegarder l'original
            orig_backup = archive_dir / f"{orig_path.relative_to(REPO_ROOT)}.orig"
            orig_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(orig_path), str(orig_backup))

            # Remplacer
            shutil.copy2(str(bak_path), str(orig_path))

            # Supprimer le .bak
            exit_code, _, _ = run_cmd(
                ["git", "ls-files", "--error-unmatch", str(bak_path)], check=False
            )
            if exit_code == 0:
                run_cmd(["git", "rm", "-f", str(bak_path)], check=False)
            else:
                if bak_path.exists():
                    bak_path.unlink()

            print(
                f"  ⚠ REMPLACÉ: {orig_path.relative_to(REPO_ROOT)} (original sauvegardé dans archive)"
            )
        except Exception as e:
            print(f"  ✗ Erreur remplacement: {bak_path.relative_to(REPO_ROOT)} - {e}")
            success = False

    return success


def update_gitignore():
    """Met à jour le fichier .gitignore"""
    gitignore_path = REPO_ROOT / ".gitignore"

    # Lire le contenu actuel
    existing_lines = []
    existing_patterns = set()

    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
            existing_patterns = {
                line.strip()
                for line in existing_lines
                if line.strip() and not line.strip().startswith("#")
            }

    # Ajouter les nouveaux patterns
    new_patterns = set(GITIGNORE_PATTERNS)
    patterns_to_add = new_patterns - existing_patterns

    if patterns_to_add:
        # Ajouter les nouveaux patterns
        with open(gitignore_path, "a", encoding="utf-8") as f:
            if not existing_lines or not existing_lines[-1].strip():
                f.write("\n")
            f.write("# Auto-added by cleanup script\n")
            for pattern in sorted(patterns_to_add):
                f.write(f"{pattern}\n")

        print(
            f"\n✓ .gitignore mis à jour avec {len(patterns_to_add)} nouveaux patterns"
        )
    else:
        print(f"\n✓ .gitignore déjà à jour (tous les patterns présents)")


def print_summary(
    candidates: Dict[str, List[FileCandidate]], bak_actions: Dict[str, List]
):
    """Affiche un résumé du nettoyage"""
    print("\n" + "=" * 70)
    print("RÉSUMÉ DU NETTOYAGE")
    print("=" * 70)

    total_safe = sum(
        len([c for c in candidates[cat] if c.safe_to_remove])
        for cat in ["ui_qt", "pyqt_files"]
    )
    total_referenced = sum(
        len([c for c in candidates[cat] if not c.safe_to_remove])
        for cat in ["ui_qt", "pyqt_files"]
    )

    print(f"\nFichiers sûrs à supprimer : {total_safe}")
    print(f"Fichiers référencés (conservés) : {total_referenced}")
    print(f"\nFichiers .bak identiques : {len(bak_actions['remove'])}")
    print(
        f"Fichiers .bak à archiver (anciens/orphelins) : {len(bak_actions['archive_old']) + len(bak_actions['archive_orphan'])}"
    )
    print(f"Fichiers .bak plus récents (remplacement) : {len(bak_actions['replace'])}")

    if bak_actions["replace"]:
        print("\n⚠ ATTENTION: Fichiers qui seront remplacés par leur version .bak:")
        for bak_path, orig_path in bak_actions["replace"]:
            print(f"  - {orig_path.relative_to(REPO_ROOT)}")

    if total_referenced > 0:
        print("\nFichiers référencés (non supprimés):")
        for category in ["ui_qt", "pyqt_files"]:
            for candidate in candidates[category]:
                if not candidate.safe_to_remove:
                    print(f"  - {candidate.path.relative_to(REPO_ROOT)}")
                    for ref in candidate.references[:3]:
                        print(f"    → {ref}")


def main():
    """Fonction principale"""
    print("=" * 70)
    print("NETTOYAGE COMPLET DU DÉPÔT")
    print("=" * 70)

    # 1. Vérifier la branche
    current_branch = get_current_branch()
    print(f"\nBranche courante : {current_branch}")

    if (
        not current_branch
        or current_branch.startswith("main")
        or current_branch.startswith("master")
    ):
        response = input(
            "\n⚠ Vous êtes sur la branche principale. Continuer? (oui/non): "
        )
        if response.lower() not in ["oui", "o", "yes", "y"]:
            print("Arrêt.")
            return 1

    # 2. Créer branche de sauvegarde
    backup_branch = create_backup_branch()

    # 3. Créer archive
    archive_path = create_archive()
    if archive_path:
        print(f"Archive disponible à : {archive_path}")

    # 4. Inventaire
    candidates = inventory_candidates()

    # 5. Traiter les .bak
    bak_actions = process_bak_files(candidates["backups"])

    # 6. Afficher le résumé
    print_summary(candidates, bak_actions)

    # 7. Demander confirmation
    print("\n" + "=" * 70)
    response = input("\nContinuer avec le nettoyage? (oui/non): ")
    if response.lower() not in ["oui", "o", "yes", "y"]:
        print("Arrêt. Aucune modification effectuée.")
        return 0

    # 8. Exécuter le nettoyage
    success = execute_cleanup(candidates, bak_actions)

    # 9. Mettre à jour .gitignore
    update_gitignore()

    # 10. Résumé final
    print("\n" + "=" * 70)
    if success:
        print("✓ NETTOYAGE TERMINÉ")
        print("\n⚠ IMPORTANT: Vérifiez les modifications avant de push:")
        print("  git status")
        print("  git diff")
        print("\nSi tout est correct:")
        print("  git add .")
        print("  git commit -m 'chore: nettoyage fichiers UI/Qt et .bak'")
    else:
        print("✗ NETTOYAGE TERMINÉ AVEC ERREURS")
        print("Vérifiez les messages ci-dessus.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
