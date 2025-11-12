import os
import psycopg
from pathlib import Path
from urllib.parse import urlparse


def main() -> None:
    dsn = os.getenv("DATABASE_URL") or os.getenv("PAYROLL_DSN")
    if not dsn:
        raise SystemExit("DATABASE_URL/PAYROLL_DSN absent dans l'environnement")

    # Facultatif: élever les droits si un mot de passe superuser est fourni (postgres)
    pg_super_pass = os.getenv("PG_SUPER_PASS")
    if pg_super_pass:
        parsed = urlparse(dsn)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        dbname = (parsed.path or "/payroll_db").lstrip("/") or "payroll_db"
        super_dsn = f"postgresql://postgres:{pg_super_pass}@{host}:{port}/{dbname}"
        try:
            with psycopg.connect(super_dsn) as conn_super, conn_super.cursor() as cur:
                cur.execute(
                    "SET search_path TO public, core, payroll, paie, reference, agent"
                )
                # Accorder droits au rôle owner (issu d'alembic)
                owner_url = os.getenv("ALEMBIC_DATABASE_URL", "")
                owner_user = None
                if owner_url:
                    up = urlparse(
                        owner_url.replace("postgresql+psycopg://", "postgresql://")
                    )
                    owner_user = up.username
                owner_user = owner_user or "payroll_owner"
                # Droits requis
                cur.execute(
                    f"GRANT USAGE ON SCHEMA core, payroll, paie TO {owner_user}"
                )
                cur.execute(f"GRANT CREATE ON SCHEMA paie TO {owner_user}")
                cur.execute(
                    f"GRANT SELECT ON ALL TABLES IN SCHEMA core TO {owner_user}"
                )
                cur.execute(
                    f"GRANT SELECT ON ALL TABLES IN SCHEMA payroll TO {owner_user}"
                )
                cur.execute(
                    f"GRANT SELECT ON ALL TABLES IN SCHEMA paie TO {owner_user}"
                )
                cur.execute(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA paie GRANT SELECT ON TABLES TO "
                    + owner_user
                )
                print(f"OK: droits GRANT sur schéma paie accordés à {owner_user}")
                # Accorder droits au rôle applicatif pour validation/lecture
                app_user = "payroll_app"
                cur.execute("GRANT USAGE ON SCHEMA core, payroll, paie TO " + app_user)
                cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA core TO " + app_user)
                cur.execute(
                    "GRANT SELECT ON ALL TABLES IN SCHEMA payroll TO " + app_user
                )
                cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA paie TO " + app_user)
                print(f"OK: droits SELECT/USAGE accordés à {app_user}")
        except Exception as e:
            print(f"AVERTISSEMENT: impossible d'accorder les droits via superuser: {e}")

    # Définition explicite de la vue (évite dépendance au fichier temporaire)
    view_sql = """
CREATE OR REPLACE VIEW paie.v_kpi_par_employe_mois AS
WITH
agg AS (
    SELECT
        t.pay_date::date                              AS date_paie,
        TO_CHAR(t.pay_date, 'YYYY-MM')                AS periode_paie,
        t.employee_id,
        COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
        COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions,
        COALESCE(SUM(t.amount_cents), 0) / 100.0                                         AS net,
        COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 AS part_employeur
    FROM payroll.payroll_transactions t
    GROUP BY t.pay_date, TO_CHAR(t.pay_date, 'YYYY-MM'), t.employee_id
),
stg_agg AS (
    SELECT
        s.date_paie::date                             AS date_paie,
        COALESCE(s.matricule::text, '')               AS matricule,
        MAX(NULLIF(s.nom_prenom, ''))                 AS nom_prenom,
        MAX(NULLIF(s.categorie_emploi, ''))           AS categorie_emploi,
        MAX(NULLIF(s.titre_emploi, ''))               AS titre_emploi,
        MAX(NULLIF(s.poste_budgetaire, ''))           AS poste_budgetaire
    FROM paie.stg_paie_transactions s
    WHERE COALESCE(s.is_valid, TRUE) = TRUE
    GROUP BY s.date_paie, COALESCE(s.matricule::text, '')
)
SELECT
    a.periode_paie,
    TO_CHAR(a.date_paie, 'YYYY-MM-DD') AS date_paie,
    COALESCE(e.matricule_norm, e.matricule)::text     AS matricule,
    COALESCE(sa.nom_prenom, COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')), 'N/A') AS nom_prenom,
    COALESCE(NULLIF(sa.categorie_emploi, ''), 'Non défini')   AS categorie_emploi,
    COALESCE(NULLIF(sa.titre_emploi, ''), 'Non défini')       AS titre_emploi,
    COALESCE(NULLIF(sa.poste_budgetaire, ''), 'Non défini')   AS poste_budgetaire,
    a.gains_brut,
    a.deductions,
    a.net,
    a.part_employeur,
    ROUND(a.net + a.part_employeur, 2) AS cout_total
FROM agg a
JOIN core.employees e
  ON e.employee_id = a.employee_id
LEFT JOIN stg_agg sa
  ON sa.date_paie = a.date_paie
 AND (sa.matricule = e.matricule OR sa.matricule = e.matricule_norm)
ORDER BY a.periode_paie, a.date_paie, e.matricule_norm NULLS LAST, e.matricule NULLS LAST;
""".strip()

    # Essayer de créer la vue avec le propriétaire si nécessaire
    owner_url = os.getenv("ALEMBIC_DATABASE_URL", "")
    if owner_url.startswith("postgresql+psycopg://"):
        owner_url = owner_url.replace("postgresql+psycopg://", "postgresql://", 1)
    if view_sql:
        try:
            with psycopg.connect(owner_url or dsn) as conn_owner:
                with conn_owner.cursor() as cur:
                    cur.execute(
                        "SET search_path TO public, core, payroll, paie, reference, agent"
                    )
                    cur.execute(view_sql)
                    print("OK: vue paie.v_kpi_par_employe_mois recréée (owner)")
        except Exception as e:
            # Tentative avec le DSN applicatif si owner indisponible
            # Si superuser dispo: on drop + recreate et on remet le propriétaire
            if pg_super_pass:
                parsed = urlparse(dsn)
                host = parsed.hostname or "localhost"
                port = parsed.port or 5432
                dbname = (parsed.path or "/payroll_db").lstrip("/") or "payroll_db"
                super_dsn = (
                    f"postgresql://postgres:{pg_super_pass}@{host}:{port}/{dbname}"
                )
                owner_url_eff = owner_url or dsn
                owner_name = (
                    urlparse(
                        owner_url_eff.replace("postgresql+psycopg://", "postgresql://")
                    ).username
                    if owner_url
                    else "payroll_owner"
                )
                with (
                    psycopg.connect(super_dsn) as conn_super,
                    conn_super.cursor() as cur,
                ):
                    cur.execute(
                        "SET search_path TO public, core, payroll, paie, reference, agent"
                    )
                    cur.execute(
                        "DROP VIEW IF EXISTS paie.v_kpi_par_employe_mois CASCADE"
                    )
                    cur.execute(view_sql)
                    cur.execute(
                        f"ALTER VIEW paie.v_kpi_par_employe_mois OWNER TO {owner_name}"
                    )
                    print(
                        "OK: vue paie.v_kpi_par_employe_mois recréée (superuser) et ownership rétabli"
                    )
            else:
                # Fallback: essayer avec le DSN applicatif
                with psycopg.connect(dsn) as conn_app:
                    with conn_app.cursor() as cur:
                        cur.execute(
                            "SET search_path TO public, core, payroll, paie, reference, agent"
                        )
                        cur.execute(view_sql)
                        print("OK: vue paie.v_kpi_par_employe_mois recréée (app)")

    with psycopg.connect(owner_url or dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SET search_path TO public, core, payroll, paie, reference, agent"
            )
            date_str = "2025-08-28"
            q1 = (
                "WITH agg AS ("
                " SELECT employee_id, SUM(amount_cents)/100.0 AS net"
                " FROM payroll.payroll_transactions"
                " WHERE pay_date = %s::date"
                " GROUP BY employee_id )"
                " SELECT ROUND(SUM(net), 2) FROM agg"
            )
            q2 = "SELECT ROUND(SUM(net), 2) FROM paie.v_kpi_par_employe_mois WHERE date_paie = %s"

            cur.execute(q1, (date_str,))
            t1 = cur.fetchone()[0]
            cur.execute(q2, (date_str,))
            t2 = cur.fetchone()[0]

            print(
                {
                    "total_transactions": float(t1 or 0),
                    "total_vue": float(t2 or 0),
                    "match": (t1 == t2),
                }
            )


if __name__ == "__main__":
    main()
