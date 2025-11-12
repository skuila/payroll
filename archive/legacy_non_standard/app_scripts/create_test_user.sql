-- Créer un utilisateur de test pour les imports
-- UUID fixe pour faciliter les tests

INSERT INTO security.users (
    user_id, 
    username, 
    password_hash, 
    role, 
    email, 
    active
) VALUES (
    '00000000-0000-0000-0000-000000000000'::uuid,
    'test_user',
    'dummy_hash_for_testing',
    'admin',
    'test@payroll.local',
    TRUE
)
ON CONFLICT (user_id) DO NOTHING;

-- Vérifier
SELECT user_id, username, role FROM security.users WHERE username = 'test_user';

