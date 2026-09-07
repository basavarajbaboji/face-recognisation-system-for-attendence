import cv2
import asyncio
import aiosqlite
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..config import DB_PATH
from ..ai_engine.camera_manager import camera_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/camera", tags=["Camera & Live Telemetry"])

# Alias pipeline for main.py lifespan compatibility
pipeline = camera_manager.shared_pipeline

class CameraSwitchRequest(BaseModel):
    source: str

class CameraAddRequest(BaseModel):
    name: str
    source: str

class CameraAttachRequest(BaseModel):
    id: Optional[str] = None
    camera_id: Optional[str] = None
    name: Optional[str] = None
    source: Optional[str] = None

class CameraDetachRequest(BaseModel):
    id: Optional[str] = None
    camera_id: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    similarity_threshold: Optional[float] = None
    min_quality_score: Optional[float] = None
    attendance_cooldown_minutes: Optional[int] = None
    late_time: Optional[str] = None
    camera_source: Optional[str] = None

@router.get("/detect")
async def detect_hardware_cameras():
    """Scans and detects real physical webcam hardware devices connected to this machine."""
    return camera_manager.scan_hardware()

@router.get("/list")
async def list_cameras():
    """Lists all configured cameras with live attachment state (attached/detached) and FPS."""
    return camera_manager.list_cameras()

@router.post("/attach")
async def attach_camera_endpoint(req: CameraAttachRequest):
    """
    Attaches a camera to active AI process:
    Initializes hardware capture, starts face detection pipeline worker, and marks active in DB.
    """
    cam_id = req.id or req.camera_id
    source = req.source
    name = req.name

    # If source is not provided, look up from saved cameras
    if not source and cam_id:
        for sc in camera_manager.saved_cameras:
            if sc.get("id") == cam_id:
                source = str(sc.get("source", "0"))
                if not name:
                    name = sc.get("name")
                break

    source = source or "0"
    cam_id = cam_id or f"cam_{source}"
    cam_name = name or f"Camera {source}"

    res = camera_manager.attach_camera(cam_id, cam_name, source)
    await camera_manager.save_camera_config(cam_id, cam_name, source)
    await camera_manager.set_camera_active_db(cam_id, 1)
    return res

@router.post("/detach")
async def detach_camera_endpoint(req: CameraDetachRequest):
    """
    Detaches a camera from active AI process:
    Stops worker, completely releases physical hardware capture handle (camera LED turns off, 0% CPU).
    """
    cam_id = req.id or req.camera_id
    if not cam_id:
        raise HTTPException(status_code=400, detail="id or camera_id is required")
    success = camera_manager.detach_camera(cam_id)
    await camera_manager.set_camera_active_db(cam_id, 0)
    return {"status": "success", "detached": success, "cam_id": cam_id}

@router.post("/add")
async def add_camera(req: CameraAddRequest):
    """Adds a new camera (Webcam index or RTSP CCTV stream), saves to DB, and attaches immediately."""
    result = await camera_manager.add_camera(req.name, req.source)
    return result

@router.delete("/{cam_id}")
async def delete_camera(cam_id: str):
    """Detaches and deletes a camera permanently from database."""
    success = await camera_manager.remove_camera(cam_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"status": "success", "message": f"Camera {cam_id} removed successfully"}

@router.get("/status")
@router.get("/{cam_id}/status")
async def get_camera_status(cam_id: Optional[str] = None):
    """Returns real-time status and FPS of the camera."""
    cam = camera_manager.get_camera(cam_id or "cam_1")
    if not cam:
        return {
            "source": "0",
            "fps": 0.0,
            "is_running": False,
            "similarity_threshold": pipeline.similarity_threshold,
            "cooldown_minutes": int(pipeline.attendance_cooldown_seconds / 60),
            "late_time": pipeline.late_time_str
        }
    return {
        "cam_id": cam.cam_id,
        "name": cam.name,
        "source": str(cam.source),
        "fps": round(cam.capture.fps, 1),
        "is_running": cam.is_running,
        "similarity_threshold": pipeline.similarity_threshold,
        "cooldown_minutes": int(pipeline.attendance_cooldown_seconds / 60),
        "late_time": pipeline.late_time_str
    }

@router.post("/switch")
async def switch_camera(req: CameraSwitchRequest):
    """Switches default camera input source."""
    new_src = req.source.strip()
    cam = camera_manager.get_camera("cam_1")
    if cam:
        cam.capture.change_source(new_src)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO system_settings (key, value)
            VALUES ('camera_source', ?);
        """, (new_src,))
        await db.commit()

    return {"status": "success", "message": f"Camera switched to {new_src}"}

@router.get("/settings")
async def get_settings():
    """Fetch all runtime system settings."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT key, value FROM system_settings;") as cursor:
            rows = await cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}

@router.post("/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Update runtime settings and reload pipeline."""
    async with aiosqlite.connect(DB_PATH) as db:
        if req.similarity_threshold is not None:
            await db.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('similarity_threshold', ?);", (str(req.similarity_threshold),))
        if req.min_quality_score is not None:
            await db.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('min_quality_score', ?);", (str(req.min_quality_score),))
        if req.attendance_cooldown_minutes is not None:
            await db.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('attendance_cooldown_minutes', ?);", (str(req.attendance_cooldown_minutes),))
        if req.late_time is not None:
            await db.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('late_time', ?);", (req.late_time,))
        if req.camera_source is not None:
            await db.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('camera_source', ?);", (req.camera_source,))
            cam = camera_manager.get_camera("cam_1")
            if cam:
                cam.capture.change_source(req.camera_source)
        await db.commit()

    await camera_manager.reload_vectors()
    return {"status": "success", "message": "Settings updated and pipeline reloaded."}

async def background_pipeline_worker():
    """Main startup worker: initializes camera manager and all registered CCTV streams."""
    logger.info("Initializing multi-camera manager streams...")
    await camera_manager.initialize()

# High-Performance MJPEG Live Stream Generator
async def generate_mjpeg_stream(cam_id: Optional[str] = None):
    """
    Streams raw decoded video frames directly to browser at maximum camera framerate.
    Zero AI blocking or CPU encoding overhead (serves pre-encoded JPEG).
    """
    while True:
        target_id = cam_id or "cam_1"
        jpeg_bytes = camera_manager.get_jpeg(target_id)
        if jpeg_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
        await asyncio.sleep(0.033) # ~30 FPS smooth stream

@router.get("/stream")
@router.get("/{cam_id}/stream")
async def live_video_stream(cam_id: Optional[str] = None):
    """MJPEG Live video stream for specific or default camera."""
    return StreamingResponse(
        generate_mjpeg_stream(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# WebSocket Telemetry Stream (High-Speed HUD sync)
@router.websocket("/ws")
@router.websocket("/{cam_id}/ws")
async def telemetry_websocket(websocket: WebSocket, cam_id: Optional[str] = None):
    """Pushes real-time JSON detection metadata and bounding boxes."""
    await websocket.accept()
    try:
        while True:
            if cam_id and cam_id != "all":
                telemetry = camera_manager.get_telemetry(cam_id)
            else:
                telemetry = camera_manager.get_all_telemetry()
            await websocket.send_json(telemetry)
            await asyncio.sleep(0.033) # 30 FPS telemetry push
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket disconnected: {e}")
