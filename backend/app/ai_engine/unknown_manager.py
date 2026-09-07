import cv2
import aiosqlite
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Optional
from .tracker import TrackState
from ..config import SNAPSHOTS_DIR, DB_PATH

logger = logging.getLogger(__name__)

class UnknownVisitorManager:
    """
    Manages and deduplicates unknown visitor snapshots at the gate.
    Saves only ONE representative high-quality image per unknown track
    and updates first_seen, last_seen, and seen_count.
    """
    def __init__(self, min_hits: int = 5):
        self.min_hits = min_hits
        # In-memory tracking of active unknown tracks: track_id -> {db_id, best_quality, snapshot_path}
        self.active_unknowns: Dict[int, Dict] = {}
        self.logged_track_ids: Set[int] = set()

    async def process_unknown_track(self, track: TrackState, gate_id: str = "Main Gate"):
        """
        Processes an unknown track state and records/updates deduplicated visitor entry.
        """
        # Only log if track has enough temporal persistence (not a flicker) and no confirmed user
        if track.identity_state != "UNKNOWN" or track.hits < self.min_hits or track.best_face_crop is None:
            return

        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        track_id = track.track_id

        # 1. If already registered in this session
        if track_id in self.active_unknowns:
            info = self.active_unknowns[track_id]
            # Check if a better quality frame is available to upgrade the snapshot
            if track.best_quality_score > info["best_quality"]:
                try:
                    snapshot_path = info["snapshot_path"]
                    cv2.imwrite(snapshot_path, track.best_face_crop)
                    info["best_quality"] = track.best_quality_score
                except Exception as e:
                    logger.error(f"Error upgrading unknown snapshot: {e}")

            # Update last_seen and seen_count periodically (every 10 hits)
            if track.hits % 10 == 0:
                try:
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("""
                            UPDATE unknown_visitors 
                            SET last_seen = ?, seen_count = seen_count + 1
                            WHERE id = ?;
                        """, (current_time, info["db_id"]))
                        await db.commit()
                except Exception as e:
                    logger.error(f"Error updating unknown visitor log: {e}")
            return

        # 2. New Unknown Visitor Track -> Save image and create single DB entry
        if track_id not in self.logged_track_ids:
            self.logged_track_ids.add(track_id)
            filename = f"unknown_track_{track_id}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = SNAPSHOTS_DIR / filename

            try:
                cv2.imwrite(str(filepath), track.best_face_crop)
                relative_path = f"/data/snapshots/{filename}"

                async with aiosqlite.connect(DB_PATH) as db:
                    cursor = await db.execute("""
                        INSERT INTO unknown_visitors (track_id, date, first_seen, last_seen, seen_count, best_snapshot_path, gate_id)
                        VALUES (?, ?, ?, ?, 1, ?, ?);
                    """, (track_id, current_date, current_time, current_time, relative_path, gate_id))
                    await db.commit()
                    db_id = cursor.lastrowid

                self.active_unknowns[track_id] = {
                    "db_id": db_id,
                    "best_quality": track.best_quality_score,
                    "snapshot_path": str(filepath)
                }
                logger.info(f"Logged new unknown visitor Track #{track_id} at {current_time}")
            except Exception as e:
                logger.error(f"Error saving unknown visitor snapshot: {e}")
