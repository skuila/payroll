-- migration/analytics_aggregations.sql
-- Vues d'agrégation par écran, basées UNIQUEMENT sur paie.v_lignes_paie

-- 1) Masse salariale par date
CREATE OR REPLACE VIEW paie.v_masse_salariale AS
SELECT
  date_paie,
  SUM(montant_combine)                                          AS total_combine,
  SUM(CASE WHEN categorie_paie = 'Gains' THEN montant_employe ELSE 0 END)         AS gains,
  SUM(CASE WHEN categorie_paie LIKE 'Déduction%' THEN montant_employe ELSE 0 END) AS deductions,
  SUM(part_employeur)                                           AS part_employeur
FROM paie.v_lignes_paie
GROUP BY date_paie;

-- 2) Catégories / Codes
CREATE OR REPLACE VIEW paie.v_categories AS
SELECT
  date_paie,
  categorie_paie,
  code_paie,
  SUM(montant_combine)   AS total_combine,
  SUM(part_employeur)    AS part_employeur,
  COUNT(*)               AS lignes
FROM paie.v_lignes_paie
GROUP BY date_paie, categorie_paie, code_paie;

-- 3) Postes budgétaires
CREATE OR REPLACE VIEW paie.v_postes AS
SELECT
  date_paie,
  poste_budgetaire,
  description_poste_budgetaire,
  SUM(montant_combine)                                          AS total_combine,
  SUM(part_employeur)                                           AS part_employeur,
  SUM(CASE WHEN categorie_paie = 'Gains' THEN montant_employe ELSE 0 END)         AS gains,
  SUM(CASE WHEN categorie_paie LIKE 'Déduction%' THEN montant_employe ELSE 0 END) AS deductions
FROM paie.v_lignes_paie
GROUP BY date_paie, poste_budgetaire, description_poste_budgetaire;

-- 4) Fonctions
CREATE OR REPLACE VIEW paie.v_fonctions AS
SELECT
  date_paie,
  categorie_emploi,
  code_emploi,
  titre_emploi,
  SUM(montant_combine)                                  AS total_combine,
  COUNT(DISTINCT matricule)                              AS nb_employes
FROM paie.v_lignes_paie
GROUP BY date_paie, categorie_emploi, code_emploi, titre_emploi;

-- 5) Employés
CREATE OR REPLACE VIEW paie.v_employes AS
SELECT
  date_paie,
  matricule,
  nom_employe,
  SUM(montant_combine)                                          AS total_combine,
  SUM(CASE WHEN categorie_paie = 'Gains' THEN montant_employe ELSE 0 END)         AS gains,
  SUM(CASE WHEN categorie_paie LIKE 'Déduction%' THEN montant_employe ELSE 0 END) AS deductions,
  SUM(part_employeur)                                           AS part_employeur,
  COUNT(*)                                                      AS lignes
FROM paie.v_lignes_paie
GROUP BY date_paie, matricule, nom_employe;

-- 6) Codes
CREATE OR REPLACE VIEW paie.v_codes AS
SELECT
  date_paie,
  code_paie,
  description_code_paie,
  categorie_paie,
  SUM(montant_combine)   AS total_combine,
  SUM(part_employeur)    AS part_employeur,
  COUNT(*)               AS lignes
FROM paie.v_lignes_paie
GROUP BY date_paie, code_paie, description_code_paie, categorie_paie;

-- 7) Heures & primes (via référentiel famille = 'HS' si disponible)
CREATE OR REPLACE VIEW paie.v_heures_primes AS
WITH hs AS (
  SELECT l.*
  FROM paie.v_lignes_paie l
  LEFT JOIN paie.ref_codes_paie r ON r.code_paie = l.code_paie
  WHERE (r.famille = 'HS') OR r.famille IS NULL AND l.categorie_paie ILIKE '%prime%' -- fallback heuristique
)
SELECT
  date_paie,
  poste_budgetaire,
  SUM(montant_employe) AS total_hs,
  COUNT(*)             AS lignes
FROM hs
GROUP BY date_paie, poste_budgetaire;

-- 8) Avantages sociaux
CREATE OR REPLACE VIEW paie.v_avantages AS
SELECT
  date_paie,
  code_paie,
  description_code_paie,
  SUM(part_employeur)                                                        AS part_employeur,
  SUM(CASE WHEN categorie_paie ILIKE 'Assurances%' THEN montant_employe ELSE 0 END) AS retenu_employe,
  SUM(montant_combine)                                                       AS total_combine
FROM paie.v_lignes_paie
GROUP BY date_paie, code_paie, description_code_paie;

-- 9) Turnover (entrées/sorties heuristiques)
CREATE OR REPLACE VIEW paie.v_turnover AS
WITH bounds AS (
  SELECT
    matricule,
    MIN(date_paie) AS first_date,
    MAX(date_paie) AS last_date
  FROM paie.v_lignes_paie
  GROUP BY matricule
),
stamped AS (
  SELECT l.*, b.first_date, b.last_date
  FROM paie.v_lignes_paie l
  JOIN bounds b USING (matricule)
),
entries AS (
  SELECT DISTINCT
    first_date AS date_paie, 'Entree'::text AS type, matricule, nom_employe, poste_budgetaire
  FROM stamped
  WHERE date_paie = first_date
),
exits AS (
  SELECT DISTINCT
    last_date AS date_paie, 'Sortie'::text AS type, matricule, nom_employe, poste_budgetaire
  FROM stamped
  WHERE date_paie = last_date
)
SELECT * FROM entries
UNION ALL
SELECT * FROM exits;

-- 10) Conformité (exemple simple: somme cotisations/impôts par date)
CREATE OR REPLACE VIEW paie.v_conformite AS
SELECT
  date_paie,
  SUM(CASE WHEN categorie_paie ILIKE '%cotisation%' OR categorie_paie ILIKE '%impot%' THEN montant_employe ELSE 0 END)
    AS somme_cotisations
FROM paie.v_lignes_paie
GROUP BY date_paie;





