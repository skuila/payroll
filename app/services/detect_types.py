# services/detect_types.py
# ========================================
# MOTEUR DÉTECTION GÉNÉRIQUE (Value-First)
# ========================================
# Détection automatique types colonnes avec scoring multi-critères
# Support segments (changements structure en cours de fichier)

import re
import math
from collections import Counter
from typing import Dict, List, Any, Tuple, Optional

# Import du parseur neutre depuis le module parsers
from app.services.parsers import parse_amount_neutral, parse_date_robust


# ========== UTILITAIRES FEATURES ==========


def build_mask(value: str, allow_chars: List[str]) -> str:
    """
    Construit un masque pour une valeur

    Mapping:
        A = lettre (a-zA-Z)
        9 = chiffre (0-9)
        - = tiret littéral
        _ = underscore littéral
        . = point littéral
        (autres) = préservés

    Args:
        value: Valeur à masquer
        allow_chars: Caractères autorisés dans le masque

    Returns:
        str: Masque (ex: "A999-AA" pour "B123-CD")
    """
    mask = []
    for c in str(value):
        if c.isalpha():
            mask.append("A" if "A" in allow_chars else c)
        elif c.isdigit():
            mask.append("9" if "9" in allow_chars else c)
        elif c in allow_chars:
            mask.append(c)
        else:
            mask.append(".")  # Wildcard pour caractères non attendus
    return "".join(mask)


def calculate_entropy(values: List[Any]) -> float:
    """
    Calcule l'entropie de Shannon d'une distribution

    Args:
        values: Liste de valeurs

    Returns:
        float: Entropie (0 = constant, >4 = très varié)
    """
    if not values:
        return 0.0

    counts = Counter(str(v) for v in values if v is not None)
    total = sum(counts.values())

    if total == 0:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    return entropy


def get_cardinality_stats(values: List[Any]) -> Dict[str, Any]:
    """
    Statistiques de cardinalité

    Returns:
        dict: {
            "total": int,
            "unique": int,
            "unique_ratio": float,
            "most_common_value": Any,
            "most_common_count": int,
            "most_common_ratio": float
        }
    """
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    total = len(non_null)

    if total == 0:
        return {
            "total": 0,
            "unique": 0,
            "unique_ratio": 0.0,
            "most_common_value": None,
            "most_common_count": 0,
            "most_common_ratio": 0.0,
        }

    counts = Counter(str(v) for v in non_null)
    unique = len(counts)
    most_common = counts.most_common(1)[0] if counts else (None, 0)

    return {
        "total": total,
        "unique": unique,
        "unique_ratio": unique / total,
        "most_common_value": most_common[0],
        "most_common_count": most_common[1],
        "most_common_ratio": most_common[1] / total,
    }


# ========== DÉTECTEURS ==========


def detector_mask_dominance(values: List[Any], config: Dict) -> float:
    """
    Détecteur: masque alphanumérique dominant

    Returns:
        float: Score 0.0-1.0
    """
    allow = config.get("allow", ["A", "9"])
    min_len = config.get("min_len", 1)
    max_len = config.get("max_len", 100)
    coverage_min = config.get("coverage_min", 0.60)
    noise_max = config.get("noise_max", 0.15)

    non_null = [
        str(v).strip() for v in values if v is not None and str(v).strip() != ""
    ]

    if not non_null:
        return 0.0

    # Construire masques
    masks = [build_mask(v, allow) for v in non_null]
    mask_counts = Counter(masks)

    # Masque dominant
    if not mask_counts:
        return 0.0

    dominant_mask, dominant_count = mask_counts.most_common(1)[0]
    coverage = dominant_count / len(non_null)
    noise = 1.0 - coverage

    # Vérifier longueur masque dominant
    mask_len = len(dominant_mask)
    if not (min_len <= mask_len <= max_len):
        return 0.0

    # Score basé sur coverage et noise
    if coverage >= coverage_min and noise <= noise_max:
        return coverage
    else:
        return coverage * 0.5  # Pénalité si hors critères


def detector_all_numeric_ratio(values: List[Any], config: Dict) -> float:
    """
    Détecteur: % valeurs 100% numériques

    Returns:
        float: Score 0.0-1.0
    """
    min_ratio = config.get("min_ratio", 0.80)

    non_null = [
        str(v).strip() for v in values if v is not None and str(v).strip() != ""
    ]

    if not non_null:
        return 0.0

    numeric_count = sum(1 for v in non_null if re.fullmatch(r"\d+", v))
    ratio = numeric_count / len(non_null)

    return ratio if ratio >= min_ratio else ratio * 0.5


def detector_contains_comma_ratio(values: List[Any], config: Dict) -> float:
    """
    Détecteur: % valeurs contenant virgule (pour montants FR-CA)

    Returns:
        float: Score 0.0-1.0
    """
    min_ratio = config.get("min_ratio", 0.45)

    non_null = [str(v) for v in values if v is not None and str(v).strip() != ""]

    if not non_null:
        return 0.0

    comma_count = sum(1 for v in non_null if "," in v)
    ratio = comma_count / len(non_null)

    return ratio if ratio >= min_ratio else ratio * 0.5


def detector_alpha_token_ratio(values: List[Any], config: Dict) -> float:
    """
    Détecteur: % tokens alphabétiques

    Returns:
        float: Score 0.0-1.0
    """
    min_ratio = config.get("min_ratio", 0.80)

    non_null = [
        str(v).strip() for v in values if v is not None and str(v).strip() != ""
    ]

    if not non_null:
        return 0.0

    total_tokens = 0
    alpha_tokens = 0

    for v in non_null:
        tokens = re.findall(r"\w+", v)
        total_tokens += len(tokens)
        alpha_tokens += sum(1 for t in tokens if re.fullmatch(r"[A-Za-z]+", t))

    if total_tokens == 0:
        return 0.0

    ratio = alpha_tokens / total_tokens
    return ratio if ratio >= min_ratio else ratio * 0.5


def detector_high_entropy_alpha(values: List[Any], config: Dict) -> float:
    """
    Détecteur: haute entropie (valeurs variées)

    Returns:
        float: Score 0.0-1.0
    """
    min_entropy = config.get("min_entropy", 2.5)
    max_const_ratio = config.get("max_const_ratio", 0.25)

    non_null = [v for v in values if v is not None and str(v).strip() != ""]

    if not non_null:
        return 0.0

    # Entropie
    entropy = calculate_entropy(non_null)

    # Ratio constante
    card_stats = get_cardinality_stats(non_null)
    const_ratio = card_stats["most_common_ratio"]

    # Score composé
    entropy_score = min(1.0, entropy / min_entropy) if min_entropy > 0 else 0.0
    const_score = 1.0 if const_ratio <= max_const_ratio else 0.0

    return (entropy_score + const_score) / 2.0


def detector_date_parse_ratio(values: List[Any], config: Dict) -> float:
    """
    Détecteur: % valeurs parsables comme date

    Returns:
        float: Score 0.0-1.0
    """
    min_ratio = config.get("min_ratio", 0.70)

    non_null = [v for v in values if v is not None and str(v).strip() != ""]

    if not non_null:
        return 0.0

    parsable_count = sum(1 for v in non_null if parse_date_robust(v) is not None)
    ratio = parsable_count / len(non_null)

    return ratio if ratio >= min_ratio else ratio * 0.5


def detector_number_parse_ratio(values: List[Any], config: Dict) -> float:
    """
    Détecteur: % valeurs parsables comme nombre (avec parseur neutre)

    Returns:
        float: Score 0.0-1.0
    """
    min_ratio = config.get("min_ratio", 0.70)

    non_null = [v for v in values if v is not None and str(v).strip() != ""]

    if not non_null:
        return 0.0

    parsable_count = sum(1 for v in non_null if parse_amount_neutral(v) is not None)
    ratio = parsable_count / len(non_null)

    return ratio if ratio >= min_ratio else ratio * 0.5


def detector_pattern_any(values: List[Any], config: Dict) -> float:
    """
    Détecteur: match au moins un pattern regex

    Returns:
        float: Score 0.0-1.0 (max ratio parmi les patterns)
    """
    patterns = config.get("patterns", [])

    non_null = [
        str(v).strip() for v in values if v is not None and str(v).strip() != ""
    ]

    if not non_null or not patterns:
        return 0.0

    max_ratio = 0.0

    for pattern in patterns:
        try:
            match_count = sum(1 for v in non_null if re.fullmatch(pattern, v))
            ratio = match_count / len(non_null)
            max_ratio = max(max_ratio, ratio)
        except re.error:
            continue

    return max_ratio


def detector_low_cardinality_hint(values: List[Any], config: Dict) -> float:
    """
    Détecteur: cardinalité faible (peu de valeurs distinctes)

    Returns:
        float: Score 0.0-1.0
    """
    max_uniques_ratio = config.get("max_uniques_ratio", 0.15)

    card_stats = get_cardinality_stats(values)
    unique_ratio = card_stats["unique_ratio"]

    if unique_ratio <= max_uniques_ratio:
        return 1.0 - (unique_ratio / max_uniques_ratio) * 0.5
    else:
        return 0.0


def detector_avg_length_range(values: List[Any], config: Dict) -> float:
    """
    Détecteur: longueur moyenne dans plage

    Returns:
        float: Score 0.0-1.0
    """
    min_len = config.get("min_len", 0)
    max_len = config.get("max_len", 1000)

    non_null = [
        str(v).strip() for v in values if v is not None and str(v).strip() != ""
    ]

    if not non_null:
        return 0.0

    avg_len = sum(len(v) for v in non_null) / len(non_null)

    if min_len <= avg_len <= max_len:
        return 1.0
    else:
        # Décroissance linéaire hors plage
        if avg_len < min_len:
            return max(0.0, avg_len / min_len) if min_len > 0 else 0.0
        else:  # avg_len > max_len
            return max(0.0, 1.0 - (avg_len - max_len) / max_len) if max_len > 0 else 0.0


# ========== REGISTRY DISPATCHER ==========

DETECTOR_FUNCTIONS = {
    "mask_dominance": detector_mask_dominance,
    "all_numeric_ratio": detector_all_numeric_ratio,
    "contains_comma_ratio": detector_contains_comma_ratio,
    "alpha_token_ratio": detector_alpha_token_ratio,
    "high_entropy_alpha": detector_high_entropy_alpha,
    "date_parse_ratio": detector_date_parse_ratio,
    "number_parse_ratio": detector_number_parse_ratio,
    "pattern_any": detector_pattern_any,
    "low_cardinality_hint": detector_low_cardinality_hint,
    "avg_length_range": detector_avg_length_range,
}


def run_detector(detector_config: Dict, values: List[Any]) -> float:
    """
    Exécute un détecteur et retourne son score

    Args:
        detector_config: Configuration détecteur (kind + params)
        values: Valeurs de la colonne

    Returns:
        float: Score 0.0-1.0 (ou négatif si pénalité)
    """
    kind = detector_config.get("kind")
    weight = detector_config.get("weight", 1.0)

    if kind not in DETECTOR_FUNCTIONS:
        return 0.0

    try:
        base_score = DETECTOR_FUNCTIONS[kind](values, detector_config)
        return base_score * weight
    except Exception as e:
        print(f"WARN: Erreur détecteur {kind}: {e}")
        return 0.0


# ========== VALIDATION ==========


def run_validators(validator_configs: List[Dict], values: List[Any]) -> bool:
    """
    Exécute les validateurs (filtres post-détection)

    Returns:
        bool: True si tous validateurs passent
    """
    for validator in validator_configs:
        kind = validator.get("kind")

        if kind == "uniqueness_hint":
            card_stats = get_cardinality_stats(values)
            min_ratio = validator.get("min_uniques_ratio", 0.30)
            if card_stats["unique_ratio"] < min_ratio:
                return False

        elif kind == "reject_constant":
            card_stats = get_cardinality_stats(values)
            max_const = validator.get("max_const_ratio", 0.10)
            if card_stats["most_common_ratio"] > max_const:
                return False

        elif kind == "high_entropy":
            min_ent = validator.get("min_entropy", 2.5)
            entropy = calculate_entropy(values)
            if entropy < min_ent:
                return False

    return True


# ========== DÉTECTION SEGMENTS ==========


def detect_segments(df, sample_size: int = 200) -> List[Tuple[int, int]]:
    """
    Détecte les changements de structure dans le fichier

    Stratégie:
    - Analyser masques dominants par tranche de N lignes
    - Si masque change brusquement → nouveau segment

    Args:
        df: DataFrame ou list[list]
        sample_size: Taille tranches

    Returns:
        List[(start_row, end_row)]: Liste de segments
    """
    # Pour l'instant: retourne un seul segment (tout le fichier)
    # TODO: implémenter détection multi-segments

    try:
        import pandas as pd

        if isinstance(df, pd.DataFrame):
            total_rows = len(df)
        else:
            total_rows = len(df) - 1 if df else 0
    except Exception as _exc:
        total_rows = len(df) - 1 if df else 0

    return [(0, total_rows)]


# ========== MOTEUR PRINCIPAL ==========


def detect_types(df, registry: Optional[Dict] = None) -> Dict:
    """
    Détecte automatiquement les types de colonnes

    Args:
        df: DataFrame pandas ou list[list]
        registry: Configuration depuis schema_registry.yaml (optionnel, chargé automatiquement si None)

    Returns:
        dict: {
            "segments": [{
                "range": (start, end),
                "mapping": {"matricule": 2, "nom": 0, ...},
                "confidence": {"matricule": 0.92, ...},
                "scores_detail": {...},
                "notes": [...]
            }],
            "global_suggestion": {...}  # Meilleur mapping global
        }
    """

    # ========== CHARGEMENT REGISTRE PAR DÉFAUT ==========

    if registry is None:
        try:
            from config.schema_registry import load_registry

            registry = load_registry()
        except ImportError:
            # Fallback si le module n'est pas disponible
            registry = {
                "types": {},
                "ui": {
                    "sample_rows": 200,
                    "min_confidence_accept": 0.70,
                    "min_confidence_warn": 0.50,
                },
            }

    # ========== PARSING INPUT ==========

    try:
        import pandas as pd  # type: ignore[import]
    except Exception as _exc:
        pd = None  # type: ignore[assignment]
        is_pandas = False
    else:
        is_pandas = isinstance(df, pd.DataFrame)

    if is_pandas:
        headers = [str(h) for h in df.columns]
        sample_size = registry["ui"].get("sample_rows", 200)
        sample_data = df.head(sample_size).values.tolist()
    else:
        if not df or len(df) == 0:
            return {"segments": [], "global_suggestion": {}, "notes": ["Fichier vide"]}
        headers = [str(h) for h in df[0]]
        sample_size = registry["ui"].get("sample_rows", 200)
        sample_data = df[1 : min(len(df), 1 + sample_size)]

    n_cols = len(headers)

    if n_cols == 0:
        return {"segments": [], "global_suggestion": {}, "notes": ["Aucune colonne"]}

    # ========== EXTRACTION TYPES DU REGISTRE ==========

    type_defs = registry.get("types", {})
    visible_types = {k: v for k, v in type_defs.items() if v.get("visible", True)}

    # ========== CALCUL SCORES PAR COLONNE ==========

    scores_matrix = {}  # scores_matrix[type_name][col_idx] = score

    for type_name, type_def in visible_types.items():
        scores_matrix[type_name] = [0.0] * n_cols

        for col_idx in range(n_cols):
            # Extraire valeurs colonne
            col_values = []
            for row in sample_data:
                if col_idx < len(row):
                    col_values.append(row[col_idx])
                else:
                    col_values.append(None)

            # Exécuter détecteurs
            detectors = type_def.get("detectors", [])
            total_score = 0.0

            for detector_config in detectors:
                score = run_detector(detector_config, col_values)
                total_score += score

            # Normaliser score (clamp 0-1, sauf pénalités)
            total_score = max(-1.0, min(1.0, total_score))

            # Valider
            validators = type_def.get("validators", [])
            if validators and not run_validators(validators, col_values):
                total_score *= 0.3  # Pénalité forte si validation échoue

            scores_matrix[type_name][col_idx] = total_score

    # ========== ASSIGNATION GREEDY PAR PRIORITÉ ==========

    # Trier types par priorité décroissante
    types_by_priority = sorted(
        visible_types.keys(),
        key=lambda t: type_defs[t].get("priority", 50),
        reverse=True,
    )

    taken_cols: set[int] = set()
    mapping: Dict[str, Optional[int]] = {}
    confidence: Dict[str, float] = {}
    scores_detail: Dict[str, List[Tuple[int, float]]] = {}

    for type_name in types_by_priority:
        # Trier colonnes par score décroissant
        ranked: List[Tuple[int, float]] = sorted(
            [(col_idx, scores_matrix[type_name][col_idx]) for col_idx in range(n_cols)],
            key=lambda x: -x[1],
        )

        scores_detail[type_name] = ranked[:3]  # Top 3 pour UI

        # Assigner meilleure colonne non prise
        for col_idx, score in ranked:
            if col_idx not in taken_cols and score > 0:
                mapping[type_name] = col_idx
                confidence[type_name] = round(score, 3)
                taken_cols.add(col_idx)
                break
        else:
            mapping[type_name] = None
            confidence[type_name] = 0.0

    # ========== NOTES & WARNINGS ==========

    notes = []
    min_accept = registry["ui"].get("min_confidence_accept", 0.70)
    min_warn = registry["ui"].get("min_confidence_warn", 0.50)

    for type_name, col_idx_opt in mapping.items():
        conf = confidence[type_name]

        if col_idx_opt is not None:
            col_idx = col_idx_opt
            col_name = headers[col_idx]
            if conf >= min_accept:
                notes.append(
                    f"OK: {type_name}: col {col_idx} '{col_name}' (confiance: {conf})"
                )
            elif conf >= min_warn:
                notes.append(
                    f"WARN: {type_name}: col {col_idx} '{col_name}' (FAIBLE confiance: {conf})"
                )
            else:
                notes.append(
                    f"❌ {type_name}: col {col_idx} '{col_name}' (TRÈS FAIBLE: {conf})"
                )
        else:
            notes.append(f"❌ {type_name}: NON DÉTECTÉ")

    # ========== RETOUR RÉSULTATS ==========

    return {
        "segments": [
            {
                "range": (0, len(sample_data)),
                "mapping": mapping,
                "confidence": confidence,
                "scores_detail": scores_detail,
                "notes": notes,
            }
        ],
        "global_suggestion": {
            "mapping": mapping,
            "confidence": confidence,
            "notes": notes,
        },
        "headers": headers,
    }


# ========== TESTS ==========

if __name__ == "__main__":
    import yaml  # type: ignore[import]
    from pathlib import Path

    print("=" * 70)
    print("TEST MOTEUR DÉTECTION")
    print("=" * 70)

    # Charger registre
    registry_path = Path(__file__).parent.parent / "config" / "schema_registry.yaml"

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    print(f"OK: Registre chargé: {len(registry['types'])} types")

    # Données test (colonnes inversées + "Gains" constant)
    test_data = [
        ["Type Paie", "Nom, Prénom", "Matricule", "Date", "Montant"],
        ["Gains", "Dupont, Jean", "1001", "2023-01-15", "1234,56"],
        ["Gains", "Martin, Claire", "1002", "2023-01-15", "2500,00"],
        ["Gains", "Tremblay, Pierre", "1003", "15/01/2023", "(500,00)"],
        ["Gains", "Adrienne, Terry", "1004", "44927", "3200,50"],
    ]

    result = detect_types(test_data, registry)

    print("\n🎯 RÉSULTATS:")
    for note in result["global_suggestion"]["notes"]:
        print(f"  {note}")

    print("\n✅ Test terminé")
