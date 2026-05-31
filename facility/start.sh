#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

PYTHON="${PYTHON:-../.venv/bin/python}"
UVICORN="${UVICORN:-../.venv/bin/uvicorn}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8008}"
DB_PATH="${DB_PATH:-data/ffl.sqlite}"

if [[ ! -x "$PYTHON" ]]; then
  echo "Python executable not found at: $PYTHON" >&2
  echo "Run this from the existing armada checkout, or set PYTHON=/path/to/python." >&2
  exit 1
fi

if [[ ! -x "$UVICORN" ]]; then
  echo "Uvicorn executable not found at: $UVICORN" >&2
  echo "Run this from the existing armada checkout, or set UVICORN=/path/to/uvicorn." >&2
  exit 1
fi

if [[ ! -f "0426-ffl-list.csv" ]]; then
  echo "Missing 0426-ffl-list.csv in $APP_DIR" >&2
  exit 1
fi

if [[ ! -f "data/2025_Gaz_zcta_national.zip" ]]; then
  echo "Missing data/2025_Gaz_zcta_national.zip" >&2
  echo "Download it from:" >&2
  echo "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_zcta_national.zip" >&2
  exit 1
fi

if [[ ! -f "$DB_PATH" || "${FORCE_IMPORT:-0}" == "1" ]]; then
  echo "Loading FFL data into SQLite..."
  "$PYTHON" -m app.import_data --db "$DB_PATH"
fi

echo "Starting FFL License Map at http://$HOST:$PORT"
exec "$UVICORN" app.main:app --host "$HOST" --port "$PORT"

