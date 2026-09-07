import aiosqlite
import sqlite3
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from .config import (
    DB_PATH,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_MIN_QUALITY_SCORE,
    DEFAULT_CAMERA_SOURCE,
    DEFAULT_ATTENDANCE_COOLDOWN_MINUTES,
    DEFAULT_LATE_TIME
)

async def init_db():
    """Initialize SQLite database with WAL mode and normalized multi-template schema."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        
        # 1. Users Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                department TEXT NOT NULL,
                year TEXT DEFAULT '1st Year',
                email TEXT,
                photo_path TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Multi-Template User Embeddings Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                angle TEXT NOT NULL DEFAULT 'front',
                quality_score REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 3. Attendance Events Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS attendance_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                timestamp REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Present',
                confidence REAL NOT NULL,
                track_id INTEGER,
                gate_id TEXT DEFAULT 'Main Gate',
                snapshot_path TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 4. Deduplicated Unknown Visitors Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS unknown_visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                seen_count INTEGER DEFAULT 1,
                best_snapshot_path TEXT,
                gate_id TEXT DEFAULT 'Main Gate'
            );
        """)

        # 5. System Settings Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        # 6. Audit Logs Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                actor TEXT DEFAULT 'System',
                details TEXT
            );
        """)

        # 7. Multi-Camera Configuration Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 8. Person Footprint & Movement Audit Trail Table (One consolidated record per person per day)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS person_footprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                entry_gate TEXT DEFAULT 'Main Gate',
                last_gate TEXT DEFAULT 'Main Gate',
                seen_count INTEGER DEFAULT 1,
                trail_json TEXT DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, date)
            );
        """)

        # Ensure required data directories exist
        from .config import DATA_DIR, SNAPSHOTS_DIR, FACES_DIR, MODELS_DIR, EXPORTS_DIR
        for d in [DATA_DIR, SNAPSHOTS_DIR, FACES_DIR, MODELS_DIR, EXPORTS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

        # Insert default settings if not exists
        default_settings = [
            ("similarity_threshold", str(DEFAULT_SIMILARITY_THRESHOLD)),
            ("min_quality_score", str(DEFAULT_MIN_QUALITY_SCORE)),
            ("camera_source", DEFAULT_CAMERA_SOURCE),
            ("attendance_cooldown_minutes", str(DEFAULT_ATTENDANCE_COOLDOWN_MINUTES)),
            ("late_time", DEFAULT_LATE_TIME),
            ("retention_days", "30")
        ]
        for k, v in default_settings:
            await db.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?);", (k, v))

        # Insert default camera 1 if not exists
        await db.execute("""
            INSERT OR IGNORE INTO cameras (id, name, source, is_active)
            VALUES ('cam_1', 'Main Campus Gate - Entry A', '0', 1);
        """)

        await db.commit()


# Vector Helper Utilities
def serialize_embedding(embedding: np.ndarray) -> bytes:
    """Convert float32 numpy array (512-d) to binary BLOB."""
    arr = np.ascontiguousarray(embedding, dtype=np.float32)
    return arr.tobytes()

def deserialize_embedding(blob: bytes) -> np.ndarray:
    """Convert binary BLOB back to float32 numpy array."""
    return np.frombuffer(blob, dtype=np.float32)


# Synchronous Database Loader for High-Speed Memory Cache Initialization
def load_all_enrolled_templates_sync() -> Tuple[List[int], List[str], np.ndarray]:
    """
    Loads all active user embeddings into contiguous memory for vectorized BLAS search.
    Returns:
        (user_ids_list, user_names_list, embedding_matrix_2d [N x 512])
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.user_id, u.name, u.roll_number, e.embedding 
        FROM user_embeddings e
        JOIN users u ON e.user_id = u.id
        WHERE u.is_active = 1
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return [], [], np.empty((0, 512), dtype=np.float32)

    user_ids = []
    labels = []
    embeddings_list = []

    for user_id, name, roll_no, blob in rows:
        user_ids.append(user_id)
        labels.append(f"{name} ({roll_no})")
        embeddings_list.append(deserialize_embedding(blob))

    embedding_matrix = np.vstack(embeddings_list).astype(np.float32)
    return user_ids, labels, embedding_matrix
