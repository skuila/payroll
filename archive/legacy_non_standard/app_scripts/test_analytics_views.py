import os
import sys
from types import SimpleNamespace
from typing import Tuple
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
        # Do NOT hardcode password; prefer PAYROLL_DB_PASSWORD or PGPASSWORD
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


def test_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"Connexion DB échouée: {exc}")
        return False


def ok(msg: str):
    print(f"✅ {msg}")


def fail(msg: str):
    print(f"❌ {msg}")


def test_connection_ok() -> bool:
    if test_connection():
        ok("Connexion DB OK")
        return True
    fail("Connexion DB KO")
    return False


def test_masse_equals_sum_lignes() -> Tuple[bool, str]:
    sql = """
    WITH a AS (
      SELECT date_paie, SUM(montant_combine) AS total_lignes
      FROM paie.v_lignes_paie
      GROUP BY date_paie
    ),
    b AS (
      SELECT date_paie, total_combine
      FROM paie.v_masse_salariale
    )
    SELECT COUNT(*) AS broken
    FROM (
      SELECT coalesce(a.date_paie,b.date_paie) AS d,
             coalesce(a.total_lignes,0) AS x,
             coalesce(b.total_combine,0) AS y
      FROM a FULL JOIN b ON a.date_paie = b.date_paie
      WHERE coalesce(a.total_lignes,0) <> coalesce(b.total_combine,0)
    ) t;
    """
    r = execute_query(sql)
    broken = r[0]["broken"] if r else 0
    if broken == 0:
        return (
            True,
            "v_masse_salariale = somme(montant_combine) de v_lignes_paie (par date)",
        )
    return False, f"Incohérences détectées: {broken} dates"


def test_categories_sum_equals_masse() -> Tuple[bool, str]:
    sql = """
    WITH a AS (
      SELECT date_paie, SUM(total_combine) AS total_cat
      FROM paie.v_categories
      GROUP BY date_paie
    ),
    b AS (
      SELECT date_paie, total_combine
      FROM paie.v_masse_salariale
    )
    SELECT COUNT(*) AS broken
    FROM (
      SELECT coalesce(a.date_paie,b.date_paie) AS d,
             coalesce(a.total_cat,0) AS x,
             coalesce(b.total_combine,0) AS y
      FROM a FULL JOIN b ON a.date_paie = b.date_paie
      WHERE coalesce(a.total_cat,0) <> coalesce(b.total_combine,0)
    ) t;
    """
    r = execute_query(sql)
    broken = r[0]["broken"] if r else 0
    if broken == 0:
        return True, "Somme v_categories = v_masse_salariale (par date)"
    return False, f"Incohérences détectées (cat vs masse): {broken} dates"


def test_postes_sum_equals_masse() -> Tuple[bool, str]:
    sql = """
    WITH a AS (
      SELECT date_paie, SUM(total_combine) AS total_postes
      FROM paie.v_postes
      GROUP BY date_paie
    ),
    b AS (
      SELECT date_paie, total_combine
      FROM paie.v_masse_salariale
    )
    SELECT COUNT(*) AS broken
    FROM (
      SELECT coalesce(a.date_paie,b.date_paie) AS d,
             coalesce(a.total_postes,0) AS x,
             coalesce(b.total_combine,0) AS y
      FROM a FULL JOIN b ON a.date_paie = b.date_paie
      WHERE coalesce(a.total_postes,0) <> coalesce(b.total_combine,0)
    ) t;
    """
    r = execute_query(sql)
    broken = r[0]["broken"] if r else 0
    if broken == 0:
        return True, "Somme v_postes = v_masse_salariale (par date)"
    return False, f"Incohérences détectées (postes vs masse): {broken} dates"


if __name__ == "__main__":
    if not test_connection_ok():
        sys.exit(2)

    ok_all = True
    for fn in (
        test_masse_equals_sum_lignes,
        test_categories_sum_equals_masse,
        test_postes_sum_equals_masse,
    ):
        success, message = fn()
        if success:
            ok(message)
        else:
            fail(message)
            ok_all = False

    if ok_all:
        ok("Tous les tests Analytics sont PASS ✅")
        sys.exit(0)
    else:
        fail("Des tests ont échoué ❌")
        sys.exit(1)
