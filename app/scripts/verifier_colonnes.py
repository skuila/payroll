#!/usr/bin/env python3
"""
Script pour comparer les noms de colonnes entre différentes sources
"""

print("=" * 70)
print("COMPARAISON DES NOMS DE COLONNES ENTRE LES SOURCES")
print("=" * 70)

# Source 1: LISTE_COLONNES_EXCEL_REQUISES.txt
colonnes_txt = [
    "N de ligne",
    "Categorie d'emploi",
    "code emploi",  # SANS 'e' à la fin
    "titre d'emploi",
    "date de paie",
    "matricule",
    "employé",
    "categorie de paie",
    "code de paie",
    "desc code de paie",
    "poste Budgetaire",
    "desc poste Budgétaire",  # AVEC accent 'é'
    "montant ",  # AVEC espace
    "part employeur",
    "Mnt/Cmb",
]

# Source 2: fast_track_importer.py MASTER_COLUMNS
colonnes_code = [
    "N de ligne",
    "Categorie d'emploi",
    "code emploie",  # AVEC 'e' à la fin
    "titre d'emploi",
    "date de paie",
    "matricule",
    "employé",
    "categorie de paie",
    "code de paie",
    "desc code de paie",
    "poste Budgetaire",
    "desc poste Budgetaire",  # SANS accent 'é'
    "montant",  # SANS espace
    "part employeur",
    "Mnt/Cmb",
]

print("\n1. COLONNES DANS LISTE_COLONNES_EXCEL_REQUISES.txt:")
for i, col in enumerate(colonnes_txt, 1):
    print(f"   {i:2d}. '{col}'")

print("\n2. COLONNES DANS fast_track_importer.py (MASTER_COLUMNS):")
for i, col in enumerate(colonnes_code, 1):
    print(f"   {i:2d}. '{col}'")

print("\n" + "=" * 70)
print("DIFFÉRENCES DÉTECTÉES:")
print("=" * 70)

differences = []
for i, (txt_col, code_col) in enumerate(zip(colonnes_txt, colonnes_code), 1):
    if txt_col != code_col:
        differences.append((i, txt_col, code_col))
        print(f"\n❌ Colonne {i}:")
        print(f"   LISTE_COLONNES_EXCEL_REQUISES.txt: '{txt_col}'")
        print(f"   fast_track_importer.py:            '{code_col}'")
        print(f"   Différence: {repr(txt_col)} vs {repr(code_col)}")

if not differences:
    print("\n✅ Aucune différence trouvée")
else:
    print(f"\n⚠️  {len(differences)} différence(s) trouvée(s)")

print("\n" + "=" * 70)
print("NOTE IMPORTANTE:")
print("=" * 70)
print("Le code utilise normalize_header() qui:")
print("  - Met en minuscules")
print("  - Enlève les espaces (trim)")
print("  - Enlève les accents (unidecode)")
print("  - Compresse les espaces multiples")
print("\nDonc 'code emploi' et 'code emploie' peuvent être normalisés")
print("de la même façon, mais il faut vérifier quelle est la source")
print("de vérité pour les fichiers Excel réels.")
