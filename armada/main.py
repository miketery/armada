from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from armada.routers.products import products_router
from armada.routers.users import users_router

app = FastAPI(title="Armada", version="0.1.0")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"

API_PREFIX = "/api"

app.include_router(users_router, prefix=API_PREFIX)
app.include_router(products_router, prefix=API_PREFIX)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{page}.html", response_class=HTMLResponse)
async def page(page: str):
    file_path = FRONTEND_DIR / f"{page}.html"
    if not file_path.is_file():
        return HTMLResponse("Not found", status_code=404)
    return FileResponse(file_path)
