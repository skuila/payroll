# logic/kpi_engine.py - Moteur de calcul des KPI avancés
"""
Moteur centralisé pour tous les calculs de KPI (Key Performance Indicators).
Supporte les KPI financiers, RH, de tendance, avec détection d'anomalies et prévisions.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
from app.logic.metrics import _load_df


@dataclass
class KPIValue:
    """Valeur d'un KPI avec métadonnées"""

    id: str
    title: str
    value: float
    formatted_value: str
    unit: str
    delta: float = 0.0  # Variation vs période précédente (%)
    trend: str = "neutral"  # "up", "down", "neutral"
    alert_level: str = "ok"  # "ok", "warning", "critical"
    alert_message: str = ""
    sparkline_data: List[float] = None  # Données pour mini-graphique
    details: Dict[str, Any] = None  # Détails additionnels

    def __post_init__(self):
        if self.sparkline_data is None:
            self.sparkline_data = []
        if self.details is None:
            self.details = {}


@dataclass
class KPIComparison:
    """Comparaison de KPI entre deux périodes"""

    current_value: float
    previous_value: float
    delta: float
    delta_percent: float
    trend: str
    is_significant: bool  # True si delta > 10%


class KPIEngine:
    """Moteur de calcul des KPI avec cache et optimisations"""

    def __init__(self, db_path: str = "payroll.db"):
        self.db_path = db_path
        self._cache: Dict[str, Any] = {}
        self._last_load_time: Optional[datetime] = None

    def _money(self, v: float) -> str:
        """Format monétaire avec séparateur d'espace normal"""
        try:
            return f"{abs(v):,.2f} $".replace(",", " ")
        except Exception as _exc:
            return "0,00 $"

    def _percent(self, v: float) -> str:
        """Format pourcentage"""
        try:
            return f"{v:.1f}%"
        except Exception as _exc:
            return "0.0%"

    def _number(self, v: float) -> str:
        """Format nombre entier"""
        try:
            return f"{int(v):,}".replace(",", "\u202f")
        except Exception as _exc:
            return "0"

    def _detect_alert(
        self,
        current: float,
        previous: float,
        threshold_warning: float = 10.0,
        threshold_critical: float = 20.0,
    ) -> Tuple[str, str]:
        """
        Détecte le niveau d'alerte basé sur la variation.
        Returns: (alert_level, alert_message)
        """
        if previous == 0:
            return "ok", ""

        delta_percent = abs(((current - previous) / previous) * 100)

        if delta_percent >= threshold_critical:
            return "critical", f"Variation critique de {delta_percent:.1f}%"
        elif delta_percent >= threshold_warning:
            return "warning", f"Variation importante de {delta_percent:.1f}%"
        else:
            return "ok", ""

    def _compute_trend(self, current: float, previous: float) -> str:
        """Calcule la tendance (up/down/neutral)"""
        if previous == 0:
            return "neutral"

        delta_percent = ((current - previous) / previous) * 100

        if abs(delta_percent) < 1.0:  # Moins de 1% = neutral
            return "neutral"
        elif delta_percent > 0:
            return "up"
        else:
            return "down"

    def _compute_sparkline(
        self, df: pd.DataFrame, amount_col: str, months: int = 6
    ) -> List[float]:
        """Calcule les données pour un sparkline (mini-graphique de tendance)"""
        if df.empty or "_Period" not in df.columns or amount_col not in df.columns:
            return []

        # Grouper par période et sommer
        periods = sorted([p for p in df["_Period"].unique() if pd.notna(p)])[-months:]

        sparkline = []
        for period in periods:
            period_df = df[df["_Period"] == period]
            amounts = pd.to_numeric(period_df[amount_col], errors="coerce").fillna(0.0)
            total = float(amounts.sum())
            sparkline.append(total)

        return sparkline

    # ========== KPI FINANCIERS ==========

    def masse_salariale(
        self, df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None
    ) -> KPIValue:
        """
        Calcule la masse salariale totale (somme de tous les montants positifs).
        """
        if df.empty or "_Amount" not in df.columns:
            return KPIValue(
                id="masse_salariale",
                title="Masse salariale",
                value=0.0,
                formatted_value="0,00 $",
                unit="$",
            )

        amounts = pd.to_numeric(df["_Amount"], errors="coerce").fillna(0.0)
        total = float(amounts[amounts >= 0].sum())

        # Comparaison avec période précédente
        delta = 0.0
        trend = "neutral"
        alert_level = "ok"
        alert_msg = ""

        if previous_df is not None and not previous_df.empty:
            prev_amounts = pd.to_numeric(
                previous_df["_Amount"], errors="coerce"
            ).fillna(0.0)
            prev_total = float(prev_amounts[prev_amounts >= 0].sum())

            if prev_total > 0:
                delta = ((total - prev_total) / prev_total) * 100
                trend = self._compute_trend(total, prev_total)
                alert_level, alert_msg = self._detect_alert(total, prev_total)

        sparkline = self._compute_sparkline(df, "_Amount", 6)

        return KPIValue(
            id="masse_salariale",
            title="Masse salariale",
            value=total,
            formatted_value=self._money(total),
            unit="$",
            delta=delta,
            trend=trend,
            alert_level=alert_level,
            alert_message=alert_msg,
            sparkline_data=sparkline,
            details={"description": "Somme de tous les salaires bruts"},
        )

    def salaire_net(
        self, df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None
    ) -> KPIValue:
        """
        Calcule le salaire net total (montants positifs - déductions).
        """
        if df.empty or "_Amount" not in df.columns:
            return KPIValue(
                id="salaire_net",
                title="Salaire net",
                value=0.0,
                formatted_value="0,00 $",
                unit="$",
            )

        amounts = pd.to_numeric(df["_Amount"], errors="coerce").fillna(0.0)
        total = float(amounts.sum())

        delta = 0.0
        trend = "neutral"

        if previous_df is not None and not previous_df.empty:
            prev_amounts = pd.to_numeric(
                previous_df["_Amount"], errors="coerce"
            ).fillna(0.0)
            prev_total = float(prev_amounts.sum())

            if prev_total != 0:
                delta = ((total - prev_total) / abs(prev_total)) * 100
                trend = self._compute_trend(total, prev_total)

        sparkline = self._compute_sparkline(df, "_Amount", 6)

        return KPIValue(
            id="salaire_net",
            title="Salaire net",
            value=total,
            formatted_value=self._money(total),
            unit="$",
            delta=delta,
            trend=trend,
            sparkline_data=sparkline,
            details={"description": "Salaire après déductions"},
        )

    def deductions_totales(
        self, df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None
    ) -> KPIValue:
        """
        Calcule les déductions totales (somme des montants négatifs).
        """
        if df.empty or "_Amount" not in df.columns:
            return KPIValue(
                id="deductions",
                title="Déductions",
                value=0.0,
                formatted_value="0,00 $",
                unit="$",
            )

        amounts = pd.to_numeric(df["_Amount"], errors="coerce").fillna(0.0)
        total = float(amounts[amounts < 0].sum())

        delta = 0.0
        trend = "neutral"
        alert_level = "ok"
        alert_msg = ""

        if previous_df is not None and not previous_df.empty:
            prev_amounts = pd.to_numeric(
                previous_df["_Amount"], errors="coerce"
            ).fillna(0.0)
            prev_total = float(prev_amounts[prev_amounts < 0].sum())

            if prev_total != 0:
                delta = ((abs(total) - abs(prev_total)) / abs(prev_total)) * 100
                # Pour les déductions, une augmentation est une tendance "down" (négatif)
                trend = "down" if delta > 1 else ("up" if delta < -1 else "neutral")
                alert_level, alert_msg = self._detect_alert(
                    abs(total), abs(prev_total), 15.0, 25.0
                )

        sparkline_neg = [
            abs(x) for x in self._compute_sparkline(df[df["_Amount"] < 0], "_Amount", 6)
        ]

        return KPIValue(
            id="deductions",
            title="Déductions",
            value=abs(total),
            formatted_value=self._money(total),
            unit="$",
            delta=delta,
            trend=trend,
            alert_level=alert_level,
            alert_message=alert_msg,
            sparkline_data=sparkline_neg,
            details={"description": "Impôts, cotisations, retenues"},
        )

    def cout_employeur(
        self, df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None
    ) -> KPIValue:
        """
        Calcule le coût employeur (salaires + part employeur des cotisations).
        """
        if df.empty or "_Amount" not in df.columns:
            return KPIValue(
                id="cout_employeur",
                title="Coût employeur",
                value=0.0,
                formatted_value="0,00 $",
                unit="$",
            )

        # Salaires bruts
        amounts = pd.to_numeric(df["_Amount"], errors="coerce").fillna(0.0)
        salaires = float(amounts[amounts >= 0].sum())

        # Part employeur (si disponible)
        part_emp = 0.0
        if "_PartEmp" in df.columns:
            part_emp = float(
                pd.to_numeric(df["_PartEmp"], errors="coerce").fillna(0.0).sum()
            )

        total = salaires + part_emp

        delta = 0.0
        trend = "neutral"

        if previous_df is not None and not previous_df.empty:
            prev_amounts = pd.to_numeric(
                previous_df["_Amount"], errors="coerce"
            ).fillna(0.0)
            prev_salaires = float(prev_amounts[prev_amounts >= 0].sum())
            prev_part = 0.0
            if "_PartEmp" in previous_df.columns:
                prev_part = float(
                    pd.to_numeric(previous_df["_PartEmp"], errors="coerce")
                    .fillna(0.0)
                    .sum()
                )
            prev_total = prev_salaires + prev_part

            if prev_total > 0:
                delta = ((total - prev_total) / prev_total) * 100
                trend = self._compute_trend(total, prev_total)

        return KPIValue(
            id="cout_employeur",
            title="Coût employeur",
            value=total,
            formatted_value=self._money(total),
            unit="$",
            delta=delta,
            trend=trend,
            details={
                "description": "Salaires + cotisations patronales",
                "salaires": salaires,
                "cotisations": part_emp,
            },
        )

    def cout_moyen_employe(
        self, df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None
    ) -> KPIValue:
        """
        Calcule le coût moyen par employé.
        """
        if df.empty or "_Amount" not in df.columns or "_EmpKey" not in df.columns:
            return KPIValue(
                id="cout_moyen",
                title="Coût moyen/employé",
                value=0.0,
                formatted_value="0,00 $",
                unit="$",
            )

        amounts = pd.to_numeric(df["_Amount"], errors="coerce").fillna(0.0)
        total = float(amounts.sum())
        nb_employes = df["_EmpKey"].nunique()

        cout_moyen = abs(total) / nb_employes if nb_employes > 0 else 0.0

        delta = 0.0
        trend = "neutral"

        if previous_df is not None and not previous_df.empty:
            prev_amounts = pd.to_numeric(
                previous_df["_Amount"], errors="coerce"
            ).fillna(0.0)
            prev_total = float(prev_amounts.sum())
            prev_nb = previous_df["_EmpKey"].nunique()
            prev_cout_moyen = abs(prev_total) / prev_nb if prev_nb > 0 else 0.0

            if prev_cout_moyen > 0:
                delta = ((cout_moyen - prev_cout_moyen) / prev_cout_moyen) * 100
                trend = self._compute_trend(cout_moyen, prev_cout_moyen)

        return KPIValue(
            id="cout_moyen",
            title="Coût moyen/employé",
            value=cout_moyen,
            formatted_value=self._money(cout_moyen),
            unit="$/emp",
            delta=delta,
            trend=trend,
            details={
                "description": "Coût total / nombre d'employés",
                "total": abs(total),
                "nb_employes": nb_employes,
            },
        )

    # ========== KPI RH ==========

    def effectifs(
        self, df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None
    ) -> KPIValue:
        """
        Calcule le nombre d'employés actifs.
        """
        if df.empty or "_EmpKey" not in df.columns:
            return KPIValue(
                id="effectifs",
                title="Effectifs",
                value=0,
                formatted_value="0",
                unit="employés",
            )

        # Exclure les employés inactifs (majuscules uniquement)
        df_actifs = (
            df[~df.get("_IsInactive", False)] if "_IsInactive" in df.columns else df
        )
        nb_employes = df_actifs["_EmpKey"].nunique()

        delta = 0.0
        trend = "neutral"

        if previous_df is not None and not previous_df.empty:
            prev_actifs = (
                previous_df[~previous_df.get("_IsInactive", False)]
                if "_IsInactive" in previous_df.columns
                else previous_df
            )
            prev_nb = prev_actifs["_EmpKey"].nunique()

            if prev_nb > 0:
                delta = ((nb_employes - prev_nb) / prev_nb) * 100
                trend = self._compute_trend(nb_employes, prev_nb)

        return KPIValue(
            id="effectifs",
            title="Effectifs",
            value=nb_employes,
            formatted_value=self._number(nb_employes),
            unit="employés",
            delta=delta,
            trend=trend,
            details={"description": "Nombre d'employés actifs"},
        )

    def taux_rotation(
        self, df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None
    ) -> KPIValue:
        """
        Calcule le taux de rotation (turnover) approximatif.
        Taux = (Départs / Effectif moyen) * 100
        """
        if (
            df.empty
            or "_EmpKey" not in df.columns
            or previous_df is None
            or previous_df.empty
        ):
            return KPIValue(
                id="taux_rotation",
                title="Taux de rotation",
                value=0.0,
                formatted_value="0.0%",
                unit="%",
            )

        # Employés actuels et précédents
        current_emps = set(df["_EmpKey"].unique())
        previous_emps = set(previous_df["_EmpKey"].unique())

        # Nouveaux et départs
        nouveaux = len(current_emps - previous_emps)
        departs = len(previous_emps - current_emps)

        # Effectif moyen
        effectif_moyen = (len(current_emps) + len(previous_emps)) / 2

        taux = (departs / effectif_moyen * 100) if effectif_moyen > 0 else 0.0

        alert_level = "ok"
        alert_msg = ""
        if taux > 15:
            alert_level = "critical"
            alert_msg = "Taux de rotation élevé"
        elif taux > 10:
            alert_level = "warning"
            alert_msg = "Taux de rotation modéré"

        return KPIValue(
            id="taux_rotation",
            title="Taux de rotation",
            value=taux,
            formatted_value=self._percent(taux),
            unit="%",
            delta=0.0,
            trend="neutral",
            alert_level=alert_level,
            alert_message=alert_msg,
            details={
                "description": "Turnover mensuel",
                "nouveaux": nouveaux,
                "departs": departs,
                "effectif_moyen": int(effectif_moyen),
            },
        )

    def heures_supplementaires(
        self, df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None
    ) -> KPIValue:
        """
        Calcule le coût des heures supplémentaires.
        Identifie les lignes avec "heures sup", "overtime", "HS", etc.
        """
        if df.empty or "_Amount" not in df.columns or "_CodePaie" not in df.columns:
            return KPIValue(
                id="heures_sup",
                title="Heures supplémentaires",
                value=0.0,
                formatted_value="0,00 $",
                unit="$",
            )

        # Mots-clés pour heures sup
        keywords = ["heures sup", "overtime", "hs", "heure sup", "temps supp"]

        mask = (
            df["_CodePaie"]
            .astype(str)
            .str.lower()
            .str.contains("|".join(keywords), na=False)
        )
        df_hs = df[mask]

        if df_hs.empty:
            return KPIValue(
                id="heures_sup",
                title="Heures supplémentaires",
                value=0.0,
                formatted_value="0,00 $",
                unit="$",
            )

        amounts = pd.to_numeric(df_hs["_Amount"], errors="coerce").fillna(0.0)
        total = float(amounts.sum())

        delta = 0.0
        trend = "neutral"
        alert_level = "ok"
        alert_msg = ""

        if previous_df is not None and not previous_df.empty:
            prev_mask = (
                previous_df["_CodePaie"]
                .astype(str)
                .str.lower()
                .str.contains("|".join(keywords), na=False)
            )
            prev_hs = previous_df[prev_mask]

            if not prev_hs.empty:
                prev_amounts = pd.to_numeric(
                    prev_hs["_Amount"], errors="coerce"
                ).fillna(0.0)
                prev_total = float(prev_amounts.sum())

                if prev_total != 0:
                    delta = ((total - prev_total) / abs(prev_total)) * 100
                    trend = self._compute_trend(total, prev_total)

                    # Alerte si augmentation significative des HS
                    if delta > 20:
                        alert_level = "warning"
                        alert_msg = f"Augmentation de {delta:.0f}% des heures sup"

        return KPIValue(
            id="heures_sup",
            title="Heures supplémentaires",
            value=abs(total),
            formatted_value=self._money(total),
            unit="$",
            delta=delta,
            trend=trend,
            alert_level=alert_level,
            alert_message=alert_msg,
            details={
                "description": "Coût des heures supplémentaires",
                "nb_lignes": len(df_hs),
            },
        )

    # ========== API PRINCIPALE ==========

    def calculate_all_kpis(
        self, period: Optional[str] = None, compare_with_previous: bool = True
    ) -> List[KPIValue]:
        """
        Calcule tous les KPI pour une période donnée.

        Args:
            period: Période au format "YYYY-MM" (None = dernière période)
            compare_with_previous: Si True, compare avec la période précédente

        Returns:
            Liste de KPIValue avec tous les KPI calculés
        """
        df = _load_df()

        if df.empty:
            return []

        # Filtrer par période si spécifié
        if period:
            df_period = df[df["_Period"] == period]
        else:
            # Dernière période disponible
            periods = sorted([p for p in df["_Period"].unique() if pd.notna(p)])
            if periods:
                period = periods[-1]
                df_period = df[df["_Period"] == period]
            else:
                df_period = df

        # Période précédente pour comparaison
        previous_df = None
        if compare_with_previous and period:
            try:
                year, month = map(int, period.split("-"))
                prev_month = month - 1 if month > 1 else 12
                prev_year = year if month > 1 else year - 1
                prev_period = f"{prev_year}-{prev_month:02d}"

                previous_df = df[df["_Period"] == prev_period]
                if previous_df.empty:
                    previous_df = None
            except Exception as _exc:
                previous_df = None

        # Calculer tous les KPI
        kpis = [
            self.masse_salariale(df_period, previous_df),
            self.salaire_net(df_period, previous_df),
            self.deductions_totales(df_period, previous_df),
            self.effectifs(df_period, previous_df),
            self.cout_moyen_employe(df_period, previous_df),
            self.heures_supplementaires(df_period, previous_df),
        ]

        # Ajouter KPI conditionnels
        if previous_df is not None:
            kpis.append(self.taux_rotation(df_period, previous_df))

        return kpis

    def get_kpi_history(self, kpi_id: str, months: int = 12) -> List[Dict[str, Any]]:
        """
        Récupère l'historique d'un KPI sur plusieurs mois.

        Returns:
            Liste de dict avec {period, value, formatted_value}
        """
        df = _load_df()

        if df.empty or "_Period" not in df.columns:
            return []

        periods = sorted([p for p in df["_Period"].unique() if pd.notna(p)])[-months:]

        history = []
        for period in periods:
            df_period = df[df["_Period"] == period]

            # Calculer le KPI spécifique
            if kpi_id == "masse_salariale":
                kpi = self.masse_salariale(df_period)
            elif kpi_id == "salaire_net":
                kpi = self.salaire_net(df_period)
            elif kpi_id == "deductions":
                kpi = self.deductions_totales(df_period)
            elif kpi_id == "effectifs":
                kpi = self.effectifs(df_period)
            elif kpi_id == "cout_moyen":
                kpi = self.cout_moyen_employe(df_period)
            elif kpi_id == "heures_sup":
                kpi = self.heures_supplementaires(df_period)
            else:
                continue

            history.append(
                {
                    "period": period,
                    "value": kpi.value,
                    "formatted_value": kpi.formatted_value,
                }
            )

        return history

    def get_alerts(self, period: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère toutes les alertes KPI pour une période.

        Returns:
            Liste de dict avec {kpi_id, title, alert_level, message}
        """
        kpis = self.calculate_all_kpis(period, compare_with_previous=True)

        alerts = []
        for kpi in kpis:
            if kpi.alert_level in ["warning", "critical"]:
                alerts.append(
                    {
                        "kpi_id": kpi.id,
                        "title": kpi.title,
                        "alert_level": kpi.alert_level,
                        "message": kpi.alert_message,
                        "value": kpi.formatted_value,
                        "delta": f"{kpi.delta:+.1f}%",
                    }
                )

        return alerts


# Instance globale
_engine_instance: Optional[KPIEngine] = None


def get_engine() -> KPIEngine:
    """Retourne l'instance singleton du moteur KPI"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = KPIEngine()
    return _engine_instance


# API simplifiée
def calculate_kpis(period: Optional[str] = None) -> List[KPIValue]:
    """Raccourci pour calculer tous les KPI"""
    return get_engine().calculate_all_kpis(period)


def get_kpi_alerts(period: Optional[str] = None) -> List[Dict[str, Any]]:
    """Raccourci pour récupérer les alertes"""
    return get_engine().get_alerts(period)
