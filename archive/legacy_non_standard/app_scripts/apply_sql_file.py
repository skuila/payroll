# scripts/apply_sql_file.py
import sys
from pathlib import Path

# Allow imports from project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.providers.postgres_provider import PostgresProvider


def _strip_psql_meta(sql: str) -> str:
    # Remove psql meta-commands like \set, \echo, etc.
    lines = []
    for line in sql.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("\\"):
            continue
        lines.append(line)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/apply_sql_file.py <path/to/file.sql>")
        sys.exit(1)
    sql_path = Path(sys.argv[1])
    if not sql_path.exists():
        print(f"❌ Fichier introuvable: {sql_path}")
        sys.exit(2)

    raw_sql = sql_path.read_text(encoding="utf-8")
    sql = _strip_psql_meta(raw_sql)

    prov = PostgresProvider()
    repo = prov.repo
    if not repo:
        print("❌ Repository PostgreSQL indisponible.")
        sys.exit(3)

    try:
        with repo.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        print(f"OK: SQL appliqué: {sql_path}")
    except Exception as e:
        print(f"❌ Erreur application SQL: {e}")
        raise


if __name__ == "__main__":
    main()
