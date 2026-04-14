#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

container="armada-postgres-1"

echo "Dropping and recreating database..."
docker exec "$container" psql -U armada -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "Running migrations..."
uv run alembic upgrade head

echo "Running bootstrap..."
uv run python runbooks/bootstrap.py

echo "Done."
