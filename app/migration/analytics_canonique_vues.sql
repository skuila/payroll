-- migration/analytics_canonique_vues.sql
-- Vue canonique des lignes de paie: seule source de vérité pour l'analytics paie
-- Idempotent: crée le schéma si absent et remplace la vue

-- 1) Schéma (lecture analytique)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'paie') THEN
    EXECUTE 'CREATE SCHEMA paie';
  END IF;
END$$;

-- 2) Vue canonique
-- Note:
-- - On s'appuie sur paie.stg_paie_transactions (staging) pour les champs descriptifs et montants,
--   et sur core.employees pour l'identité employé (matricule_norm, nom).
-- - montant_combine est pris tel quel (aucun recalcul).
-- - date_paie est la période unique de vérité.
-- - numero_ligne est un ordinal stable par ordre logique.
CREATE OR REPLACE VIEW paie.v_lignes_paie AS
SELECT
  ROW_NUMBER() OVER (
    ORDER BY s.date_paie NULLS LAST,
             s.matricule NULLS LAST,
             s.code_paie NULLS LAST,
             s.poste_budgetaire NULLS LAST
  )                                                          AS numero_ligne,
  s.date_paie                                                AS date_paie,
  e.matricule_norm                                           AS matricule,
  COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')) AS nom_employe,
  s.categorie_emploi,
  s.code_emploi,
  s.titre_emploi,
  s.categorie_paie,
  s.code_paie,
  s.description_code_paie,
  s.poste_budgetaire,
  s.description_poste_budgetaire,
  s.montant_employe::numeric                                 AS montant_employe,
  s.part_employeur::numeric                                  AS part_employeur,
  s.montant_combine::numeric                                 AS montant_combine
FROM paie.stg_paie_transactions s
LEFT JOIN core.employees e
  ON e.matricule_norm = s.matricule;

COMMENT ON VIEW paie.v_lignes_paie IS
'Vue canonique Analytics Paie - Source unique de vérité. 
Champs de paie issus du staging (paie.stg_paie_transactions), identité employé issue de core.employees.
date_paie = période exacte; montant_combine non recalculé.';





