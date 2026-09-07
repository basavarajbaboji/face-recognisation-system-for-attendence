import asyncio
import aiosqlite
import logging
import cv2
import time
from typing import Dict, List, Any, Optional

from ..config import DB_PATH
from .video_stream import ThreadedVideoCapture
from .pipeline import SurveillanceAttendancePipeline

logger = logging.getLogger(__name__)

def scan_system_cameras(max_tested: int = 4) -> List[Dict[str, Any]]:
    """
    Scans physical USB / built-in webcam devices on this computer (indices 0..3)
    and returns only REAL physical hardware cameras found.
    """
    detected = []
    for i in range(max_tested):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
            cap.release()
            detected.append({
                "source": str(i),
                "name": f"Camera {i} ({w}x{h})",
                "resolution": f"{w}x{h}",
                "type": "Physical Webcam (USB/Internal)",
                "detected": True
            })
        else:
            cap.release()
    return detected


class ManagedCamera:
    """Represents an attached real CCTV / webcam stream with active worker and tracker."""
    def __init__(self, cam_id: str, name: str, source: str, shared_pipeline: SurveillanceAttendancePipeline):
        self.cam_id = cam_id
        self.name = name
        self.source = source
        self.capture = ThreadedVideoCapture(source=source)
        
        # Dedicated pipeline instance per camera to maintain independent tracking states
        self.pipeline = SurveillanceAttendancePipeline()
        # Share the exact same in-memory ArcFace vector matcher and detector
        self.pipeline.matcher = shared_pipeline.matcher
        self.pipeline.detector = shared_pipeline.detector
        self.pipeline.aligner = shared_pipeline.aligner
        self.pipeline.embedder = shared_pipeline.embedder
        self.pipeline.gate_id = name
        
        self.is_running = True
        self.worker_task: Optional[asyncio.Task] = None
        self.latest_telemetry: Dict[str, Any] = {
            "cam_id": cam_id,
            "name": name,
            "source": source,
            "timestamp": 0,
            "crowd_headcount": 0,
            "confirmed_count": 0,
            "candidate_count": 0,
            "unknown_count": 0,
            "frame_width": 1280,
            "frame_height": 720,
            "fps": 0.0,
            "tracks": [],
            "recent_events": []
        }

    def start_worker(self):
        """Starts background AI vision frame processor."""
        self.is_running = True
        self.worker_task = asyncio.create_task(self._process_loop())

    async def _process_loop(self):
        logger.info(f"Started AI vision worker for attached camera: {self.name} (source: {self.source})")
        while self.is_running:
            try:
                frame = self.capture.read()
                if frame is not None:
                    h, w = frame.shape[:2]
                    telemetry = await self.pipeline.process_frame(frame)
                    telemetry["cam_id"] = self.cam_id
                    telemetry["name"] = self.name
                    telemetry["source"] = self.source
                    telemetry["frame_width"] = w
                    telemetry["frame_height"] = h
                    telemetry["fps"] = round(self.capture.fps, 1)
                    self.latest_telemetry = telemetry
                else:
                    self.latest_telemetry["fps"] = 0.0

                await asyncio.sleep(0.005) # Low latency real-time frame processing
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in camera {self.cam_id} vision loop: {e}")
                await asyncio.sleep(0.1)

    def stop(self):
        """Stops the worker thread and releases physical hardware camera handle."""
        self.is_running = False
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
        self.capture.release()
        logger.info(f"Detached and released camera: {self.name} [{self.cam_id}]")


class MultiCameraManager:
    """
    Real Camera Hardware & CCTV Stream Orchestrator:
    - Scans real physical webcams connected to the PC.
    - Attach to process (starts stream and tracking).
    - Detach from process (stops stream, releases hardware handle, 0% CPU).
    - Sources all attendance check-ins into single central SQLite DB.
    """
    def __init__(self):
        self.shared_pipeline = SurveillanceAttendancePipeline()
        self.active_cameras: Dict[str, ManagedCamera] = {}
        self.saved_cameras: List[Dict[str, Any]] = []

    async def initialize(self):
        """Load settings, reload vectors, and auto-attach primary camera."""
        await self.shared_pipeline.reload_settings()

        # Load configured cameras from database
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, name, source, is_active FROM cameras;") as cursor:
                rows = await cursor.fetchall()
                self.saved_cameras = [dict(r) for r in rows]

        # If no camera configured, default to Camera 0
        if not self.saved_cameras:
            default_cam = {"id": "cam_0", "name": "Main Camera (Device 0)", "source": "0", "is_active": 1}
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO cameras (id, name, source, is_active)
                    VALUES ('cam_0', 'Main Camera (Device 0)', '0', 1);
                """)
                await db.commit()
            self.saved_cameras = [default_cam]

        # Auto-attach active cameras
        for cam_data in self.saved_cameras:
            if cam_data.get("is_active", 1) == 1:
                self.attach_camera(cam_data["id"], cam_data["name"], str(cam_data["source"]))

        logger.info(f"MultiCameraManager initialized. Attached cameras: {list(self.active_cameras.keys())}")

    def scan_hardware(self) -> List[Dict[str, Any]]:
        """Scans for real physical webcam devices on this machine."""
        detected = []
        active_sources = {str(c.source): c for c in self.active_cameras.values()}

        for i in range(4):
            src_str = str(i)
            if src_str in active_sources:
                cam = active_sources[src_str]
                w = cam.latest_telemetry.get("frame_width", 1280)
                h = cam.latest_telemetry.get("frame_height", 720)
                detected.append({
                    "source": src_str,
                    "name": f"Physical Camera {i} ({w}x{h})",
                    "resolution": f"{w}x{h}",
                    "type": "Physical Webcam (USB/Internal)",
                    "detected": True,
                    "is_attached": True,
                    "attached_cam_id": cam.cam_id,
                    "fps": round(cam.capture.fps, 1)
                })
            else:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
                    cap.release()
                    detected.append({
                        "source": src_str,
                        "name": f"Physical Camera {i} ({w}x{h})",
                        "resolution": f"{w}x{h}",
                        "type": "Physical Webcam (USB/Internal)",
                        "detected": True,
                        "is_attached": False,
                        "attached_cam_id": None,
                        "fps": 0.0
                    })
                else:
                    cap.release()
        return detected

    def attach_camera(self, cam_id: str, name: str, source: str) -> Dict[str, Any]:
        """Attaches a camera source to active process and begins processing."""
        source_str = str(source).strip()
        # If already attached on this source, return existing
        for existing_id, cam in self.active_cameras.items():
            if cam.source == source_str:
                return {
                    "id": existing_id,
                    "name": cam.name,
                    "source": cam.source,
                    "is_attached": True,
                    "status": "already_attached"
                }

        # If cam_id exists with different source, detach first
        if cam_id in self.active_cameras:
            self.active_cameras[cam_id].stop()

        cam = ManagedCamera(cam_id, name, source_str, self.shared_pipeline)
        cam.start_worker()
        self.active_cameras[cam_id] = cam

        # Update or add in saved_cameras
        found = False
        for sc in self.saved_cameras:
            if sc["id"] == cam_id:
                sc["is_active"] = 1
                sc["name"] = name
                sc["source"] = source_str
                found = True
                break
        if not found:
            self.saved_cameras.append({"id": cam_id, "name": name, "source": source_str, "is_active": 1})

        logger.info(f"Attached camera '{name}' (source: {source_str}) as [{cam_id}]")
        return {
            "id": cam_id,
            "name": name,
            "source": source_str,
            "is_attached": True,
            "status": "attached"
        }

    def detach_camera(self, cam_id: str) -> bool:
        """Detaches a camera from the process, stopping worker and releasing physical hardware handle."""
        if cam_id in self.active_cameras:
            self.active_cameras[cam_id].stop()
            del self.active_cameras[cam_id]
            for sc in self.saved_cameras:
                if sc["id"] == cam_id:
                    sc["is_active"] = 0
            logger.info(f"Detached camera [{cam_id}] from active process.")
            return True
        return False

    async def add_camera(self, name: str, source: str) -> Dict[str, Any]:
        """Adds, persists to DB, and immediately attaches a new camera."""
        source_str = str(source).strip()
        cam_id = f"cam_{abs(hash(source_str + str(time.time()))) % 100000}"
        res = self.attach_camera(cam_id, name, source_str)
        await self.save_camera_config(cam_id, name, source_str)
        return res

    async def remove_camera(self, cam_id: str) -> bool:
        """Detaches and deletes a camera permanently from database."""
        self.detach_camera(cam_id)
        self.saved_cameras = [c for c in self.saved_cameras if c["id"] != cam_id]
        await self.delete_camera_config(cam_id)
        return True

    async def save_camera_config(self, cam_id: str, name: str, source: str):
        """Persists a camera to SQLite configuration table."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO cameras (id, name, source, is_active)
                VALUES (?, ?, ?, 1);
            """, (cam_id, name, str(source)))
            await db.commit()

    async def delete_camera_config(self, cam_id: str):
        """Deletes a camera configuration from SQLite."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM cameras WHERE id = ?;", (cam_id,))
            await db.commit()

    async def set_camera_active_db(self, cam_id: str, is_active: int):
        """Updates camera active status in SQLite."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE cameras SET is_active = ? WHERE id = ?;", (is_active, cam_id))
            await db.commit()

    def list_cameras(self) -> List[Dict[str, Any]]:
        """Returns all configured cameras with live attachment state and FPS."""
        result = []
        seen_ids = set()

        # First, include all active cameras
        for cam_id, cam in self.active_cameras.items():
            seen_ids.add(cam_id)
            result.append({
                "id": cam_id,
                "name": cam.name,
                "source": str(cam.source),
                "fps": round(cam.capture.fps, 1),
                "headcount": cam.latest_telemetry.get("crowd_headcount", 0),
                "is_attached": True,
                "is_running": cam.is_running
            })

        # Next, include saved cameras that are currently detached
        for sc in self.saved_cameras:
            if sc["id"] not in seen_ids:
                seen_ids.add(sc["id"])
                result.append({
                    "id": sc["id"],
                    "name": sc["name"],
                    "source": str(sc["source"]),
                    "fps": 0.0,
                    "headcount": 0,
                    "is_attached": False,
                    "is_running": False
                })

        return result

    def get_camera(self, cam_id: str) -> Optional[ManagedCamera]:
        """Gets specific attached camera, or first attached camera."""
        if cam_id in self.active_cameras:
            return self.active_cameras[cam_id]
        if self.active_cameras:
            return next(iter(self.active_cameras.values()))
        return None

    def get_jpeg(self, cam_id: str) -> Optional[bytes]:
        """Returns pre-encoded JPEG bytes for the camera."""
        cam = self.get_camera(cam_id)
        if cam:
            return cam.capture.read_jpeg()
        return None

    def get_telemetry(self, cam_id: str) -> Dict[str, Any]:
        """Returns telemetry for specific camera."""
        cam = self.get_camera(cam_id)
        if cam:
            return cam.latest_telemetry
        return {}

    def get_all_telemetry(self) -> Dict[str, Any]:
        """Returns aggregate telemetry across all attached cameras."""
        total_headcount = 0
        total_confirmed = 0
        total_candidate = 0
        total_unknown = 0
        all_tracks = []
        # Deduplicate recent events across all cameras by user_id (strictly 1 consolidated card per person)
        merged_by_user = {}
        for cam_id, cam in self.active_cameras.items():
            t = cam.latest_telemetry
            total_headcount += t.get("crowd_headcount", 0)
            total_confirmed += t.get("confirmed_count", 0)
            total_candidate += t.get("candidate_count", 0)
            total_unknown += t.get("unknown_count", 0)
            
            for trk in t.get("tracks", []):
                trk_copy = dict(trk)
                trk_copy["cam_id"] = cam_id
                trk_copy["cam_name"] = cam.name
                all_tracks.append(trk_copy)

            for ev in t.get("recent_events", []):
                uid = ev.get("user_id")
                if not uid:
                    continue
                if uid not in merged_by_user:
                    merged_by_user[uid] = dict(ev)
                else:
                    m = merged_by_user[uid]
                    # Keep max seen_count
                    m["seen_count"] = max(m.get("seen_count", 1), ev.get("seen_count", 1))
                    # Keep earliest first_seen
                    if ev.get("first_seen", "") and (not m.get("first_seen") or ev["first_seen"] < m["first_seen"]):
                        m["first_seen"] = ev["first_seen"]
                        m["entry_gate"] = ev.get("entry_gate", m.get("entry_gate"))
                    # Keep latest last_seen
                    if ev.get("time", "") >= m.get("time", ""):
                        m["time"] = ev["time"]
                        m["current_gate"] = ev.get("current_gate", cam.name)
                        m["confidence"] = ev.get("confidence", m.get("confidence"))
                    # Merge footprint trails
                    t1 = m.get("trail", [])
                    t2 = ev.get("trail", [])
                    combined = {f"{pt.get('time')}_{pt.get('gate')}": pt for pt in (t1 + t2)}
                    m["trail"] = sorted(combined.values(), key=lambda x: x.get("time", ""))[-20:]

        recent_events = sorted(merged_by_user.values(), key=lambda x: x.get("time", ""), reverse=True)[:20]

        return {
            "timestamp": time.time(),
            "crowd_headcount": total_headcount,
            "confirmed_count": total_confirmed,
            "candidate_count": total_candidate,
            "unknown_count": total_unknown,
            "cameras": self.list_cameras(),
            "tracks": all_tracks,
            "recent_events": recent_events
        }

    async def reload_vectors(self):
        """Hot-reloads enrolled embeddings across all attached cameras."""
        await self.shared_pipeline.reload_settings()
        for cam in self.active_cameras.values():
            cam.pipeline.matcher = self.shared_pipeline.matcher
        logger.info("Hot-reloaded vector embeddings across all attached cameras.")

    def shutdown(self):
        """Releases all cameras on exit."""
        for cam in self.active_cameras.values():
            cam.stop()
        self.active_cameras.clear()

camera_manager = MultiCameraManager()
