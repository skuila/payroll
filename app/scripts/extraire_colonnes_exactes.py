#!/usr/bin/env python3
"""
Extrait les noms de colonnes EXACTS depuis la migration 010 (source de vérité DB)
"""

import re
from pathlib import Path

migration_file = (
    Path(__file__).parent.parent / "alembic" / "versions" / "010_raw_and_profiles.py"
)

print("=" * 70)
print("NOMS DE COLONNES EXACTS DANS LA MIGRATION 010 (source de vérité DB)")
print("=" * 70)

if migration_file.exists():
    with open(migration_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Extraire les colonnes entre guillemets dans la section CREATE TABLE
    # Chercher le pattern: "nom colonne" TYPE
    pattern = r'"([^"]+)"\s+(?:TEXT|DATE|NUMERIC)'
    matches = re.findall(pattern, content)

    # Filtrer pour garder seulement les 15 colonnes Excel
    colonnes_excel = []
    for match in matches:
        if match not in ["raw_row_id", "file_id", "created_at"]:
            colonnes_excel.append(match)

    print("\nColonnes trouvées dans la migration 010:")
    print("-" * 70)
    for i, col in enumerate(colonnes_excel, 1):
        print(f"   {i:2d}. '{col}'")

    # Vérifier les différences
    print("\n" + "=" * 70)
    print("VÉRIFICATION DES DIFFÉRENCES:")
    print("=" * 70)

    # Comparer avec fast_track_importer.py
    fast_track_cols = [
        "N de ligne",
        "Categorie d'emploi",
        "code emploie",  # AVEC 'e'
        "titre d'emploi",
        "date de paie",
        "matricule",
        "employé",
        "categorie de paie",
        "code de paie",
        "desc code de paie",
        "poste Budgetaire",
        "desc poste Budgetaire",  # SANS accent
        "montant",  # SANS espace
        "part employeur",
        "Mnt/Cmb",
    ]

    print("\nComparaison avec fast_track_importer.py:")
    print("-" * 70)
    for i, (migration_col, fast_track_col) in enumerate(
        zip(colonnes_excel, fast_track_cols), 1
    ):
        if migration_col != fast_track_col:
            print(f"❌ Colonne {i}:")
            print(f"   Migration 010: '{migration_col}'")
            print(f"   fast_track:    '{fast_track_col}'")
        else:
            print(f"✅ Colonne {i}: '{migration_col}'")

    print("\n" + "=" * 70)
    print("CONCLUSION - NOMS DE COLONNES EXCEL (source de vérité DB):")
    print("=" * 70)
    for i, col in enumerate(colonnes_excel, 1):
        print(f"{i:2d}. {col}")

else:
    print(f"❌ Fichier non trouvé: {migration_file}")
