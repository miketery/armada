#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

container="armada-postgres-1"

if [ "$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null)" != "true" ]; then
    echo "Starting postgres..."
    docker compose -f scripts/docker-compose.yml up -d
    echo "Waiting for postgres to accept connections..."
    until docker exec "$container" pg_isready -U armada -q 2>/dev/null; do
        sleep 0.5
    done
    echo "Postgres ready."
else
    echo "Postgres already running."
fi

echo "Running migrations..."
uv run alembic upgrade head

echo "Starting server..."
exec uv run uvicorn armada.main:app --reload
