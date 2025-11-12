# agent/payroll_agent.py — agent métier (Q&A + calculs)
from app.logic.metrics import summary
from logic.audit import run_basic_audit
from .openai_client import ask_text

MASK = "E-{idx:04d}"


def _anonymize_keys(keys):
    # transforme des identifiants/nom en pseudo-ID stables
    mapping = {}
    for i, k in enumerate(keys, 1):
        mapping[k] = MASK.format(idx=i)
    return mapping


def _build_context():
    s = summary()
    aud = run_basic_audit()

    # anonymisation légère pour le contexte envoyé au LLM
    emp_keys = [k for k, _ in s.get("top_employees", [])]
    mapping = _anonymize_keys(emp_keys)
    top_emps = [(mapping.get(k, "E-?"), v) for k, v in s.get("top_employees", [])]

    ctx = {
        "rows": s["rows"],
        "employees": s["employees"],
        "net_total": s["net_total"],
        "neg_pct": s["neg_pct"],
        "periods": s["latest_periods"],
        "by_period": s["by_period"][-6:],  # dernières périodes
        "by_category": s["by_category"][:10],
        "top_employees": top_emps,
        "audit": aud["findings"][:10],
    }
    # string compact lisible
    lines = [
        f"Lignes={ctx['rows']}, Employés={ctx['employees']}, Net total={ctx['net_total']:.2f}, %nets négatifs={ctx['neg_pct']:.2f}%",
        f"Dernières périodes: {', '.join(ctx['periods'])}",
        "Net par période (AAAAMM: net): "
        + ", ".join(f"{p}: {v:.2f}" for p, v in ctx["by_period"]),
        "Top catégories: " + ", ".join(f"{c}={v:.2f}" for c, v in ctx["by_category"]),
        "Top employés (anonymisés): "
        + ", ".join(f"{k}={v:.2f}" for k, v in ctx["top_employees"]),
        "Audit (règle: nb): "
        + ", ".join(f"{f['rule']}={f['count']}" for f in ctx["audit"]),
    ]
    return "\n".join(lines)


def answer(question: str, model: str = "gpt-5-mini") -> str:
    base = _build_context()
    prompt = f"""Contexte (données réelles résumées):
{base}

Tâche:
- Réponds à la question en t'appuyant uniquement sur le contexte (ne devine pas).
- Si l'information n'est pas présente, dis-le et propose le calcul SQL ou agrégation à exécuter.
- Réponds en français (Québec), style professionnel, très direct.

Question:
{question}
"""
    return ask_text(prompt, model=model)
