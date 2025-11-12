# services/schema_detector.py
# ========================================
# DÉTECTEUR SCHEMA OFFLINE FR-CA (Value-First)
# ========================================
# Identifie automatiquement les colonnes par analyse des valeurs
# Support inversion colonnes (ex: montant ↔ poste_budgetaire)

import re
from typing import Dict, List, Any

# Import du parseur neutre depuis le module parsers
from app.services.parsers import parse_amount_neutral, parse_date_robust

try:
    import pandas as pd
except ImportError:
    pd = None


def _norm_header(h: Any) -> str:
    """
    Normalise un en-tête de colonne pour matching flexible

    Args:
        h: En-tête brut

    Returns:
        str: En-tête normalisé (lowercase, sans caractères spéciaux)
    """
    raw = str(h or "").strip().lower()
    # Remplacer caractères spéciaux par espaces
    normalized = re.sub(r"[^a-z0-9]+", " ", raw, flags=re.IGNORECASE)
    return normalized.strip()


def detect_schema(df, config: Dict) -> Dict:
    """
    Détecte automatiquement le schéma des colonnes (VALUE-FIRST)

    Stratégie:
    1. Analyser les VALEURS de chaque colonne (parsing dates, nombres, regex patterns)
    2. Analyser les EN-TÊTES (matching lexique)
    3. Analyser les STATISTIQUES (longueur, variété, distribution)
    4. Calculer score pondéré pour chaque paire (champ_cible, colonne)
    5. Assigner colonnes par score décroissant (greedy stable)

    Args:
        df: DataFrame pandas OU liste de listes [[headers], [row1], [row2], ...]
        config: Configuration dict (chargée depuis schema_fr_ca.yaml)

    Returns:
        dict: {
            "mapping": {"date": 0, "montant": 3, ...},  # col_index par champ
            "confidence": {"date": 0.91, "montant": 0.98, ...},  # scores
            "alternatives": {"date": [(0, 0.91), (2, 0.45), ...], ...},  # top 3
            "notes": ["date: haute confiance", ...]  # warnings/infos
        }
    """

    # ========== PARSING INPUT ==========

    # Support DataFrame pandas OU list[list]
    if pd is not None and isinstance(df, pd.DataFrame):
        headers = [str(h) for h in df.columns]
        sample_data = df.head(config.get("sample_size", 200)).values.tolist()
    else:
        # Format list[list]: première ligne = headers
        if not df or len(df) == 0:
            return {
                "mapping": {},
                "confidence": {},
                "alternatives": {},
                "notes": ["Aucune donnée fournie"],
            }
        headers = [str(h) for h in df[0]]
        sample_size = config.get("sample_size", 200)
        sample_data = df[1 : min(len(df), 1 + sample_size)]

    n_cols = len(headers)

    if n_cols == 0:
        return {
            "mapping": {},
            "confidence": {},
            "alternatives": {},
            "notes": ["Aucune colonne détectée"],
        }

    # ========== EXTRACTION CONFIG ==========

    W = config["weights"]
    TH = config["thresholds"]
    LEX = config["headers_lexicon"]
    PAT = config["patterns"]
    HINT = config.get("position_hints", {})

    # ========== ANALYSE COLONNES ==========

    col_stats = []

    for j in range(n_cols):
        # Extraire valeurs colonne j
        col_values = []
        for row in sample_data:
            if j < len(row):
                col_values.append(row[j])
            else:
                col_values.append(None)

        n_values = len(col_values)

        # --- SIGNAUX VALEURS (value patterns) ---

        # Date: % de valeurs parsables comme date
        v_date = sum(1 for v in col_values if parse_date_robust(v) is not None) / max(
            1, n_values
        )

        # Montant: % de valeurs parsables comme nombre avec parseur neutre
        v_montant = sum(
            1 for v in col_values if parse_amount_neutral(v) is not None
        ) / max(1, n_values)

        # Matricule: % de valeurs matching pattern digits
        v_matricule = sum(
            1
            for v in col_values
            if re.fullmatch(PAT["matricule_digits"], str(v or "").strip())
        ) / max(1, n_values)

        # Code paie: % de valeurs matching pattern alphanumérique
        v_code = sum(
            1
            for v in col_values
            if re.fullmatch(PAT["code_paie"], str(v or "").strip())
        ) / max(1, n_values)

        # Poste budgétaire: % de valeurs matching ANY pattern
        v_pb = 0.0
        for rgx in PAT["poste_budgetaire"]:
            score_pb = sum(
                1 for v in col_values if re.fullmatch(rgx, str(v or "").strip())
            ) / max(1, n_values)
            v_pb = max(v_pb, score_pb)

        # Nom/prénom: % de valeurs avec virgule OU 2+ mots
        col_str = [str(v or "").strip() for v in col_values]
        v_np = sum(
            1
            for s in col_str
            if (PAT["name_has_comma"] in s)
            or (len(s.split()) >= config["patterns"]["name_words_min"])
        ) / max(1, len(col_str))

        # Description poste: texte long (10+ caractères) + pas nombre + pas code
        lens = [len(s) for s in col_str if s]
        v_desc = (
            (sum(1 for L in lens if L >= 10) / max(1, len(lens)))
            * (1 - v_montant)  # Pénalise si ressemble à nombre
            * (1 - v_code)  # Pénalise si ressemble à code
        )

        # --- SIGNAUX EN-TÊTE (header matching) ---

        h_norm = _norm_header(headers[j])

        def head_score(lex_keys: List[str]) -> float:
            """Score matching en-tête (1.0 si match, 0.0 sinon)"""
            if not h_norm:
                return 0.0
            # Normaliser chaque clé du lexique
            lex_norm = [_norm_header(k) for k in lex_keys]
            # Match si une clé est contenue dans l'en-tête
            for k in lex_norm:
                if k and k in h_norm:
                    return 1.0
            return 0.0

        h_date = head_score(LEX["date"])
        h_montant = head_score(LEX["montant"])
        h_matricule = head_score(LEX["matricule"])
        h_nom_prenom = head_score(LEX["nom_prenom"])
        h_code_paie = head_score(LEX["code_paie"])
        h_poste_budgetaire = head_score(LEX["poste_budgetaire"])
        h_description_poste = head_score(LEX["description_poste"])
        h_type_paie = head_score(LEX["type_paie"])

        # Stocker stats colonne
        col_stats.append(
            {
                # Value patterns
                "v_date": v_date,
                "v_montant": v_montant,
                "v_matricule": v_matricule,
                "v_code": v_code,
                "v_pb": v_pb,
                "v_np": v_np,
                "v_desc": v_desc,
                # Header matches
                "h_date": h_date,
                "h_montant": h_montant,
                "h_matricule": h_matricule,
                "h_nom_prenom": h_nom_prenom,
                "h_code_paie": h_code_paie,
                "h_poste_budgetaire": h_poste_budgetaire,
                "h_description_poste": h_description_poste,
                "h_type_paie": h_type_paie,
            }
        )

    # ========== CALCUL SCORES ==========

    targets = [
        "date",
        "montant",
        "matricule",
        "nom_prenom",
        "code_paie",
        "poste_budgetaire",
        "description_poste",
        "type_paie",
    ]

    # Initialiser matrice scores[target][col_index]
    score = {t: [0.0] * n_cols for t in targets}

    for j, s in enumerate(col_stats):
        # Score = weighted sum (value_patterns + header + statistics + position)

        score["date"][j] = W["value_patterns"] * s["v_date"] + W["header"] * s["h_date"]

        score["montant"][j] = (
            W["value_patterns"] * s["v_montant"] + W["header"] * s["h_montant"]
        )

        score["matricule"][j] = (
            W["value_patterns"] * s["v_matricule"] + W["header"] * s["h_matricule"]
        )

        score["nom_prenom"][j] = (
            W["value_patterns"] * s["v_np"] + W["header"] * s["h_nom_prenom"]
        )

        score["code_paie"][j] = (
            W["value_patterns"] * s["v_code"] + W["header"] * s["h_code_paie"]
        )

        score["poste_budgetaire"][j] = (
            W["value_patterns"] * s["v_pb"] + W["header"] * s["h_poste_budgetaire"]
        )

        score["description_poste"][j] = (
            W["value_patterns"] * s["v_desc"] + W["header"] * s["h_description_poste"]
        )

        score["type_paie"][j] = (
            W["header"] * s["h_type_paie"]  # Souvent détecté par en-tête uniquement
        )

    # ========== ASSIGNATION GREEDY STABLE ==========

    taken_cols = set()
    mapping = {}
    confidence = {}
    alternatives = {}

    for t in targets:
        # Trier colonnes par score décroissant
        ranked = sorted([(j, score[t][j]) for j in range(n_cols)], key=lambda x: -x[1])

        # Top 3 alternatives pour logging
        alternatives[t] = [(j, round(sc, 3)) for j, sc in ranked[:3]]

        # Assigner meilleure colonne non prise
        for j, sc in ranked:
            if j not in taken_cols:
                if sc > 0:
                    mapping[t] = j
                    confidence[t] = max(0.0, round(sc, 3))
                    taken_cols.add(j)
                else:
                    mapping[t] = None
                    confidence[t] = 0.0
                break
        else:
            # Aucune colonne disponible
            mapping[t] = None
            confidence[t] = 0.0

    # ========== NOTES & WARNINGS ==========

    notes = []

    for t in targets:
        c = confidence[t]

        if mapping[t] is not None:
            col_name = headers[mapping[t]]
            if c >= TH["accept"]:
                notes.append(f"{t}: OK: col '{col_name}' (confiance {c})")
            elif c >= TH["warn"]:
                notes.append(f"{t}: WARN: col '{col_name}' (confiance faible {c})")
            else:
                notes.append(f"{t}: WARN: col '{col_name}' (confiance très faible {c})")
        else:
            notes.append(f"{t}: ❌ non détecté")

    return {
        "mapping": mapping,
        "confidence": confidence,
        "alternatives": alternatives,
        "notes": notes,
    }


# Tests unitaires intégrés
if __name__ == "__main__":
    print("=== Test detect_schema ===")

    # Données test (colonnes inversées volontairement)
    test_data = [
        # Headers
        ["Montant", "Date Paie", "Matricule", "Nom, Prénom", "Code"],
        # Données
        ["1234,56", "2023-01-15", "1001", "Dupont, Jean", "SAL"],
        ["2500,00", "2023-01-15", "1002", "Martin Claire", "BON"],
        ["(500,00)", "2023-01-15", "1003", "Tremblay, Pierre", "DED"],
    ]

    test_config = {
        "weights": {
            "value_patterns": 0.55,
            "header": 0.25,
            "statistics": 0.15,
            "position": 0.05,
        },
        "thresholds": {"accept": 0.70, "warn": 0.50},
        "headers_lexicon": {
            "date": ["date", "date paie"],
            "montant": ["montant", "amount"],
            "matricule": ["matricule", "id"],
            "nom_prenom": ["nom", "nom prenom"],
            "code_paie": ["code", "pay code"],
            "poste_budgetaire": ["poste", "budget"],
            "description_poste": ["description"],
            "type_paie": ["type"],
        },
        "patterns": {
            "matricule_digits": r"^\d{3,10}$",
            "code_paie": r"^[A-Za-z]\w{1,7}$",
            "poste_budgetaire": [r"^\d{2,5}(-\d{2,5})*$"],
            "name_has_comma": ",",
            "name_words_min": 2,
        },
        "sample_size": 200,
    }

    result = detect_schema(test_data, test_config)

    print("\n📊 RÉSULTATS:")
    print(f"Mapping: {result['mapping']}")
    print(f"Confidence: {result['confidence']}")
    print("\n📝 Notes:")
    for note in result["notes"]:
        print(f"  {note}")
