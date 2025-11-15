#!/usr/bin/env python3
"""
Crée un fichier Excel de test avec les colonnes exactes requises
"""

from pathlib import Path

import pandas as pd

# Colonnes exactes requises (source de vérité: migration 011)
# D'après app/alembic/versions/011_fix_headers_spelling.py
columns = [
    "N de ligne",
    "catégorie d'emploi",  # Corrigé: avec accent
    "code emploi",  # Corrigé: sans 'e'
    "titre d'emploi",
    "date de paie",
    "matricule",
    "employé",
    "catégorie de paie",  # Corrigé: avec accent
    "code de paie",
    "description du code de paie",  # Corrigé: nom complet
    "poste budgétaire",  # Corrigé: avec accent, minuscule
    "description du poste budgétaire",  # Corrigé: nom complet, avec accent
    "montant",  # Corrigé: sans espace
    "part employeur",
    "montant combiné",  # Corrigé: nom complet
]

# Données de test
data = {
    "N de ligne": [1, 2, 3, 4, 5],
    "catégorie d'emploi": [
        "Permanent",
        "Permanent",
        "Contractuel",
        "Permanent",
        "Contractuel",
    ],
    "code emploi": ["EMP001", "EMP002", "EMP003", "EMP004", "EMP005"],
    "titre d'emploi": [
        "Analyste",
        "Gestionnaire",
        "Technicien",
        "Directeur",
        "Assistant",
    ],
    "date de paie": [
        "2025-01-15",
        "2025-01-15",
        "2025-01-15",
        "2025-01-15",
        "2025-01-15",
    ],
    "matricule": ["MAT001", "MAT002", "MAT003", "MAT004", "MAT005"],
    "employé": [
        "Dupont Jean",
        "Martin Marie",
        "Bernard Pierre",
        "Tremblay Sophie",
        "Gagnon Luc",
    ],
    "catégorie de paie": ["Salaire", "Salaire", "Salaire", "Salaire", "Salaire"],
    "code de paie": ["SAL", "SAL", "SAL", "SAL", "SAL"],
    "description du code de paie": [
        "Salaire de base",
        "Salaire de base",
        "Salaire de base",
        "Salaire de base",
        "Salaire de base",
    ],
    "poste budgétaire": ["1001", "1002", "1001", "1003", "1002"],
    "description du poste budgétaire": [
        "Poste A",
        "Poste B",
        "Poste A",
        "Poste C",
        "Poste B",
    ],
    "montant": [5000.00, 4500.00, 4800.00, 6000.00, 4200.00],  # Sans espace
    "part employeur": [750.00, 675.00, 720.00, 900.00, 630.00],
    "montant combiné": [5750.00, 5175.00, 5520.00, 6900.00, 4830.00],
}

df = pd.DataFrame(data)

# Créer le fichier
output_path = Path(__file__).parent.parent / "test_import_paie.xlsx"
df.to_excel(output_path, index=False, engine="openpyxl")

print(f"✅ Fichier de test créé: {output_path}")
print(f"   - {len(df)} lignes")
print(f"   - {len(df.columns)} colonnes")
print("\nColonnes:")
for i, col in enumerate(df.columns, 1):
    print(f"   {i:2d}. {col}")
