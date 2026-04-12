#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

response=$(curl -s -X POST http://localhost:8000/users/login \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

token=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null)

if [ -z "$token" ]; then
    echo "Login failed: $response" >&2
    return 1 2>/dev/null || exit 1
fi

export TOKEN="$token"
echo "TOKEN set."
