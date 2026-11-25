"""Alembic environment — async, autogenerate from app.models."""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import app.models  # noqa: F401,E402 — registers all models
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_settings().database_url
    # Alembic offline needs a sync URL. Only the async SQLite driver
    # suffix is stripped; postgresql+psycopg:// is already usable
    # synchronously (psycopg3), so it must be kept.
    url = url.replace("+aiosqlite", "")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = get_settings().database_url
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    connectable = async_engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
