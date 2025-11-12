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
