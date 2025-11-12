import json
import os
from types import SimpleNamespace
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from decimal import Decimal


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
        pgpassword=os.getenv("PAYROLL_DB_PASSWORD", ""),
        pghost=os.getenv("PAYROLL_DB_HOST", "localhost"),
        pgport=int(os.getenv("PAYROLL_DB_PORT", "5432")),
        pgdatabase=os.getenv("PAYROLL_DB_NAME", "payroll_db"),
    )


settings = load_settings()

url = f"postgresql+pg8000://{settings.pguser}:{settings.pgpassword}@{settings.pghost}:{settings.pgport}/{settings.pgdatabase}"
engine = create_engine(url, echo=False)
result = {"last_pay_date": None, "sample_rows": []}

try:
    with engine.connect() as conn:
        last_date = conn.execute(
            text("SELECT MAX(date_paie)::text FROM paie.v_employes")
        ).scalar()
        result["last_pay_date"] = last_date
        if last_date:
            rows = conn.execute(
                text(
                    """
                    SELECT nom_employe,
                           date_paie::text AS pay_date,
                           total_combine,
                           gains,
                           deductions,
                           part_employeur,
                           lignes,
                           masse_salariale
                    FROM paie.v_employes
                    WHERE date_paie = :d
                    ORDER BY nom_employe
                    LIMIT 50
                    """
                ),
                {"d": last_date},
            ).fetchall()
            ser = []
            for r in rows:
                d = dict(r._mapping)
                for k, v in list(d.items()):
                    if isinstance(v, Decimal):
                        d[k] = float(v)
                ser.append(d)
            result["sample_rows"] = ser
except Exception as exc:
    result["error"] = str(exc)

print(json.dumps(result, ensure_ascii=False))
