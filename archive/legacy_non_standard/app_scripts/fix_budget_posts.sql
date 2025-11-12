-- Créer les postes budgétaires par défaut
-- Fix: Foreign key constraint violation pour budget_post_id

-- Poste par défaut (ID=1) - utilisé quand aucun poste n'est spécifié
INSERT INTO reference.budget_posts (post_id, code, description, category, is_active)
VALUES 
    (1, 'NON_CLASSE', 'Non classé', 'general', true)
ON CONFLICT (post_id) DO NOTHING;

-- Postes budgétaires communs
INSERT INTO reference.budget_posts (post_id, code, description, category, is_active)
VALUES 
    (2, 'SALAIRES_BASE', 'Salaires de base', 'personnel', true),
    (3, 'PRIMES', 'Primes et bonus', 'personnel', true),
    (4, 'CHARGES_SOCIALES', 'Charges sociales', 'charges', true),
    (5, 'AVANTAGES', 'Avantages sociaux', 'personnel', true),
    (6, 'HEURES_SUPP', 'Heures supplémentaires', 'personnel', true),
    (7, 'INDEMNITES', 'Indemnités diverses', 'personnel', true),
    (8, 'FORMATION', 'Formation professionnelle', 'formation', true),
    (9, 'REMBOURSEMENTS', 'Remboursements', 'general', true),
    (10, 'AUTRES', 'Autres dépenses', 'general', true)
ON CONFLICT (post_id) DO NOTHING;

-- Afficher résultat
SELECT post_id, code, description, category, is_active 
FROM reference.budget_posts 
ORDER BY post_id;

