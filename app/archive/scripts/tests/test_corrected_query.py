"""
Test de la requête corrigée avec v_employe_profil
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.providers.postgres_provider import PostgresProvider


def test():
    provider = PostgresProvider()
    date = "2025-08-28"

    print("=" * 70)
    print("TEST: Requête corrigée avec v_employe_profil")
    print("=" * 70)

    sql = f"""
      SELECT
        e.employee_id,
        e.matricule_norm AS matricule,
        COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')) AS nom_complet,
        MAX(t.pay_date) AS pay_date,
        COALESCE(prof.categorie_emploi, 'Non défini') AS categorie_emploi,
        COALESCE(prof.titre_emploi, 'Non défini') AS titre_emploi,
        CASE 
          WHEN BOOL_OR(m.nom_employe IS NOT NULL AND m.nom_employe ~ '[A-Za-z]' AND m.nom_employe = UPPER(m.nom_employe)) 
          THEN 'inactif' 
          ELSE 'actif' 
        END AS statut_calcule,
        SUM(t.amount_cents)::numeric / 100.0 AS amount_paid
      FROM payroll.payroll_transactions t
      JOIN core.employees e ON e.employee_id = t.employee_id
      LEFT JOIN paie.v_employe_profil prof ON prof.employee_id = e.employee_id
      LEFT JOIN payroll.imported_payroll_master m
        ON m.source_row_number = t.source_row_no
      WHERE t.pay_date = DATE '{date}'
      GROUP BY e.employee_id, e.matricule_norm, e.nom_complet, e.nom_norm, e.prenom_norm, prof.categorie_emploi, prof.titre_emploi
      ORDER BY nom_complet
      LIMIT 10
    """

    try:
        rows = provider.repo.run_query(sql)
        print(f"\n✅ Requête exécutée avec succès: {len(rows)} résultats\n")

        print(
            f"{'ID':<8} {'Matricule':<12} {'Nom':<30} {'Catégorie':<20} {'Titre':<25} {'Statut':<8} {'Montant':<12}"
        )
        print("-" * 120)

        for row in rows:
            emp_id = row[0]
            matricule = str(row[1] or "-")[:12]
            nom = str(row[2] or "-")[:28]
            categorie = str(row[4] or "-")[:18]
            titre = str(row[5] or "-")[:23]
            statut = str(row[6] or "-")
            montant = f"${row[7]:,.2f}" if row[7] else "$0.00"

            print(
                f"{emp_id:<8} {matricule:<12} {nom:<30} {categorie:<20} {titre:<25} {statut:<8} {montant:<12}"
            )

        # Vérifier les catégories et titres
        print("\n📊 Statistiques:")
        categories = set(r[4] for r in rows if r[4] and r[4] != "Non défini")
        titres = set(r[5] for r in rows if r[5] and r[5] != "Non défini")
        print(f"   Catégories trouvées: {len(categories)}")
        if categories:
            print(f"   Exemples: {list(categories)[:3]}")
        print(f"   Titres trouvés: {len(titres)}")
        if titres:
            print(f"   Exemples: {list(titres)[:3]}")

        # Compter le total
        sql_count = f"""
          SELECT COUNT(DISTINCT e.employee_id)
          FROM payroll.payroll_transactions t
          JOIN core.employees e ON e.employee_id = t.employee_id
          WHERE t.pay_date = DATE '{date}'
        """
        count_rows = provider.repo.run_query(sql_count)
        total = count_rows[0][0] if count_rows else 0
        print(f"\n   Total employés pour {date}: {total}")

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test()
