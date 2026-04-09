"""
NotingHill — main.py
FastAPI application entry point.
"""
import mimetypes
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    APP_NAME,
    APP_VERSION,
    PORT,
    HOST,
    WORKERS,
    DB_PATH,
    DATA_DIR,
    THUMBNAILS_DIR,
    CACHE_DIR,
    LOG_DIR,
    STATIC_DIR,
)
from app.db.connection import init_db
from app.core.job_queue import start_workers
from app.services.indexing_service import resume_incomplete_jobs
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_search import router as search_router
from app.api.routes_timeline import router as timeline_router
from app.api.routes_duplicates import router as duplicates_router
from app.api.routes_indexing import router as indexing_router
from app.api.routes_settings import router as settings_router
from app.api.routes_images import router as images_router

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")

for d in (DATA_DIR, THUMBNAILS_DIR, CACHE_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

init_db(DB_PATH)

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        f"http://localhost:{PORT}",
        f"http://127.0.0.1:{PORT}",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(search_router)
app.include_router(timeline_router)
app.include_router(duplicates_router)
app.include_router(indexing_router)
app.include_router(settings_router)
app.include_router(images_router)

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("assets/"):
            return {"error": "Asset not found"}
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"error": "Frontend not built. Run: npm run build in /frontend"}
else:
    @app.get("/")
    def root():
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "status": "API running",
            "note": "Frontend not built. Run npm run build in /frontend first.",
            "api_docs": f"http://{HOST}:{PORT}/api/docs",
        }


@app.on_event("startup")
async def on_startup():
    start_workers(WORKERS)
    resumed = resume_incomplete_jobs()
    if resumed:
        print(f"[IndexResume] resumed jobs: {resumed}")

    def _open():
        time.sleep(1.5)
        webbrowser.open(f"http://{HOST}:{PORT}")

    threading.Thread(target=_open, daemon=True).start()


@app.on_event("shutdown")
async def on_shutdown():
    from app.core.job_queue import stop_workers

    stop_workers()


if __name__ == "__main__":
    print(
        f"""
╔══════════════════════════════════════════╗
║          N O T I N G H I L L            ║
║     Local File Intelligence System      ║
╠══════════════════════════════════════════╣
║  http://{HOST}:{PORT}
║  API Docs: http://{HOST}:{PORT}/api/docs
╚══════════════════════════════════════════╝
    """
    )
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
