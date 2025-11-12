-- ==========================================================
-- 🔧 SCRIPT D'ADMINISTRATION - CRÉATION DES VUES KPI DURABLES
-- ==========================================================
-- Ce script utilise les comptes administrateur pour créer
-- les vues KPI harmonisées de façon permanente.
-- ==========================================================

-- 1️⃣ Se connecter avec un compte admin
\c payroll_db postgres

-- 2️⃣ Créer (ou corriger) le schéma canonique
CREATE SCHEMA IF NOT EXISTS paie AUTHORIZATION postgres;

-- Supprimer les anciennes vues (DROP VIEW puis DROP MATERIALIZED VIEW). Le
-- script Python effectue un rollback après chaque erreur, donc si un DROP
-- échoue car le type est différent, la commande suivante pourra gérer le cas.
-- Robust drop: detect object type (view vs materialized view) and drop it without aborting the whole script
DO $$
DECLARE
    v text;
    relkind char;
BEGIN
    FOR v IN SELECT unnest(ARRAY[
        'v_kpi_periode',
        'v_kpi_par_categorie_emploi',
        'v_kpi_par_code_paie',
        'v_kpi_par_poste_budgetaire',
        'v_kpi_par_employe_periode',
        'v_kpi_temps_mensuel',
        'v_kpi_temps_annuel'
    ]) LOOP
        SELECT c.relkind INTO relkind
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = 'paie' AND c.relname = v
        LIMIT 1;

        IF FOUND THEN
            IF relkind = 'm' THEN
                EXECUTE format('DROP MATERIALIZED VIEW IF EXISTS paie.%I CASCADE', v);
            ELSE
                EXECUTE format('DROP VIEW IF EXISTS paie.%I CASCADE', v);
            END IF;
        END IF;
    END LOOP;
EXCEPTION WHEN OTHERS THEN
    -- Ne pas interrompre la suite du script; consigner un NOTICE pour diagnostic
    RAISE NOTICE 'Ignorer erreur lors des DROP: %', SQLERRM;
END$$;

-- =====================================================
-- 4️⃣ VUE PRINCIPALE : v_kpi_periode
-- =====================================================
CREATE OR REPLACE VIEW paie.v_kpi_periode AS
SELECT
    -- Période (format YYYY-MM pour agrégation mensuelle)
    TO_CHAR(pay_date, 'YYYY-MM') as periode,
    TO_CHAR(pay_date, 'YYYY-MM') as periode_paie,
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    
    -- Masse salariale brute (montants positifs)
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    
    -- Déductions nettes (montants négatifs)
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    
    -- Net à payer (brut + déductions)
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    
    -- Part employeur (charges patronales)
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    
    -- Coût total employeur (net + part employeur)
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_employeur_pnl,
    
    -- Cash out total (sorties de trésorerie)
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    
    -- Nombre d'employés uniques (avec montant non nul)
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
    
    -- Ajustements gains (montants positifs spéciaux)
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    
    -- Déductions brutes (tous les montants négatifs)
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    
    -- Remboursements (montants négatifs de type remboursement)
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions
GROUP BY TO_CHAR(pay_date, 'YYYY-MM'), TO_CHAR(pay_date, 'YYYY-MM-DD')
ORDER BY periode, date_paie;

-- =====================================================
-- 5️⃣ VUE PAR CATÉGORIE D'EMPLOI
-- =====================================================
CREATE OR REPLACE VIEW paie.v_kpi_par_categorie_emploi AS
SELECT 
    TO_CHAR(t.pay_date, 'YYYY-MM') as periode,
    TO_CHAR(t.pay_date, 'YYYY-MM') as periode_paie,
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') as date_paie,
    TRIM(COALESCE(s.categorie_emploi, 'Non défini')) as categorie_emploi,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_employeur_pnl,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN t.amount_cents != 0 THEN t.employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 AND t.pay_code LIKE '%AJUST%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 AND t.pay_code LIKE '%REMBOURSE%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions t
LEFT JOIN paie.stg_paie_transactions s
  ON t.source_file = s.source_file
 AND t.source_row_no = s.source_row_number
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD'), 
  TRIM(COALESCE(s.categorie_emploi, 'Non défini'))
ORDER BY periode, categorie_emploi;

-- =====================================================
-- 6️⃣ VUE PAR CODE DE PAIE
-- =====================================================
CREATE OR REPLACE VIEW paie.v_kpi_par_code_paie AS
SELECT 
    TO_CHAR(pay_date, 'YYYY-MM') as periode,
    TO_CHAR(pay_date, 'YYYY-MM') as periode_paie,
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    pay_code,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_employeur_pnl,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions
GROUP BY TO_CHAR(pay_date, 'YYYY-MM'), TO_CHAR(pay_date, 'YYYY-MM-DD'), pay_code
ORDER BY periode, pay_code;

-- =====================================================
-- 7️⃣ VUE PAR POSTE BUDGÉTAIRE
-- =====================================================
CREATE OR REPLACE VIEW paie.v_kpi_par_poste_budgetaire AS
SELECT 
    TO_CHAR(t.pay_date, 'YYYY-MM') as periode,
    TO_CHAR(t.pay_date, 'YYYY-MM') as periode_paie,
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') as date_paie,
    COALESCE(TRIM(s.poste_budgetaire), 'Non défini') as poste_budgetaire,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_employeur_pnl,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN t.amount_cents != 0 THEN t.employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 AND t.pay_code LIKE '%AJUST%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 AND t.pay_code LIKE '%REMBOURSE%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions t
LEFT JOIN paie.stg_paie_transactions s
  ON t.source_file = s.source_file
 AND t.source_row_no = s.source_row_number
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD'), 
  TRIM(s.poste_budgetaire)
ORDER BY periode, poste_budgetaire;

-- =====================================================
-- 8️⃣ VUE PAR EMPLOYÉ ET PÉRIODE
-- =====================================================
CREATE OR REPLACE VIEW paie.v_kpi_par_employe_periode AS
SELECT 
    TO_CHAR(t.pay_date, 'YYYY-MM') as periode,
    TO_CHAR(t.pay_date, 'YYYY-MM') as periode_paie,
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') as date_paie,
    t.employee_id,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_employeur_pnl,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    1 as nb_employes, -- 1 employé par ligne
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 AND t.pay_code LIKE '%AJUST%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 AND t.pay_code LIKE '%REMBOURSE%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions t
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD'), t.employee_id
ORDER BY periode, employee_id;

-- =====================================================
-- 9️⃣ VUE TEMPS MENSUEL
-- =====================================================
CREATE OR REPLACE VIEW paie.v_kpi_temps_mensuel AS
SELECT 
    TO_CHAR(pay_date, 'YYYY-MM') as periode,
    TO_CHAR(pay_date, 'YYYY-MM') as periode_paie,
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_employeur_pnl,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions
GROUP BY TO_CHAR(pay_date, 'YYYY-MM'), TO_CHAR(pay_date, 'YYYY-MM-DD')
ORDER BY periode;

-- =====================================================
-- 🔟 VUE TEMPS ANNUEL
-- =====================================================
CREATE OR REPLACE VIEW paie.v_kpi_temps_annuel AS
SELECT 
    TO_CHAR(pay_date, 'YYYY') as periode,
    NULL::text as periode_paie,
    NULL::text as date_paie,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_employeur_pnl,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions
GROUP BY TO_CHAR(pay_date, 'YYYY')
ORDER BY periode;

-- =====================================================
-- 1️⃣1️⃣ ALIAS RÉTRO-COMPATIBLES
-- =====================================================
CREATE OR REPLACE VIEW paie.v_kpi_periode_compat AS
SELECT 
    periode,
    date_paie,
    gains_brut as brut,
    deductions_net as deductions_employe,
    net_a_payer as net,
    part_employeur,
    cout_total as cout_employeur_pnl,
    cash_out_total,
    nb_employes,
    ajustements_gains,
    deductions_brutes,
    remboursements
FROM paie.v_kpi_periode;

-- =====================================================
-- 1️⃣2️⃣ SÉCURISATION : LECTURE SEULE POUR PAYROLL_APP
-- =====================================================
GRANT USAGE ON SCHEMA paie TO payroll_app;
GRANT SELECT ON ALL TABLES IN SCHEMA paie TO payroll_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA paie GRANT SELECT ON TABLES TO payroll_app;

-- =====================================================
-- 1️⃣3️⃣ COMMENTAIRES ET DOCUMENTATION
-- =====================================================
COMMENT ON VIEW paie.v_kpi_periode IS 'Vue principale KPI avec contrat de colonnes harmonisé';
COMMENT ON VIEW paie.v_kpi_par_categorie_emploi IS 'KPI par catégorie d''emploi - contrat harmonisé';
COMMENT ON VIEW paie.v_kpi_par_code_paie IS 'KPI par code de paie - contrat harmonisé';
COMMENT ON VIEW paie.v_kpi_par_poste_budgetaire IS 'KPI par poste budgétaire - contrat harmonisé';
COMMENT ON VIEW paie.v_kpi_par_employe_periode IS 'KPI par employé et période - contrat harmonisé';
COMMENT ON VIEW paie.v_kpi_temps_mensuel IS 'KPI temps mensuel - contrat harmonisé';
COMMENT ON VIEW paie.v_kpi_temps_annuel IS 'KPI temps annuel - contrat harmonisé';

-- =====================================================
-- 1️⃣4️⃣ VÉRIFICATION
-- =====================================================
SELECT table_schema, table_name
FROM information_schema.views
WHERE table_schema = 'paie'
ORDER BY 1,2;

-- =====================================================
-- 1️⃣5️⃣ TEST SIMPLE
-- =====================================================
SELECT * FROM paie.v_kpi_periode ORDER BY periode DESC LIMIT 5;
