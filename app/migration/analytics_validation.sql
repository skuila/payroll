-- migration/analytics_validation.sql
-- Vérifications d'intégrité de la vue canonique et des vues d'agrégation

-- 1) Colonnes attendues dans paie.v_lignes_paie
-- (Utilise information_schema pour vérifier la présence)
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'paie' AND table_name = 'v_lignes_paie'
ORDER BY ordinal_position;

-- 2) date_paie non nulle sur les lignes
SELECT COUNT(*) AS nb_lignes_sans_date
FROM paie.v_lignes_paie
WHERE date_paie IS NULL;

-- 3) montant_combine n'est pas recalculé ici (simplement présent); distribution de nulls
SELECT
  COUNT(*) FILTER (WHERE montant_combine IS NULL) AS nb_nulls,
  COUNT(*)                                        AS nb_total
FROM paie.v_lignes_paie;

-- 4) Jointure identité: nom_employe présent quand matricule connu
SELECT COUNT(*) AS nb_employes_sans_nom
FROM paie.v_lignes_paie
WHERE matricule IS NOT NULL AND (nom_employe IS NULL OR btrim(nom_employe) = '');

-- 5) Vues d'agrégation accessibles
SELECT 'v_masse_salariale' AS vue, COUNT(*) AS n FROM paie.v_masse_salariale
UNION ALL
SELECT 'v_categories', COUNT(*) FROM paie.v_categories
UNION ALL
SELECT 'v_postes', COUNT(*) FROM paie.v_postes
UNION ALL
SELECT 'v_fonctions', COUNT(*) FROM paie.v_fonctions
UNION ALL
SELECT 'v_employes', COUNT(*) FROM paie.v_employes
UNION ALL
SELECT 'v_codes', COUNT(*) FROM paie.v_codes;





