-- ============================================================================
-- Migration 011: Création du schéma en étoile pour métriques unifiées
-- ============================================================================
-- Exécution: psql -d payroll_db -f migration/011_schema_etoile.sql
-- ============================================================================

\set ON_ERROR_STOP on

-- ============================================================================
-- SCHEMA PAIE
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS paie;

-- ============================================================================
-- ENUM: Catégorie de paie
-- ============================================================================
DO $$ 
BEGIN
    CREATE TYPE paie.categorie_paie_enum AS ENUM (
        'Gains',
        'Deductions',
        'Deductions_legales',
        'Assurances',
        'Syndicats'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- DIMENSION: Temps
-- ============================================================================
CREATE TABLE IF NOT EXISTS paie.dim_temps (
    temps_id SERIAL PRIMARY KEY,
    date_paie DATE NOT NULL UNIQUE,
    jour_paie INTEGER NOT NULL,
    mois_paie INTEGER NOT NULL,
    annee_paie INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    semestre INTEGER NOT NULL,
    mois_paie VARCHAR(7) NOT NULL,
    exercice_fiscal INTEGER NOT NULL,
    is_fin_mois BOOLEAN NOT NULL,
    is_fin_trimestre BOOLEAN NOT NULL,
    is_fin_annee BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_mois_valide CHECK (mois_paie BETWEEN 1 AND 12),
    CONSTRAINT chk_jour_valide CHECK (jour_paie BETWEEN 1 AND 31),
    CONSTRAINT chk_trimestre_valide CHECK (trimestre BETWEEN 1 AND 4),
    CONSTRAINT chk_semestre_valide CHECK (semestre BETWEEN 1 AND 2)
);

CREATE INDEX IF NOT EXISTS idx_dim_temps_mois ON paie.dim_temps(mois_paie);
CREATE INDEX IF NOT EXISTS idx_dim_temps_annee ON paie.dim_temps(annee_paie);
CREATE INDEX IF NOT EXISTS idx_dim_temps_exercice ON paie.dim_temps(exercice_fiscal);

COMMENT ON TABLE paie.dim_temps IS 'Dimension temporelle - Grain: jour de paie';

-- ============================================================================
-- DIMENSION: Employé
-- ============================================================================
CREATE TABLE IF NOT EXISTS paie.dim_employe (
    employe_id SERIAL PRIMARY KEY,
    matricule VARCHAR(50) NOT NULL UNIQUE,
    nom_prenom VARCHAR(255) NOT NULL,
    nom_norm VARCHAR(255),
    prenom_norm VARCHAR(255),
    statut VARCHAR(20) DEFAULT 'actif',
    date_embauche DATE,
    date_depart DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_statut CHECK (statut IN ('actif', 'inactif', 'termine'))
);

CREATE INDEX IF NOT EXISTS idx_dim_employe_matricule ON paie.dim_employe(matricule);
CREATE INDEX IF NOT EXISTS idx_dim_employe_nom ON paie.dim_employe(nom_norm);
CREATE INDEX IF NOT EXISTS idx_dim_employe_statut ON paie.dim_employe(statut);

COMMENT ON TABLE paie.dim_employe IS 'Dimension employé - Slowly Changing Dimension Type 1';

-- ============================================================================
-- DIMENSION: Code de paie
-- ============================================================================
CREATE TABLE IF NOT EXISTS paie.dim_code_paie (
    code_paie_id SERIAL PRIMARY KEY,
    code_paie VARCHAR(50) NOT NULL UNIQUE,
    libelle_paie VARCHAR(255),
    categorie_paie paie.categorie_paie_enum NOT NULL,
    est_imposable BOOLEAN DEFAULT TRUE,
    est_cotisation BOOLEAN DEFAULT FALSE,
    ordre_affichage INTEGER,
    actif BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Note: Pas de contrainte de signe stricte
    -- Les ajustements (gains négatifs) et remboursements (retenues positives) sont acceptés
);

CREATE INDEX IF NOT EXISTS idx_dim_code_paie_categorie ON paie.dim_code_paie(categorie_paie);
CREATE INDEX IF NOT EXISTS idx_dim_code_paie_actif ON paie.dim_code_paie(actif);

COMMENT ON TABLE paie.dim_code_paie IS 'Dimension codes de paie - Référentiel métier';

-- ============================================================================
-- DIMENSION: Poste budgétaire
-- ============================================================================
CREATE TABLE IF NOT EXISTS paie.dim_poste_budgetaire (
    poste_budgetaire_id SERIAL PRIMARY KEY,
    poste_budgetaire VARCHAR(100) NOT NULL UNIQUE,
    libelle_poste VARCHAR(255),
    segment_1 VARCHAR(50),
    segment_2 VARCHAR(50),
    segment_3 VARCHAR(50),
    segment_4 VARCHAR(50),
    actif BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_poste_budgetaire_segment1 ON paie.dim_poste_budgetaire(segment_1);
CREATE INDEX IF NOT EXISTS idx_dim_poste_budgetaire_actif ON paie.dim_poste_budgetaire(actif);

COMMENT ON TABLE paie.dim_poste_budgetaire IS 'Dimension postes budgétaires - Hiérarchie à 4 segments';

-- ============================================================================
-- DIMENSION: Emploi
-- ============================================================================
CREATE TABLE IF NOT EXISTS paie.dim_emploi (
    emploi_id SERIAL PRIMARY KEY,
    code_emploi VARCHAR(50) NOT NULL UNIQUE,
    titre_emploi VARCHAR(255),
    categorie_emploi VARCHAR(100),
    actif BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_emploi_categorie ON paie.dim_emploi(categorie_emploi);

COMMENT ON TABLE paie.dim_emploi IS 'Dimension métiers/emplois';

-- ============================================================================
-- TABLE STAGING
-- ============================================================================
CREATE TABLE IF NOT EXISTS paie.stg_paie_transactions (
    stg_id BIGSERIAL PRIMARY KEY,
    source_batch_id VARCHAR(50) NOT NULL,
    source_file VARCHAR(255),
    source_row_number INTEGER,
    
    -- Données brutes
    date_paie_raw VARCHAR(50),
    matricule_raw VARCHAR(50),
    nom_prenom_raw VARCHAR(255),
    code_emploi_raw VARCHAR(50),
    titre_emploi_raw VARCHAR(255),
    categorie_emploi_raw VARCHAR(100),
    code_paie_raw VARCHAR(50),
    libelle_paie_raw VARCHAR(255),
    poste_budgetaire_raw VARCHAR(100),
    libelle_poste_raw VARCHAR(255),
    montant_raw VARCHAR(50),
    part_employeur_raw VARCHAR(50),
    
    -- Données nettoyées
    date_paie DATE,
    matricule VARCHAR(50),
    nom_prenom VARCHAR(255),
    code_emploi VARCHAR(50),
    titre_emploi VARCHAR(255),
    categorie_emploi VARCHAR(100),
    code_paie VARCHAR(50),
    libelle_paie VARCHAR(255),
    poste_budgetaire VARCHAR(100),
    libelle_poste VARCHAR(255),
    montant_cents BIGINT,
    part_employeur_cents BIGINT,
    
    -- Validation
    is_valid BOOLEAN DEFAULT FALSE,
    validation_errors TEXT[],
    
    -- Traçabilité
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_stg_batch ON paie.stg_paie_transactions(source_batch_id);
CREATE INDEX IF NOT EXISTS idx_stg_date ON paie.stg_paie_transactions(date_paie);
CREATE INDEX IF NOT EXISTS idx_stg_valid ON paie.stg_paie_transactions(is_valid);

COMMENT ON TABLE paie.stg_paie_transactions IS 'Table de staging - Landing zone pour imports Excel/CSV';

-- ============================================================================
-- FAIT: Transactions de paie
-- ============================================================================
-- Note: Si fact_paie existe déjà, skip cette section
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'paie' AND tablename = 'fact_paie') THEN
        CREATE TABLE paie.fact_paie (
            fact_id BIGSERIAL PRIMARY KEY,
            temps_id INTEGER NOT NULL,
            employe_id INTEGER NOT NULL,
            code_paie_id INTEGER NOT NULL,
            poste_budgetaire_id INTEGER NOT NULL,
            emploi_id INTEGER,
            
            montant_cents BIGINT NOT NULL,
            part_employeur_cents BIGINT NOT NULL DEFAULT 0,
            
            cle_metier VARCHAR(255) NOT NULL,
            
            source_batch_id VARCHAR(50) NOT NULL,
            source_row_number INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            CONSTRAINT chk_part_employeur_positif CHECK (part_employeur_cents >= 0),
            CONSTRAINT uq_cle_metier UNIQUE (cle_metier)
        );
        
        -- Foreign Keys
        ALTER TABLE paie.fact_paie ADD CONSTRAINT fk_fact_temps 
            FOREIGN KEY (temps_id) REFERENCES paie.dim_temps(temps_id);
        ALTER TABLE paie.fact_paie ADD CONSTRAINT fk_fact_employe 
            FOREIGN KEY (employe_id) REFERENCES paie.dim_employe(employe_id);
        ALTER TABLE paie.fact_paie ADD CONSTRAINT fk_fact_code_paie 
            FOREIGN KEY (code_paie_id) REFERENCES paie.dim_code_paie(code_paie_id);
        ALTER TABLE paie.fact_paie ADD CONSTRAINT fk_fact_poste 
            FOREIGN KEY (poste_budgetaire_id) REFERENCES paie.dim_poste_budgetaire(poste_budgetaire_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_fact_paie_temps ON paie.fact_paie(temps_id);
CREATE INDEX IF NOT EXISTS idx_fact_paie_employe ON paie.fact_paie(employe_id);
CREATE INDEX IF NOT EXISTS idx_fact_paie_code_paie ON paie.fact_paie(code_paie_id);
CREATE INDEX IF NOT EXISTS idx_fact_paie_poste ON paie.fact_paie(poste_budgetaire_id);
CREATE INDEX IF NOT EXISTS idx_fact_paie_batch ON paie.fact_paie(source_batch_id);

COMMENT ON TABLE paie.fact_paie IS 'Fait paie - Grain: transaction';

-- ============================================================================
-- TABLE: Batches d'import
-- ============================================================================
CREATE TABLE IF NOT EXISTS paie.import_batches (
    batch_id VARCHAR(50) PRIMARY KEY,
    batch_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    nom_fichier VARCHAR(255),
    chemin_fichier TEXT,
    nb_lignes_totales INTEGER,
    nb_lignes_valides INTEGER,
    nb_lignes_rejetees INTEGER,
    statut VARCHAR(20) DEFAULT 'en_cours',
    message_erreur TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    created_by VARCHAR(100),
    
    CONSTRAINT chk_statut_batch CHECK (
        statut IN ('en_cours', 'complete', 'echec', 'partiel')
    )
);

CREATE INDEX IF NOT EXISTS idx_import_batches_statut ON paie.import_batches(statut);
CREATE INDEX IF NOT EXISTS idx_import_batches_date ON paie.import_batches(started_at);

-- ============================================================================
-- FONCTION: Générer clé métier
-- ============================================================================
CREATE OR REPLACE FUNCTION paie.generer_cle_metier(
    p_date_paie DATE,
    p_matricule VARCHAR,
    p_code_paie VARCHAR,
    p_poste_budgetaire VARCHAR,
    p_montant_cents BIGINT,
    p_part_employeur_cents BIGINT
)
RETURNS VARCHAR AS $$
BEGIN
    RETURN MD5(
        COALESCE(p_date_paie::TEXT, '') || '|' ||
        COALESCE(p_matricule, '') || '|' ||
        COALESCE(p_code_paie, '') || '|' ||
        COALESCE(p_poste_budgetaire, '') || '|' ||
        COALESCE(p_montant_cents::TEXT, '0') || '|' ||
        COALESCE(p_part_employeur_cents::TEXT, '0')
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION paie.generer_cle_metier IS 'Génère clé métier unique pour déduplication';

-- ============================================================================
-- FONCTION: Upsert dimension temps
-- ============================================================================
CREATE OR REPLACE FUNCTION paie.upsert_dim_temps(p_date_paie DATE)
RETURNS INTEGER AS $$
DECLARE
    v_temps_id INTEGER;
BEGIN
    INSERT INTO paie.dim_temps (
        date_paie,
        jour_paie,
        mois_paie,
        annee_paie,
        trimestre,
        semestre,
        mois_paie,
        exercice_fiscal,
        is_fin_mois,
        is_fin_trimestre,
        is_fin_annee
    )
    VALUES (
        p_date_paie,
        EXTRACT(DAY FROM p_date_paie),
        EXTRACT(MONTH FROM p_date_paie),
        EXTRACT(YEAR FROM p_date_paie),
        EXTRACT(QUARTER FROM p_date_paie),
        CASE WHEN EXTRACT(MONTH FROM p_date_paie) <= 6 THEN 1 ELSE 2 END,
        TO_CHAR(p_date_paie, 'YYYY-MM'),
        EXTRACT(YEAR FROM p_date_paie),
        p_date_paie = (DATE_TRUNC('MONTH', p_date_paie) + INTERVAL '1 month - 1 day')::DATE,
        EXTRACT(MONTH FROM p_date_paie) IN (3, 6, 9, 12),
        EXTRACT(MONTH FROM p_date_paie) = 12
    )
    ON CONFLICT (date_paie) DO UPDATE SET
        date_paie = EXCLUDED.date_paie
    RETURNING temps_id INTO v_temps_id;
    
    RETURN v_temps_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
\echo '✓ Schema en étoile créé avec succès'

