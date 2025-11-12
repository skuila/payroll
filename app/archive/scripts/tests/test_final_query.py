"""
Test final de la requête corrigée avec imported_payroll_master
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
    print("TEST FINAL: Requête corrigée avec imported_payroll_master")
    print("=" * 70)

    sql = f"""
      SELECT
        e.employee_id,
        e.matricule_norm AS matricule,
        COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')) AS nom_complet,
        MAX(t.pay_date) AS pay_date,
        COALESCE((ARRAY_AGG(m."Categorie d'emploi" ORDER BY m."Categorie d'emploi" NULLS LAST) FILTER (WHERE m."Categorie d'emploi" IS NOT NULL AND TRIM(m."Categorie d'emploi") <> ''))[1], 'Non défini') AS categorie_emploi,
        COALESCE((ARRAY_AGG(m."titre d'emploi" ORDER BY m."titre d'emploi" NULLS LAST) FILTER (WHERE m."titre d'emploi" IS NOT NULL AND TRIM(m."titre d'emploi") <> ''))[1], 'Non défini') AS titre_emploi,
        CASE 
          WHEN BOOL_OR(m."employé " IS NOT NULL AND m."employé " ~ '[A-Za-z]' AND m."employé " = UPPER(m."employé ")) 
          THEN 'inactif' 
          ELSE 'actif' 
        END AS statut_calcule,
        SUM(t.amount_cents)::numeric / 100.0 AS amount_paid
      FROM payroll.payroll_transactions t
      JOIN core.employees e ON e.employee_id = t.employee_id
      LEFT JOIN payroll.imported_payroll_master m
        ON m.source_row_number = t.source_row_no
      WHERE t.pay_date = DATE '{date}'
      GROUP BY e.employee_id, e.matricule_norm, e.nom_complet, e.nom_norm, e.prenom_norm
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

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test()
