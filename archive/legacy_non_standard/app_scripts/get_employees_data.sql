-- Salaires nets par employé (2025-08-28)
SELECT 
  COALESCE(e.nom_complet, e.nom_norm || ' ' || COALESCE(e.prenom_norm,''), s.matricule) AS nom_employe,
  COALESCE(s.categorie_emploi, 'Non defini') AS categorie,
  COALESCE(s.titre_emploi, 'Non defini') AS titre,
  s.date_paie,
  CASE WHEN e.statut = 'inactif' THEN 'inactif' ELSE 'actif' END AS statut,
  ROUND(SUM(s.montant_cents) / 100.0, 2) AS salaire_net
FROM paie.stg_paie_transactions s
LEFT JOIN core.employees e ON (e.matricule = s.matricule OR e.matricule_norm = s.matricule)
WHERE s.date_paie = '2025-08-28'
GROUP BY e.nom_complet, e.nom_norm, e.prenom_norm, s.matricule, s.categorie_emploi, s.titre_emploi, s.date_paie, e.statut
ORDER BY salaire_net DESC
LIMIT 25;




