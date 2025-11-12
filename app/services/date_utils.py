#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module utilitaire de gestion des dates
Gère la détection Excel 1900/1904 et parsing day-first

Fonctions:
- is_already_datetime() : Vérifie si déjà typé date
- detect_excel_date_system() : Détecte origine Excel (1900 vs 1904)
- parse_mixed_dates() : Parse dates mixtes (texte + numéros)
- sanitize_date_range() : Filtre dates hors plage valide
"""

import pandas as pd
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Plage valide pour dates de paie (1990-2100)
MIN_VALID_YEAR = 1990
MAX_VALID_YEAR = 2100
MIN_VALID_DATE = pd.Timestamp(f"{MIN_VALID_YEAR}-01-01")
MAX_VALID_DATE = pd.Timestamp(f"{MAX_VALID_YEAR}-12-31")


def is_already_datetime(series: pd.Series) -> bool:
    """
    Vérifie si une série est déjà typée datetime/date

    Returns:
        True si déjà datetime, False sinon
    """
    return pd.api.types.is_datetime64_any_dtype(series)


def detect_excel_date_system(
    series: pd.Series, workbook_flag: Optional[str] = None
) -> dict:
    """
    Détecte le système de dates Excel (1900 vs 1904)

    Teste les deux origines et choisit celle qui produit
    le plus de dates dans la plage valide (1990-2100).

    Args:
        series: Série pandas avec valeurs numériques (serial Excel)
        workbook_flag: Flag Excel date1904 (si connu) - 'True'/'False'/None

    Returns:
        dict avec:
        - system: '1900' ou '1904'
        - origin: '1899-12-30' ou '1904-01-01'
        - valid_dates_pct: Pourcentage de dates valides
        - pct_1900: Score système 1900
        - pct_1904: Score système 1904
    """
    # Si flag Excel connu, l'utiliser directement
    if workbook_flag == "True" or workbook_flag == True:
        return {
            "system": "1904",
            "origin": "1904-01-01",
            "source": "workbook_flag",
            "valid_dates_pct": 100.0,
            "pct_1900": 0,
            "pct_1904": 100.0,
        }

    # Filtrer les valeurs numériques
    numeric_values = pd.to_numeric(series, errors="coerce").dropna()

    if len(numeric_values) == 0:
        return {
            "system": "1900",
            "origin": "1899-12-30",
            "reason": "no_numeric_values",
            "valid_dates_pct": 0,
            "pct_1900": 0,
            "pct_1904": 0,
        }

    # Plage valide serial Excel (1 à 100000 = 1900-01-01 à 2173-10-15)
    valid_serials = numeric_values[(numeric_values >= 1) & (numeric_values <= 100000)]

    if len(valid_serials) == 0:
        return {
            "system": "1900",
            "origin": "1899-12-30",
            "reason": "no_valid_serials",
            "valid_dates_pct": 0,
            "pct_1900": 0,
            "pct_1904": 0,
        }

    # Test origine 1900 (1899-12-30)
    try:
        dates_1900 = pd.to_datetime(
            valid_serials, unit="D", origin="1899-12-30", errors="coerce"
        )
        valid_1900 = dates_1900[
            (dates_1900 >= MIN_VALID_DATE) & (dates_1900 <= MAX_VALID_DATE)
        ]
        pct_1900 = (len(valid_1900) / len(valid_serials)) * 100
    except Exception as _exc:
        pct_1900 = 0

    # Test origine 1904 (1904-01-01)
    try:
        dates_1904 = pd.to_datetime(
            valid_serials, unit="D", origin="1904-01-01", errors="coerce"
        )
        valid_1904 = dates_1904[
            (dates_1904 >= MIN_VALID_DATE) & (dates_1904 <= MAX_VALID_DATE)
        ]
        pct_1904 = (len(valid_1904) / len(valid_serials)) * 100
    except Exception as _exc:
        pct_1904 = 0

    # Choisir l'origine avec le meilleur taux de dates valides
    if pct_1900 >= pct_1904:
        origin = "1899-12-30"
        pct = pct_1900
        system = "1900"
    else:
        origin = "1904-01-01"
        pct = pct_1904
        system = "1904"

    stats = {
        "system": system,
        "origin": origin,
        "total_values": int(len(valid_serials)),
        "valid_dates_pct": round(pct, 1),
        "pct_1900": round(pct_1900, 1),
        "pct_1904": round(pct_1904, 1),
        "source": "auto_detection",
    }

    logger.info(
        f"Détection Excel: système {system} choisi ({pct:.1f}% valides, 1900={pct_1900:.1f}%, 1904={pct_1904:.1f}%)"
    )

    return stats


def parse_text_dates(series: pd.Series, dayfirst: bool = True) -> pd.Series:
    """
    Parse dates texte avec nettoyage et anti-inversion YYYY-DD-MM

    Args:
        series: Série de textes à parser
        dayfirst: Parser avec jour en premier (28-08-2025)

    Returns:
        Série de dates parsées
    """
    import re

    # Nettoyage + normalisation séparateurs (/ → -)
    cleaned = (
        series.astype(str).str.strip().str.replace("\xa0", " ").str.replace("  ", " ")
    )
    cleaned = cleaned.str.replace("/", "-")  # Normaliser: 15/09/2025 → 15-09-2025

    # Anti-inversion YYYY-DD-MM: détecter pattern YYYY-(13..31)-(01..12)
    # Ex: "2025-28-08" doit devenir "2025-08-28"
    def fix_yyyy_dd_mm(date_str):
        if not isinstance(date_str, str):
            return date_str

        match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", date_str)
        if match:
            year, val1, val2 = match.groups()
            try:
                val1_int = int(val1)
                val2_int = int(val2)

                # Si val1 > 12 et val2 <= 12, c'est probablement YYYY-DD-MM
                if val1_int > 12 and 1 <= val2_int <= 12:
                    # Inverser: YYYY-DD-MM → YYYY-MM-DD
                    return f"{year}-{val2.zfill(2)}-{val1.zfill(2)}"
            except Exception as _exc:
                pass

        return date_str

    # Appliquer fix seulement si présence de pattern YYYY-XX-XX
    try:
        if cleaned.str.match(r"^\d{4}-\d{1,2}-\d{1,2}$").any():
            cleaned = cleaned.apply(fix_yyyy_dd_mm)
    except Exception as _exc:
        pass  # Pas grave si regex échoue

    # Parser avec pandas
    result = pd.to_datetime(cleaned, dayfirst=dayfirst, errors="coerce")

    return result


def parse_mixed_dates(
    series: pd.Series, origin_choice: Optional[str] = None, dayfirst: bool = True
) -> Tuple[pd.Series, dict]:
    """
    Parse une série de dates mixtes (texte + numéros Excel)

    Args:
        series: Série pandas avec dates mixtes
        origin_choice: Origine Excel ('1899-12-30' ou '1904-01-01') ou None pour auto-détection
        dayfirst: Parser texte avec jour en premier (28/08/2025 vs 08/28/2025)

    Returns:
        Tuple (dates_parsed, stats) où:
        - dates_parsed: Série pandas de dates normalisées
        - stats: dictionnaire avec statistiques de parsing
    """
    total = len(series)

    # Déjà datetime ?
    if is_already_datetime(series):
        logger.info("Colonne déjà datetime, pas de conversion")
        return series, {"already_datetime": True, "total": total}

    # Séparer numéros et textes
    numeric_mask = pd.to_numeric(series, errors="coerce").notna()
    text_mask = ~numeric_mask & series.notna()

    numeric_count = numeric_mask.sum()
    text_count = text_mask.sum()

    logger.info(
        f"Détection valeurs: {numeric_count} numériques, {text_count} texte, {total - numeric_count - text_count} vides"
    )

    # Initialiser série résultat
    result = pd.Series([pd.NaT] * total, index=series.index)

    # 1. Parser les numéros (serial Excel)
    if numeric_count > 0:
        numeric_series = pd.to_numeric(series[numeric_mask], errors="coerce")

        # Auto-détection origine si non fournie
        if origin_choice is None:
            detection_stats = detect_excel_date_system(numeric_series)
            origin_choice = detection_stats.get("origin", "1899-12-30")
            logger.info(
                f"Auto-détection: système {detection_stats.get('system', '1900')}, origin={origin_choice}"
            )

        # Filtrer serial Excel plausibles (1 à 100000)
        valid_mask = (numeric_series >= 1) & (numeric_series <= 100000)
        valid_serials = numeric_series[valid_mask]

        if len(valid_serials) > 0:
            try:
                # Conversion serial Excel
                dates_converted = pd.to_datetime(
                    valid_serials, unit="D", origin=origin_choice, errors="coerce"
                )

                # Stocker dans résultat
                result.loc[valid_serials.index] = dates_converted

                logger.info(
                    f"Numéros: {len(valid_serials)} serial Excel convertis (origin={origin_choice})"
                )
            except Exception as e:
                logger.warning(f"Erreur conversion serial Excel: {e}")

    # 2. Parser les textes
    if text_count > 0:
        text_series = series[text_mask]

        # Parser avec parse_text_dates (inclut anti-inversion YYYY-DD-MM)
        try:
            dates_text = parse_text_dates(text_series, dayfirst=dayfirst)

            # Stocker dans résultat
            result.loc[text_series.index] = dates_text

            valid_text = dates_text.notna().sum()
            logger.info(
                f"Texte: {valid_text}/{text_count} dates parsées (dayfirst={dayfirst}, anti-inversion YYYY-DD-MM)"
            )
        except Exception as e:
            logger.error(f"Erreur parsing texte: {e}")

    # Statistiques finales
    total_parsed = result.notna().sum()
    total_failed = total - total_parsed

    # Déterminer système à partir de l'origine choisie
    system = "1904" if origin_choice and "1904" in origin_choice else "1900"

    stats = {
        "total": total,
        "numeric_count": int(numeric_count),
        "text_count": int(text_count),
        "parsed": int(total_parsed),
        "failed": int(total_failed),
        "success_rate_pct": round((total_parsed / total) * 100, 1) if total > 0 else 0,
        "origin": origin_choice,
        "system": system,
    }

    logger.info(
        f"Résultat parsing: {total_parsed}/{total} dates ({stats['success_rate_pct']}%), système={system}"
    )

    return result, stats


def sanitize_date_range(
    series: pd.Series, min_year: int = MIN_VALID_YEAR, max_year: int = MAX_VALID_YEAR
) -> Tuple[pd.Series, dict]:
    """
    Filtre les dates hors plage valide (met à NaT)

    Args:
        series: Série pandas de dates
        min_year: Année minimum acceptable (défaut: 1990)
        max_year: Année maximum acceptable (défaut: 2100)

    Returns:
        Tuple (dates_sanitized, stats)
    """
    if not is_already_datetime(series):
        series = pd.to_datetime(series, errors="coerce")

    total = len(series)
    valid_before = series.notna().sum()

    # Filtrer par plage
    min_date = pd.Timestamp(f"{min_year}-01-01")
    max_date = pd.Timestamp(f"{max_year}-12-31")

    # Créer masque : date valide ET dans la plage
    valid_mask = (series >= min_date) & (series <= max_date)

    # Copier et mettre à NaT les dates hors plage
    result = series.copy()
    result[~valid_mask & series.notna()] = pd.NaT

    valid_after = result.notna().sum()
    rejected = valid_before - valid_after

    stats = {
        "total": total,
        "valid_before": int(valid_before),
        "rejected": int(rejected),
        "valid_after": int(valid_after),
        "min_year": min_year,
        "max_year": max_year,
    }

    if rejected > 0:
        logger.warning(
            f"Sanitize: {rejected} dates rejetées (hors {min_year}-{max_year})"
        )
    else:
        logger.info(f"Sanitize: Toutes les dates sont valides ({valid_after}/{total})")

    return result, stats


def format_dates_iso(series: pd.Series) -> pd.Series:
    """
    Formate une série de dates en ISO 8601 (YYYY-MM-DD)

    Args:
        series: Série pandas de dates

    Returns:
        Série de strings au format YYYY-MM-DD
    """
    if not is_already_datetime(series):
        series = pd.to_datetime(series, errors="coerce")

    # Formater en YYYY-MM-DD (ISO)
    return series.dt.strftime("%Y-%m-%d")


def process_date_column(
    series: pd.Series,
    column_name: str = "Date",
    dayfirst: bool = True,
    min_year: int = MIN_VALID_YEAR,
    max_year: int = MAX_VALID_YEAR,
) -> Tuple[pd.Series, dict]:
    """
    Pipeline complet de traitement d'une colonne de dates

    Étapes:
    1. Vérifier si déjà datetime (skip si oui)
    2. Parser dates mixtes (numéros + texte)
    3. Sanitize (filtrer hors plage)
    4. Formater en ISO

    Args:
        series: Série pandas à traiter
        column_name: Nom de la colonne (pour logging)
        dayfirst: Parser texte avec jour en premier
        min_year: Année minimum acceptable
        max_year: Année maximum acceptable

    Returns:
        Tuple (dates_iso, full_stats)
    """
    logger.info(f"=== Traitement colonne '{column_name}' ===")

    # Étape 1 : Vérifier si déjà datetime
    if is_already_datetime(series):
        logger.info(f"Colonne '{column_name}' déjà typée datetime")
        sanitized, sanitize_stats = sanitize_date_range(series, min_year, max_year)
        iso_dates = format_dates_iso(sanitized)

        full_stats = {
            "column": column_name,
            "already_datetime": True,
            "total": len(series),
            "final_valid": int(sanitized.notna().sum()),
            "final_valid_pct": (
                round((sanitized.notna().sum() / len(series)) * 100, 1)
                if len(series) > 0
                else 0
            ),
            "sanitize": sanitize_stats,
        }

        return iso_dates, full_stats

    # Étape 2 : Parser dates mixtes
    parsed, parse_stats = parse_mixed_dates(series, dayfirst=dayfirst)

    # Étape 3 : Sanitize
    sanitized, sanitize_stats = sanitize_date_range(parsed, min_year, max_year)

    # Étape 4 : Formater ISO
    iso_dates = format_dates_iso(sanitized)

    # Statistiques complètes (avec propagation système Excel si détecté)
    full_stats = {
        "column": column_name,
        "already_datetime": False,
        "total": parse_stats.get("total", len(series)),
        "numeric_count": parse_stats.get("numeric_count", 0),
        "text_count": parse_stats.get("text_count", 0),
        "parsed": parse_stats.get("parsed", 0),
        "failed": parse_stats.get("failed", 0),
        "success_rate_pct": parse_stats.get("success_rate_pct", 0),
        "origin": parse_stats.get("origin"),
        "system": parse_stats.get("system"),
        "sanitize": sanitize_stats,
        "final_valid": int(sanitized.notna().sum()),
        "final_valid_pct": round((sanitized.notna().sum() / len(series)) * 100, 1),
    }

    logger.info(
        f"=== Résultat '{column_name}': {full_stats['final_valid']}/{len(series)} dates valides ({full_stats['final_valid_pct']}%) ==="
    )

    # Avertissement si taux de succès < 90%
    if full_stats["final_valid_pct"] < 90:
        logger.warning(
            f"WARN:  Colonne '{column_name}': seulement {full_stats['final_valid_pct']}% de dates valides. "
            f"Vérifiez le format de vos données."
        )

    return iso_dates, full_stats


def detect_date_columns(df: pd.DataFrame, threshold: float = 0.6) -> list:
    """
    Détecte automatiquement les colonnes de dates

    Une colonne est considérée comme date si:
    - Son nom contient 'date', 'paie', 'pay', 'period', 'période'
    - OU si >= 60% de ses valeurs non-vides sont "datables"

    Args:
        df: DataFrame pandas
        threshold: Seuil de détection (0.6 = 60%)

    Returns:
        Liste des noms de colonnes détectées comme dates
    """
    date_columns = []

    # Patterns de noms de colonnes
    date_patterns = [
        "date",
        "paie",
        "pay",
        "period",
        "période",
        "datum",
        "fecha",
        "data",  # Support multilingue
    ]

    for col in df.columns:
        col_lower = str(col).lower().strip()

        # Test 1 : Nom contient un pattern
        if any(pattern in col_lower for pattern in date_patterns):
            date_columns.append(col)
            logger.info(f"Colonne détectée (nom): '{col}'")
            continue

        # Test 2 : Déjà typée datetime
        if is_already_datetime(df[col]):
            date_columns.append(col)
            logger.info(f"Colonne détectée (dtype datetime): '{col}'")
            continue

        # Test 3 : Heuristique (>= 60% valeurs datables)
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue

        # Tester si les valeurs ressemblent à des dates
        sample = non_null.head(min(100, len(non_null)))  # Échantillon max 100

        # Essayer conversion date
        test_dates = pd.to_datetime(sample, errors="coerce", dayfirst=True)
        valid_dates_pct = (test_dates.notna().sum() / len(sample)) * 100

        if valid_dates_pct >= (threshold * 100):
            date_columns.append(col)
            logger.info(
                f"Colonne détectée (heuristique {valid_dates_pct:.1f}% datables): '{col}'"
            )

    logger.info(f"Total colonnes date détectées: {len(date_columns)}")
    return date_columns
