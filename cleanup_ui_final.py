#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nettoyage final UI/Qt - Suppression complète des fichiers UI/Qt
Car migration complète vers Tabler
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path.cwd()

# Fichiers et dossiers à supprimer définitivement
FILES_TO_REMOVE = [
    "app/config/theme_manager.py",
    "app/logic/insights.py",
    "app/ui/themes/",
    "app/ui/overlays/",
    "app/ui/menus/",
]


def run_cmd(cmd, check=False):
    """Exécute une commande"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def remove_file_or_dir(path):
    """Supprime un fichier ou dossier"""
    full_path = REPO_ROOT / path

    if not full_path.exists():
        print(f"  ⚠ {path} n'existe pas")
        return False

    try:
        # Vérifier si tracké par Git
        exit_code, _, _ = run_cmd(
            ["git", "ls-files", "--error-unmatch", str(full_path)], check=False
        )
        is_tracked = exit_code == 0

        if full_path.is_file():
            if is_tracked:
                success, _, err = run_cmd(
                    ["git", "rm", "-f", str(full_path)], check=False
                )
                if success:
                    print(f"  ✓ Supprimé (git): {path}")
                    return True
                else:
                    print(f"  ✗ Erreur git rm: {path} - {err}")
                    return False
            else:
                full_path.unlink()
                print(f"  ✓ Supprimé: {path}")
                return True
        else:
            # Dossier
            if is_tracked:
                # Supprimer les fichiers trackés d'abord
                success, _, _ = run_cmd(
                    ["git", "rm", "-rf", str(full_path)], check=False
                )
                if success:
                    print(f"  ✓ Supprimé (git): {path}/")
                    return True
            # Supprimer physiquement
            import shutil

            shutil.rmtree(full_path)
            print(f"  ✓ Supprimé: {path}/")
            return True
    except Exception as e:
        print(f"  ✗ Erreur: {path} - {e}")
        return False


def main():
    print("=" * 70)
    print("NETTOYAGE FINAL UI/QT - SUPPRESSION COMPLÈTE")
    print("=" * 70)
    print("\nFichiers/dossiers à supprimer:")
    for item in FILES_TO_REMOVE:
        print(f"  - {item}")

    response = input("\nContinuer? (oui/non): ")
    if response.lower() not in ["oui", "o", "yes", "y"]:
        print("Arrêt.")
        return 1

    print("\n=== SUPPRESSION ===\n")
    success = True
    for item in FILES_TO_REMOVE:
        if not remove_file_or_dir(item):
            success = False

    print("\n" + "=" * 70)
    if success:
        print("✓ NETTOYAGE FINAL TERMINÉ")
        print("\nVérifiez avec: git status")
    else:
        print("✗ NETTOYAGE TERMINÉ AVEC ERREURS")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
