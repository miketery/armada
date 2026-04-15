# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Armada is a FastAPI-based user authentication and session management service. Python 3.13, PostgreSQL 17 (via Docker on port 6130), fully async.

## Toolchain

- **uv** for package management and running Python (`uv sync`, `uv run`)
- **ruff** for linting and formatting (line length 100, rules: E, F, I, N, W, UP)
- **alembic** for database migrations (async, autogenerate from models)
- **SQLAlchemy 2.0+** async ORM with asyncpg driver
- **Pydantic** for request/response schemas (in `armada/types/`)

## Common Commands

```bash
# Start app (postgres + migrations + uvicorn with reload on :8000)
./scripts/start.sh

# Install/sync dependencies
uv sync

# Lint and format
uv run ruff check .
uv run ruff format .

# Database migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
uv run alembic downgrade -1

# Test migration reversibility (downgrade 1, upgrade 1)
./scripts/alembic_bounce.sh

# Reset database (drop schema, migrate, bootstrap test user)
./scripts/reset_db.sh

# Runbooks (manual operations)
uv run python runbooks/bootstrap.py          # seed test user
source runbooks/set_token.sh                 # login and export TOKEN
uv run python runbooks/users.py me           # test authenticated endpoint
```

## Architecture

Layered architecture with clear separation:

```
routers/  →  managers/  →  models/
(API)        (business)     (ORM)
   ↕             ↕
types/        db/
(Pydantic)    (engine/session)
```

- **models/** — SQLAlchemy ORM models. All inherit from `TimestampedBase` (UUID pk, created_at, updated_at) or `Base` (adds soft-delete `is_deleted` flag).
- **managers/** — Business logic. Each manager takes a DB session and provides CRUD + domain operations.
- **routers/** — FastAPI route handlers. Thin layer that delegates to managers.
- **types/** — Pydantic schemas for API request/response validation.
- **db/** — Database engine, async session factory, base model classes. Lazy engine init with `get_engine()`.
- **auth/** — FastAPI dependencies for bearer token authentication. `CurrentUser` and `Database` dependency types.

### DBO Pattern

The project follows a DBO (Database Object) pattern for database object handling, keeping database interaction logic organized through manager classes that wrap SQLAlchemy operations.

### Key Conventions

- All database operations are async (asyncpg + SQLAlchemy async sessions)
- Auth uses bearer tokens stored in `user_sessions` table with expiration
- Password hashing via Argon2 (passlib)
- Config via `pydantic-settings` with `ARMADA_` env prefix
- Alembic migrations use ruff as post-write hook for formatting
- Docker Compose for PostgreSQL lives in `scripts/docker-compose.yml`
- Database URL: `postgresql+asyncpg://armada:armada@localhost:6130/armada`
