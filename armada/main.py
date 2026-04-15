from fastapi import FastAPI

from armada.routers.products import products_router
from armada.routers.users import users_router

app = FastAPI(title="Armada", version="0.1.0")

API_PREFIX = "/api"

app.include_router(users_router, prefix=API_PREFIX)
app.include_router(products_router, prefix=API_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok"}
