"""
Parseurs neutres pour les montants et dates
Évite les imports circulaires entre les modules
"""

import re
import pandas as pd
from datetime import datetime
from typing import Any, Optional


def parse_amount_neutral(value: Any, context: str = "") -> Optional[float]:
    """
    Parseur neutre pour les montants avec virgule et parenthèses.

    Gère nativement:
    - 1 234,56 (espaces fines/insécables OK)
    - 1234,56
    - -1234,56
    - (1 234,56) → négatif
    - Refuse le point comme séparateur décimal

    Args:
        value: Valeur à parser
        context: Contexte pour les logs (ex: "Ligne 123")

    Returns:
        float ou None si parsing impossible
    """
    if value is None or pd.isna(value):
        return None

    # Si déjà un nombre
    if isinstance(value, (int, float)):
        return float(value)

    # Convertir en string et nettoyer
    raw_value = str(value).strip()
    if not raw_value:
        return None

    # Détecter notation comptable négative (parenthèses)
    is_negative = raw_value.startswith("(") and raw_value.endswith(")")
    if is_negative:
        raw_value = raw_value[1:-1].strip()

    # Retirer caractères non numériques courants
    # NBSP (non-breaking space U+202F et U+00A0)
    cleaned = raw_value.replace("\u202f", "").replace("\u00a0", "")
    cleaned = cleaned.replace("$", "").replace("CA", "").replace("CAD", "")

    # Retirer tous les espaces
    cleaned = re.sub(r"\s+", "", cleaned)

    # Gestion des séparateurs décimaux
    # Si contient un point ET une virgule, le point est séparateur de milliers
    if "." in cleaned and "," in cleaned:
        # Remplacer le point par rien (séparateur de milliers)
        cleaned = cleaned.replace(".", "")
        # Remplacer la virgule par un point (séparateur décimal)
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned:
        # Virgule seule = séparateur décimal
        cleaned = cleaned.replace(",", ".")
    # Si point seul, le garder tel quel (format anglais)

    # Parse avec float
    try:
        result = float(cleaned)
        if is_negative:
            result = -result
        return result
    except ValueError:
        return None


def parse_date_robust(value: Any, context: str = "") -> Optional[str]:
    """
    Parseur robuste pour les dates avec validation stricte.

    Args:
        value: Valeur à parser
        context: Contexte pour les logs

    Returns:
        str au format YYYY-MM-DD ou None
    """
    if value is None or pd.isna(value):
        return None

    # Si déjà un Timestamp pandas ou datetime
    if isinstance(value, (pd.Timestamp, datetime)):
        year_num = value.year
        if 2000 <= year_num <= 2050:
            return value.strftime("%Y-%m-%d")
        else:
            return None

    # Convertir en string
    date_str = str(value).strip()
    if not date_str:
        return None

    # Format ISO complet: "2025-08-28 00:00:00" → "2025-08-28"
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_str)
    if match:
        year_str, month_str, day_str = match.groups()
        year_int = int(year_str)
        if 2000 <= year_int <= 2050:
            return f"{year_str}-{month_str}-{day_str}"
        else:
            return None

    # Format européen: DD/MM/YYYY ou DD-MM-YYYY
    match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", date_str)
    if match:
        day_str, month_str, year_str = match.groups()
        year_int = int(year_str)
        month_int = int(month_str)
        day_int = int(day_str)

        # Validation date logique
        if not (1 <= month_int <= 12 and 1 <= day_int <= 31):
            return None

        if 2000 <= year_int <= 2050:
            return f"{year_str}-{month_str.zfill(2)}-{day_str.zfill(2)}"
        else:
            return None

    # Essai parsing pandas (dernier recours)
    try:
        date_dt = pd.to_datetime(date_str, errors="coerce", dayfirst=True)
        if not pd.isna(date_dt):
            year_num = date_dt.year
            if 2000 <= year_num <= 2050:
                return date_dt.strftime("%Y-%m-%d")
            else:
                return None
    except Exception as _exc:
        pass

    return None
