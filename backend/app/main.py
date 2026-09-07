import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import DATA_DIR, SNAPSHOTS_DIR, FACES_DIR
from .database import init_db
from .routes.users import router as users_router
from .routes.attendance import router as attendance_router
from .routes.unknown import router as unknown_router
from .routes.calibration import router as calibration_router
import asyncio
from .routes.camera import router as camera_router, pipeline, background_pipeline_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("campus_attendance")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables and pre-load vectors
    logger.info("Initializing Smart Campus Face Recognition Backend...")
    await init_db()
    await pipeline.reload_settings()
    
    # Start continuous non-blocking frame processor & MJPEG streamer
    worker_task = asyncio.create_task(background_pipeline_worker())
    logger.info("Database initialized, AI models loaded, and camera worker active.")
    yield
    # Shutdown
    logger.info("Shutting down Campus Face Recognition Backend...")
    worker_task.cancel()

app = FastAPI(
    title="Smart Campus Crowd Face Recognition & Attendance API",
    description="High-performance, privacy-conscious multi-target face recognition surveillance and automated attendance system.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware (Enable React / Vite frontend connectivity)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static image directories
app.mount("/data/faces", StaticFiles(directory=str(FACES_DIR)), name="faces")
app.mount("/data/snapshots", StaticFiles(directory=str(SNAPSHOTS_DIR)), name="snapshots")

# Include Routers
app.include_router(camera_router)
app.include_router(users_router)
app.include_router(attendance_router)
app.include_router(unknown_router)
app.include_router(calibration_router)

from fastapi.responses import FileResponse
from .config import BASE_DIR

PROJECT_ROOT = BASE_DIR.parent
PPTX_MINIMAL_FILE = PROJECT_ROOT / "Smart_Campus_Face_Attendance_Tech_Expo_Minimal.pptx"
PPTX_EXPO_FILE = PROJECT_ROOT / "Smart_Campus_Face_Attendance_Tech_Expo.pptx"
PPTX_FILE = PROJECT_ROOT / "Smart_Campus_Face_Attendance_System.pptx"
HTML_PRESENTATION_FILE = PROJECT_ROOT / "presentation_preview.html"

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Smart Campus AI Surveillance & Attendance Engine",
        "version": "2.0.0"
    }

@app.get("/presentation")
async def get_presentation_html():
    if HTML_PRESENTATION_FILE.exists():
        return FileResponse(str(HTML_PRESENTATION_FILE), media_type="text/html")
    return {"error": "Presentation preview not found"}

@app.get("/api/presentation/download")
async def download_presentation_pptx():
    target = PPTX_MINIMAL_FILE if PPTX_MINIMAL_FILE.exists() else (PPTX_EXPO_FILE if PPTX_EXPO_FILE.exists() else PPTX_FILE)
    if target.exists():
        return FileResponse(
            str(target),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=target.name
        )
    return {"error": "Presentation file not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
