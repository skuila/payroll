#!/usr/bin/env python3
"""
Extrait les noms de colonnes FINAUX depuis la migration 011 (source de vérité DB)
"""

print("=" * 70)
print("NOMS DE COLONNES FINAUX DANS LA MIGRATION 011 (source de vérité DB)")
print("=" * 70)

# D'après la migration 011_fix_headers_spelling.py
# C'est la migration la plus récente qui corrige les noms

colonnes_finales = [
    "N de ligne",  # 1. Inchangé
    "catégorie d'emploi",  # 2. Corrigé: "Categorie d'emploi" -> "catégorie d'emploi"
    "code emploi",  # 3. Corrigé: "code emploie" -> "code emploi"
    "titre d'emploi",  # 4. Inchangé
    "date de paie",  # 5. Inchangé
    "matricule",  # 6. Inchangé
    "employé",  # 7. Inchangé
    "catégorie de paie",  # 8. Corrigé: "categorie de paie" -> "catégorie de paie"
    "code de paie",  # 9. Inchangé
    "description du code de paie",  # 10. Corrigé: "desc code de paie" -> "description du code de paie"
    "poste budgétaire",  # 11. Corrigé: "poste Budgetaire" -> "poste budgétaire"
    "description du poste budgétaire",  # 12. Corrigé: "desc poste Budgetaire" -> "description du poste budgétaire"
    "montant",  # 13. Inchangé (SANS espace)
    "part employeur",  # 14. Inchangé
    "montant combiné",  # 15. Corrigé: "Mnt/Cmb" -> "montant combiné"
]

print("\nColonnes FINALES (après migration 011):")
print("-" * 70)
for i, col in enumerate(colonnes_finales, 1):
    print(f"   {i:2d}. '{col}'")

print("\n" + "=" * 70)
print("COMPARAISON AVEC LES AUTRES SOURCES:")
print("=" * 70)

# Comparaison avec fast_track_importer.py
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

print("\n❌ fast_track_importer.py (ANCIEN - doit être mis à jour):")
for i, (final, old) in enumerate(zip(colonnes_finales, fast_track_cols), 1):
    if final != old:
        print(f"   {i:2d}. '{old}' -> '{final}'")

# Comparaison avec LISTE_COLONNES_EXCEL_REQUISES.txt
txt_cols = [
    "N de ligne",
    "Categorie d'emploi",
    "code emploi",  # SANS 'e'
    "titre d'emploi",
    "date de paie",
    "matricule",
    "employé",
    "categorie de paie",
    "code de paie",
    "desc code de paie",
    "poste Budgetaire",
    "desc poste Budgétaire",  # AVEC accent
    "montant ",  # AVEC espace
    "part employeur",
    "Mnt/Cmb",
]

print("\n⚠️  LISTE_COLONNES_EXCEL_REQUISES.txt (partiellement correct):")
for i, (final, txt) in enumerate(zip(colonnes_finales, txt_cols), 1):
    if final != txt:
        print(f"   {i:2d}. '{txt}' -> '{final}'")

print("\n" + "=" * 70)
print("✅ SOURCE DE VÉRITÉ (Migration 011 - la plus récente):")
print("=" * 70)
for i, col in enumerate(colonnes_finales, 1):
    print(f"{i:2d}. {col}")
