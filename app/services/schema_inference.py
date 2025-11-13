# services/schema_inference.py
# ========================================
# INFERENCE DE SCHEMA AVEC NOMS CANONIQUES
# ========================================

import pandas as pd
from typing import List, Dict, Any

# Noms canoniques (corrigés) pour les colonnes payroll
CANONICAL_HEADERS = [
    "N de ligne",
    "catégorie d'emploi",
    "code emploi",
    "titre d'emploi",
    "date de paie",
    "matricule",
    "employé",
    "catégorie de paie",
    "code de paie",
    "description du code de paie",
    "poste budgétaire",
    "description du poste budgétaire",
    "montant",
    "part employeur",
    "montant combiné",
]

# Alias d'anciens noms -> nouveaux (tolérance import)
HEADER_ALIASES = {
    "Categorie d'emploi": "catégorie d'emploi",
    "code emploie": "code emploi",
    "categorie de paie": "catégorie de paie",
    "desc code de paie": "description du code de paie",
    "poste Budgetaire": "poste budgétaire",
    "desc poste Budgetaire": "description du poste budgétaire",
    "Mnt/Cmb": "montant combiné",
}


def normalize_header(h: str) -> str:
    """
    Normalise un en-tête en appliquant les alias si nécessaire

    Args:
        h: En-tête brut

    Returns:
        str: En-tête normalisé
    """
    if h is None:
        return ""
    hs = str(h).strip()
    return HEADER_ALIASES.get(hs, hs)


def suggest_mapping(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Suggère un mapping entre les colonnes du DataFrame et les champs canoniques

    Args:
        df: DataFrame à analyser

    Returns:
        dict: Mapping suggéré avec scores de confiance
    """
    if df is None or df.empty:
        return {"mapping": {}, "confidence": {}, "notes": ["DataFrame vide"]}

    # Normaliser les colonnes du DataFrame
    dfc = df.copy()
    dfc.columns = [str(c).strip() for c in dfc.columns]
    dfc.columns = [normalize_header(c) for c in dfc.columns]

    # Créer mapping automatique basé sur les noms canoniques
    mapping = {}
    confidence = {}
    notes = []

    for idx, col in enumerate(dfc.columns):
        if col in CANONICAL_HEADERS:
            mapping[col] = idx
            confidence[col] = 1.0
            notes.append(f"{col}: ✓ match exact (confiance 1.0)")
        else:
            notes.append(f"{col}: ⚠️ non reconnu dans les champs canoniques")

    return {"mapping": mapping, "confidence": confidence, "notes": notes}
