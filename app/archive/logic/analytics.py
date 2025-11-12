# logic/analytics.py — Calcul des KPIs, anomalies et comparaisons pour le bilan post-import
from __future__ import annotations
import pandas as pd
from typing import Optional
from .metrics import _load_df

CODES_SENSIBLES = ["401", "501", "701"]  # Codes à surveiller (exemples)


def compute_period_summary(provider, file_path: Optional[str] = None) -> dict:
    """
    Calcule un résumé complet de la dernière période importée.

    Args:
        provider: PayrollDataProvider
        file_path: Chemin du fichier source (optionnel)

    Returns:
        dict avec clés: period, source_path, kpis, anomalies, comparaison
    """
    try:
        df_all = _load_df()
        if df_all.empty:
            return {}

        # Dernière période
        if "_Date" not in df_all.columns or df_all["_Date"].isna().all():
            period_str = "(tout)"
            df_period = df_all.copy()
        else:
            dates = df_all["_Date"].dropna()
            if dates.empty:
                period_str = "(tout)"
                df_period = df_all.copy()
            else:
                last_date = dates.max()
                period_str = last_date.strftime("%Y-%m")
                # Filtrer sur le mois complet
                df_period = df_all[
                    (df_all["_Date"].dt.year == last_date.year)
                    & (df_all["_Date"].dt.month == last_date.month)
                ].copy()

        if df_period.empty:
            return {}

        # KPIs
        kpis = _compute_kpis(df_period)

        # Anomalies
        anomalies = _detect_all_anomalies(df_period, df_all)

        # Comparaison avec période précédente
        comparaison = _compare_with_previous_period(df_all, period_str)

        return {
            "period": period_str,
            "source_path": file_path or "(inconnu)",
            "kpis": kpis,
            "anomalies": anomalies,
            "comparaison": comparaison,
        }
    except Exception as e:
        # En cas d'erreur, retourner un dict minimal
        return {
            "period": "(erreur)",
            "source_path": file_path or "(inconnu)",
            "kpis": {},
            "anomalies": {},
            "comparaison": {"exists": False},
            "error": str(e),
        }


def _compute_kpis(df: pd.DataFrame) -> dict:
    """Calcule les KPIs de base."""
    # Ne prendre que les transactions (hors meta-rows)
    df_tx = df[~df["_IsMetaRow"]].copy() if "_IsMetaRow" in df.columns else df.copy()

    if df_tx.empty:
        return {
            "net_total": 0.0,
            "brut_total": 0.0,
            "deductions_total": 0.0,
            "nb_employes": 0,
            "net_moyen": 0.0,
            "net_median": 0.0,
        }

    # Montants
    amounts = (
        df_tx["_Amount"]
        if "_Amount" in df_tx.columns
        else pd.Series([0.0] * len(df_tx))
    )
    net_total = float(amounts.sum())

    # Déductions = somme des montants négatifs
    deductions_total = float(amounts[amounts < 0].sum())

    # Brut = net + abs(déductions) (approximation)
    brut_total = net_total + abs(deductions_total)

    # Nombre d'employés uniques
    nb_employes = int(
        df_tx["_EmpKey"].nunique() if "_EmpKey" in df_tx.columns else len(df_tx)
    )

    # Net par employé
    if nb_employes > 0 and "_EmpKey" in df_tx.columns:
        net_par_emp = df_tx.groupby("_EmpKey")["_Amount"].sum()
        net_moyen = float(net_par_emp.mean())
        net_median = float(net_par_emp.median())
    else:
        net_moyen = 0.0
        net_median = 0.0

    return {
        "net_total": net_total,
        "brut_total": brut_total,
        "deductions_total": deductions_total,
        "nb_employes": nb_employes,
        "net_moyen": net_moyen,
        "net_median": net_median,
    }


def _detect_all_anomalies(df_period: pd.DataFrame, df_all: pd.DataFrame) -> dict:
    """Détecte toutes les anomalies de la période."""
    anomalies = {}

    # 1. Nets négatifs
    anomalies["nets_negatifs"] = _detect_nets_negatifs(df_period)

    # 2. Inactifs avec gains (noms en MAJUSCULES)
    anomalies["inactifs_avec_gains"] = _detect_inactifs_avec_gains(df_period)

    # 3. Codes sensibles
    anomalies["codes_sensibles"] = _detect_codes_sensibles(df_period)

    # 4. Nouveaux codes de paie
    anomalies["nouveaux_codes"] = _detect_nouveaux_codes(df_period, df_all)

    # 5. Changements de poste budgétaire
    anomalies["changements_poste"] = _detect_changements_poste(df_period, df_all)

    return anomalies


def _detect_nets_negatifs(df: pd.DataFrame) -> dict:
    """Détecte les employés avec net négatif."""
    if df.empty or "_EmpKey" not in df.columns or "_Amount" not in df.columns:
        return {"count": 0, "matricules": []}

    df_tx = df[~df["_IsMetaRow"]].copy() if "_IsMetaRow" in df.columns else df.copy()
    net_emp = df_tx.groupby("_EmpKey")["_Amount"].sum()
    neg = net_emp[net_emp < -0.01]

    # Anonymisation: E-0001, E-0002, etc.
    matricules_anon = [f"E-{i:04d}" for i in range(1, len(neg) + 1)]

    return {"count": len(neg), "matricules": matricules_anon}


def _detect_inactifs_avec_gains(df: pd.DataFrame) -> dict:
    """Détecte les employés inactifs (nom MAJUSCULES) avec gains positifs."""
    if df.empty or "_IsInactive" not in df.columns or "_EmpName" not in df.columns:
        return {"count": 0, "noms": []}

    df_tx = df[~df["_IsMetaRow"]].copy() if "_IsMetaRow" in df.columns else df.copy()

    # Inactifs avec gains
    mask_inactif = df_tx["_IsInactive"]
    mask_gains = (df_tx["_Category"].str.lower() == "gains") & (df_tx["_Amount"] > 0)
    inactifs = df_tx[mask_inactif & mask_gains]["_EmpName"].unique()

    # Anonymisation
    noms_anon = [f"EMPLOYE-{i:02d}" for i in range(1, len(inactifs) + 1)]

    return {"count": len(inactifs), "noms": noms_anon}


def _detect_codes_sensibles(df: pd.DataFrame) -> dict:
    """Détecte les codes de paie sensibles."""
    if df.empty or "_CodePaie" not in df.columns:
        return {"count": 0, "codes": []}

    df_tx = df[~df["_IsMetaRow"]].copy() if "_IsMetaRow" in df.columns else df.copy()
    codes = df_tx["_CodePaie"].astype(str).str.strip()
    sensibles = codes[codes.isin(CODES_SENSIBLES)].unique().tolist()

    return {"count": len(sensibles), "codes": sensibles}


def _detect_nouveaux_codes(df_period: pd.DataFrame, df_all: pd.DataFrame) -> dict:
    """Détecte les nouveaux codes de paie par rapport aux périodes précédentes."""
    if df_period.empty or "_CodePaie" not in df_period.columns:
        return {"count": 0, "codes": []}

    # Codes de la période actuelle
    codes_current = set(df_period["_CodePaie"].astype(str).str.strip().unique())

    # Codes des périodes précédentes
    if "_Period" in df_all.columns and "_Period" in df_period.columns:
        period_current = df_period["_Period"].iloc[0] if not df_period.empty else None
        df_previous = df_all[df_all["_Period"] != period_current]
        if not df_previous.empty and "_CodePaie" in df_previous.columns:
            codes_previous = set(
                df_previous["_CodePaie"].astype(str).str.strip().unique()
            )
            nouveaux = codes_current - codes_previous
            nouveaux_list = sorted([c for c in nouveaux if c and c != "nan"])
            return {
                "count": len(nouveaux_list),
                "codes": nouveaux_list[:10],  # Limiter à 10 pour l'affichage
            }

    return {"count": 0, "codes": []}


def _detect_changements_poste(df_period: pd.DataFrame, df_all: pd.DataFrame) -> dict:
    """Détecte les employés ayant changé de poste budgétaire."""
    if (
        df_period.empty
        or "_EmpKey" not in df_period.columns
        or "_Budget" not in df_period.columns
    ):
        return {"count": 0, "matricules": []}

    # Postes de la période actuelle par employé
    postes_current = df_period.groupby("_EmpKey")["_Budget"].first()

    # Postes des périodes précédentes
    if "_Period" in df_all.columns and "_Period" in df_period.columns:
        period_current = df_period["_Period"].iloc[0] if not df_period.empty else None
        df_previous = df_all[df_all["_Period"] != period_current]
        if (
            not df_previous.empty
            and "_EmpKey" in df_previous.columns
            and "_Budget" in df_previous.columns
        ):
            postes_previous = df_previous.groupby("_EmpKey")["_Budget"].last()

            # Comparer
            changements = []
            for emp in postes_current.index:
                if emp in postes_previous.index:
                    if postes_current[emp] != postes_previous[emp]:
                        changements.append(emp)

            # Anonymisation
            matricules_anon = [f"E-{i:04d}" for i in range(1, len(changements) + 1)]

            return {"count": len(changements), "matricules": matricules_anon}

    return {"count": 0, "matricules": []}


def _compare_with_previous_period(df_all: pd.DataFrame, period_current: str) -> dict:
    """Compare la période actuelle avec la précédente."""
    try:
        if (
            df_all.empty
            or "_Period" not in df_all.columns
            or period_current == "(tout)"
        ):
            return {"exists": False}

        # Obtenir toutes les périodes
        periods = sorted(df_all["_Period"].dropna().unique().tolist())
        if period_current not in periods or len(periods) < 2:
            return {"exists": False}

        idx = periods.index(period_current)
        if idx == 0:  # Pas de période précédente
            return {"exists": False}

        period_precedente = periods[idx - 1]

        # DataFrames des deux périodes
        df_current = df_all[df_all["_Period"] == period_current]
        df_previous = df_all[df_all["_Period"] == period_precedente]

        # KPIs des deux périodes
        kpis_current = _compute_kpis(df_current)
        kpis_previous = _compute_kpis(df_previous)

        # Deltas
        delta_net = kpis_current["net_total"] - kpis_previous["net_total"]
        delta_deductions = (
            kpis_current["deductions_total"] - kpis_previous["deductions_total"]
        )
        delta_effectif = kpis_current["nb_employes"] - kpis_previous["nb_employes"]

        # Tendance
        if abs(delta_net) < 100:  # Seuil de stabilité
            tendance = "stable"
        elif delta_net > 0:
            tendance = "hausse"
        else:
            tendance = "baisse"

        # Pourcentage de variation
        pct_variation = 0.0
        if kpis_previous["net_total"] != 0:
            pct_variation = (delta_net / abs(kpis_previous["net_total"])) * 100.0

        return {
            "exists": True,
            "period_precedente": period_precedente,
            "delta_net": delta_net,
            "delta_deductions": delta_deductions,
            "delta_effectif": delta_effectif,
            "tendance": tendance,
            "pct_variation": pct_variation,
        }
    except Exception:
        return {"exists": False}


def get_latest_period_from_db() -> Optional[str]:
    """Retourne la dernière période disponible dans la DB."""
    try:
        df = _load_df()
        if df.empty or "_Date" not in df.columns:
            return None
        dates = df["_Date"].dropna()
        if dates.empty:
            return None
        last_date = dates.max()
        return last_date.strftime("%Y-%m")
    except Exception:
        return None
