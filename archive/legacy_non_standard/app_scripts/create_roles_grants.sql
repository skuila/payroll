-- Création des rôles PostgreSQL pour PayrollAnalyzer v2.0
-- Exécuter en tant que superuser (postgres)

\echo '🔐 Création des rôles PostgreSQL...'


CREATE ROLE payroll_owner WITH
    LOGIN
     PASSWORD '<REDACTED_PAYROLL_OWNER_PASSWORD>'
    CREATEDB
    CREATEROLE
    INHERIT
    NOREPLICATION
    CONNECTION LIMIT -1;

COMMENT ON ROLE payroll_owner IS 'Propriétaire des schémas PayrollAnalyzer - Peut effectuer DDL';

\echo '  ✓ payroll_owner créé'


CREATE ROLE payroll_app WITH
    LOGIN
     PASSWORD '<REDACTED_PAYROLL_APP_PASSWORD>'
    INHERIT
    NOREPLICATION
    CONNECTION LIMIT 50;

COMMENT ON ROLE payroll_app IS 'Rôle applicatif PayrollAnalyzer - DML uniquement';

\echo '  ✓ payroll_app créé'


CREATE ROLE payroll_ro WITH
    LOGIN
     PASSWORD '<REDACTED_PAYROLL_RO_PASSWORD>'
    INHERIT
    NOREPLICATION
    CONNECTION LIMIT 20;

COMMENT ON ROLE payroll_ro IS 'Rôle lecture seule PayrollAnalyzer - SELECT uniquement';

\echo '  ✓ payroll_ro créé'


\c payroll_db


\echo '🔑 Application des GRANTs...'

GRANT USAGE ON SCHEMA core TO payroll_app, payroll_ro;
GRANT ALL ON SCHEMA core TO payroll_owner;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core TO payroll_app;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO payroll_ro;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core TO payroll_app;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA core TO payroll_ro;

ALTER DEFAULT PRIVILEGES IN SCHEMA core
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO payroll_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA core
    GRANT SELECT ON TABLES TO payroll_ro;

\echo '  ✓ core: app (DML), ro (SELECT)'

GRANT USAGE ON SCHEMA payroll TO payroll_app, payroll_ro;
GRANT ALL ON SCHEMA payroll TO payroll_owner;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA payroll TO payroll_app;
GRANT SELECT ON ALL TABLES IN SCHEMA payroll TO payroll_ro;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA payroll TO payroll_app;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA payroll TO payroll_ro;

ALTER DEFAULT PRIVILEGES IN SCHEMA payroll
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO payroll_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA payroll
    GRANT SELECT ON TABLES TO payroll_ro;

\echo '  ✓ payroll: app (DML), ro (SELECT)'

GRANT USAGE ON SCHEMA reference TO payroll_app, payroll_ro;
GRANT ALL ON SCHEMA reference TO payroll_owner;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA reference TO payroll_app;
GRANT SELECT ON ALL TABLES IN SCHEMA reference TO payroll_ro;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA reference TO payroll_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA reference
    GRANT SELECT, INSERT, UPDATE ON TABLES TO payroll_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA reference
    GRANT SELECT ON TABLES TO payroll_ro;

\echo '  ✓ reference: app (INSERT/UPDATE), ro (SELECT)'

GRANT USAGE ON SCHEMA security TO payroll_app, payroll_ro;
GRANT ALL ON SCHEMA security TO payroll_owner;

GRANT SELECT ON security.users TO payroll_app, payroll_ro;

GRANT SELECT, INSERT ON security.audit_logs TO payroll_app;
GRANT SELECT ON security.audit_logs TO payroll_ro;

REVOKE DELETE ON security.audit_logs FROM payroll_app, payroll_ro;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA security TO payroll_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA security
    GRANT SELECT, INSERT ON TABLES TO payroll_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA security
    GRANT SELECT ON TABLES TO payroll_ro;

\echo '  ✓ security: app (SELECT/INSERT audit), ro (SELECT), DELETE interdit'


GRANT SELECT ON ALL MATERIALIZED VIEWS IN SCHEMA payroll TO payroll_app, payroll_ro;

\echo '  ✓ Vues matérialisées: app (SELECT + REFRESH), ro (SELECT)'


\echo ''
\echo '✅ Rôles et GRANTs configurés avec succès !'
\echo ''
\echo 'Rôles créés :'
\echo '  - payroll_owner : DDL (création schémas, tables, migrations)'
\echo '  - payroll_app   : DML (INSERT/UPDATE/DELETE/SELECT, runtime)'
\echo '  - payroll_ro    : SELECT uniquement (analytics, BI)'
\echo ''
\echo 'Configuration recommandée :'
\echo '  - Migrations Alembic : utiliser payroll_owner'
\echo '  - Application Python : utiliser payroll_app'
\echo '  - Dashboards/BI     : utiliser payroll_ro'
\echo ''
\echo 'Connexion DATABASE_URL (pour .env) :'
  DATABASE_URL=postgresql://payroll_app:<REDACTED_PAYROLL_APP_PASSWORD>@localhost:5432/payroll_db
\echo ''

