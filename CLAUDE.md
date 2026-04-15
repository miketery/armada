# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Armada is a FastAPI-based user authentication, session management, and product catalog service. Python 3.13, PostgreSQL 17 (via Docker on port 6130), fully async. All API routes are prefixed with `/api`.

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
uv run python runbooks/seed_products.py      # seed 15 guns from data/guns.csv
uv run python runbooks/products.py list      # list all products
uv run python runbooks/products.py list --type gun
uv run python runbooks/products.py create-gun --name "..." --description "..." \
  --msrp 799 --caliber "9mm" --action-type semi-automatic \
  --weight-lbs 1.5 --category pistol --manufacturer "..."
uv run python runbooks/products.py update-gun <uuid> --msrp 899
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
- **auth/** — FastAPI dependencies for bearer token authentication. `UserDependency`, `SuperUserDependency`, and `Database` dependency types.

### DBO Pattern

The project follows a DBO (Database Object) pattern for database object handling, keeping database interaction logic organized through manager classes that wrap SQLAlchemy operations.

### Products (Joined Table Inheritance)

Products use SQLAlchemy joined table inheritance. `products` is the parent table (inherits `Base` with soft-delete), and child tables like `product_guns` extend it with type-specific columns. The `product_type` discriminator column controls polymorphism.

- **Adding a new product type:** Create a new child model inheriting from `Product`, set `polymorphic_identity`, add a FK `id` column, and add type-specific columns. The manager uses `with_polymorphic(Product, "*")` so new types are auto-discovered.
- **`updated_at` with inheritance:** Child-only updates don't trigger `onupdate` on the parent row. The manager explicitly sets `product.updated_at = func.now()` in update methods to ensure the parent timestamp is touched.
- **Superuser-only mutations:** Create, update, and delete require `SuperUserDependency`. Read endpoints use `UserDependency`.
- **Seed data:** `data/guns.csv` contains 15 firearms (3 each: semi-auto rifles, bolt-action rifles, pistols, revolvers, shotguns).

### Key Conventions

- All database operations are async (asyncpg + SQLAlchemy async sessions)
- Auth uses bearer tokens stored in `user_sessions` table with expiration
- Password hashing via Argon2 (passlib)
- Config via `pydantic-settings` with `ARMADA_` env prefix
- Alembic migrations use ruff as post-write hook for formatting
- Docker Compose for PostgreSQL lives in `scripts/docker-compose.yml`
- Database URL: `postgresql+asyncpg://armada:armada@localhost:6130/armada`
