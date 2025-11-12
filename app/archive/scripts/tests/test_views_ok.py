"""
Script de test autonome (fonctionne sans dépendre d'autres scripts):
 - Vérifie paie.v_employe_profil (catégorie/titre)
 - Vérifie core.v_employees_enriched (enrichissement métier)
 - Ne dépend PAS du nombre de lignes des fichiers Excel
"""

import sys
from datetime import date, datetime

try:
    from app.config.connection_standard import get_connection, get_dsn, mask_dsn
except ImportError:  # pragma: no cover
    from config.connection_standard import get_connection, get_dsn, mask_dsn  # type: ignore


def safe_print_rows(title: str, rows: list):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    if not rows:
        print("(aucun résultat)")
        return
    for r in rows:
        try:
            print(
                "  - ",
                tuple((str(v) if isinstance(v, (date, datetime)) else v) for v in r),
            )
        except Exception:
            print("  - ", r)


def main():
    try:
        dsn = get_dsn()
    except Exception as exc:
        print(f"❌ Impossible de construire le DSN standard : {exc}")
        sys.exit(1)

    print("DSN prêt (masqué):", mask_dsn(dsn))

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1) Statistiques v_employe_profil
                cur.execute(
                    """
                    SELECT COUNT(*) AS total,
                           COUNT(*) FILTER (WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) <> 'Non défini') AS avec_cat,
                           COUNT(*) FILTER (WHERE titre_emploi     IS NOT NULL AND TRIM(titre_emploi)     <> 'Non défini') AS avec_titre
                    FROM paie.v_employe_profil
                    """
                )
                stats = cur.fetchone()
                print("\n--- v_employe_profil: total, avec_categorie, avec_titre ---")
                print(stats)

                # 2) Top 5 catégories/titres
                cur.execute(
                    """
                    SELECT categorie_emploi, titre_emploi, COUNT(*)
                    FROM paie.v_employe_profil
                    GROUP BY 1,2
                    ORDER BY COUNT(*) DESC
                    LIMIT 5
                    """
                )
                top = cur.fetchall()
                safe_print_rows("Top 5 catégories/titres (profil)", top)

                # 3) Employés enrichis (5 premiers)
                cur.execute(
                    """
                    SELECT matricule_norm, nom_complet, categorie_emploi, titre_emploi
                    FROM core.v_employees_enriched
                    ORDER BY nom_complet
                    LIMIT 5
                    """
                )
                enr = cur.fetchall()
                safe_print_rows("Employés enrichis (5)", enr)

                # 4) Vérification de la jointure métier (exemple sur dernière date)
                cur.execute(
                    "SELECT MAX(pay_date)::date FROM payroll.payroll_transactions"
                )
                last_date = cur.fetchone()[0]
                print("\nDernière date trouvée:", last_date)

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM payroll.payroll_transactions t
                    JOIN core.employees e ON e.employee_id = t.employee_id
                    LEFT JOIN paie.stg_paie_transactions s
                      ON s.matricule     = e.matricule_norm
                     AND s.date_paie     = t.pay_date
                     AND s.code_paie     = t.pay_code
                     AND s.montant_cents = t.amount_cents
                    WHERE t.pay_date = %s
                      AND (s.categorie_emploi IS NOT NULL OR s.titre_emploi IS NOT NULL)
                    """,
                    (last_date,),
                )
                cnt_join = cur.fetchone()[0]
                print(
                    "Jointure métier (cat/titre non NULL) sur dernière date:", cnt_join
                )

                # 5) Échantillon concret avec cat/titre non 'Non défini' (si présent)
                cur.execute(
                    """
                    SELECT e.matricule_norm, e.nom_complet, p.categorie_emploi, p.titre_emploi
                    FROM core.employees e
                    JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
                    WHERE p.categorie_emploi <> 'Non défini' OR p.titre_emploi <> 'Non défini'
                    ORDER BY e.nom_complet
                    LIMIT 10
                    """
                )
                sample = cur.fetchall()
                safe_print_rows("Échantillon cat/titre définis (si disponible)", sample)

                print("\n✓ Test terminé")

    except Exception as e:
        print("❌ Erreur lors du test:", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
