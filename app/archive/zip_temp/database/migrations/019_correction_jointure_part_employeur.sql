-- =============================================================================
-- Migration 019: Correction jointure part_employeur - Utiliser imported_payroll_master
-- Objectif: Joindre avec imported_payroll_master qui a le vrai source_file et part employeur
-- Exécution: psql -d payroll_db -f migration/019_correction_jointure_part_employeur.sql
-- =============================================================================

\set ON_ERROR_STOP on
SET client_min_messages TO NOTICE;

\echo ''
\echo '========================================================================='
\echo '019 - Début migration: Correction jointure part_employeur'
\echo '========================================================================='
\echo ''

-- ============================================================================
-- 1) Supprimer les vues existantes
-- ============================================================================

DROP VIEW IF EXISTS paie.v_kpi_par_employe_mois CASCADE;
DROP VIEW IF EXISTS paie.v_kpi_mois CASCADE;

-- ============================================================================
-- 2) Vue mensuelle/quotidienne consolidée
--    Joindre avec imported_payroll_master via source_row_number
--    (source_file dans payroll_transactions = 'imported_payroll_master')
-- ============================================================================

CREATE VIEW paie.v_kpi_mois AS
SELECT
    TO_CHAR(t.pay_date, 'YYYY-MM')    AS periode_paie,
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_paie,
    
    -- Gains bruts (montants > 0)
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    
    -- Déductions (montants < 0)
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions_net,
    
    -- Net à payer (somme totale)
    COALESCE(SUM(t.amount_cents), 0) / 100.0 AS net_a_payer,
    
    -- Part employeur (LUE depuis imported_payroll_master.part_employeur)
    COALESCE(SUM(COALESCE(m.part_employeur, 0)), 0) AS part_employeur,
    
    -- Coût total (net + part employeur réelle)
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(COALESCE(m.part_employeur * 100, 0)), 0)) / 100.0 AS cout_total,
    
    -- Cash out total (déductions en valeur absolue)
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 AS cash_out_total,
    
    -- Taux réel (indicatif) = part_employeur / gains_bruts
    CASE 
        WHEN SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) > 0 
        THEN (COALESCE(SUM(COALESCE(m.part_employeur * 100, 0)), 0)::NUMERIC / 
              SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END)) * 100.0
        ELSE NULL
    END AS taux_part_employeur_pct,
    
    -- Compteurs
    COUNT(DISTINCT CASE WHEN t.amount_cents <> 0 THEN t.employee_id END) AS nb_employes,
    COUNT(*) AS nb_transactions
FROM payroll.payroll_transactions t
LEFT JOIN payroll.imported_payroll_master m
  ON t.source_row_no = m.source_row_number
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD')
ORDER BY periode_paie, date_paie;

COMMENT ON VIEW paie.v_kpi_mois IS 
'KPI consolidés par mois/jour - part_employeur lue depuis imported_payroll_master, taux calculé (indicatif)';

-- ============================================================================
-- 3) Vue par employé et période
--    Même logique: joindre avec imported_payroll_master
-- ============================================================================

CREATE VIEW paie.v_kpi_par_employe_mois AS
SELECT
    TO_CHAR(t.pay_date, 'YYYY-MM')    AS periode_paie,
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_paie,
    t.employee_id                      AS matricule,
    COALESCE(m.nom_employe, 'N/A')      AS nom_prenom,
    COALESCE(m.categorie_emploi, 'Non défini')  AS categorie_emploi,
    COALESCE(m.titre_emploi, 'Non défini')      AS titre_emploi,
    COALESCE(m.poste_budgetaire, 'Non défini')  AS poste_budgetaire,
    
    -- Gains bruts
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    
    -- Déductions
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions,
    
    -- Net
    COALESCE(SUM(t.amount_cents), 0) / 100.0 AS net,
    
    -- Part employeur (LUE depuis imported_payroll_master.part_employeur)
    COALESCE(SUM(COALESCE(m.part_employeur, 0)), 0) AS part_employeur,
    
    -- Coût total
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(COALESCE(m.part_employeur * 100, 0)), 0)) / 100.0 AS cout_total,
    
    -- Taux réel (indicatif) par employé
    CASE 
        WHEN SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) > 0 
        THEN (COALESCE(SUM(COALESCE(m.part_employeur * 100, 0)), 0)::NUMERIC / 
              SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END)) * 100.0
        ELSE NULL
    END AS taux_part_employeur_pct
FROM payroll.payroll_transactions t
LEFT JOIN payroll.imported_payroll_master m
  ON t.source_row_no = m.source_row_number
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD'),
         t.employee_id, m.nom_employe, m.categorie_emploi, m.titre_emploi, m.poste_budgetaire
ORDER BY periode_paie, date_paie, matricule;

COMMENT ON VIEW paie.v_kpi_par_employe_mois IS 
'KPI par employé et période - part_employeur lue depuis imported_payroll_master, taux calculé (indicatif)';

\echo '  ✓ Vues KPI corrigées pour utiliser imported_payroll_master'
\echo '  ✓ Jointure via source_row_number'
\echo '  ✓ Part employeur lue depuis données réelles (pas calculée)'
\echo '  ✓ Taux réel calculé (indicatif) = part_employeur / gains_bruts'

\echo ''
\echo '========================================================================='
\echo '019 - Migration terminée avec succès'
\echo '========================================================================='
\echo ''

