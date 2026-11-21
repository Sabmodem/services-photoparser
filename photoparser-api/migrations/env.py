import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, event
from sqlalchemy import Pool
from sqlalchemy.pool import NullPool
from sqlalchemy.pool import StaticPool

from alembic import context

# Add the parent directory to sys.path to import our models
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the database models
from database import Base, SQLALCHEMY_DATABASE_URL

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target_metadata from the models
# This enables autogenerate support for async models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use DATABASE_URL from environment variable or default to SQLALCHEMY_DATABASE_URL
    url = os.environ.get("DATABASE_URL") or SQLALCHEMY_DATABASE_URL
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
    Uses sync engine with pg8000 driver for simplicity.

    """
    # Use DATABASE_URL from environment variable or default to SQLALCHEMY_DATABASE_URL
    url = os.environ.get("DATABASE_URL") or SQLALCHEMY_DATABASE_URL

    # Convert asyncpg URL to pg8000 for sync migrations
    sync_url = url.replace("postgresql+asyncpg", "postgresql+pg8000")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        url=sync_url,
        poolclass=NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
