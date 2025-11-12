-- migration/seed_dim_code_paie_standards.sql
\set ON_ERROR_STOP on

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'paie') THEN
    EXECUTE 'CREATE SCHEMA paie';
  END IF;
END $$;

-- Codes standards (à compléter selon votre référentiel)
INSERT INTO paie.dim_code_paie (code_paie, libelle_paie, categorie_paie, est_imposable, est_cotisation, actif)
VALUES
  ('101','Salaire régulier','Gains', true, false, true),
  ('105','Heures supplémentaires','Gains', true, false, true),
  ('106','Prime','Gains', true, false, true),
  ('107','Bonus','Gains', true, false, true),
  ('111','Indemnité','Gains', true, false, true),
  ('151','Allocation','Gains', true, false, true),
  ('153','Avantage imposable','Gains', true, false, true),

  ('450','RRQ employé','Deductions_legales', false, true, true),
  ('451','AE employé','Deductions_legales', false, true, true),
  ('504','Pension alimentaire','Deductions', false, false, true),
  ('520','Cotisation syndicale','Deductions', false, false, true),
  ('522','Impôt fédéral','Deductions_legales', false, false, true),
  ('523','Impôt provincial','Deductions_legales', false, false, true),
  ('580','REER','Deductions', false, false, true),
  ('581','Épargne','Deductions', false, false, true),

  ('701','Assurance collective employé','Deductions_legales', false, true, true),
  ('702','Assurance vie','Assurances', false, true, true),
  ('703','Assurance invalidité','Assurances', false, true, true),
  ('704','Assurance médicaments','Assurances', false, true, true),
  ('705','Assurance dentaire','Assurances', false, true, true),
  ('801','RRQ employeur','Assurances', false, true, true),
  ('802','AE employeur','Assurances', false, true, true),
  ('803','FSS employeur','Assurances', false, true, true),
  ('804','RQAP employeur','Assurances', false, true, true),
  ('805','CNESST employeur','Assurances', false, true, true),
  ('806','Régime retraite employeur','Assurances', false, true, true),
  ('807','Assurance collective employeur','Assurances', false, true, true),
  ('808','Autres charges sociales','Assurances', false, true, true)
ON CONFLICT (code_paie) DO UPDATE SET
  libelle_paie = EXCLUDED.libelle_paie,
  categorie_paie = EXCLUDED.categorie_paie,
  est_imposable = EXCLUDED.est_imposable,
  est_cotisation = EXCLUDED.est_cotisation,
  actif = EXCLUDED.actif,
  updated_at = CURRENT_TIMESTAMP;



