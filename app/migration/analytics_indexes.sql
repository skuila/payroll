-- Indexes recommandés pour améliorer les filtres des vues analytics

-- Staging paie
CREATE INDEX IF NOT EXISTS idx_stg_paie_date_paie
  ON paie.stg_paie_transactions (date_paie);

CREATE INDEX IF NOT EXISTS idx_stg_paie_matricule_date
  ON paie.stg_paie_transactions (matricule, date_paie);

CREATE INDEX IF NOT EXISTS idx_stg_paie_poste_date
  ON paie.stg_paie_transactions (poste_budgetaire, date_paie);

CREATE INDEX IF NOT EXISTS idx_stg_paie_code_date
  ON paie.stg_paie_transactions (code_paie, date_paie);

CREATE INDEX IF NOT EXISTS idx_stg_paie_categorie_date
  ON paie.stg_paie_transactions (categorie_paie, date_paie);

-- Référentiel employés
CREATE INDEX IF NOT EXISTS idx_employees_matricule_norm
  ON core.employees (matricule_norm);





