from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from armada.config import settings


class DatabaseSession(AsyncSession):
    """Custom async session — extend for commit hooks, logging, etc."""


_engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
_session_factory: async_sessionmaker[DatabaseSession] = async_sessionmaker(
    _engine,
    expire_on_commit=False,
    class_=DatabaseSession,
)


def get_database_session() -> DatabaseSession:
    """Return a disposable database session instance."""
    return _session_factory()


async def database_dependency() -> AsyncGenerator[DatabaseSession, None]:
    """Yield a session for FastAPI dependency injection."""
    async with get_database_session() as session:
        yield session


@asynccontextmanager
async def get_database() -> AsyncGenerator[DatabaseSession, None]:
    """Provide a commit/rollback-protected session context for non-DI usage."""
    async with get_database_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Dispose the global engine and close pooled connections."""
    await _engine.dispose()
