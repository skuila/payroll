# services/transformers.py
# ========================================
# TRANSFORMERS FR-CA (Normalisations)
# ========================================
# Transformations et nettoyages pour import données paie

import re
import unicodedata
from decimal import Decimal
from typing import Any, Optional, Dict

from .locale_fr_ca import parse_date_fr_ca, parse_number_fr_ca


# ========== UTILITAIRES BASE ==========


def _normalize_unicode(s: str) -> str:
    """
    Normalise Unicode (supprime accents)

    Args:
        s: Texte à normaliser

    Returns:
        str: Texte sans accents
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


# ========== TRANSFORMERS TEXTE ==========


def transform_strip(value: Any, config: Dict = None) -> str:
    """Supprime espaces début/fin"""
    return str(value).strip() if value is not None else ""


def transform_collapse_spaces(value: Any, config: Dict = None) -> str:
    """Collapse espaces multiples"""
    s = str(value) if value is not None else ""
    return " ".join(s.split())


def transform_to_upper(value: Any, config: Dict = None) -> str:
    """Convertir en MAJUSCULES"""
    return str(value).upper() if value is not None else ""


def transform_to_lower(value: Any, config: Dict = None) -> str:
    """Convertir en minuscules"""
    return str(value).lower() if value is not None else ""


def transform_title_case(value: Any, config: Dict = None) -> str:
    """
    Majuscule première lettre de chaque mot

    Exemple: "jean dupont" → "Jean Dupont"
    """
    s = str(value).strip() if value is not None else ""
    return s.title()


def transform_title_case_keep_hyphen(value: Any, config: Dict = None) -> str:
    """
    Title case en préservant les tirets

    Exemple: "jean-pierre" → "Jean-Pierre"
    """
    s = str(value).strip() if value is not None else ""
    parts = s.split("-")
    return "-".join(p.capitalize() for p in parts)


def transform_sentence_case(value: Any, config: Dict = None) -> str:
    """
    Première lettre majuscule uniquement

    Exemple: "description du poste" → "Description du poste"
    """
    s = str(value).strip() if value is not None else ""
    return s[0].upper() + s[1:] if s else ""


def transform_drop_trailing_digit(value: Any, config: Dict = None) -> str:
    """
    Supprime chiffre final (parasite)

    Exemple: "Amin 6" → "Amin"
    """
    s = str(value).strip() if value is not None else ""
    return re.sub(r"\s+\d+$", "", s)


# ========== TRANSFORMERS NOMS ==========


def transform_split_fullname(value: Any, config: Dict = None) -> Dict[str, str]:
    """
    Sépare "Nom, Prénom" en composants

    Args:
        value: Nom complet (ex: "Dupont, Jean")
        config: {format: "Nom, Prénom"} (optionnel)

    Returns:
        dict: {"nom": "Dupont", "prenom": "Jean", "nom_norm": "dupont", ...}
    """
    raw = str(value).strip() if value is not None else ""

    if "," in raw:
        # Format "Nom, Prénom"
        left, right = raw.split(",", 1)
        nom = left.strip()
        prenom = right.strip()
    else:
        # Format "Prénom Nom" (dernier mot = nom)
        parts = raw.split()
        if len(parts) >= 2:
            nom = parts[-1]
            prenom = " ".join(parts[:-1])
        else:
            nom = raw
            prenom = ""

    # Normaliser
    nom_norm = _normalize_unicode(nom).lower()
    prenom_norm = _normalize_unicode(prenom).lower() if prenom else ""

    return {
        "nom": nom,
        "prenom": prenom or "Inconnu",  # Jamais vide pour DB
        "nom_norm": nom_norm,
        "prenom_norm": prenom_norm or "inconnu",
        "nom_prenom": raw,
    }


# ========== TRANSFORMERS NOMBRES/DATES ==========


def transform_to_iso_date(value: Any, config: Dict = None) -> Optional[str]:
    """
    Convertit en date ISO (YYYY-MM-DD)

    Args:
        value: Valeur date (texte, serial Excel, etc.)
        config: {locale: "fr-CA"} (optionnel)

    Returns:
        str: Date ISO ou None
    """
    date_obj = parse_date_fr_ca(value)
    return str(date_obj) if date_obj else None


def transform_to_decimal(value: Any, config: Dict = None) -> Optional[Decimal]:
    """
    Convertit en Decimal

    Args:
        value: Valeur numérique (texte FR-CA, nombre, etc.)
        config: {locale: "fr-CA"} (optionnel)

    Returns:
        Decimal ou None
    """
    return parse_number_fr_ca(value)


def transform_normalize_currency(value: Any, config: Dict = None) -> str:
    """
    Normalise code devise

    Mapping:
        $ → CAD
        C$ → CAD
        CA$ → CAD
        CAD → CAD
        USD → USD
        EUR → EUR

    Returns:
        str: Code devise normalisé
    """
    s = str(value).strip().upper() if value is not None else ""

    mapping = {
        "$": "CAD",
        "C$": "CAD",
        "CA$": "CAD",
        "CAD": "CAD",
        "USD": "USD",
        "EUR": "EUR",
    }

    return mapping.get(s, s)


# ========== REGISTRY DISPATCHER ==========

TRANSFORMER_FUNCTIONS = {
    "strip": transform_strip,
    "collapse_spaces": transform_collapse_spaces,
    "to_upper": transform_to_upper,
    "to_lower": transform_to_lower,
    "title_case": transform_title_case,
    "title_case_keep_hyphen": transform_title_case_keep_hyphen,
    "sentence_case": transform_sentence_case,
    "drop_trailing_digit": transform_drop_trailing_digit,
    "split_fullname": transform_split_fullname,
    "to_iso_date": transform_to_iso_date,
    "to_decimal": transform_to_decimal,
    "normalize_currency": transform_normalize_currency,
}


def apply_transforms(value: Any, transform_configs: List[Dict]) -> Any:
    """
    Applique une chaîne de transformations

    Args:
        value: Valeur initiale
        transform_configs: Liste transformations [{kind: "strip"}, {kind: "to_upper"}, ...]

    Returns:
        Any: Valeur transformée
    """
    result = value

    for transform_config in transform_configs:
        kind = (
            transform_config.get("kind")
            if isinstance(transform_config, dict)
            else transform_config
        )

        # Support format court: "strip" au lieu de {"kind": "strip"}
        if isinstance(kind, str):
            transform_config = {"kind": kind}

        kind = transform_config.get("kind")

        if kind in TRANSFORMER_FUNCTIONS:
            try:
                result = TRANSFORMER_FUNCTIONS[kind](result, transform_config)
            except Exception as e:
                print(f"WARN: Erreur transform {kind}: {e}")
                continue

    return result


# ========== TESTS ==========

if __name__ == "__main__":
    print("=" * 70)
    print("TEST TRANSFORMERS FR-CA")
    print("=" * 70)

    # Test split_fullname
    print("\n👤 Test split_fullname:")
    test_names = [
        "Dupont, Jean",
        "Jean Dupont",
        "Dupont,",
        "Adrienne, Terry",
    ]
    for name in test_names:
        result = transform_split_fullname(name)
        print(f"  '{name}' → nom='{result['nom']}' prenom='{result['prenom']}'")

    # Test to_iso_date
    print("\n📅 Test to_iso_date:")
    test_dates = [
        "2023-01-15",
        "15/01/2023",
        "44927",  # Excel serial
    ]
    for date in test_dates:
        result = transform_to_iso_date(date)
        print(f"  '{date}' → '{result}'")

    # Test to_decimal
    print("\n💰 Test to_decimal:")
    test_nums = [
        "1 234,56",
        "(500,00)",
        "1234.56",
    ]
    for num in test_nums:
        result = transform_to_decimal(num)
        print(f"  '{num}' → {result}")

    # Test chaîne transforms
    print("\n🔗 Test chaîne transforms:")
    value = "  jean-pierre  "
    transforms = [{"kind": "strip"}, {"kind": "title_case_keep_hyphen"}]
    result = apply_transforms(value, transforms)
    print(f"  '{value}' → '{result}'")

    print("\n✅ Tests terminés")
