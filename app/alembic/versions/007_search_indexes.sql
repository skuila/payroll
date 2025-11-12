-- Migration 007: Search indexes for employees (trigram + unaccent)
-- Date: 2025-10-20

\echo '================================================'
\echo 'Migration 007: Index de recherche sur employés'
\echo '================================================'

-- Vérifier version actuelle
\echo '\nVersion actuelle:'
SELECT version_num FROM alembic_version;

-- Installer extensions si nécessaire
\echo '\n[0/3] Vérification des extensions...'
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
\echo '✓ Extensions OK'

-- Index 1: Recherche par nom avec unaccent + trigram
\echo '\n[1/3] Création index nom_complet (unaccent + trigram)...'
CREATE INDEX IF NOT EXISTS idx_employees_nom_unaccent_trgm
    ON core.employees
    USING GIN ( (unaccent(lower(nom_complet))) gin_trgm_ops );
\echo '✓ Index idx_employees_nom_unaccent_trgm créé'

-- Index 2: Recherche par matricule avec trigram
\echo '\n[2/3] Création index matricule_norm (trigram)...'
CREATE INDEX IF NOT EXISTS idx_employees_matricule_trgm
    ON core.employees
    USING GIN ( matricule_norm gin_trgm_ops );
\echo '✓ Index idx_employees_matricule_trgm créé'

-- Mettre à jour version Alembic
\echo '\n[3/3] Mise à jour version Alembic...'
UPDATE alembic_version SET version_num = '007';
\echo '✓ Version mise à jour: 007'

-- Vérifier nouvelle version
\echo '\nNouvelle version:'
SELECT version_num FROM alembic_version;

\echo '\n================================================'
\echo '✅ Migration 007 appliquée avec succès !'
\echo '================================================'

