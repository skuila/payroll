import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


def load_settings() -> SimpleNamespace:
    dsn = os.getenv("PAYROLL_DSN") or os.getenv("DATABASE_URL")
    if dsn:
        parsed = urlparse(dsn)
        return SimpleNamespace(
            pguser=parsed.username or "postgres",
            pgpassword=parsed.password or "",
            pghost=parsed.hostname or "localhost",
            pgport=parsed.port or 5432,
            pgdatabase=(parsed.path.lstrip("/") or "postgres"),
        )

    return SimpleNamespace(
        pguser=os.getenv("PAYROLL_DB_USER", "postgres"),
        pgpassword=(os.getenv("PAYROLL_DB_PASSWORD") or os.getenv("PGPASSWORD") or ""),
        pghost=os.getenv("PAYROLL_DB_HOST", "localhost"),
        pgport=int(os.getenv("PAYROLL_DB_PORT", "5432")),
        pgdatabase=os.getenv("PAYROLL_DB_NAME", "payroll_db"),
    )


settings = load_settings()

DATABASE_URL = (
    f"postgresql+pg8000://{settings.pguser}:{settings.pgpassword}"
    f"@{settings.pghost}:{settings.pgport}/{settings.pgdatabase}"
)

engine = create_engine(DATABASE_URL, future=True, echo=False)


def execute_query(sql: str, params: dict | None = None):
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "logs" / "analytics"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def write_text(name: str, content: str) -> None:
    (OUT_DIR / name).write_text(content, encoding="utf-8")


def dump_last_date():
    sql = "SELECT to_char(MAX(date_paie),'YYYY-MM-DD') AS last_pay_date FROM paie.v_lignes_paie"
    rows = execute_query(sql)
    last = rows[0]["last_pay_date"] if rows and rows[0]["last_pay_date"] else ""
    write_text("last_date.txt", f"{last}\n")


def dump_masse_last():
    sql = """
    WITH d AS (SELECT MAX(date_paie) AS dp FROM paie.v_lignes_paie)
    SELECT to_char(m.date_paie,'YYYY-MM-DD') AS date_paie,
           m.total_combine, m.gains, m.deductions, m.part_employeur
    FROM paie.v_masse_salariale m
    JOIN d ON d.dp = m.date_paie
    """
    rows = execute_query(sql)
    lines = ["date_paie;total_combine;gains;deductions;part_employeur"]
    for r in rows or []:
        lines.append(
            f"{r['date_paie']};{r['total_combine']};{r['gains']};{r['deductions']};{r['part_employeur']}"
        )
    write_text("masse_last.csv", "\n".join(lines) + "\n")


def dump_codes_top10():
    sql = """
    WITH d AS (SELECT MAX(date_paie) AS dp FROM paie.v_lignes_paie)
    SELECT c.code_paie, c.description_code_paie, c.categorie_paie,
           c.total_combine, c.part_employeur, c.lignes
    FROM paie.v_categories c
    JOIN d ON d.dp = c.date_paie
    ORDER BY ABS(c.total_combine) DESC
    LIMIT 10
    """
    rows = execute_query(sql)
    lines = [
        "code_paie;description_code_paie;categorie_paie;total_combine;part_employeur;lignes"
    ]
    for r in rows or []:
        lines.append(
            f"{r['code_paie']};{r['description_code_paie']};{r['categorie_paie']};{r['total_combine']};{r['part_employeur']};{r['lignes']}"
        )
    write_text("codes_top10.csv", "\n".join(lines) + "\n")


def dump_postes_top10():
    sql = """
    WITH d AS (SELECT MAX(date_paie) AS dp FROM paie.v_lignes_paie)
    SELECT p.poste_budgetaire, p.description_poste_budgetaire,
           p.total_combine, p.part_employeur, p.gains, p.deductions
    FROM paie.v_postes p
    JOIN d ON d.dp = p.date_paie
    ORDER BY ABS(p.total_combine) DESC
    LIMIT 10
    """
    rows = execute_query(sql)
    lines = [
        "poste_budgetaire;description_poste_budgetaire;total_combine;part_employeur;gains;deductions"
    ]
    for r in rows or []:
        lines.append(
            f"{r['poste_budgetaire']};{r['description_poste_budgetaire']};{r['total_combine']};{r['part_employeur']};{r['gains']};{r['deductions']}"
        )
    write_text("postes_top10.csv", "\n".join(lines) + "\n")


def dump_employes_top10():
    sql = """
    WITH d AS (SELECT MAX(date_paie) AS dp FROM paie.v_lignes_paie)
    SELECT e.matricule, e.nom_employe,
           e.total_combine, e.gains, e.deductions, e.part_employeur, e.lignes
    FROM paie.v_employes e
    JOIN d ON d.dp = e.date_paie
    ORDER BY ABS(e.total_combine) DESC
    LIMIT 10
    """
    rows = execute_query(sql)
    lines = [
        "matricule;nom_employe;total_combine;gains;deductions;part_employeur;lignes"
    ]
    for r in rows or []:
        lines.append(
            f"{r['matricule']};{r['nom_employe']};{r['total_combine']};{r['gains']};{r['deductions']};{r['part_employeur']};{r['lignes']}"
        )
    write_text("employes_top10.csv", "\n".join(lines) + "\n")


if __name__ == "__main__":
    dump_last_date()
    dump_masse_last()
    dump_codes_top10()
    dump_postes_top10()
    dump_employes_top10()
    print(str(OUT_DIR))
