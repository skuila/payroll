-- ============================================================================
-- DDL: Création des structures pour référentiel employés
-- Version: 1.0
-- Date: 2025-10-16
-- ============================================================================

-- Configuration
SET client_min_messages TO WARNING;

-- Créer schéma core si nécessaire
CREATE SCHEMA IF NOT EXISTS core;
GRANT USAGE ON SCHEMA core TO payroll_app;
GRANT CREATE ON SCHEMA core TO payroll_app;

-- ============================================================================
-- TABLE: core.employees (Dimension Employés)
-- ============================================================================

CREATE TABLE IF NOT EXISTS core.employees (
    -- Clés
    employee_id         SERIAL PRIMARY KEY,
    employee_key        VARCHAR(255) NOT NULL UNIQUE,
    
    -- Identifiants
    matricule_norm      VARCHAR(50),
    matricule_raw       VARCHAR(100),
    
    -- Informations personnelles
    nom_norm            VARCHAR(255) NOT NULL,
    prenom_norm         VARCHAR(255),
    nom_complet         VARCHAR(500),
    
    -- Statut
    statut              VARCHAR(20) DEFAULT 'actif'
        CHECK (statut IN ('actif', 'inactif', 'suspendu')),
    
    -- Métadonnées
    source_system       VARCHAR(50) DEFAULT 'excel_import',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by          VARCHAR(100) DEFAULT CURRENT_USER,
    updated_by          VARCHAR(100) DEFAULT CURRENT_USER
);

-- Index
CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_key 
    ON core.employees(employee_key);
CREATE INDEX IF NOT EXISTS idx_employees_matricule 
    ON core.employees(matricule_norm) WHERE matricule_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_employees_statut 
    ON core.employees(statut);
CREATE INDEX IF NOT EXISTS idx_employees_nom 
    ON core.employees(nom_norm, prenom_norm);

-- Trigger pour updated_at
CREATE OR REPLACE FUNCTION core.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.updated_by = CURRENT_USER;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_employees_updated_at
    BEFORE UPDATE ON core.employees
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

-- Commentaires
COMMENT ON TABLE core.employees IS 
    'Référentiel unique des employés - source de vérité';
COMMENT ON COLUMN core.employees.employee_key IS 
    'Clé normalisée unique (matricule_norm ou MD5(nom_norm))';
COMMENT ON COLUMN core.employees.employee_id IS 
    'Clé technique auto-incrémentée';
COMMENT ON COLUMN core.employees.statut IS 
    'Statut employé: actif, inactif, suspendu';

-- ============================================================================
-- TABLE: payroll.import_batches (Traçabilité imports)
-- ============================================================================

CREATE TABLE IF NOT EXISTS payroll.import_batches (
    batch_id            SERIAL PRIMARY KEY,
    batch_uuid          UUID DEFAULT gen_random_uuid() UNIQUE,
    filename            VARCHAR(500),
    file_checksum       VARCHAR(64),
    total_rows          INTEGER,
    valid_rows          INTEGER,
    invalid_rows        INTEGER,
    new_employees       INTEGER,
    new_transactions    INTEGER,
    status              VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'rolled_back')),
    error_message       TEXT,
    started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP,
    created_by          VARCHAR(100) DEFAULT CURRENT_USER
);

CREATE INDEX IF NOT EXISTS idx_batches_status 
    ON payroll.import_batches(status);
CREATE INDEX IF NOT EXISTS idx_batches_filename 
    ON payroll.import_batches(filename);
CREATE INDEX IF NOT EXISTS idx_batches_started 
    ON payroll.import_batches(started_at DESC);

COMMENT ON TABLE payroll.import_batches IS 
    'Historique des imports de données (traçabilité et audit)';

-- ============================================================================
-- TABLE: payroll.stg_imported_payroll (Staging)
-- ============================================================================

CREATE TABLE IF NOT EXISTS payroll.stg_imported_payroll (
    -- Données brutes
    matricule_raw       VARCHAR(100),
    employe_raw         VARCHAR(500),
    date_paie_raw       VARCHAR(50),
    categorie_paie_raw  VARCHAR(200),
    montant_raw         VARCHAR(50),
    
    -- Données normalisées
    matricule_clean     VARCHAR(50),
    nom_norm            VARCHAR(255),
    prenom_norm         VARCHAR(255),
    employee_key        VARCHAR(255),
    pay_date            DATE,
    pay_code            VARCHAR(50),
    amount_cents        BIGINT,
    
    -- Validation
    is_valid            BOOLEAN DEFAULT TRUE,
    validation_errors   TEXT[],
    
    -- Traçabilité
    import_batch_id     INTEGER,
    source_row_no       INTEGER,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stg_employee_key 
    ON payroll.stg_imported_payroll(employee_key);
CREATE INDEX IF NOT EXISTS idx_stg_batch 
    ON payroll.stg_imported_payroll(import_batch_id);

COMMENT ON TABLE payroll.stg_imported_payroll IS 
    'Table staging pour imports Excel (nettoyée après validation)';

-- ============================================================================
-- TABLE: payroll.payroll_transactions (Fait Paie - Partitionné)
-- ============================================================================

CREATE TABLE IF NOT EXISTS payroll.payroll_transactions (
    -- Clés
    transaction_id      BIGSERIAL,
    employee_id         INTEGER NOT NULL,
    
    -- Période de paie
    pay_date            DATE NOT NULL,
    pay_day             INTEGER GENERATED ALWAYS AS (EXTRACT(DAY FROM pay_date)) STORED,
    pay_month           INTEGER GENERATED ALWAYS AS (EXTRACT(MONTH FROM pay_date)) STORED,
    pay_year            INTEGER GENERATED ALWAYS AS (EXTRACT(YEAR FROM pay_date)) STORED,
    period_seq_in_year  INTEGER,
    
    -- Détails paie
    pay_code            VARCHAR(50) NOT NULL,
    amount_cents        BIGINT NOT NULL,
    
    -- Traçabilité import
    import_batch_id     INTEGER,
    source_file         VARCHAR(500),
    source_row_no       INTEGER,
    
    -- Métadonnées
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by          VARCHAR(100) DEFAULT CURRENT_USER,
    
    -- Contraintes
    CONSTRAINT pk_payroll_transactions PRIMARY KEY (transaction_id, pay_date),
    CONSTRAINT fk_employee 
        FOREIGN KEY (employee_id) 
        REFERENCES core.employees(employee_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_import_batch 
        FOREIGN KEY (import_batch_id) 
        REFERENCES payroll.import_batches(batch_id)
        ON DELETE SET NULL,
    CONSTRAINT chk_amount_not_zero 
        CHECK (amount_cents <> 0)
) PARTITION BY RANGE (pay_date);

-- Index
CREATE INDEX IF NOT EXISTS idx_payroll_employee 
    ON payroll.payroll_transactions(employee_id);
CREATE INDEX IF NOT EXISTS idx_payroll_date 
    ON payroll.payroll_transactions(pay_date);
CREATE INDEX IF NOT EXISTS idx_payroll_period 
    ON payroll.payroll_transactions(pay_year, pay_month);
CREATE INDEX IF NOT EXISTS idx_payroll_code 
    ON payroll.payroll_transactions(pay_code);
CREATE INDEX IF NOT EXISTS idx_payroll_batch 
    ON payroll.payroll_transactions(import_batch_id) 
    WHERE import_batch_id IS NOT NULL;

COMMENT ON TABLE payroll.payroll_transactions IS 
    'Transactions de paie (fait) - partitionné par année sur pay_date';
COMMENT ON COLUMN payroll.payroll_transactions.amount_cents IS 
    'Montant en cents pour précision (évite erreurs arrondis)';
COMMENT ON COLUMN payroll.payroll_transactions.period_seq_in_year IS 
    'Numéro de séquence de la période dans l''année';

-- ============================================================================
-- PARTITIONS: Créer partitions pour années connues
-- ============================================================================

-- Partition 2024
CREATE TABLE IF NOT EXISTS payroll.payroll_transactions_2024
    PARTITION OF payroll.payroll_transactions
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Partition 2025
CREATE TABLE IF NOT EXISTS payroll.payroll_transactions_2025
    PARTITION OF payroll.payroll_transactions
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- Partition 2026 (anticiper)
CREATE TABLE IF NOT EXISTS payroll.payroll_transactions_2026
    PARTITION OF payroll.payroll_transactions
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

COMMENT ON TABLE payroll.payroll_transactions_2024 IS 'Partition année 2024';
COMMENT ON TABLE payroll.payroll_transactions_2025 IS 'Partition année 2025';
COMMENT ON TABLE payroll.payroll_transactions_2026 IS 'Partition année 2026';

-- ============================================================================
-- TABLE: reference.pay_codes (Référentiel codes paie)
-- ============================================================================

CREATE TABLE IF NOT EXISTS reference.pay_codes (
    pay_code_id         SERIAL PRIMARY KEY,
    pay_code            VARCHAR(50) NOT NULL UNIQUE,
    pay_code_desc       VARCHAR(255),
    pay_code_type       VARCHAR(20)
        CHECK (pay_code_type IN ('earning', 'deduction', 'tax', 'benefit', 'other')),
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pay_codes_type 
    ON reference.pay_codes(pay_code_type);
CREATE INDEX IF NOT EXISTS idx_pay_codes_active 
    ON reference.pay_codes(is_active);

COMMENT ON TABLE reference.pay_codes IS 
    'Référentiel des codes de paie (catégories)';

-- Pré-remplir codes de base
INSERT INTO reference.pay_codes (pay_code, pay_code_desc, pay_code_type)
VALUES 
    ('NON_SPECIFIE', 'Non spécifié', 'other'),
    ('SALAIRE_BASE', 'Salaire de base', 'earning'),
    ('HEURES_SUPP', 'Heures supplémentaires', 'earning'),
    ('PRIME', 'Prime', 'earning'),
    ('IMPOT', 'Impôts', 'tax'),
    ('COTISATION', 'Cotisations sociales', 'deduction'),
    ('ASSURANCE', 'Assurance', 'benefit')
ON CONFLICT (pay_code) DO NOTHING;

-- ============================================================================
-- FONCTION: Calcul employee_key
-- ============================================================================

CREATE OR REPLACE FUNCTION core.compute_employee_key(
    p_matricule TEXT,
    p_nom TEXT
) RETURNS VARCHAR(255) AS $$
DECLARE
    v_matricule_clean TEXT;
    v_nom_norm TEXT;
BEGIN
    -- Nettoyer matricule
    v_matricule_clean := NULLIF(
        BTRIM(regexp_replace(p_matricule, '[^0-9A-Za-z\-]', '', 'g')),
        ''
    );
    
    -- Si matricule numérique → retirer zéros en tête
    IF v_matricule_clean ~ '^[0-9]+$' THEN
        v_matricule_clean := NULLIF(
            regexp_replace(v_matricule_clean, '^0+', ''),
            ''
        );
    END IF;
    
    -- Si matricule valide → retourner
    IF v_matricule_clean IS NOT NULL THEN
        RETURN v_matricule_clean;
    END IF;
    
    -- Sinon fallback sur nom normalisé (hashé)
    v_nom_norm := regexp_replace(
        unaccent(LOWER(COALESCE(p_nom, ''))),
        '\s+', ' ', 'g'
    );
    
    RETURN MD5(v_nom_norm);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION core.compute_employee_key IS 
    'Calcule employee_key normalisé: matricule_clean ou MD5(nom_norm)';

-- ============================================================================
-- VUE: Compatibilité avec ancienne structure
-- ============================================================================

CREATE OR REPLACE VIEW payroll.v_imported_payroll_compat AS
SELECT
    e.matricule_raw AS "matricule ",
    e.nom_complet AS "employé ",
    t.pay_date AS "date de paie ",
    t.pay_code AS "categorie de paie ",
    t.amount_cents / 100.0 AS "montant ",
    t.employee_id,
    t.transaction_id
FROM payroll.payroll_transactions t
JOIN core.employees e ON t.employee_id = e.employee_id;

COMMENT ON VIEW payroll.v_imported_payroll_compat IS 
    'Vue de compatibilité émulant imported_payroll_master (transition)';

-- ============================================================================
-- VUE: Employés enrichis
-- ============================================================================

CREATE OR REPLACE VIEW core.v_employees_enriched AS
SELECT
    e.*,
    COUNT(DISTINCT t.pay_date) AS nb_moiss_paie,
    MIN(t.pay_date) AS premiere_paie,
    MAX(t.pay_date) AS derniere_paie,
    SUM(t.amount_cents) / 100.0 AS total_paie_lifetime
FROM core.employees e
LEFT JOIN payroll.payroll_transactions t ON e.employee_id = t.employee_id
GROUP BY e.employee_id;

COMMENT ON VIEW core.v_employees_enriched IS 
    'Vue employés avec statistiques de paie agrégées';

-- ============================================================================
-- GRANTS
-- ============================================================================

-- core.employees
GRANT SELECT, INSERT, UPDATE ON core.employees TO payroll_app;
GRANT USAGE, SELECT ON SEQUENCE core.employees_employee_id_seq TO payroll_app;

-- payroll.payroll_transactions
GRANT SELECT, INSERT ON payroll.payroll_transactions TO payroll_app;
GRANT USAGE, SELECT ON SEQUENCE payroll.payroll_transactions_transaction_id_seq TO payroll_app;

-- payroll.import_batches
GRANT SELECT, INSERT, UPDATE ON payroll.import_batches TO payroll_app;
GRANT USAGE, SELECT ON SEQUENCE payroll.import_batches_batch_id_seq TO payroll_app;

-- payroll.stg_imported_payroll
GRANT ALL ON payroll.stg_imported_payroll TO payroll_app;

-- reference.pay_codes
GRANT SELECT, INSERT ON reference.pay_codes TO payroll_app;
GRANT USAGE, SELECT ON SEQUENCE reference.pay_codes_pay_code_id_seq TO payroll_app;

-- Vues
GRANT SELECT ON payroll.v_imported_payroll_compat TO payroll_app;
GRANT SELECT ON core.v_employees_enriched TO payroll_app;

-- Fonctions
GRANT EXECUTE ON FUNCTION core.compute_employee_key TO payroll_app;
GRANT EXECUTE ON FUNCTION core.update_updated_at_column TO payroll_app;

-- ============================================================================
-- FIN DDL
-- ============================================================================

\echo '✓ Structures créées avec succès'
\echo '  - core.employees'
\echo '  - payroll.payroll_transactions (avec partitions 2024-2026)'
\echo '  - payroll.import_batches'
\echo '  - payroll.stg_imported_payroll'
\echo '  - reference.pay_codes'
\echo '  - Vues et fonctions utilitaires'

