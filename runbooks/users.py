import json
import sys

from client import get_client


def me():
    with get_client() as client:
        resp = client.get("/users/me")
        resp.raise_for_status()
        print(json.dumps(resp.json(), indent=2))


commands = {"me": me}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f"Usage: uv run runbooks/users.py [{' | '.join(commands)}]")
        sys.exit(1)
    commands[sys.argv[1]]()
