from datetime import date, datetime

import pandas as pd
from config.connection_standard import get_connection, run_select
from logic.formatting import _normalize_period, _parse_number_safe

CODES_SENSIBLES = ["401", "501", "701", "999"]


def run_basic_audit(period=None):
    try:
        df = _load_period_data(period)
        if df.empty:
            return {"findings": [], "anomalies_df": pd.DataFrame(), "kpis": {}}

        findings = []

        nets_negatifs_df = _detect_nets_negatifs(df)
        if not nets_negatifs_df.empty:
            findings.append(
                {
                    "rule": "nets_negatifs",
                    "count": len(nets_negatifs_df),
                    "detail": "Nets négatifs par employé",
                }
            )

        majuscules_df = _detect_majuscules(df)
        if not majuscules_df.empty:
            findings.append(
                {
                    "rule": "noms_majuscules",
                    "count": len(majuscules_df),
                    "detail": "Noms en MAJUSCULES",
                }
            )

        codes_sensibles_df = _detect_codes_sensibles(df)
        if not codes_sensibles_df.empty:
            findings.append(
                {
                    "rule": "codes_sensibles",
                    "count": len(codes_sensibles_df),
                    "detail": f"Codes sensibles : {', '.join(CODES_SENSIBLES)}",
                }
            )

        kpis = _compute_kpis(df)

        return {
            "findings": findings,
            "anomalies_df": (
                pd.concat(
                    [nets_negatifs_df, majuscules_df, codes_sensibles_df],
                    ignore_index=True,
                )
                if not nets_negatifs_df.empty
                else pd.DataFrame()
            ),
            "nets_negatifs_df": nets_negatifs_df,
            "majuscules_df": majuscules_df,
            "codes_sensibles_df": codes_sensibles_df,
            "kpis": kpis,
        }
    except Exception as e:
        return {
            "findings": [{"rule": "error", "count": 0, "detail": str(e)}],
            "kpis": {},
        }


def compare_periods(p1, p2):
    try:
        df1 = _load_period_data(p1)
        df2 = _load_period_data(p2)

        if df1.empty or df2.empty:
            return {"delta_net": 0, "pct": 0, "error": "Données manquantes"}

        montant_col = _find_column(df1, ["Montant", "montant", "Amount"])

        if not montant_col:
            return {"delta_net": 0, "pct": 0, "error": "Colonne montant non trouvée"}

        net1 = df1[montant_col].apply(_parse_number_safe).sum()
        net2 = df2[montant_col].apply(_parse_number_safe).sum()

        delta_net = net1 - net2
        pct = (delta_net / abs(net2) * 100) if net2 != 0 else 0

        code_col = _find_column(df1, ["Code de paie", "code_paie", "CodePaie", "Code"])
        delta_par_code = {}
        if code_col:
            g1 = df1.groupby(code_col)[montant_col].apply(
                lambda x: x.apply(_parse_number_safe).sum()
            )
            g2 = df2.groupby(code_col)[montant_col].apply(
                lambda x: x.apply(_parse_number_safe).sum()
            )
            delta_par_code = (g1 - g2).fillna(0).to_dict()

        poste_col = _find_column(
            df1, ["Poste budgétaire", "poste_budgetaire", "PosteBudgetaire", "Poste"]
        )
        delta_par_poste = {}
        if poste_col:
            g1 = df1.groupby(poste_col)[montant_col].apply(
                lambda x: x.apply(_parse_number_safe).sum()
            )
            g2 = df2.groupby(poste_col)[montant_col].apply(
                lambda x: x.apply(_parse_number_safe).sum()
            )
            delta_par_poste = (g1 - g2).fillna(0).to_dict()

        return {
            "delta_net": float(delta_net),
            "pct": float(pct),
            "delta_par_code": delta_par_code,
            "delta_par_poste": delta_par_poste,
            "top_up": (
                sorted(delta_par_code.items(), key=lambda x: x[1], reverse=True)[:5]
                if delta_par_code
                else []
            ),
            "top_down": (
                sorted(delta_par_code.items(), key=lambda x: x[1])[:5]
                if delta_par_code
                else []
            ),
        }
    except Exception as e:
        return {"delta_net": 0, "pct": 0, "error": str(e)}


def _load_period_data(pay_date):
    """
    Charge les données de date de paie depuis PostgreSQL.

    Args:
        pay_date: Date de paie exacte au format YYYY-MM-DD (ex: '2025-08-28')
    """
    try:
        if pay_date:
            # Normaliser la date
            if isinstance(pay_date, (date, datetime)):
                pay_date_str = pay_date.strftime("%Y-%m-%d")
            else:
                # Essayer de parser la date
                normalized = _normalize_period(pay_date)
                pay_date_str = (
                    normalized.strftime("%Y-%m-%d") if normalized else str(pay_date)
                )

            query = """
                SELECT *
                FROM payroll.imported_payroll_master 
                WHERE "date de paie " = %(pay_date)s::date
            """
            rows = run_select(query, {"pay_date": pay_date_str})
        else:
            query = "SELECT * FROM payroll.imported_payroll_master"
            rows = run_select(query)

        # Convertir en DataFrame
        if not rows:
            return pd.DataFrame()

        # Récupérer les noms de colonnes
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM payroll.imported_payroll_master LIMIT 0")
                columns = [desc[0] for desc in cur.description]
        return pd.DataFrame(rows, columns=columns)
    except Exception as e:
        print(f"Erreur chargement données: {e}")
        return pd.DataFrame()


def _detect_nets_negatifs(df):
    montant_col = _find_column(df, ["Montant", "montant", "Amount"])
    emp_col = _find_column(
        df, ["Matricule", "matricule", "EmployeeID", "employee_id", "Nom et prénom"]
    )

    if not montant_col or not emp_col:
        return pd.DataFrame()

    df_copy = df.copy()
    df_copy["_montant_num"] = df_copy[montant_col].apply(_parse_number_safe)

    nets = df_copy.groupby(emp_col)["_montant_num"].sum()
    negs = nets[nets < -0.01]

    if negs.empty:
        return pd.DataFrame()

    result = pd.DataFrame(
        {"Employé": negs.index, "Net": negs.values, "Type": "Net négatif"}
    )

    return result


def _detect_majuscules(df):
    name_col = _find_column(
        df, ["Nom et prénom", "Nom", "nom", "employee_name", "EmployeeName"]
    )

    if not name_col:
        return pd.DataFrame()

    df_copy = df.copy()
    df_copy["_is_upper"] = df_copy[name_col].apply(
        lambda x: str(x).isupper() if pd.notna(x) else False
    )

    upper_df = df_copy[df_copy["_is_upper"]][[name_col]].drop_duplicates()

    if upper_df.empty:
        return pd.DataFrame()

    upper_df = upper_df.rename(columns={name_col: "Nom"})
    upper_df["Type"] = "Nom en MAJUSCULES"

    return upper_df


def _detect_codes_sensibles(df):
    code_col = _find_column(df, ["Code de paie", "code_paie", "CodePaie", "Code"])

    if not code_col:
        return pd.DataFrame()

    df_copy = df.copy()
    df_copy["_is_sensible"] = df_copy[code_col].astype(str).isin(CODES_SENSIBLES)

    sens_df = df_copy[df_copy["_is_sensible"]][[code_col]].drop_duplicates()

    if sens_df.empty:
        return pd.DataFrame()

    sens_df = sens_df.rename(columns={code_col: "Code"})
    sens_df["Type"] = "Code sensible"

    return sens_df


def _compute_kpis(df):
    montant_col = _find_column(df, ["Montant", "montant", "Amount"])
    emp_col = _find_column(df, ["Matricule", "matricule", "EmployeeID", "employee_id"])

    if not montant_col:
        return {}

    df_copy = df.copy()
    df_copy["_montant_num"] = df_copy[montant_col].apply(_parse_number_safe)

    net_total = float(df_copy["_montant_num"].sum())
    deductions = float(df_copy[df_copy["_montant_num"] < 0]["_montant_num"].sum())
    brut_total = net_total + abs(deductions)

    nb_employes = int(df_copy[emp_col].nunique()) if emp_col else len(df_copy)
    net_moyen = net_total / nb_employes if nb_employes > 0 else 0

    return {
        "net_total": net_total,
        "brut_total": brut_total,
        "deductions_total": deductions,
        "nb_employes": nb_employes,
        "net_moyen": net_moyen,
    }


def _find_column(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
        for col in df.columns:
            if col.lower() == c.lower():
                return col
    return None
