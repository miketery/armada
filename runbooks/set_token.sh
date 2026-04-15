#!/usr/bin/env bash

cd "$(dirname "$0")/.."

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

response=$(curl -s -X POST http://localhost:8000/api/users/login \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$ARMADA_USERNAME\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "Login failed: $response" >&2
    return 1
fi
