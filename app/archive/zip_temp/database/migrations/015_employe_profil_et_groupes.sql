-- =============================================================================
-- Migration 015: Vues profil employé et groupements (catégorie/titre)
-- Exécution: psql -d payroll_db -f migration/015_employe_profil_et_groupes.sql
-- =============================================================================
\set ON_ERROR_STOP on
SET client_min_messages TO NOTICE;

\echo ''
\echo '========================================================================='
\echo '015 - Début migration: Vues profil employé et groupements'
\echo '========================================================================='
\echo ''

CREATE SCHEMA IF NOT EXISTS paie;

-- Nettoyage préventif
DROP VIEW IF EXISTS paie.v_employes_groupes CASCADE;
DROP VIEW IF EXISTS paie.v_employe_profil CASCADE;

-- Vue profil employé: catégorie/titre dominants selon occurrences dans transactions
CREATE OR REPLACE VIEW paie.v_employe_profil AS
WITH base AS (
  SELECT 
    t.employee_id,
    COALESCE(NULLIF(TRIM(s.categorie_emploi), ''), 'Non défini') AS categorie_emploi,
    COALESCE(NULLIF(TRIM(s.titre_emploi), ''), 'Non défini')     AS titre_emploi,
    COUNT(*) AS nb
  FROM payroll.payroll_transactions t
  LEFT JOIN paie.stg_paie_transactions s
    ON t.source_file = s.source_file
   AND t.source_row_no = s.source_row_number
  GROUP BY t.employee_id, COALESCE(NULLIF(TRIM(s.categorie_emploi), ''), 'Non défini'), COALESCE(NULLIF(TRIM(s.titre_emploi), ''), 'Non défini')
), ranked AS (
  SELECT 
    b.*,
    ROW_NUMBER() OVER (PARTITION BY b.employee_id ORDER BY b.nb DESC, b.categorie_emploi, b.titre_emploi) AS rn
  FROM base b
)
SELECT 
  e.employee_id,
  e.matricule,
  COALESCE(TRIM(e.nom), '')     AS nom,
  COALESCE(TRIM(e.prenom), '')  AS prenom,
  r.categorie_emploi,
  r.titre_emploi,
  r.nb AS occurrences
FROM ranked r
JOIN core.employees e ON e.employee_id = r.employee_id
WHERE r.rn = 1;

COMMENT ON VIEW paie.v_employe_profil IS 'Profil employé: catégorie et titre dominants d’après les transactions';

-- Vue groupements employés: comptes par catégorie/titre
CREATE OR REPLACE VIEW paie.v_employes_groupes AS
SELECT 
  p.categorie_emploi,
  p.titre_emploi,
  COUNT(DISTINCT p.employee_id) AS nb_employes
FROM paie.v_employe_profil p
GROUP BY p.categorie_emploi, p.titre_emploi
ORDER BY nb_employes DESC, p.categorie_emploi, p.titre_emploi;

COMMENT ON VIEW paie.v_employes_groupes IS 'Groupements employés par catégorie et titre (profil dominant)';

GRANT USAGE ON SCHEMA paie TO payroll_app;
GRANT SELECT ON ALL TABLES IN SCHEMA paie TO payroll_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA paie GRANT SELECT ON TABLES TO payroll_app;

\echo ''
\echo '========================================================================='
\echo '015 - Migration terminée'
\echo '========================================================================='
\echo ''


