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


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[DatabaseSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def _get_session_factory() -> async_sessionmaker[DatabaseSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            expire_on_commit=False,
            class_=DatabaseSession,
        )
    return _session_factory


def get_database_session() -> DatabaseSession:
    """Return a disposable database session instance."""
    return _get_session_factory()()


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
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
