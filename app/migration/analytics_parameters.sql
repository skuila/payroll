-- migration/analytics_parameters.sql
\set ON_ERROR_STOP on

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'paie') THEN
    EXECUTE 'CREATE SCHEMA paie';
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS paie.param_categories_synonyms (
  categorie TEXT PRIMARY KEY,
  synonyms  TEXT[] NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paie.param_calcul_flags (
  id SMALLINT PRIMARY KEY DEFAULT 1,
  use_sign_fallback BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO paie.param_calcul_flags (id, use_sign_fallback)
VALUES (1, TRUE)
ON CONFLICT (id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP;

-- Exemples de synonymes par défaut
INSERT INTO paie.param_categories_synonyms (categorie, synonyms)
VALUES
  ('Gains', ARRAY['gains','revenu','salaire','brut','base']),
  ('Deductions', ARRAY['deductions','retenues','retenue','debit'])
ON CONFLICT (categorie) DO UPDATE SET updated_at = CURRENT_TIMESTAMP;



