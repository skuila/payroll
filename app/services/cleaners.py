import re
import pandas as pd
from typing import Set

# Valeurs "marqueurs" de blocs (peuvent être revues plus tard)
_CATEGORY_LABELS: Set[str] = {
    "gains",
    "syndicats",
    "assurances",
    "déductions légales",
    "deductions legales",  # tolère sans accents
}


def _strip_accents_lower(s: str) -> str:
    try:
        import unicodedata

        s = "".join(
            c
            for c in unicodedata.normalize("NFKD", str(s))
            if not unicodedata.combining(c)
        )
    except Exception:
        s = str(s)
    return s.strip().lower()


def _is_digits(s: str) -> bool:
    return bool(re.fullmatch(r"\d+", str(s).strip()))


def clean_payroll_excel_df(
    df: pd.DataFrame, remove_category_markers: bool = True
) -> pd.DataFrame:
    """
    Nettoie un DataFrame issu d'un export paie FR-CA.

    - Normalise les en-têtes (strip espaces) en conservant les libellés FR attendus par les tests:
      'employé', 'matricule', 'date de paie', 'montant', 'part employeur', 'code de paie', etc.
    - (Optionnel) Retire les lignes 'marqueurs' de catégorie (gains/syndicats/assurances/...)
    - Filtre les lignes dont 'matricule' n'est pas entièrement numérique
    - Convertit 'montant' et 'part employeur' en nombres et expose en cents:
      'amount_employee_cents', 'amount_employer_cents'
    """
    if df is None or df.empty:
        return df

    # 1) Normaliser les en-têtes (strip)
    dfx = df.copy()
    dfx.columns = [str(c).strip() for c in dfx.columns]

    # 2) Harmoniser colonnes vers les nouveaux noms canoniques (avec tolérance anciens)
    # Mapping explicite anciens -> nouveaux noms
    RENAME_TO_CANON = {
        "Categorie d'emploi": "catégorie d'emploi",
        "code emploie": "code emploi",
        "categorie de paie": "catégorie de paie",
        "desc code de paie": "description du code de paie",
        "poste Budgetaire": "poste budgétaire",
        "desc poste Budgetaire": "description du poste budgétaire",
        "Mnt/Cmb": "montant combiné",
    }

    rename_pairs = {}
    for col in list(dfx.columns):
        # D'abord appliquer les mappings explicites anciens->nouveaux
        if col in RENAME_TO_CANON:
            rename_pairs[col] = RENAME_TO_CANON[col]
            continue

        # Puis harmoniser via normalisation accents
        norm = _strip_accents_lower(col)
        if norm in {"employe"}:
            rename_pairs[col] = "employé"
        elif norm in {"matricule"}:
            rename_pairs[col] = "matricule"
        elif norm in {"date de paie", "date paie", "date"}:
            rename_pairs[col] = "date de paie"
        elif norm in {"montant", "mnt"}:
            rename_pairs[col] = "montant"
        elif norm in {"part employeur", "part patronale", "employeur"}:
            rename_pairs[col] = "part employeur"
        elif norm in {"code de paie", "code paie", "code"}:
            rename_pairs[col] = "code de paie"
        elif norm in {
            "description du code de paie",
            "description code paie",
            "libelle code",
        }:
            rename_pairs[col] = "description du code de paie"
        elif norm in {"poste budgetaire", "poste"}:
            rename_pairs[col] = "poste budgétaire"
        elif norm in {
            "description du poste budgetaire",
            "description poste",
            "libelle poste",
        }:
            rename_pairs[col] = "description du poste budgétaire"
    if rename_pairs:
        dfx.rename(columns=rename_pairs, inplace=True)

    # 3) Vérifier les colonnes minimales
    required = ["employé", "matricule", "montant"]
    for r in required:
        if r not in dfx.columns:
            # si colonnes avec espaces de fin dans la source, elles sont déjà "strip" ci-dessus
            dfx[r] = dfx.get(r, pd.Series([None] * len(dfx)))

    # 4) (Optionnel) Retirer les lignes "marqueurs" (catégories)
    if remove_category_markers and "employé" in dfx.columns:
        mask_cat = (
            dfx["employé"].astype(str).map(_strip_accents_lower).isin(_CATEGORY_LABELS)
        )
        dfx = dfx[~mask_cat].copy()

    # 5) Ne garder que les matricules numériques
    if "matricule" in dfx.columns:
        mask_digits = dfx["matricule"].astype(str).apply(_is_digits)
        dfx = dfx[mask_digits].copy()

    # 6) Convertir montants
    for col in ["montant", "part employeur"]:
        if col in dfx.columns:
            dfx[col] = pd.to_numeric(dfx[col], errors="coerce").fillna(0.0)

    # 7) Date de paie (si présente)
    if "date de paie" in dfx.columns:
        dfx["date de paie"] = pd.to_datetime(
            dfx["date de paie"], errors="coerce"
        ).dt.date

    # 8) Exposer en cents (entiers tolérant NA)
    if "montant" in dfx.columns:
        dfx["amount_employee_cents"] = (dfx["montant"] * 100).round().astype("Int64")
    else:
        dfx["amount_employee_cents"] = pd.Series([pd.NA] * len(dfx), dtype="Int64")

    if "part employeur" in dfx.columns:
        dfx["amount_employer_cents"] = (
            (dfx["part employeur"] * 100).round().astype("Int64")
        )
    else:
        dfx["amount_employer_cents"] = pd.Series([pd.NA] * len(dfx), dtype="Int64")

    return dfx.reset_index(drop=True)
