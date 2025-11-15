# logic/metrics.py — chargement robuste & colonnes canoniques pour les audits
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

# Import DataRepository pour PostgreSQL
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.data_repo import DataRepository

# PostgreSQL: table source
SCHEMA = "payroll"
TABLE = "imported_payroll_master"

# === Candidats de colonnes (observés dans tes fichiers FR) ====================
COL_EMP_ID_CANDIDATES = [
    "Matricule",
    "No employé",
    "No employe",
    "Employé",
    "Employe",
    "ID",
    "Code employe",
]
COL_EMP_NAME_CANDIDATES = [
    "Nom et prénom",
    "Nom et prenom",
    "Nom",
    "Employé",
    "Employe",
]
COL_DATE_CANDIDATES = ["Date de paie", "Date", "Période", "Periode"]
COL_CATEGORY_CANDIDATES = [
    "Catégorie de paie",
    "Categorie de paie",
    "Catégorie",
    "Categorie",
]
COL_CODEPAIE_CANDIDATES = ["Code Paie", "code de paie", "Code de paie", "Code"]
COL_BUDGET_CANDIDATES = [
    "poste Budgetaire",
    "Poste Budgetaire",
    "Poste budgétaire",
    "poste budgétaire",
    "Poste budgetaire",
]
COL_AMOUNT_CANDIDATES = ["Montant", "montant", "Mnt", "Amount"]
COL_PARTEMP_CANDIDATES = [
    "Part employeur",
    "part employeur",
    "PartEmployeur",
    "Part employeur $",
]
COL_MNTCMB_CANDIDATES = ["Mnt/Cmb", "Mnt cmb", "MntCmb", "Mnt_Cmb"]


# === Helpers ==================================================================
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().lower()


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_map = {_norm(c): c for c in df.columns}
    for cand in candidates:
        k = _norm(cand)
        if k in cols_map:
            return cols_map[k]
    # tolérance "contient"
    for cand in candidates:
        pat = _norm(cand)
        for k, v in cols_map.items():
            if pat in k:
                return v
    return None


def _to_number(series_like) -> pd.Series:
    s = pd.Series(series_like)
    s = (
        s.astype(str)
        .str.replace("\u00a0", " ")
        .str.replace(" ", "")
        .str.replace(",", ".")
    )
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _is_all_upper(s: str) -> bool:
    if not isinstance(s, str):
        return False
    base = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    letters = re.sub(r"[^A-Za-z]+", "", base)
    if not letters:
        return False
    return base.upper() == base


# === Chargement/Canonisation ==================================================
def _load_df() -> pd.DataFrame:
    """Charge les données depuis PostgreSQL."""
    # Utiliser config_manager pour DSN centralisé
    from config.config_manager import get_dsn

    dsn = get_dsn()
    repo = DataRepository(dsn, min_size=1, max_size=2)
    try:
        rows = repo.run_query(f"SELECT * FROM {SCHEMA}.{TABLE}", fetch_all=True)

        # Récupérer les noms de colonnes
        with repo.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {SCHEMA}.{TABLE} LIMIT 0")
                columns = [desc[0] for desc in cur.description]

        df = pd.DataFrame(rows, columns=columns)
    finally:
        repo.close()

    if df.empty:
        return df

    # pick colonnes sources
    id_col = _pick_col(df, COL_EMP_ID_CANDIDATES)
    name_col = _pick_col(df, COL_EMP_NAME_CANDIDATES)
    date_col = _pick_col(df, COL_DATE_CANDIDATES)
    cat_col = _pick_col(df, COL_CATEGORY_CANDIDATES)
    code_col = _pick_col(df, COL_CODEPAIE_CANDIDATES)
    bud_col = _pick_col(df, COL_BUDGET_CANDIDATES)
    amt_col = _pick_col(df, COL_AMOUNT_CANDIDATES)
    part_col = _pick_col(df, COL_PARTEMP_CANDIDATES)
    mntcmb_col = _pick_col(df, COL_MNTCMB_CANDIDATES)

    # canoniques
    df["_EmpKey"] = (
        df[id_col].astype(str).str.strip() if id_col else df.index.astype(str)
    )
    df["_EmpName"] = df[name_col].astype(str).str.strip() if name_col else ""
    if date_col:
        df["_Date"] = pd.to_datetime(
            df[date_col], errors="coerce", utc=True
        ).dt.tz_convert(None)
    else:
        df["_Date"] = pd.NaT
    df["_Category"] = df[cat_col].astype(str).str.strip() if cat_col else ""
    df["_CodePaie"] = df[code_col].astype(str).str.strip() if code_col else ""
    df["_Budget"] = df[bud_col].astype(str).str.strip() if bud_col else ""
    df["_Amount"] = _to_number(df[amt_col]) if amt_col else 0.0
    df["_PartEmp"] = _to_number(df[part_col]) if part_col else 0.0
    df["_MntCmb"] = _to_number(df[mntcmb_col]) if mntcmb_col else 0.0

    # dérivées
    df["_IsMetaRow"] = df["_MntCmb"] == 0.0
    df["_IsInactive"] = df["_EmpName"].apply(_is_all_upper)
    df["_PayDate"] = df["_Date"].dt.strftime("%Y-%m-%d")  # Date de paie exacte
    df["_Period"] = df["_Date"].dt.strftime("%Y-%m")  # Compatibilité (mois)

    return df


# Petit résumé (aide au mode hors-ligne éventuel)
def summary() -> dict:
    df = _load_df()
    if df.empty:
        return {"rows": 0}
    rows = int(len(df))
    employees = int(df["_EmpKey"].nunique())
    net_total = float(df.loc[~df["_IsMetaRow"], "_Amount"].sum())
    neg_pct = float((df.groupby("_EmpKey")["_Amount"].sum() < -0.01).mean() * 100.0)
    return {
        "rows": rows,
        "employees": employees,
        "net_total": net_total,
        "neg_pct": neg_pct,
    }


def get_latest_pay_date() -> str | None:
    """
    Retourne la dernière date de paie disponible dans la DB (format YYYY-MM-DD).

    Returns:
        Date de paie au format YYYY-MM-DD ou None si aucune date trouvée
    """
    try:
        df = _load_df()
        if df.empty or "_Date" not in df.columns:
            return None
        dates = df["_Date"].dropna()
        if dates.empty:
            return None
        last_date = dates.max()
        return last_date.strftime("%Y-%m-%d")
    except Exception:
        return None


# Alias pour compatibilité
def get_latest_period() -> str | None:
    """Alias pour get_latest_pay_date (compatibilité)"""
    return get_latest_pay_date()


__all__ = [
    "_load_df",
    "_pick_col",
    "COL_EMP_ID_CANDIDATES",
    "COL_EMP_NAME_CANDIDATES",
    "COL_DATE_CANDIDATES",
    "COL_CATEGORY_CANDIDATES",
    "COL_CODEPAIE_CANDIDATES",
    "COL_BUDGET_CANDIDATES",
    "COL_AMOUNT_CANDIDATES",
    "COL_PARTEMP_CANDIDATES",
    "COL_MNTCMB_CANDIDATES",
]
