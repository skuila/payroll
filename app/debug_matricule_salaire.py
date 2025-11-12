#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug matricule et salaire net"""

from app.providers.postgres_provider import PostgresProvider


def debug():
    p = PostgresProvider()

    print("🔍 Vérifier un employé spécifique (matricule 2093):")
    print("\n1️⃣ Dans core.employees:")
    emp = p.repo.run_query(
        """
        SELECT employee_id, matricule_norm, nom_complet, nom_norm, prenom_norm
        FROM core.employees
        WHERE matricule_norm = '2093'
    """
    )
    if emp:
        print(f"  employee_id: {emp[0][0]}")
        print(f"  matricule_norm: {emp[0][1]}")
        print(f"  nom_complet: {emp[0][2]}")
        print(f"  nom_norm: {emp[0][3]}")
        print(f"  prenom_norm: {emp[0][4]}")
    else:
        print("  ❌ Aucun enregistrement dans core.employees")

    print("\n2️⃣ Dans payroll.payroll_transactions (2025-08-28):")
    trans = p.repo.run_query(
        """
        SELECT COUNT(*), SUM(amount_cents) / 100.0
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON e.employee_id = t.employee_id
        WHERE e.matricule_norm = '2093' AND t.pay_date = '2025-08-28'
    """
    )
    if trans:
        print(f"  Nb transactions: {trans[0][0]}")
        print(f"  Total bruts cumulés: {trans[0][1]:.2f} $")
    else:
        print("  ❌ Aucune transaction pour cette date")

    print("\n3️⃣ Données staging (paie.stg_paie_transactions):")
    stg = p.repo.run_query(
        """
        SELECT matricule, nom_prenom, categorie_emploi, titre_emploi, COUNT(*), SUM(montant_cents) / 100.0
        FROM paie.stg_paie_transactions
        WHERE matricule = '2093' AND date_paie = '2025-08-28' AND is_valid = TRUE
        GROUP BY matricule, nom_prenom, categorie_emploi, titre_emploi
    """
    )
    if stg:
        print(f"  matricule: {stg[0][0]}")
        print(f"  nom_prenom: {stg[0][1]}")
        print(f"  categorie: {stg[0][2]}")
        print(f"  titre: {stg[0][3]}")
        print(f"  Nb lignes: {stg[0][4]}")
        print(f"  Total staging: {stg[0][5]:.2f} $")
    else:
        print("  ❌ Aucune donnée staging pour ce matricule/date")

    print("\n4️⃣ Requête utilisée dans employees.html:")
    current = p.repo.run_query(
        """
        WITH agg AS (
           SELECT 
             e.employee_id,
             COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm, '')) AS nom,
             COALESCE(e.matricule_norm, '') AS matricule,
             COALESCE(SUM(t.amount_cents) / 100.0, 0.0) AS salaire_net
           FROM payroll.payroll_transactions t
           JOIN core.employees e ON e.employee_id = t.employee_id
           WHERE t.pay_date = DATE '2025-08-28'
             AND e.matricule_norm = '2093'
           GROUP BY
             e.employee_id,
             e.nom_complet,
             e.nom_norm,
             e.prenom_norm,
             e.matricule_norm
        ),
        stg AS (
           SELECT
             COALESCE(matricule::text, '') AS matricule,
             MAX(categorie_emploi) AS categorie_emploi,
             MAX(titre_emploi) AS titre_emploi
           FROM paie.stg_paie_transactions
           WHERE date_paie = DATE '2025-08-28'
             AND is_valid = TRUE
           GROUP BY COALESCE(matricule::text, '')
        )
        SELECT
          agg.nom,
          agg.matricule,
          COALESCE(stg.categorie_emploi, '') AS categorie_emploi,
          COALESCE(stg.titre_emploi, '') AS titre_emploi,
          agg.salaire_net AS total_a_payer
        FROM agg
        LEFT JOIN stg ON stg.matricule = agg.matricule
    """
    )
    if current:
        print(f"  Nom: {current[0][0]}")
        print(f"  Matricule (résultat requête): {current[0][1]}")
        print(f"  Catégorie affichée: {current[0][2]}")
        print(f"  Titre affiché: {current[0][3]}")
        print(f"  Total affiché: {current[0][4]:.2f} $")
    else:
        print("  ❌ La requête n'a retourné aucun résultat")

    print("\n5️⃣ Vérifier les 5 premiers employés (requête actuelle):")
    first_5 = p.repo.run_query(
        """
        WITH agg AS (
           SELECT 
             e.employee_id,
             COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm, '')) AS nom,
             COALESCE(e.matricule_norm, '') AS matricule,
             COALESCE(SUM(t.amount_cents) / 100.0, 0.0) AS salaire_net
           FROM payroll.payroll_transactions t
           JOIN core.employees e ON e.employee_id = t.employee_id
           WHERE t.pay_date = DATE '2025-08-28'
           GROUP BY
             e.employee_id,
             e.nom_complet,
             e.nom_norm,
             e.prenom_norm,
             e.matricule_norm
        ),
        stg AS (
           SELECT
             COALESCE(matricule::text, '') AS matricule,
             MAX(categorie_emploi) AS categorie_emploi,
             MAX(titre_emploi) AS titre_emploi
           FROM paie.stg_paie_transactions
           WHERE date_paie = DATE '2025-08-28'
             AND is_valid = TRUE
           GROUP BY COALESCE(matricule::text, '')
        )
        SELECT
          agg.nom,
          agg.matricule,
          COALESCE(stg.categorie_emploi, '') AS categorie_emploi,
          COALESCE(stg.titre_emploi, '') AS titre_emploi,
          agg.salaire_net AS total_a_payer
        FROM agg
        LEFT JOIN stg ON stg.matricule = agg.matricule
        ORDER BY agg.nom
        LIMIT 5
    """
    )
    for i, row in enumerate(first_5, 1):
        print(f"  {i}. {row[1]:6} | {row[0][:30]:30} | {row[4]:10.2f}")


if __name__ == "__main__":
    debug()
