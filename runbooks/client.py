import os

import httpx

BASE_URL = os.environ.get("ARMADA_BASE_URL", "http://localhost:8000")


def get_client() -> httpx.Client:
    token = os.environ.get("TOKEN", "")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
