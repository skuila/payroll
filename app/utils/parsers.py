"""Utilities for parsing amounts and excel dates.
Extracted from payroll_app_qt_Version4.py to make parsing logic testable.
"""

from datetime import datetime, timedelta
from decimal import Decimal


def parse_amount_neutral(value, context: str = ""):
    """
    Parseur neutre pour les montants avec virgule et parenthèses.
    Supporte formats comme 1 234,56 ou (1 234,56) pour négatif.
    Retourne float ou None si non parseable.
    """
    import re

    if value is None:
        return None

    # Si déjà un nombre
    if isinstance(value, (int, float, Decimal)):
        try:
            return float(value)
        except Exception:
            return None

    raw_value = str(value).strip()
    if raw_value == "":
        return None

    is_negative = raw_value.startswith("(") and raw_value.endswith(")")
    if is_negative:
        raw_value = raw_value[1:-1].strip()

    cleaned = raw_value.replace("\u202F", "").replace("\u00A0", "")
    cleaned = cleaned.replace("$", "").replace("CA", "").replace("CAD", "")
    cleaned = re.sub(r"\s+", "", cleaned)

    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "")
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        result = float(cleaned)
        if is_negative:
            result = -result
        return result
    except ValueError:
        return None


def parse_excel_date_robust(date_value, row_idx=None):
    """Parse robuste des dates Excel.

    Retourne (iso_date_str or None, error_message or None)
    """
    import re

    # None / empty
    if date_value is None or (isinstance(date_value, str) and date_value.strip() == ""):
        return None, "Valeur vide"

    # datetime-like
    if isinstance(date_value, datetime):
        year = date_value.year
        if 2000 <= year <= 2050:
            return date_value.strftime("%Y-%m-%d"), None
        return None, f"Année hors période: {year}"

    if isinstance(date_value, str):
        date_str = date_value.strip()
        # ISO
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_str)
        if m:
            y = int(m.group(1))
            if 2000 <= y <= 2050:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", None
            return None, f"Année ISO hors période: {y}"

        # EU format
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", date_str)
        if m:
            d, mo, y = m.groups()
            y_i = int(y)
            mo_i = int(mo)
            d_i = int(d)
            if not (1 <= mo_i <= 12 and 1 <= d_i <= 31):
                return None, "Date invalide"
            if 2000 <= y_i <= 2050:
                return f"{y}-{mo.zfill(2)}-{d.zfill(2)}", None
            return None, f"Année hors période: {y_i}"

        # Last resort: try to parse with common separators
        try:
            from dateutil import parser as _p

            dt = _p.parse(date_str, dayfirst=True)
            if 2000 <= dt.year <= 2050:
                return dt.strftime("%Y-%m-%d"), None
            return None, f"Pandas/dateutil parse → {dt.year}"
        except Exception:
            return None, f"Format texte non reconnu: '{date_str}'"

    # Numeric (Excel serial)
    if isinstance(date_value, (int, float)):
        try:
            # Excel serial realistic for 2000-2050: 36526 - 55154
            if 36526 <= date_value <= 55154:
                days = int(date_value)
                if days > 60:
                    days -= 1
                base = datetime(1899, 12, 30)
                date_dt = base + timedelta(days=days)
                if 2000 <= date_dt.year <= 2050:
                    return date_dt.strftime("%Y-%m-%d"), None
                return None, f"Serial → {date_dt.year} hors plage"
            return None, f"Nombre {date_value} n'est pas un serial Excel valide"
        except Exception as e:
            return None, f"Erreur conversion serial: {e}"

    return None, f"Type non géré: {type(date_value).__name__}"
