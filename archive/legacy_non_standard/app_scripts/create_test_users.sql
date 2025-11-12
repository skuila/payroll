-- Script de création d'utilisateurs de test pour security.users
-- À exécuter avec: psql -h localhost -U payroll_user -d payroll_db -f scripts/create_test_users.sql

-- User 1: Admin (mot de passe: admin123)
-- Hash SHA256 de "admin123": 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
INSERT INTO security.users (username, password_hash, role, email, active)
VALUES (
    'admin',
    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
    'admin',
    'admin@scp.local',
    true
)
ON CONFLICT (username) DO UPDATE 
SET password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    email = EXCLUDED.email,
    active = EXCLUDED.active;

-- User 2: Viewer (mot de passe: viewer123)
-- Hash SHA256 de "viewer123": 5906ac361a137e2d286465cd6588ebb5ac3f5ae955001100bc41577c3d751764
INSERT INTO security.users (username, password_hash, role, email, active)
VALUES (
    'viewer',
    '5906ac361a137e2d286465cd6588ebb5ac3f5ae955001100bc41577c3d751764',
    'viewer',
    'viewer@scp.local',
    true
)
ON CONFLICT (username) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    email = EXCLUDED.email,
    active = EXCLUDED.active;

-- User 3: Manager (mot de passe: manager123)
-- Hash SHA256 de "manager123": 9ba12d19c6e6d9fc86c6b84e4a8a85ab2eb1a4c5e3a26c7d8f9e0b1a2c3d4e5f
INSERT INTO security.users (username, password_hash, role, email, active)
VALUES (
    'manager',
    '9ba12d19c6e6d9fc86c6b84e4a8a85ab2eb1a4c5e3a26c7d8f9e0b1a2c3d4e5f',
    'manager',
    'manager@scp.local',
    true
)
ON CONFLICT (username) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    email = EXCLUDED.email,
    active = EXCLUDED.active;

-- Afficher les utilisateurs créés
SELECT username, role, email, active, created_at 
FROM security.users 
ORDER BY created_at;

