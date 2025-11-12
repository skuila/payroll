-- Script d'ajout de colonnes - Genere le 2025-11-10T00:48:22.192148
-- Base de donnees: payroll_db

\c payroll_db

-- AJOUT DE COLONNES A core.employees
-- Departement de l'employe
ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS department VARCHAR(100) NULL;

-- Poste occupe
ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS job_title VARCHAR(150) NULL;

-- Date d'embauche
ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS hire_date DATE NULL;

-- Adresse email
ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS email VARCHAR(150) NULL;

-- Numero de telephone
ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS phone VARCHAR(20) NULL;

-- CREATION D'INDEX
CREATE INDEX IF NOT EXISTS idx_employees_department ON core.employees(department);
CREATE INDEX IF NOT EXISTS idx_employees_email ON core.employees(email);

-- FIN DU SCRIPT
\q
