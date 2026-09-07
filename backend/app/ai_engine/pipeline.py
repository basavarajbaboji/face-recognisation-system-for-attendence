import cv2
import time
import json
import aiosqlite
import asyncio
import numpy as np
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from .detector import YuNetFaceDetector
from .aligner import FaceAlignerAndQuality
from .embedder import ArcFaceEmbedder
from .tracker import ByteTracker, TrackState
from .matcher import MultiTemplateVectorMatcher
from .temporal_engine import TemporalConfirmationEngine
from .unknown_manager import UnknownVisitorManager
from ..config import (
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_MIN_QUALITY_SCORE,
    DEFAULT_ATTENDANCE_COOLDOWN_MINUTES,
    DEFAULT_LATE_TIME,
    DB_PATH
)

logger = logging.getLogger(__name__)

class SurveillanceAttendancePipeline:
    """
    Main Orchestrator for the Smart Campus Face Surveillance & Attendance System.
    Connects Detection -> Quality Assessment -> ByteTrack -> ArcFace ONNX ->
    Temporal Consistency State Machine -> Attendance DB & Deduplicated Unknown Manager.
    """
    def __init__(self):
        self.detector = YuNetFaceDetector()
        self.aligner = FaceAlignerAndQuality()
        self.embedder = ArcFaceEmbedder()
        self.tracker = ByteTracker(iou_threshold=0.35, max_age=30, min_hits=2)
        self.matcher = MultiTemplateVectorMatcher()
        self.temporal_engine = TemporalConfirmationEngine()
        self.unknown_manager = UnknownVisitorManager()

        # Dynamic runtime settings
        self.similarity_threshold = DEFAULT_SIMILARITY_THRESHOLD
        self.min_quality_score = DEFAULT_MIN_QUALITY_SCORE
        self.attendance_cooldown_seconds = DEFAULT_ATTENDANCE_COOLDOWN_MINUTES * 60
        self.late_time_str = DEFAULT_LATE_TIME
        self.gate_id = "Main Campus Gate - Entry A"

        # In-memory debounce cache: user_id -> timestamp
        self.user_attendance_cooldowns: Dict[int, float] = {}

        # Person footprint and movement history: user_id -> footprint dict
        self.user_footprints: Dict[int, Dict[str, Any]] = {}

        # Recent activity events buffer for live UI feed (Deduplicated strictly to 1 entry per person)
        self.recent_events: List[Dict[str, Any]] = []

    async def reload_settings(self):
        """Reload configuration and enrolled vector embeddings from DB."""
        self.matcher.reload()
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT key, value FROM system_settings;") as cursor:
                    rows = await cursor.fetchall()
                    for k, v in rows:
                        if k == "similarity_threshold":
                            self.similarity_threshold = float(v)
                        elif k == "min_quality_score":
                            self.min_quality_score = float(v)
                        elif k == "attendance_cooldown_minutes":
                            self.attendance_cooldown_seconds = float(v) * 60
                        elif k == "late_time":
                            self.late_time_str = v
        except Exception as e:
            logger.error(f"Error loading system settings: {e}")

    def process_frame_sync(self, frame: np.ndarray):
        """
        Synchronous CPU vision processing (Detection -> Tracking -> Alignment -> Embedding -> Matching).
        Runs inside a threadpool executor to avoid blocking the asyncio event loop.
        """
        # 1. Detect Faces (with automatic downscaled acceleration)
        detections = self.detector.detect(frame)

        # 2. Assess Quality for each detection
        for det in detections:
            det["quality"] = self.aligner.calculate_quality(frame, det["bbox"], det["landmarks"])

        # 3. Update Multi-Target Crowd Tracker
        active_tracks = self.tracker.update(detections, frame)

        # 4. Process Track Recognition on Demand
        confirmed_candidates = []
        unknown_candidates = []

        for track in active_tracks:
            # Check if this track needs an ArcFace inference run
            if track.needs_recognition(min_quality=self.min_quality_score) and track.landmarks is not None:
                aligned_crop = self.aligner.align_face(frame, track.landmarks)
                emb = self.embedder.extract_embedding(aligned_crop)

                # Match against multi-template enrolled vectors
                user_id, label, conf, top_matches = self.matcher.match_single(
                    emb, threshold=self.similarity_threshold
                )

                # Temporal consistency evaluation (UNKNOWN -> CANDIDATE -> CONFIRMED)
                state = self.temporal_engine.evaluate(
                    track, user_id, label, conf, track.best_quality_score, self.similarity_threshold
                )
                track.record_recognition_attempt()

            if track.identity_state == "CONFIRMED":
                confirmed_candidates.append(track)
            elif track.identity_state == "UNKNOWN":
                unknown_candidates.append(track)

        # 5. Format Telemetry Payload for Frontend HUD
        telemetry_boxes = []
        confirmed_count = 0
        candidate_count = 0
        unknown_count = 0

        for track in active_tracks:
            if track.identity_state == "CONFIRMED":
                confirmed_count += 1
            elif track.identity_state == "CANDIDATE":
                candidate_count += 1
            else:
                unknown_count += 1

            telemetry_boxes.append({
                "track_id": track.track_id,
                "bbox": track.bbox,
                "state": track.identity_state, # 'CONFIRMED' (green), 'CANDIDATE' (yellow), 'UNKNOWN' (orange)
                "label": track.confirmed_user_label if track.identity_state == "CONFIRMED" else (f"Verifying Candidate..." if track.identity_state == "CANDIDATE" else f"Unknown #{track.track_id}"),
                "confidence": round(track.confirmed_confidence, 2) if track.identity_state == "CONFIRMED" else 0.0,
                "quality": round(track.best_quality_score, 1),
                "attendance_marked": track.attendance_marked
            })

        telemetry = {
            "timestamp": time.time(),
            "crowd_headcount": len(active_tracks),
            "confirmed_count": confirmed_count,
            "candidate_count": candidate_count,
            "unknown_count": unknown_count,
            "tracks": telemetry_boxes,
            "recent_events": self.recent_events[-10:]
        }

        return telemetry, confirmed_candidates, unknown_candidates

    async def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Processes a single video frame end-to-end.
        Runs CPU vision in a thread pool and executes database logging asynchronously.
        """
        telemetry, confirmed_candidates, unknown_candidates = await asyncio.to_thread(self.process_frame_sync, frame)

        # Handle Confirmed Attendance Events in async DB
        for track in confirmed_candidates:
            await self._handle_confirmed_attendance(track)

        # Handle Unknown Visitors in async DB
        for track in unknown_candidates:
            await self.unknown_manager.process_unknown_track(track, gate_id=self.gate_id)

        telemetry["recent_events"] = self.recent_events[-10:]
        return telemetry

    async def _handle_confirmed_attendance(self, track: TrackState):
        """
        Processes confirmed face detections:
        1. Official daily attendance check-in is logged once per user per day.
        2. Movement Footprint is continuously tracked (when entered, where entered, last seen, last gate, seen count, and trail).
        3. Live UI activity feed maintains strictly ONE consolidated entry per person (removes previous duplicates and uses only one).
        """
        user_id = track.confirmed_user_id
        if user_id is None:
            return

        now = datetime.now()
        current_ts = now.timestamp()
        current_time_str = now.strftime("%H:%M:%S")
        current_date_str = now.strftime("%Y-%m-%d")
        gate = self.gate_id or "Main Gate"

        # Throttle processing per user to once every 2 seconds to keep CPU low
        last_processed = self.user_attendance_cooldowns.get(user_id, 0.0)
        if (current_ts - last_processed) < 2.0:
            return
        self.user_attendance_cooldowns[user_id] = current_ts

        # Determine Late vs Present
        status = "Late" if current_time_str > f"{self.late_time_str}:00" else "Present"

        # 1. Manage In-Memory Footprint
        is_first_today = user_id not in self.user_footprints
        if is_first_today:
            self.user_footprints[user_id] = {
                "user_id": user_id,
                "label": track.confirmed_user_label,
                "status": status,
                "first_seen": current_time_str,
                "entry_gate": gate,
                "last_seen": current_time_str,
                "current_gate": gate,
                "seen_count": 1,
                "confidence": round(track.confirmed_confidence, 2),
                "trail": [
                    {"time": current_time_str, "gate": gate, "type": "Entry"}
                ],
                "last_trail_ts": current_ts,
                "last_trail_gate": gate
            }
        else:
            fp = self.user_footprints[user_id]
            fp["last_seen"] = current_time_str
            fp["current_gate"] = gate
            fp["confidence"] = round(track.confirmed_confidence, 2)

            # Record a new trail waypoint if 25s elapsed OR if gate location changed
            time_since_trail = current_ts - fp.get("last_trail_ts", 0.0)
            gate_changed = (gate != fp.get("last_trail_gate", gate))

            if time_since_trail >= 25.0 or gate_changed:
                fp["seen_count"] += 1
                fp["last_trail_ts"] = current_ts
                fp["last_trail_gate"] = gate
                fp["trail"].append({
                    "time": current_time_str,
                    "gate": gate,
                    "type": "Movement" if gate_changed else "Sighting"
                })
                if len(fp["trail"]) > 25:
                    fp["trail"].pop(0)

        fp = self.user_footprints[user_id]

        # 2. Database Persistence (Official Attendance + Deduplicated Footprint Table)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # A. Log official daily attendance once
                if not track.attendance_marked:
                    async with db.execute(
                        "SELECT id FROM attendance_events WHERE user_id = ? AND date = ?;",
                        (user_id, current_date_str)
                    ) as cursor:
                        existing_att = await cursor.fetchone()

                    if not existing_att:
                        await db.execute("""
                            INSERT INTO attendance_events 
                            (user_id, date, time, timestamp, status, confidence, track_id, gate_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """, (user_id, current_date_str, current_time_str, current_ts, status, track.confirmed_confidence, track.track_id, gate))
                        await db.commit()
                        logger.info(f"Marked attendance: {track.confirmed_user_label} [{status}] at {current_time_str}")

                    track.attendance_marked = True

                # B. Upsert footprint movement audit trail (strictly 1 record per user per day)
                await db.execute("""
                    INSERT INTO person_footprints (user_id, date, first_seen, last_seen, entry_gate, last_gate, seen_count, trail_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, date) DO UPDATE SET
                        last_seen = excluded.last_seen,
                        last_gate = excluded.last_gate,
                        seen_count = person_footprints.seen_count + 1,
                        trail_json = excluded.trail_json;
                """, (user_id, current_date_str, fp["first_seen"], fp["last_seen"], fp["entry_gate"], fp["current_gate"], fp["seen_count"], json.dumps(fp["trail"])))
                await db.commit()

        except Exception as e:
            logger.error(f"Error saving attendance/footprint for user {user_id}: {e}")

        # 3. Live UI Feed: Deduplicate by person ("remove other and use only one")
        self.recent_events = [ev for ev in self.recent_events if ev.get("user_id") != user_id]

        event_obj = {
            "id": f"person_{user_id}",
            "user_id": user_id,
            "label": fp["label"],
            "time": fp["last_seen"],
            "first_seen": fp["first_seen"],
            "entry_gate": fp["entry_gate"],
            "current_gate": fp["current_gate"],
            "seen_count": fp["seen_count"],
            "trail": list(fp["trail"]),
            "status": fp["status"],
            "confidence": fp["confidence"]
        }
        self.recent_events.append(event_obj)
        if len(self.recent_events) > 30:
            self.recent_events.pop(0)
