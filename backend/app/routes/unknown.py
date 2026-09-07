import aiosqlite
import os
from pathlib import Path
from fastapi import APIRouter
from typing import Optional
from ..config import DB_PATH, BASE_DIR

router = APIRouter(prefix="/api/unknown", tags=["Unknown Visitors"])

@router.get("/")
async def list_unknown_visitors(date: Optional[str] = None):
    """List deduplicated unknown visitor records with snapshot thumbnails."""
    query = """
        SELECT id, track_id, date, first_seen, last_seen, seen_count, best_snapshot_path, gate_id
        FROM unknown_visitors
        WHERE 1=1
    """
    params = []
    if date:
        query += " AND date = ?"
        params.append(date)

    query += " ORDER BY id DESC LIMIT 100;"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

@router.delete("/{visitor_id}")
async def delete_unknown_visitor(visitor_id: int):
    """Deletes unknown visitor record and snapshot."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT best_snapshot_path FROM unknown_visitors WHERE id = ?;", (visitor_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                file_path = BASE_DIR / row[0].lstrip("/")
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception:
                        pass

        await db.execute("DELETE FROM unknown_visitors WHERE id = ?;", (visitor_id,))
        await db.commit()
    return {"status": "success", "message": f"Deleted unknown visitor {visitor_id}"}
