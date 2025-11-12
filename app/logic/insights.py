# logic/insights.py — Génération d'insights textuels à partir du résumé analytique
from __future__ import annotations
from typing import List


def generate_insights(summary: dict) -> List[str]:
    """
    Génère une liste de phrases d'analyse lisibles à partir du résumé.

    Args:
        summary: dict retourné par compute_period_summary()

    Returns:
        Liste de phrases d'analyse en français
    """
    if not summary or "kpis" not in summary:
        return ["Aucune analyse disponible."]

    insights = []

    # 1. Insights KPIs
    insights.extend(_insight_kpis(summary.get("kpis", {})))

    # 2. Insights Anomalies
    insights.extend(_insight_anomalies(summary.get("anomalies", {})))

    # 3. Insights Comparaison
    insights.extend(_insight_comparaison(summary.get("comparaison", {})))

    # Si aucun insight, message par défaut
    if not insights:
        insights.append("Aucune anomalie majeure détectée. Tout semble conforme.")

    return insights


def _insight_kpis(kpis: dict) -> List[str]:
    """Génère des insights sur les KPIs."""
    insights = []

    if not kpis:
        return insights

    net_total = kpis.get("net_total", 0.0)
    nb_employes = kpis.get("nb_employes", 0)
    net_moyen = kpis.get("net_moyen", 0.0)
    net_median = kpis.get("net_median", 0.0)

    # Résumé général
    if nb_employes > 0:
        insights.append(
            f"📊 {nb_employes} employé{'s' if nb_employes > 1 else ''} payé{'s' if nb_employes > 1 else ''} "
            f"pour un net total de {_fmt_money(net_total)}."
        )

    # Moyenne vs médiane
    if net_moyen > 0 and net_median > 0:
        ecart_pct = abs(net_moyen - net_median) / net_moyen * 100
        if ecart_pct > 15:
            insights.append(
                f"⚖️ Écart significatif entre moyenne ({_fmt_money(net_moyen)}) "
                f"et médiane ({_fmt_money(net_median)}) : dispersion des salaires."
            )

    return insights


def _insight_anomalies(anomalies: dict) -> List[str]:
    """Génère des insights sur les anomalies."""
    insights = []

    if not anomalies:
        return insights

    # 1. Nets négatifs
    nets_neg = anomalies.get("nets_negatifs", {})
    count_neg = nets_neg.get("count", 0)
    if count_neg > 0:
        matricules = nets_neg.get("matricules", [])
        matricules_str = ", ".join(matricules[:3])
        if count_neg > 3:
            matricules_str += f", ... (+{count_neg - 3} autres)"
        insights.append(
            f"WARN: {count_neg} employé{'s' if count_neg > 1 else ''} avec net négatif ({matricules_str})."
        )

    # 2. Inactifs avec gains
    inactifs = anomalies.get("inactifs_avec_gains", {})
    count_inactifs = inactifs.get("count", 0)
    if count_inactifs > 0:
        insights.append(
            f"👤 {count_inactifs} employé{'s' if count_inactifs > 1 else ''} "
            f"inactif{'s' if count_inactifs > 1 else ''} (nom en MAJUSCULES) avec gains positifs."
        )

    # 3. Codes sensibles
    codes_sens = anomalies.get("codes_sensibles", {})
    count_codes = codes_sens.get("count", 0)
    if count_codes > 0:
        codes = codes_sens.get("codes", [])
        codes_str = ", ".join(codes)
        insights.append(
            f"🔍 {count_codes} code{'s' if count_codes > 1 else ''} sensible{'s' if count_codes > 1 else ''} "
            f"détecté{'s' if count_codes > 1 else ''} ({codes_str})."
        )

    # 4. Nouveaux codes
    nouveaux = anomalies.get("nouveaux_codes", {})
    count_nouveaux = nouveaux.get("count", 0)
    if count_nouveaux > 0:
        codes = nouveaux.get("codes", [])
        codes_str = ", ".join(codes[:5])
        if count_nouveaux > 5:
            codes_str += f", ... (+{count_nouveaux - 5} autres)"
        insights.append(
            f"🆕 {count_nouveaux} nouveau{'x' if count_nouveaux > 1 else ''} code{'s' if count_nouveaux > 1 else ''} "
            f"de paie détecté{'s' if count_nouveaux > 1 else ''} ({codes_str})."
        )

    # 5. Changements de poste
    changements = anomalies.get("changements_poste", {})
    count_chang = changements.get("count", 0)
    if count_chang > 0:
        insights.append(
            f"🔄 {count_chang} employé{'s' if count_chang > 1 else ''} "
            f"{'ont' if count_chang > 1 else 'a'} changé de poste budgétaire."
        )

    return insights


def _insight_comparaison(comp: dict) -> List[str]:
    """Génère des insights sur la comparaison avec période précédente."""
    insights = []

    if not comp or not comp.get("exists", False):
        return insights

    period_prec = comp.get("period_precedente", "")
    delta_net = comp.get("delta_net", 0.0)
    pct_variation = comp.get("pct_variation", 0.0)
    tendance = comp.get("tendance", "stable")
    delta_effectif = comp.get("delta_effectif", 0)

    # Tendance générale
    if tendance == "hausse":
        emoji = "📈"
        verbe = "en hausse"
    elif tendance == "baisse":
        emoji = "📉"
        verbe = "en baisse"
    else:
        emoji = "➡️"
        verbe = "stable"

    insights.append(
        f"{emoji} Net total {verbe} de {_fmt_money(abs(delta_net))} "
        f"({pct_variation:+.1f}%) par rapport à {_fmt_period(period_prec)}."
    )

    # Variation effectif
    if delta_effectif != 0:
        if delta_effectif > 0:
            insights.append(
                f"👥 +{delta_effectif} employé{'s' if delta_effectif > 1 else ''} par rapport au mois précédent."
            )
        else:
            insights.append(
                f"👥 {delta_effectif} employé{'s' if abs(delta_effectif) > 1 else ''} par rapport au mois précédent."
            )

    return insights


def _fmt_money(value: float) -> str:
    """Formate un montant en dollars avec espaces."""
    try:
        # Format français québécois
        formatted = f"{abs(value):,.2f}".replace(",", " ")
        sign = "-" if value < 0 else ""
        return f"{sign}{formatted} $"
    except Exception:
        return f"{value} $"


def _fmt_period(period: str) -> str:
    """Formate une période YYYY-MM en français."""
    try:
        year, month = period.split("-")
        months_fr = [
            "",
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ]
        month_name = months_fr[int(month)]
        return f"{month_name} {year}"
    except Exception:
        return period
