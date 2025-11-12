-- =============================================================================
-- Migration 018: Correction part_employeur - Lire depuis données réelles
-- Objectif: Lire part_employeur depuis stg_paie_transactions (pas calculer)
--           Calculer taux réel (indicatif) = part_employeur / gains_bruts
-- Exécution: psql -d payroll_db -f migration/018_correction_part_employeur_reelle.sql
-- =============================================================================

\set ON_ERROR_STOP on
SET client_min_messages TO NOTICE;

\echo ''
\echo '========================================================================='
\echo '018 - Début migration: Correction part_employeur (lecture réelle)'
\echo '========================================================================='
\echo ''

-- ============================================================================
-- 1) Supprimer les vues existantes (pour recréer avec nouvelles colonnes)
-- ============================================================================

DROP VIEW IF EXISTS paie.v_kpi_par_employe_mois CASCADE;
DROP VIEW IF EXISTS paie.v_kpi_mois CASCADE;

-- ============================================================================
-- 2) Vue mensuelle/quotidienne consolidée
--    Lire part_employeur_cents depuis stg_paie_transactions
--    Calculer taux réel (indicatif) = part_employeur / gains_bruts
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
    
    -- Part employeur (LUE depuis stg_paie_transactions, pas calculée)
    COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0) / 100.0 AS part_employeur,
    
    -- Coût total (net + part employeur réelle)
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0)) / 100.0 AS cout_total,
    
    -- Cash out total (déductions en valeur absolue)
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 AS cash_out_total,
    
    -- Taux réel (indicatif) = part_employeur / gains_bruts
    CASE 
        WHEN SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) > 0 
        THEN (COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0)::NUMERIC / 
              SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END)) * 100.0
        ELSE NULL
    END AS taux_part_employeur_pct,
    
    -- Compteurs
    COUNT(DISTINCT CASE WHEN t.amount_cents <> 0 THEN t.employee_id END) AS nb_employes,
    COUNT(*) AS nb_transactions
FROM payroll.payroll_transactions t
LEFT JOIN paie.stg_paie_transactions s
  ON t.source_file = s.source_file
 AND t.source_row_no = s.source_row_number
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD')
ORDER BY periode_paie, date_paie;

COMMENT ON VIEW paie.v_kpi_mois IS 
'KPI consolidés par mois/jour - part_employeur lue depuis données réelles, taux calculé (indicatif)';

-- ============================================================================
-- 3) Vue par employé et période
--    Même logique: lire part_employeur depuis stg_paie_transactions
-- ============================================================================

CREATE VIEW paie.v_kpi_par_employe_mois AS
SELECT
    TO_CHAR(t.pay_date, 'YYYY-MM')    AS periode_paie,
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_paie,
    t.employee_id                      AS matricule,
    COALESCE(s.nom_prenom, 'N/A')      AS nom_prenom,
    COALESCE(s.categorie_emploi, 'Non défini')  AS categorie_emploi,
    COALESCE(s.titre_emploi, 'Non défini')      AS titre_emploi,
    COALESCE(s.poste_budgetaire, 'Non défini')  AS poste_budgetaire,
    
    -- Gains bruts
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    
    -- Déductions
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions,
    
    -- Net
    COALESCE(SUM(t.amount_cents), 0) / 100.0 AS net,
    
    -- Part employeur (LUE depuis stg_paie_transactions)
    COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0) / 100.0 AS part_employeur,
    
    -- Coût total
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0)) / 100.0 AS cout_total,
    
    -- Taux réel (indicatif) par employé
    CASE 
        WHEN SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) > 0 
        THEN (COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0)::NUMERIC / 
              SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END)) * 100.0
        ELSE NULL
    END AS taux_part_employeur_pct
FROM payroll.payroll_transactions t
LEFT JOIN paie.stg_paie_transactions s
  ON t.source_file = s.source_file
 AND t.source_row_no = s.source_row_number
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD'),
         t.employee_id, s.nom_prenom, s.categorie_emploi, s.titre_emploi, s.poste_budgetaire
ORDER BY periode_paie, date_paie, matricule;

COMMENT ON VIEW paie.v_kpi_par_employe_mois IS 
'KPI par employé et période - part_employeur lue depuis données réelles, taux calculé (indicatif)';

\echo '  ✓ Vues KPI corrigées pour lire part_employeur depuis données réelles'
\echo '  ✓ Taux réel calculé (indicatif) = part_employeur / gains_bruts'

\echo ''
\echo '========================================================================='
\echo '018 - Migration terminée avec succès'
\echo '========================================================================='
\echo ''

