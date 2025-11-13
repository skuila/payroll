#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de réorganisation complète du dépôt
- Supprime les fichiers .md inutiles
- Réorganise la structure des dossiers
- Nettoie les fichiers temporaires
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path.cwd()

# Fichiers .md essentiels à GARDER
KEEP_MD_FILES = {
    "README.md",  # README principal à la racine
    "app/README.md",  # README de l'application
    "scripts/README.md",  # README des scripts
    "app/guides/README.md",  # Index des guides
    "app/guides/GUIDE_CONNEXION.md",  # Guide principal de connexion
}

# Fichiers .md à SUPPRIMER (rapports temporaires, redondants, obsolètes)
REMOVE_MD_FILES = [
    # Rapports temporaires
    "repo_status_report.md",
    "reports/db_connection_inventory.md",
    # Rapports de refactoring obsolètes
    "app/REFACTOR_CONNEXIONS_RAPPORT.md",
    "app/STANDARDISATION_RESUME.md",
    "app/FICHIERS_MODIFIES.md",
    # Guides redondants/obsolètes
    "app/guides/ANALYSE_DOSSIER_LOGIC.md",
    "app/guides/APPROVED_CHANGES.md",
    "app/guides/CHANGELOG.md",
    "app/guides/CLEANUP_SUMMARY.md",
    "app/guides/CONNEXION_STANDARDISEE.md",  # Redondant avec GUIDE_CONNEXION.md
    "app/guides/GUIDE_PAGE_TESTE.md",
    "app/guides/INDEX.md",  # Redondant avec README.md
    "app/guides/MESSAGES_ERREUR_APPLIQUES.md",
    "app/guides/ORGANISATION_GUIDES.md",
    "app/guides/PASSWORD_UNIFIED.md",
    "app/guides/RULES_EXECUTION.md",
    "app/guides/SCHEMA_APPLICATION.md",
    "app/guides/STANDARDISATION_CONNEXIONS.md",
    "app/guides/TESTER_EMPLOYEES.md",
    "app/guides/TESTING.md",
    # Contextes obsolètes
    "app/report_datatables_dup9/CONTEXT.md",
]

# Fichiers temporaires/artefacts à supprimer
REMOVE_TEMP_FILES = [
    # Fichiers de test/debug
    "app/OU_SONT_LES_FICHIERS.txt",
    "app/REFACTOR_REPORT.txt",
    "app/SETUP_COMPLETE.txt",
    "app/structure_complete.txt",
    "app/db_overview.txt",
    "app/db_structure.txt",
    "app/comparison_result.txt",
    "app/net_result.txt",
    "app/out.txt",
    "out.txt",
    # Fichiers de logs/rapports
    "mypy_log.txt",
    "ruff-remaining.txt",
    "ruff-report-before.txt",
    "violations.txt",
    "repo_status_report.json",
    "ruff-report-before.json",
    "ruff-report-after.json",
    # Scripts temporaires de nettoyage
    "cleanup_repo.py",
    "cleanup_ui_final.py",
    "prepare_cleanup_pr.py",
    "check_report.py",
    "generate_repo_report.py",
    "summarize_ruff.py",
    "summarize_top20.py",
    # Fichiers .backup restants
    "app/calc_net.py.backup",
    "app/connect_check.py.backup",
    "app/count_columns.py.backup",
    "app/get_db_overview.py.backup",
    "app/show_columns.py.backup",
]

# Dossiers à nettoyer/réorganiser
CLEANUP_DIRS = [
    "app/_dbtest",  # Tests DB temporaires
    "app/report_datatables_dup9",  # Ancien rapport
    "app/bundle_tmp",  # Dossier temporaire
]

# Structure de réorganisation (déplacer fichiers éparpillés)
REORGANIZE = {
    # Scripts SQL isolés -> app/sql/
    "app/accorder_droits_manuel.sql": "app/sql/",
    "app/add_columns_20251110_004822.sql": "app/sql/",
    "app/backup_schema_20251110_004737.sql": "app/sql/",
    "app/corriger_montants_en_numeric.sql": "app/sql/",
    "app/corriger_montants_final.sql": "app/sql/",
    "app/corriger_montants_manuel.sql": "app/sql/",
    "app/corriger_types_montants.sql": "app/sql/",
    "app/verification-preflight_execute.sql": "app/sql/",
    "app/verification-preflight.sql": "app/sql/",
    # Scripts Python isolés -> app/scripts/
    "app/analyser_periode_paie.py": "app/scripts/",
    "app/check_table_structure.py": "app/scripts/",
    "app/check_total.py": "app/scripts/",
    "app/connect_check.py": "app/scripts/",
    "app/corriger_erreur_does_not_exist.py": "app/scripts/",
    "app/create_audit_table.py": "app/scripts/",
    "app/debug_chart_creation.py": "app/scripts/",
    "app/debug_matricule_salaire.py": "app/scripts/",
    "app/diagnostic_charts_non_fonctionnels.py": "app/scripts/",
    "app/manage_schema.py": "app/scripts/",
    "app/show_window.py": "app/scripts/",
    "app/verifier_donnees_employees.py": "app/scripts/",
    "app/vider_tables.py": "app/scripts/",
    # Tests isolés -> app/tests/
    "app/test_api_standard.py": "app/tests/",
    "app/test_appbridge_periods.py": "app/tests/",
    "app/test_get_periods.py": "app/tests/",
    "app/test_requetes_reelles.py": "app/tests/",
    "app/test_verification_preflight.py": "app/tests/",
}


def run_cmd(cmd, check=False):
    """Exécute une commande"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=check, shell=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def remove_file(path):
    """Supprime un fichier"""
    full_path = REPO_ROOT / path
    if not full_path.exists():
        return True, f"  ⚠ {path} n'existe pas"

    try:
        # Vérifier si tracké par Git
        exit_code, _, _ = run_cmd(
            f'git ls-files --error-unmatch "{full_path}"', check=False
        )
        is_tracked = exit_code == 0

        if is_tracked:
            success, _, err = run_cmd(f'git rm -f "{full_path}"', check=False)
            if success:
                return True, f"  ✓ Supprimé (git): {path}"
            else:
                return False, f"  ✗ Erreur git rm: {path} - {err}"
        else:
            if full_path.is_file():
                full_path.unlink()
            else:
                shutil.rmtree(full_path)
            return True, f"  ✓ Supprimé: {path}"
    except Exception as e:
        return False, f"  ✗ Erreur: {path} - {e}"


def move_file(src, dst_dir):
    """Déplace un fichier vers un dossier"""
    src_path = REPO_ROOT / src
    dst_path = REPO_ROOT / dst_dir

    if not src_path.exists():
        return True, f"  ⚠ {src} n'existe pas"

    try:
        dst_path.mkdir(parents=True, exist_ok=True)
        dst_file = dst_path / src_path.name

        # Vérifier si tracké par Git
        exit_code, _, _ = run_cmd(
            f'git ls-files --error-unmatch "{src_path}"', check=False
        )
        is_tracked = exit_code == 0

        if is_tracked:
            # Utiliser git mv
            success, _, err = run_cmd(f'git mv "{src_path}" "{dst_file}"', check=False)
            if success:
                return True, f"  ✓ Déplacé (git): {src} -> {dst_dir}/{src_path.name}"
            else:
                return False, f"  ✗ Erreur git mv: {src} - {err}"
        else:
            shutil.move(str(src_path), str(dst_file))
            return True, f"  ✓ Déplacé: {src} -> {dst_dir}/{src_path.name}"
    except Exception as e:
        return False, f"  ✗ Erreur déplacement: {src} - {e}"


def main():
    print("=" * 70)
    print("RÉORGANISATION COMPLÈTE DU DÉPÔT")
    print("=" * 70)

    # 1. Supprimer les fichiers .md inutiles
    print("\n=== SUPPRESSION DES FICHIERS .MD INUTILES ===\n")
    md_to_remove = []
    for md_file in REMOVE_MD_FILES:
        md_path = REPO_ROOT / md_file
        if md_path.exists():
            md_to_remove.append(md_file)
            print(f"  - {md_file}")

    if md_to_remove:
        response = input(f"\nSupprimer {len(md_to_remove)} fichiers .md? (oui/non): ")
        if response.lower() in ["oui", "o", "yes", "y"]:
            for md_file in md_to_remove:
                success, msg = remove_file(md_file)
                print(msg)
        else:
            print("  Annulé")
    else:
        print("  Aucun fichier .md à supprimer")

    # 2. Supprimer les fichiers temporaires
    print("\n=== SUPPRESSION DES FICHIERS TEMPORAIRES ===\n")
    temp_to_remove = []
    for temp_file in REMOVE_TEMP_FILES:
        temp_path = REPO_ROOT / temp_file
        if temp_path.exists():
            temp_to_remove.append(temp_file)
            print(f"  - {temp_file}")

    if temp_to_remove:
        response = input(
            f"\nSupprimer {len(temp_to_remove)} fichiers temporaires? (oui/non): "
        )
        if response.lower() in ["oui", "o", "yes", "y"]:
            for temp_file in temp_to_remove:
                success, msg = remove_file(temp_file)
                print(msg)
        else:
            print("  Annulé")
    else:
        print("  Aucun fichier temporaire à supprimer")

    # 3. Supprimer les dossiers inutiles
    print("\n=== SUPPRESSION DES DOSSIERS INUTILES ===\n")
    dirs_to_remove = []
    for dir_path in CLEANUP_DIRS:
        dir_full = REPO_ROOT / dir_path
        if dir_full.exists():
            dirs_to_remove.append(dir_path)
            print(f"  - {dir_path}/")

    if dirs_to_remove:
        response = input(f"\nSupprimer {len(dirs_to_remove)} dossiers? (oui/non): ")
        if response.lower() in ["oui", "o", "yes", "y"]:
            for dir_path in dirs_to_remove:
                success, msg = remove_file(dir_path)
                print(msg)
        else:
            print("  Annulé")
    else:
        print("  Aucun dossier à supprimer")

    # 4. Réorganiser les fichiers
    print("\n=== RÉORGANISATION DES FICHIERS ===\n")
    files_to_move = []
    for src, dst_dir in REORGANIZE.items():
        src_path = REPO_ROOT / src
        if src_path.exists():
            files_to_move.append((src, dst_dir))
            print(f"  - {src} -> {dst_dir}/")

    if files_to_move:
        response = input(f"\nDéplacer {len(files_to_move)} fichiers? (oui/non): ")
        if response.lower() in ["oui", "o", "yes", "y"]:
            for src, dst_dir in files_to_move:
                success, msg = move_file(src, dst_dir)
                print(msg)
        else:
            print("  Annulé")
    else:
        print("  Aucun fichier à déplacer")

    # Résumé final
    print("\n" + "=" * 70)
    print("✓ RÉORGANISATION TERMINÉE")
    print("\nVérifiez avec: git status")
    print("\nSi tout est correct:")
    print("  git add .")
    print("  git commit -m 'chore: réorganisation complète du dépôt'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
