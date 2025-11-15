-- =====================================================
-- HARMONISATION DES VUES KPI - CONTRAT DE COLONNES UNIFORME
-- Utilise le schéma payroll existant
-- =====================================================

-- Contrat de colonnes minimal pour toutes les vues v_kpi_*
-- Colonnes obligatoires :
-- - date_paie (YYYY-MM-DD - date exacte de paie, OBLIGATOIRE)
-- - gains_brut (alias: brut)
-- - deductions_net (alias: deductions_employe) 
-- - net_a_payer (alias: net)
-- - part_employeur
-- - cout_total (alias: cout_employeur_pnl)
-- - cash_out_total
-- - nb_employes
-- - ajustements_gains
-- - deductions_brutes
-- - remboursements

-- =====================================================
-- 1. VUE PRINCIPALE : v_kpi_periode
-- =====================================================
DROP VIEW IF EXISTS v_kpi_periode CASCADE;

CREATE VIEW v_kpi_periode AS
SELECT 
    -- Date de paie exacte (OBLIGATOIRE - format YYYY-MM-DD)
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
GROUP BY pay_date, TO_CHAR(pay_date, 'YYYY-MM-DD')
ORDER BY date_paie;

-- =====================================================
-- 2. VUE PAR CATÉGORIE D'EMPLOI
-- =====================================================
DROP VIEW IF EXISTS v_kpi_par_categorie_emploi CASCADE;

CREATE VIEW payroll.v_kpi_par_categorie_emploi AS
SELECT 
    -- Date de paie exacte (OBLIGATOIRE)
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') as date_paie,
    COALESCE(e.categorie_emploi, 'Non défini') as categorie_emploi,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN t.amount_cents != 0 THEN t.employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 AND t.pay_code LIKE '%AJUST%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 AND t.pay_code LIKE '%REMBOURSE%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions t
LEFT JOIN payroll.employees e ON t.employee_id = e.employee_id
GROUP BY t.pay_date, TO_CHAR(t.pay_date, 'YYYY-MM-DD'), e.categorie_emploi
ORDER BY date_paie, categorie_emploi;

-- =====================================================
-- 3. VUE PAR CODE DE PAIE
-- =====================================================
DROP VIEW IF EXISTS payroll.v_kpi_par_code_paie CASCADE;

CREATE VIEW payroll.v_kpi_par_code_paie AS
SELECT 
    -- Date de paie exacte (OBLIGATOIRE)
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    pay_code,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions
GROUP BY pay_date, TO_CHAR(pay_date, 'YYYY-MM-DD'), pay_code
ORDER BY date_paie, code_paie;

-- =====================================================
-- 4. VUE PAR POSTE BUDGÉTAIRE
-- =====================================================
DROP VIEW IF EXISTS payroll.v_kpi_par_poste_budgetaire CASCADE;

CREATE VIEW payroll.v_kpi_par_poste_budgetaire AS
SELECT 
    -- Date de paie exacte (OBLIGATOIRE)
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') as date_paie,
    COALESCE(e.poste_budgetaire, 'Non défini') as poste_budgetaire,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN t.amount_cents != 0 THEN t.employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 AND t.pay_code LIKE '%AJUST%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 AND t.pay_code LIKE '%REMBOURSE%' THEN t.amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions t
LEFT JOIN payroll.employees e ON t.employee_id = e.employee_id
GROUP BY t.pay_date, TO_CHAR(t.pay_date, 'YYYY-MM-DD'), e.poste_budgetaire
ORDER BY date_paie, poste_budgetaire;

-- =====================================================
-- 5. VUE PAR EMPLOYÉ ET PÉRIODE
-- =====================================================
DROP VIEW IF EXISTS payroll.v_kpi_par_employe_periode CASCADE;

CREATE VIEW payroll.v_kpi_par_employe_periode AS
SELECT 
    -- Date de paie exacte (OBLIGATOIRE)
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    employee_id,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    1 as nb_employes, -- 1 employé par ligne
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions
GROUP BY pay_date, TO_CHAR(pay_date, 'YYYY-MM-DD'), employee_id
ORDER BY date_paie, employee_id;

-- =====================================================
-- 6. VUE TEMPS MENSUEL
-- =====================================================
DROP VIEW IF EXISTS payroll.v_kpi_temps_mensuel CASCADE;

CREATE VIEW payroll.v_kpi_temps_mensuel AS
SELECT 
    -- Date de paie exacte (OBLIGATOIRE)
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions
GROUP BY pay_date, TO_CHAR(pay_date, 'YYYY-MM-DD')
ORDER BY date_paie;

-- =====================================================
-- 7. VUE TEMPS ANNUEL
-- =====================================================
DROP VIEW IF EXISTS payroll.v_kpi_temps_annuel CASCADE;

CREATE VIEW payroll.v_kpi_temps_annuel AS
SELECT 
    -- Date de paie exacte (OBLIGATOIRE)
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    
    -- Contrat de colonnes standard
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 as net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 as part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 as cout_total,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 as cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) as nb_employes,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 as ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 as deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 as remboursements

FROM payroll.payroll_transactions
GROUP BY pay_date, TO_CHAR(pay_date, 'YYYY-MM-DD')
ORDER BY date_paie;

-- =====================================================
-- ALIAS RÉTRO-COMPATIBLES
-- =====================================================

-- Alias pour compatibilité avec l'ancien code
CREATE VIEW payroll.v_kpi_periode_compat AS
SELECT 
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
FROM payroll.v_kpi_periode;

-- =====================================================
-- COMMENTAIRES ET DOCUMENTATION
-- =====================================================

COMMENT ON VIEW payroll.v_kpi_periode IS 'Vue principale KPI avec contrat de colonnes harmonisé';
COMMENT ON VIEW payroll.v_kpi_par_categorie_emploi IS 'KPI par catégorie d''emploi - contrat harmonisé';
COMMENT ON VIEW payroll.v_kpi_par_code_paie IS 'KPI par code de paie - contrat harmonisé';
COMMENT ON VIEW payroll.v_kpi_par_poste_budgetaire IS 'KPI par poste budgétaire - contrat harmonisé';
COMMENT ON VIEW payroll.v_kpi_par_employe_periode IS 'KPI par employé et période - contrat harmonisé';
COMMENT ON VIEW payroll.v_kpi_temps_mensuel IS 'KPI par date de paie exacte (YYYY-MM-DD) - contrat harmonisé';
COMMENT ON VIEW payroll.v_kpi_temps_annuel IS 'KPI par date de paie exacte (YYYY-MM-DD) - contrat harmonisé';

-- =====================================================
-- GRANTS ET PERMISSIONS
-- =====================================================

GRANT SELECT ON payroll.v_kpi_periode TO payroll_app;
GRANT SELECT ON payroll.v_kpi_par_categorie_emploi TO payroll_app;
GRANT SELECT ON payroll.v_kpi_par_code_paie TO payroll_app;
GRANT SELECT ON payroll.v_kpi_par_poste_budgetaire TO payroll_app;
GRANT SELECT ON payroll.v_kpi_par_employe_periode TO payroll_app;
GRANT SELECT ON payroll.v_kpi_temps_mensuel TO payroll_app;
GRANT SELECT ON payroll.v_kpi_temps_annuel TO payroll_app;
GRANT SELECT ON payroll.v_kpi_periode_compat TO payroll_app;
