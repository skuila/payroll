-- Migration 006: Colonnes Fast Track + Tables Log
-- ========================================
-- Ajout des 15 colonnes maître pour import direct
-- Tables traçabilité (import_runs, import_log)
-- Idempotent (IF NOT EXISTS)

BEGIN;

-- ========================================
-- ÉTAPE 1: Table import principale (15 colonnes)
-- ========================================

-- Créer table si n'existe pas
CREATE TABLE IF NOT EXISTS payroll.imported_payroll_master (
    id BIGSERIAL PRIMARY KEY,
    
    -- 15 colonnes maître (mapping exact fichier source)
    n_de_ligne INTEGER,
    categorie_emploi TEXT COLLATE "fr-CA-x-icu",
    code_emploie TEXT COLLATE "fr-CA-x-icu",
    titre_emploi TEXT COLLATE "fr-CA-x-icu",
    date_paie DATE NOT NULL,
    matricule TEXT COLLATE "fr-CA-x-icu",
    employe TEXT COLLATE "fr-CA-x-icu",
    categorie_paie TEXT COLLATE "fr-CA-x-icu",
    code_paie TEXT COLLATE "fr-CA-x-icu",
    desc_code_paie TEXT COLLATE "fr-CA-x-icu",
    poste_budgetaire TEXT COLLATE "fr-CA-x-icu",
    desc_poste_budgetaire TEXT COLLATE "fr-CA-x-icu",
    montant NUMERIC(18, 2),
    part_employeur NUMERIC(18, 2),
    mnt_cmb TEXT COLLATE "fr-CA-x-icu",  -- Texte par défaut (peut contenir formules)
    
    -- Métadonnées import
    import_run_id BIGINT,
    source_file TEXT,
    source_row_number INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Index
    CONSTRAINT imported_payroll_master_date_check CHECK (date_paie IS NOT NULL)
);

-- Index performance
CREATE INDEX IF NOT EXISTS idx_ipm_date_paie ON payroll.imported_payroll_master(date_paie);
CREATE INDEX IF NOT EXISTS idx_ipm_matricule ON payroll.imported_payroll_master(matricule) WHERE matricule IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ipm_code_paie ON payroll.imported_payroll_master(code_paie) WHERE code_paie IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ipm_poste_budgetaire ON payroll.imported_payroll_master(poste_budgetaire) WHERE poste_budgetaire IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ipm_import_run ON payroll.imported_payroll_master(import_run_id);

COMMENT ON TABLE payroll.imported_payroll_master IS 'Table maître import direct (15 colonnes fixes) - Fast track sans détection';

-- ========================================
-- ÉTAPE 2: Tables traçabilité
-- ========================================

-- Table runs (historique imports)
CREATE TABLE IF NOT EXISTS payroll.import_runs (
    run_id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    source_file TEXT NOT NULL,
    file_size_bytes BIGINT,
    total_rows INTEGER,
    rows_imported INTEGER,
    rows_skipped INTEGER,
    alerts_count INTEGER DEFAULT 0,
    status TEXT CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    import_mode TEXT CHECK (import_mode IN ('fast_track', 'detection', 'manual')),
    mapping_used JSONB,
    user_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_import_runs_started ON payroll.import_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_import_runs_file ON payroll.import_runs(source_file);

COMMENT ON TABLE payroll.import_runs IS 'Historique des imports (traçabilité)';

-- Table log détaillé (alertes par ligne)
CREATE TABLE IF NOT EXISTS payroll.import_log (
    log_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES payroll.import_runs(run_id) ON DELETE CASCADE,
    source_row_number INTEGER,
    column_name TEXT,
    raw_value TEXT,
    alert_type TEXT CHECK (alert_type IN ('conversion_failed', 'null_value', 'out_of_range', 'format_error', 'constraint_violation')),
    alert_message TEXT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_import_log_run ON payroll.import_log(run_id);
CREATE INDEX IF NOT EXISTS idx_import_log_alert_type ON payroll.import_log(alert_type);

COMMENT ON TABLE payroll.import_log IS 'Log détaillé alertes import (non bloquant)';

-- ========================================
-- ÉTAPE 3: Fallback si collation FR-CA indisponible
-- ========================================

-- Si erreur collation FR-CA, modifier colonnes TEXT existantes
DO $$
BEGIN
    -- Tester disponibilité collation
    IF NOT EXISTS (SELECT 1 FROM pg_collation WHERE collname = 'fr-CA-x-icu') THEN
        RAISE NOTICE 'Collation fr-CA-x-icu non disponible - utilisation par défaut';
        
        -- Recréer table sans collation (fallback)
        DROP TABLE IF EXISTS payroll.imported_payroll_master CASCADE;
        
        CREATE TABLE payroll.imported_payroll_master (
            id BIGSERIAL PRIMARY KEY,
            n_de_ligne INTEGER,
            categorie_emploi TEXT,
            code_emploie TEXT,
            titre_emploi TEXT,
            date_paie DATE NOT NULL,
            matricule TEXT,
            employe TEXT,
            categorie_paie TEXT,
            code_paie TEXT,
            desc_code_paie TEXT,
            poste_budgetaire TEXT,
            desc_poste_budgetaire TEXT,
            montant NUMERIC(18, 2),
            part_employeur NUMERIC(18, 2),
            mnt_cmb TEXT,
            import_run_id BIGINT,
            source_file TEXT,
            source_row_number INTEGER,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Recréer index
        CREATE INDEX idx_ipm_date_paie ON payroll.imported_payroll_master(date_paie);
        CREATE INDEX idx_ipm_matricule ON payroll.imported_payroll_master(matricule) WHERE matricule IS NOT NULL;
    END IF;
END $$;

-- ========================================
-- ÉTAPE 4: Vue compatibilité (si besoin)
-- ========================================

-- Vue pour mapper vers ancienne structure (si nécessaire)
CREATE OR REPLACE VIEW payroll.v_imported_payroll_compat AS
SELECT
    id,
    date_paie as pay_date,
    matricule,
    employe as employee_name,
    code_paie as pay_code,
    montant as amount,
    part_employeur as employer_amount,
    source_file,
    imported_at
FROM payroll.imported_payroll_master;

COMMENT ON VIEW payroll.v_imported_payroll_compat IS 'Vue compatibilité avec ancienne structure';

-- ========================================
-- COMMIT
-- ========================================

COMMIT;

-- ========================================
-- VÉRIFICATION
-- ========================================

SELECT 
    'imported_payroll_master' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'payroll' 
  AND table_name = 'imported_payroll_master';

SELECT 
    tablename as table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'payroll'
  AND tablename IN ('imported_payroll_master', 'import_runs', 'import_log')
ORDER BY tablename;

