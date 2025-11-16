"""Create PostgreSQL extensions

Revision ID: 000
Revises:
Create Date: 2025-10-12 05:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create PostgreSQL extensions required by PayrollAnalyzer."""

    print("🔌 Création des extensions PostgreSQL...")

    # Extensions essentielles
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    print("  OK: uuid-ossp")

    op.execute('CREATE EXTENSION IF NOT EXISTS "unaccent";')
    print("  OK: unaccent")

    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')
    print("  OK: pg_trgm")

    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    print("  OK: pgcrypto")

    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gist";')
    print("  OK: btree_gist")

    # pgaudit (optionnel - pour audit avancé)
    try:
        op.execute('CREATE EXTENSION IF NOT EXISTS "pgaudit";')
        print("  OK: pgaudit")
    except Exception as e:
        print(f"  WARN: pgaudit non disponible (optionnel) : {e}")

    print("✅ Extensions créées avec succès")


def downgrade() -> None:
    """Drop extensions (dangereux - peut affecter d'autres apps)."""

    print("WARN: Suppression des extensions (DANGER)")

    # Note: Ne pas dropper les extensions en production
    # car elles peuvent être utilisées par d'autres bases/apps

    # op.execute('DROP EXTENSION IF EXISTS "pgaudit";')
    # op.execute('DROP EXTENSION IF EXISTS "btree_gist";')
    # op.execute('DROP EXTENSION IF EXISTS "pgcrypto";')
    # op.execute('DROP EXTENSION IF EXISTS "pg_trgm";')
    # op.execute('DROP EXTENSION IF EXISTS "unaccent";')
    # op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')

    print("ℹ️ Extensions non supprimées (sécurité)")
