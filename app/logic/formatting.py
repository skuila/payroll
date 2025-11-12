import re
import pandas as pd
from datetime import datetime, date


def _parse_number_safe(value):
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if pd.isna(value):
            return 0.0
        s = str(value).replace("\u202f", " ").replace("\xa0", " ").replace(" ", "")
        s = s.replace(",", ".")
        s = re.sub(r"[^\d.-]", "", s)
        return float(s) if s else 0.0
    except Exception as _exc:
        return 0.0


def _fmt_money(value):
    try:
        formatted = f"{abs(value):,.2f}".replace(",", " ")
        sign = "" if value >= 0 else "-"
        return f"{sign}{formatted} $"
    except Exception as _exc:
        return f"{value} $"


def _normalize_period(date_like):
    if isinstance(date_like, (datetime, date)):
        return date_like

    if isinstance(date_like, str):
        for fmt in ["%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                return datetime.strptime(date_like, fmt).date()
            except Exception as _exc:
                pass

    return datetime.today().date()
