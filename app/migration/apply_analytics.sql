-- migration/apply_analytics.sql
-- Script complet pour créer la couche Analytics (source unique de vérité)
-- Ordre: schéma + vue canonique + vues d'agrégation + index + (optionnel) validation

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'paie') THEN
    EXECUTE 'CREATE SCHEMA paie';
  END IF;
END$$;

-- 1) Vue de compatibilité depuis le staging (expose centimes + dollars arrondis)
CREATE OR REPLACE VIEW paie.stg_paie_compat AS
SELECT
  s.date_paie::date                                       AS date_paie,
  s.matricule::text                                       AS matricule,
  COALESCE(s.montant_cents, 0)::bigint                    AS montant_cents,
  COALESCE(s.part_employeur_cents, 0)::bigint             AS part_employeur_cents,
  ROUND(COALESCE(s.montant_cents, 0) / 100.0, 2)          AS montant_employe,
  ROUND(COALESCE(s.part_employeur_cents, 0) / 100.0, 2)   AS part_employeur,
  NULL::numeric                                           AS montant_combine,
  s.categorie_emploi::text                                AS categorie_emploi,
  s.code_emploi::text                                     AS code_emploi,
  s.titre_emploi::text                                    AS titre_emploi,
  COALESCE(s.categorie_paie::text, dc.categorie_paie::text, NULL::text) AS categorie_paie,
  s.code_paie::text                                       AS code_paie,
  COALESCE(s.libelle_paie::text, dc.libelle_paie::text)   AS description_code_paie,
  s.poste_budgetaire::text                                AS poste_budgetaire,
  s.libelle_poste::text                                   AS description_poste_budgetaire
FROM paie.stg_paie_transactions s
LEFT JOIN paie.dim_code_paie dc
  ON dc.code_paie = s.code_paie;

COMMENT ON VIEW paie.stg_paie_compat IS
'Compatibilité staging analytics: expose centimes (calculs) + dollars arrondis (affichage).';

-- 2) Vue canonique (source unique de vérité)
CREATE OR REPLACE VIEW paie.v_lignes_paie AS
SELECT
  ROW_NUMBER() OVER (
    ORDER BY c.date_paie NULLS LAST, c.matricule NULLS LAST, c.code_paie NULLS LAST, c.poste_budgetaire NULLS LAST
  ) AS numero_ligne,
  c.date_paie,
  COALESCE(e.matricule_norm, e.matricule, c.matricule) AS matricule,
  COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')) AS nom_employe,
  c.categorie_emploi,
  c.code_emploi,
  c.titre_emploi,
  c.categorie_paie,
  c.code_paie,
  c.description_code_paie,
  c.poste_budgetaire,
  c.description_poste_budgetaire,
  c.montant_employe,
  c.part_employeur,
  c.montant_combine
FROM paie.stg_paie_compat c
LEFT JOIN core.employees e
  ON (e.matricule_norm = c.matricule OR e.matricule = c.matricule);

COMMENT ON VIEW paie.v_lignes_paie IS
'Vue canonique Analytics - montant_combine tel quel; date_paie = période exacte.';

-- 3) Vues d’agrégation minimales
CREATE OR REPLACE VIEW paie.v_masse_salariale AS
SELECT
  date_paie,
  NULL::numeric AS total_combine, -- jamais calculé
  SUM(ROUND(CASE
        WHEN lower(trim(categorie_paie)) IN ('gains','gain','revenu','salaire','brut') THEN montant_cents / 100.0
        WHEN categorie_paie IS NULL AND montant_cents > 0 THEN montant_cents / 100.0
        ELSE 0
      END, 2)) AS gains,
  SUM(ROUND(CASE
        WHEN lower(trim(categorie_paie)) NOT IN ('gains','gain','revenu','salaire','brut')
         AND (montant_cents < 0 OR lower(unaccent(trim(categorie_paie))) LIKE 'deduc%')
        THEN montant_cents / 100.0
        WHEN categorie_paie IS NULL AND montant_cents < 0 THEN montant_cents / 100.0
        ELSE 0
      END, 2)) AS deductions,
  SUM(ROUND(montant_cents / 100.0, 2)) AS net,
  ROUND(SUM(part_employeur_cents) / 100.0, 2) AS part_employeur,
  -- masse calculée avec gains per-line arrondis (Excel-like) + part employeur arrondi
  ROUND(SUM(ROUND(CASE
         WHEN lower(trim(categorie_paie)) IN ('gains','gain','revenu','salaire','brut') THEN montant_cents / 100.0
         WHEN categorie_paie IS NULL AND montant_cents > 0 THEN montant_cents / 100.0
         ELSE 0
       END, 2)) + ROUND(SUM(part_employeur_cents) / 100.0, 2), 2) AS masse_salariale
FROM paie.stg_paie_compat
GROUP BY date_paie;

CREATE OR REPLACE VIEW paie.v_categories AS
SELECT
  date_paie,
  categorie_paie,
  code_paie,
  NULL::numeric AS total_combine, -- jamais calculé
  ROUND(SUM(part_employeur_cents) / 100.0, 2) AS part_employeur,
  COUNT(*) AS lignes
FROM paie.stg_paie_compat
GROUP BY date_paie, categorie_paie, code_paie;

CREATE OR REPLACE VIEW paie.v_postes AS
SELECT
  date_paie,
  poste_budgetaire,
  description_poste_budgetaire,
  NULL::numeric AS total_combine, -- jamais calculé
  ROUND(SUM(part_employeur_cents) / 100.0, 2) AS part_employeur,
  ROUND(SUM(CASE
        WHEN lower(trim(categorie_paie)) IN ('gains','gain','revenu','salaire','brut') THEN montant_cents
        WHEN categorie_paie IS NULL AND montant_cents > 0 THEN montant_cents
        ELSE 0
      END) / 100.0, 2) AS gains,
  ROUND(SUM(CASE
        WHEN lower(trim(categorie_paie)) NOT IN ('gains','gain','revenu','salaire','brut')
         AND (montant_cents < 0 OR lower(unaccent(trim(categorie_paie))) LIKE 'deduc%')
        THEN montant_cents
        WHEN categorie_paie IS NULL AND montant_cents < 0 THEN montant_cents
        ELSE 0
      END) / 100.0, 2) AS deductions,
  ROUND((SUM(CASE
         WHEN lower(trim(categorie_paie)) IN ('gains','gain','revenu','salaire','brut') THEN montant_cents
         WHEN categorie_paie IS NULL AND montant_cents > 0 THEN montant_cents
         ELSE 0
       END) + SUM(part_employeur_cents)) / 100.0, 2) AS masse_salariale
FROM paie.stg_paie_compat
GROUP BY date_paie, poste_budgetaire, description_poste_budgetaire;

CREATE OR REPLACE VIEW paie.v_employes AS
SELECT
  c.date_paie,
  c.matricule,
  COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, ''), c.matricule) AS nom_employe,
  COALESCE(MAX(NULLIF(c.categorie_emploi, '')), 'Non défini') AS categorie_emploi,
  COALESCE(MAX(NULLIF(c.titre_emploi, '')), 'Non défini') AS titre_emploi,
  COALESCE(MAX(NULLIF(e.statut, '')), 'actif') AS statut,
  NULL::numeric AS total_combine, -- jamais calculé
  ROUND(SUM(CASE
        WHEN lower(trim(categorie_paie)) IN ('gains','gain','revenu','salaire','brut') THEN montant_cents
        WHEN categorie_paie IS NULL AND montant_cents > 0 THEN montant_cents
        ELSE 0
      END) / 100.0, 2) AS gains,
  ROUND(SUM(CASE
        WHEN lower(trim(categorie_paie)) NOT IN ('gains','gain','revenu','salaire','brut')
         AND (montant_cents < 0 OR lower(unaccent(trim(categorie_paie))) LIKE 'deduc%')
        THEN montant_cents
        WHEN categorie_paie IS NULL AND montant_cents < 0 THEN montant_cents
        ELSE 0
      END) / 100.0, 2) AS deductions,
  ROUND(SUM(c.montant_employe), 2) AS net,
  ROUND(SUM(part_employeur_cents) / 100.0, 2) AS part_employeur,
  COUNT(*) AS lignes,
  ROUND((SUM(CASE
         WHEN lower(trim(categorie_paie)) IN ('gains','gain','revenu','salaire','brut') THEN montant_cents
         WHEN categorie_paie IS NULL AND montant_cents > 0 THEN montant_cents
         ELSE 0
       END) + SUM(part_employeur_cents)) / 100.0, 2) AS masse_salariale
FROM paie.stg_paie_compat c
LEFT JOIN core.employees e ON (e.matricule_norm = c.matricule OR e.matricule = c.matricule)
GROUP BY c.date_paie, c.matricule, e.nom_complet, e.nom_norm, e.prenom_norm;

-- 4) Droits d'accès (lecture seule) pour le rôle applicatif
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'payroll_user') THEN
    EXECUTE 'GRANT USAGE ON SCHEMA paie TO payroll_user';
    EXECUTE 'GRANT USAGE ON SCHEMA core TO payroll_user';
    EXECUTE 'GRANT SELECT ON ALL TABLES IN SCHEMA paie TO payroll_user';
    EXECUTE 'GRANT SELECT ON ALL TABLES IN SCHEMA core TO payroll_user';
  END IF;
END$$;


