import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url


# ---------------------------------------------------------
# Project root
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[2]

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


# ---------------------------------------------------------
# Environment variables
# ---------------------------------------------------------

load_dotenv(ROOT_DIR / ".env")


# ---------------------------------------------------------
# Import SQLAlchemy models
# ---------------------------------------------------------

from services.api.app.db.models import Base


# ---------------------------------------------------------
# Alembic configuration
# ---------------------------------------------------------

config = context.config

database_url = os.getenv("DATABASE_URL")

if database_url:
    connection_url = make_url(database_url)
    if connection_url.host == "localhost":
        connection_url = connection_url.set(host="127.0.0.1")
    database_url = connection_url.update_query_dict({"connect_timeout": connection_url.query.get("connect_timeout", "5")}).render_as_string(hide_password=False)
    # ConfigParser interprets percent signs; URLs may encode passwords/options.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))


# Configure logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Metadata used by Alembic autogenerate
target_metadata = Base.metadata


# ---------------------------------------------------------
# Alembic object filter
# ---------------------------------------------------------

def include_object(object_, name, type_, reflected, compare_to):
    """
    Prevent Alembic from trying to delete tables that belong
    to PostgreSQL/PostGIS extensions.

    Alembic should manage only tables represented by our
    SQLAlchemy models.
    """

    if type_ == "table" and reflected and compare_to is None:
        return False

    return True


# ---------------------------------------------------------
# Offline migrations
# ---------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations without creating a database connection.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------
# Online migrations
# ---------------------------------------------------------

def run_migrations_online() -> None:
    """
    Run migrations using a live database connection.
    """

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------
# Run appropriate migration mode
# ---------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
