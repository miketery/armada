from fastapi import FastAPI

from armada.modules.users import router as users_router

app = FastAPI(title="Armada", version="0.1.0")

app.include_router(users_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
