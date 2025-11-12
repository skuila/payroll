# ui/data_provider.py — Provider unifié (API V2 + compat V1) avec détection tolérante des colonnes
# VERSION POSTGRESQL (DataRepository + psycopg3)
from __future__ import annotations
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_dt

# Import DataRepository pour PostgreSQL
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.data_repo import DataRepository


@dataclass
class KPI:
    masse: str = "--"
    employes: str = "--"
    deductions: str = "--"
    net: str = "--"


def _money(v: float) -> str:
    try:
        return f"{v:,.2f}".replace(",", " ")
    except Exception:
        return "--"


def _ensure_datetime(s: pd.Series) -> pd.Series:
    if s is None:
        return s
    if is_dt(s):
        return s
    try:
        return pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed")
    except Exception:
        return pd.to_datetime(pd.Series([], dtype="datetime64[ns]"))


class PayrollDataProvider:
    # PostgreSQL: table fixe (plus de candidats multiples)
    _PG_TABLE = "payroll.imported_payroll_master"
    _DATE_CANDIDATES = [
        "DatePaie",
        "date_paie",
        "Date",
        "date",
        "DateDePaie",
        "mois",
        "Period",
        "MoisPaie",
        "Mois",
        "date de paie ",
    ]
    _AMOUNT_CANDIDATES = [
        "MontantCorrigé",
        "Montant",
        "Amount",
        "Net",
        "MontantBrut",
        "SalaireNet",
        "Valeur",
        "montant ",
    ]
    _EMP_CANDIDATES = [
        "Matricule",
        "EmployeeID",
        "EmployeID",
        "NoEmploye",
        "No_Employe",
        "NomPrenom",
        "Nom",
        "Employee",
        "matricule ",
    ]
    _CAT_CANDIDATES = [
        "Categorie",
        "TypePaie",
        "CodePaie",
        "PosteBudgétaire",
        "PosteBudgetaire",
        "Code",
        "Libelle",
        "Description",
        "categorie de paie ",
    ]

    def __init__(self, dsn: Optional[str] = None):
        """Initialise le provider avec DSN PostgreSQL."""
        # Utiliser config_manager pour DSN centralisé
        from config.config_manager import get_dsn

        self.dsn = get_dsn()
        self._last: Optional[Dict[str, Any]] = None
        self._last_df: Optional[pd.DataFrame] = None
        self._last_df_selected: Optional[pd.DataFrame] = None
        self._last_period: Optional[str] = None
        self._last_columns: Dict[str, Optional[str]] = {}

    # --- DB helpers (PostgreSQL) ---
    def _get_repo(self) -> DataRepository:
        """Retourne une instance DataRepository."""
        return DataRepository(self.dsn, min_size=1, max_size=3)

    def _read_all(self) -> pd.DataFrame:
        """Charge toutes les données depuis PostgreSQL."""
        repo = self._get_repo()
        try:
            # Lire depuis la table PostgreSQL fixe
            rows = repo.run_query(f"SELECT * FROM {self._PG_TABLE}", fetch_all=True)

            if not rows:
                return pd.DataFrame()

            # Récupérer les noms de colonnes depuis cursor.description
            with repo.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT * FROM {self._PG_TABLE} LIMIT 0")
                    columns = [desc[0] for desc in cur.description]

            return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            print(f"Erreur lecture PostgreSQL: {e}")
            return pd.DataFrame()
        finally:
            repo.close()

    def _detect_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        cols = set(df.columns.astype(str))
        for c in candidates:
            if c in cols:
                return c
            for col in cols:
                if col.lower() == c.lower():
                    return col
        return None

    def _build_periods(
        self, df: pd.DataFrame, date_col: Optional[str]
    ) -> Tuple[pd.DataFrame, List[str]]:
        if date_col and date_col in df.columns:
            s = _ensure_datetime(df[date_col])
            periods = s.dt.to_period("M").astype(str).fillna("(n/a)")
            df = df.copy()
            df["__period"] = periods
            order = sorted([p for p in periods.dropna().unique() if isinstance(p, str)])
            if not order:
                order = ["(tout)"]
            return df, order
        else:
            df = df.copy()
            df["__period"] = "(tout)"
            return df, ["(tout)"]

    def _compute_kpis(
        self, df: pd.DataFrame, amount_col: Optional[str], emp_col: Optional[str]
    ) -> KPI:
        if df is None or df.empty or amount_col not in df.columns:
            emp_count = (
                df[emp_col].nunique()
                if (df is not None and emp_col in df.columns)
                else 0
            )
            return KPI(masse="--", employes=str(emp_count), deductions="--", net="--")
        amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0)
        total = float(amounts.sum())
        neg = float(amounts[amounts < 0].sum())
        emp_count = df[emp_col].nunique() if (emp_col in df.columns) else df.shape[0]
        return KPI(
            masse=_money(total if total >= 0 else -total),
            employes=str(int(emp_count)),
            deductions=_money(neg if neg != 0 else 0.0),
            net=_money(total),
        )

    def _distribution(
        self,
        df: pd.DataFrame,
        cat_col: Optional[str],
        amount_col: Optional[str],
        topn: int = 8,
    ):
        if (
            df is None
            or df.empty
            or cat_col not in df.columns
            or amount_col not in df.columns
        ):
            return [], []
        g = (
            df.groupby(cat_col, dropna=False)[amount_col]
            .apply(lambda s: pd.to_numeric(s, errors="coerce").fillna(0.0).sum())
            .sort_values(ascending=False)
        )
        g = g.head(topn)
        labels = [str(k) for k in g.index.tolist()]
        values = [float(v) for v in g.values.tolist()]
        return labels, values

    # --- API V2 ---
    def load(self, period: Optional[str] = None) -> Dict[str, Any]:
        df_all = self._read_all()
        if df_all is None:
            df_all = pd.DataFrame()

        date_col = self._detect_column(df_all, self._DATE_CANDIDATES)
        amount_col = self._detect_column(df_all, self._AMOUNT_CANDIDATES)
        emp_col = self._detect_column(df_all, self._EMP_CANDIDATES)
        cat_col = self._detect_column(df_all, self._CAT_CANDIDATES)

        df_all, periods = self._build_periods(df_all, date_col)
        selected = period or (periods[-1] if periods else "(tout)")
        df_sel = (
            df_all[df_all["__period"] == selected].copy()
            if "__period" in df_all.columns
            else df_all.copy()
        )

        kpi = self._compute_kpis(df_sel, amount_col, emp_col)
        bar_labels, bar_values = self._distribution(df_sel, cat_col, amount_col, topn=8)
        if cat_col and cat_col in df_sel.columns:
            pie_labels, pie_values = bar_labels[:6], bar_values[:6]
        else:
            if amount_col and amount_col in df_sel.columns:
                amounts = pd.to_numeric(df_sel[amount_col], errors="coerce").fillna(0.0)
                pos = float(amounts[amounts >= 0].sum())
                neg = float(amounts[amounts < 0].sum())
                pie_labels, pie_values = ["Positif", "Négatif"], [pos, abs(neg)]
            else:
                pie_labels, pie_values = [], []

        result = {
            "kpis": {
                "masse": kpi.masse,
                "employes": kpi.employes,
                "deductions": kpi.deductions,
                "net": kpi.net,
            },
            "bar": {"labels": bar_labels, "values": bar_values},
            "pie": {"labels": pie_labels, "values": pie_values},
            "table": df_sel.reset_index(drop=True),
            "periods": periods,
            "selected_period": selected,
        }

        self._last = result
        self._last_df = df_all
        self._last_df_selected = df_sel
        self._last_period = selected
        self._last_columns = {
            "date": date_col,
            "amount": amount_col,
            "employee": emp_col,
            "category": cat_col,
        }
        return result

    def get_dashboard_data(self, period: Optional[str] = None) -> Dict[str, Any]:
        """
        Charge les données et les formate pour le dashboard.
        Retourne un dict avec:
          - kpis: liste de dict [{id, title, value, delta, trend}, ...]
          - periods: liste des périodes disponibles
          - selected_period: période sélectionnée
        """
        data = self.load(period=period)

        if not data:
            return {"kpis": [], "periods": [], "selected_period": "(tout)"}

        # Transformer les KPIs en format liste pour le dashboard
        kpis_dict = data.get("kpis", {})
        kpis_list = [
            {
                "id": "net",
                "title": "Net",
                "value": float(
                    kpis_dict.get("net", "0")
                    .replace("\u202f", "")
                    .replace(" ", "")
                    .replace("$", "")
                    or 0
                ),
                "delta": 0.0,  # TODO: calculer delta avec période précédente
                "trend": "up",
            },
            {
                "id": "masse",
                "title": "Masse salariale",
                "value": float(
                    kpis_dict.get("masse", "0")
                    .replace("\u202f", "")
                    .replace(" ", "")
                    .replace("$", "")
                    or 0
                ),
                "delta": 0.0,
                "trend": "up",
            },
            {
                "id": "employes",
                "title": "Employés",
                "value": int(kpis_dict.get("employes", "0")),
                "delta": 0.0,
                "trend": "up",
            },
            {
                "id": "deductions",
                "title": "Déductions",
                "value": float(
                    kpis_dict.get("deductions", "0")
                    .replace("\u202f", "")
                    .replace(" ", "")
                    .replace("$", "")
                    or 0
                ),
                "delta": 0.0,
                "trend": "down",
            },
        ]

        return {
            "kpis": kpis_list,
            "periods": data.get("periods", []),
            "selected_period": data.get("selected_period", "(tout)"),
        }

    # --- API V1 (compat) ---
    def current_period_dataframe(self, period: Optional[str] = None) -> pd.DataFrame:
        if self._last_df_selected is not None and (
            period is None or period == self._last_period
        ):
            return self._last_df_selected
        self.load(period=period)
        return (
            self._last_df_selected
            if self._last_df_selected is not None
            else pd.DataFrame()
        )

    def kpi_values(self, df: Optional[pd.DataFrame] = None) -> Dict[str, str]:
        if df is None and self._last and "kpis" in self._last:
            return dict(self._last["kpis"])
        if df is None:
            df = self.current_period_dataframe()
        amount_col = self._last_columns.get("amount") if self._last_columns else None
        emp_col = self._last_columns.get("employee") if self._last_columns else None
        kpi = self._compute_kpis(df, amount_col, emp_col)
        return {
            "masse": kpi.masse,
            "employes": kpi.employes,
            "deductions": kpi.deductions,
            "net": kpi.net,
        }

    def chart_distribution(self, df: Optional[pd.DataFrame] = None):
        if self._last and "bar" in self._last and self._last["bar"]["labels"]:
            return self._last["bar"]["labels"], self._last["bar"]["values"]
        if df is None:
            df = self.current_period_dataframe()
        amount_col = self._last_columns.get("amount") if self._last_columns else None
        cat_col = self._last_columns.get("category") if self._last_columns else None
        labels, values = self._distribution(df, cat_col, amount_col, topn=8)
        if not labels and self._last:
            labels, values = self._last.get("pie", {}).get(
                "labels", []
            ), self._last.get("pie", {}).get("values", [])
        return labels, values

    def periods(self) -> List[str]:
        if self._last and "periods" in self._last:
            return list(self._last["periods"])
        self.load()
        return list(self._last.get("periods", [])) if self._last else []

    # --- API étendue pour HomePage (8 cartes) ---

    def get_transactions_by_category(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retourne les transactions récentes groupées par catégorie.
        Format: [{"category": str, "amount": float, "count": int}, ...]
        """
        df = (
            self._last_df_selected
            if self._last_df_selected is not None
            else self.current_period_dataframe()
        )
        if df.empty:
            return []

        cat_col = self._last_columns.get("category")
        amount_col = self._last_columns.get("amount")

        if not cat_col or cat_col not in df.columns:
            return []

        result = []
        for cat, group in df.groupby(cat_col):
            count = len(group)
            if amount_col and amount_col in group.columns:
                total = float(
                    pd.to_numeric(group[amount_col], errors="coerce").fillna(0.0).sum()
                )
            else:
                total = 0.0
            result.append({"category": str(cat), "amount": total, "count": count})

        # Trier par montant décroissant et limiter
        result.sort(key=lambda x: abs(x["amount"]), reverse=True)
        return result[:limit]

    def get_retirement_stats(self) -> Dict[str, Any]:
        """
        Calcule les statistiques de cotisations retraite.
        Retourne: {"total": float, "by_employee": List[{name, amount}], "average": float}
        """
        df = (
            self._last_df_selected
            if self._last_df_selected is not None
            else self.current_period_dataframe()
        )
        if df.empty:
            return {"total": 0.0, "by_employee": [], "average": 0.0}

        cat_col = self._last_columns.get("category")
        amount_col = self._last_columns.get("amount")
        emp_col = self._last_columns.get("employee")

        # Filtrer les lignes contenant "retraite", "RRQ", "REER", etc.
        retirement_keywords = [
            "retraite",
            "rrq",
            "reer",
            "pension",
            "401k",
            "retirement",
        ]

        if cat_col and cat_col in df.columns:
            mask = (
                df[cat_col]
                .astype(str)
                .str.lower()
                .str.contains("|".join(retirement_keywords), na=False)
            )
            df_ret = df[mask]
        else:
            df_ret = pd.DataFrame()

        if df_ret.empty or not amount_col or amount_col not in df_ret.columns:
            return {"total": 0.0, "by_employee": [], "average": 0.0}

        total = float(
            pd.to_numeric(df_ret[amount_col], errors="coerce").fillna(0.0).sum()
        )

        by_emp = []
        if emp_col and emp_col in df_ret.columns:
            for emp, group in df_ret.groupby(emp_col):
                amt = float(
                    pd.to_numeric(group[amount_col], errors="coerce").fillna(0.0).sum()
                )
                by_emp.append({"name": str(emp), "amount": abs(amt)})
            by_emp.sort(key=lambda x: x["amount"], reverse=True)

        avg = total / len(df_ret) if len(df_ret) > 0 else 0.0

        return {"total": abs(total), "by_employee": by_emp[:10], "average": abs(avg)}

    def get_investment_stats(self) -> Dict[str, Any]:
        """
        Calcule les statistiques d'investissements/épargne.
        Retourne: {"total": float, "categories": List[{name, value}]}
        """
        df = (
            self._last_df_selected
            if self._last_df_selected is not None
            else self.current_period_dataframe()
        )
        if df.empty:
            return {"total": 0.0, "categories": []}

        cat_col = self._last_columns.get("category")
        amount_col = self._last_columns.get("amount")

        # Filtrer les lignes d'investissement/épargne
        invest_keywords = [
            "invest",
            "épargne",
            "epargne",
            "reer",
            "celi",
            "tfsa",
            "placement",
        ]

        if cat_col and cat_col in df.columns:
            mask = (
                df[cat_col]
                .astype(str)
                .str.lower()
                .str.contains("|".join(invest_keywords), na=False)
            )
            df_inv = df[mask]
        else:
            df_inv = pd.DataFrame()

        if df_inv.empty or not amount_col or amount_col not in df_inv.columns:
            return {"total": 0.0, "categories": []}

        total = float(
            pd.to_numeric(df_inv[amount_col], errors="coerce").fillna(0.0).sum()
        )

        categories = []
        if cat_col and cat_col in df_inv.columns:
            for cat, group in df_inv.groupby(cat_col):
                amt = float(
                    pd.to_numeric(group[amount_col], errors="coerce").fillna(0.0).sum()
                )
                categories.append({"name": str(cat), "value": abs(amt)})
            categories.sort(key=lambda x: x["value"], reverse=True)

        return {"total": abs(total), "categories": categories[:5]}

    def get_trend_data(self, months: int = 6) -> Dict[str, Any]:
        """
        Génère des données de tendance sur plusieurs mois.
        Retourne: {"labels": List[str], "datasets": [{"label": str, "data": List[float]}]}
        """
        if self._last_df is None:
            self.load()

        df = self._last_df
        if df is None or df.empty or "__period" not in df.columns:
            # Données factices pour démonstration
            return {
                "labels": ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun"],
                "datasets": [
                    {
                        "label": "Salaires",
                        "data": [45000, 47000, 46500, 48000, 49000, 50000],
                    },
                    {
                        "label": "Déductions",
                        "data": [12000, 12500, 12300, 13000, 13200, 13500],
                    },
                ],
            }

        amount_col = self._last_columns.get("amount")
        if not amount_col or amount_col not in df.columns:
            return {"labels": [], "datasets": []}

        # Grouper par période
        periods = sorted(
            [p for p in df["__period"].unique() if p != "(tout)" and p != "(n/a)"]
        )[-months:]

        labels = []
        salaries = []
        deductions = []

        for period in periods:
            df_period = df[df["__period"] == period]
            amounts = pd.to_numeric(df_period[amount_col], errors="coerce").fillna(0.0)

            pos = float(amounts[amounts >= 0].sum())
            neg = float(abs(amounts[amounts < 0].sum()))

            # Convertir période "2024-01" en "Jan 2024"
            try:
                year, month = period.split("-")
                month_names = [
                    "Jan",
                    "Fév",
                    "Mar",
                    "Avr",
                    "Mai",
                    "Jun",
                    "Jul",
                    "Aoû",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Déc",
                ]
                month_label = (
                    month_names[int(month) - 1] if 1 <= int(month) <= 12 else month
                )
                labels.append(f"{month_label}")
            except Exception:
                labels.append(period)

            salaries.append(pos)
            deductions.append(neg)

        return {
            "labels": labels,
            "datasets": [
                {"label": "Salaires", "data": salaries},
                {"label": "Déductions", "data": deductions},
            ],
        }

    def get_budget_summary(self) -> Dict[str, Any]:
        """
        Calcule un résumé budgétaire.
        Retourne: {"allocated": float, "spent": float, "remaining": float, "percentage": float}
        """
        df = (
            self._last_df_selected
            if self._last_df_selected is not None
            else self.current_period_dataframe()
        )
        if df.empty:
            return {"allocated": 0.0, "spent": 0.0, "remaining": 0.0, "percentage": 0.0}

        amount_col = self._last_columns.get("amount")
        if not amount_col or amount_col not in df.columns:
            return {"allocated": 0.0, "spent": 0.0, "remaining": 0.0, "percentage": 0.0}

        amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0)
        total_spent = float(amounts.sum())

        # Budget alloué = 110% du dépensé (approximation)
        allocated = abs(total_spent) * 1.10
        remaining = allocated - abs(total_spent)
        percentage = (abs(total_spent) / allocated * 100) if allocated > 0 else 0.0

        return {
            "allocated": allocated,
            "spent": abs(total_spent),
            "remaining": max(0.0, remaining),
            "percentage": min(100.0, percentage),
        }

    # --- API KPI Avancée (intégration kpi_engine) ---

    def get_advanced_kpis(
        self, period: Optional[str] = None, compare_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère tous les KPI avancés via le moteur kpi_engine.

        Args:
            period: Période au format "YYYY-MM" (None = dernière période)
            compare_to: Période de comparaison (None = période précédente automatique)

        Returns:
            Liste de dict avec les KPI formatés pour l'UI
        """
        try:
            from logic.kpi_engine import get_engine

            engine = get_engine()

            kpi_values = engine.calculate_all_kpis(period, compare_with_previous=True)

            # Convertir en format dict pour l'UI
            result = []
            for kpi in kpi_values:
                result.append(
                    {
                        "id": kpi.id,
                        "title": kpi.title,
                        "value": kpi.value,
                        "formatted_value": kpi.formatted_value,
                        "unit": kpi.unit,
                        "delta": kpi.delta,
                        "trend": kpi.trend,
                        "alert_level": kpi.alert_level,
                        "alert_message": kpi.alert_message,
                        "sparkline_data": kpi.sparkline_data,
                        "details": kpi.details,
                    }
                )

            return result
        except Exception as e:
            print(f"Erreur get_advanced_kpis: {e}")
            return []

    def get_kpi_trends(self, months: int = 12) -> Dict[str, Any]:
        """
        Récupère les tendances de tous les KPI sur plusieurs mois.

        Args:
            months: Nombre de mois d'historique

        Returns:
            Dict avec labels et datasets pour graphiques
        """
        try:
            from logic.kpi_engine import get_engine
            from app.logic.metrics import _load_df

            engine = get_engine()
            df = _load_df()

            if df.empty or "_Period" not in df.columns:
                return {"labels": [], "datasets": []}

            # Récupérer les périodes disponibles
            periods = sorted([p for p in df["_Period"].unique() if pd.notna(p)])[
                -months:
            ]

            # Préparer les datasets pour chaque KPI
            masse_data = []
            net_data = []
            deductions_data = []
            effectifs_data = []

            for period in periods:
                kpis = engine.calculate_all_kpis(period, compare_with_previous=False)

                for kpi in kpis:
                    if kpi.id == "masse_salariale":
                        masse_data.append(kpi.value)
                    elif kpi.id == "salaire_net":
                        net_data.append(kpi.value)
                    elif kpi.id == "deductions":
                        deductions_data.append(kpi.value)
                    elif kpi.id == "effectifs":
                        effectifs_data.append(kpi.value)

            # Formater labels (YYYY-MM -> Mois abrégé)
            labels = []
            for period in periods:
                try:
                    year, month = period.split("-")
                    month_names = [
                        "Jan",
                        "Fév",
                        "Mar",
                        "Avr",
                        "Mai",
                        "Jun",
                        "Jul",
                        "Aoû",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Déc",
                    ]
                    month_label = (
                        month_names[int(month) - 1] if 1 <= int(month) <= 12 else month
                    )
                    labels.append(f"{month_label}")
                except Exception as _exc:
                    labels.append(period)

            return {
                "labels": labels,
                "datasets": [
                    {"label": "Masse salariale", "data": masse_data},
                    {"label": "Salaire net", "data": net_data},
                    {"label": "Déductions", "data": deductions_data},
                    {"label": "Effectifs", "data": effectifs_data},
                ],
            }
        except Exception as e:
            print(f"Erreur get_kpi_trends: {e}")
            return {"labels": [], "datasets": []}

    def get_kpi_alerts(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les alertes KPI de la période courante.

        Returns:
            Liste de dict avec les alertes
        """
        try:
            from logic.kpi_engine import get_kpi_alerts

            return get_kpi_alerts(period=None)
        except Exception as e:
            print(f"Erreur get_kpi_alerts: {e}")
            return []

    def get_kpi_history(self, kpi_id: str, months: int = 12) -> List[Dict[str, Any]]:
        """
        Récupère l'historique d'un KPI spécifique.

        Args:
            kpi_id: ID du KPI (masse_salariale, salaire_net, deductions, etc.)
            months: Nombre de mois d'historique

        Returns:
            Liste de dict avec {period, value, formatted_value}
        """
        try:
            from logic.kpi_engine import get_engine

            engine = get_engine()
            return engine.get_kpi_history(kpi_id, months)
        except Exception as e:
            print(f"Erreur get_kpi_history: {e}")
            return []
