"""
Alembic Environment Configuration — PayrollAnalyzer v2.0

Lit DATABASE_URL depuis .env (via python-dotenv).
Pas d'URL en dur dans alembic.ini.
"""

from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.config.connection_standard import get_dsn

# Charger variables d'environnement depuis .env
from dotenv import load_dotenv

load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Obtient l'URL SQLAlchemy via le module de connexion standard."""

    alembic_url = os.getenv("ALEMBIC_DATABASE_URL")
    if alembic_url:
        print("OK: Utilisation ALEMBIC_DATABASE_URL depuis .env")
        return alembic_url

    try:
        dsn = get_dsn()
    except RuntimeError as exc:
        ini_url = config.get_main_option("sqlalchemy.url")
        if ini_url:
            print("WARN: Utilisation URL depuis alembic.ini (fallback)")
            return ini_url
        raise ValueError("❌ Aucun DSN disponible pour Alembic") from exc

    if dsn.startswith("postgresql+psycopg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg://", 1)

    return dsn


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override sqlalchemy.url avec DATABASE_URL depuis .env
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
