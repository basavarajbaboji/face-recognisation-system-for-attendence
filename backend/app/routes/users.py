import io
import cv2
import base64
import zipfile
import aiosqlite
import numpy as np
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime
from PIL import Image

from ..config import FACES_DIR, DB_PATH
from ..database import serialize_embedding
from ..ai_engine.detector import YuNetFaceDetector
from ..ai_engine.aligner import FaceAlignerAndQuality
from ..ai_engine.embedder import ArcFaceEmbedder
from ..ai_engine.camera_manager import camera_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["Users & Enrollment"])

detector = YuNetFaceDetector()
aligner = FaceAlignerAndQuality()
embedder = ArcFaceEmbedder()

def extract_face_embedding_from_bytes(image_bytes: bytes) -> Optional[tuple]:
    """Helper to decode image, detect face, align, and extract 512-d embedding + quality."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    detections = detector.detect(img)
    if not detections:
        return None

    # Pick largest face
    best_det = max(detections, key=lambda d: d["bbox"][2] * d["bbox"][3])
    quality = aligner.calculate_quality(img, best_det["bbox"], best_det["landmarks"])
    aligned = aligner.align_face(img, best_det["landmarks"])
    embedding = embedder.extract_embedding(aligned)

    return embedding, quality, aligned

@router.get("/")
async def list_users(search: Optional[str] = None, department: Optional[str] = None, role: Optional[str] = None):
    """List all enrolled students and faculty with their template count."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT u.id, u.roll_number, u.name, u.role, u.department, u.year, u.email, u.photo_path, u.is_active, u.created_at,
                   COUNT(e.id) as template_count
            FROM users u
            LEFT JOIN user_embeddings e ON u.id = e.user_id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (u.name LIKE ? OR u.roll_number LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if department and department != "All":
            query += " AND u.department = ?"
            params.append(department)
        if role and role != "All":
            query += " AND u.role = ?"
            params.append(role)

        query += " GROUP BY u.id ORDER BY u.id DESC;"
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

@router.post("/enroll-single")
async def enroll_single_user(
    roll_number: str = Form(...),
    name: str = Form(...),
    role: str = Form("student"),
    department: str = Form(...),
    year: str = Form("1st Year"),
    email: Optional[str] = Form(None),
    front_photo: UploadFile = File(...),
    left_photo: Optional[UploadFile] = File(None),
    right_photo: Optional[UploadFile] = File(None)
):
    """
    3-Angle Guided Enrollment (Front, Left, Right).
    Extracts embeddings for each angle and stores them in user_embeddings.
    """
    # 1. Process Front Photo (Mandatory)
    front_bytes = await front_photo.read()
    front_res = extract_face_embedding_from_bytes(front_bytes)
    if not front_res:
        raise HTTPException(status_code=400, detail="No clear face detected in front photo.")

    front_emb, front_qual, front_aligned = front_res

    # Save primary photo to disk
    photo_filename = f"{roll_number.replace(' ', '_')}_front.jpg"
    photo_path = FACES_DIR / photo_filename
    cv2.imwrite(str(photo_path), front_aligned)
    relative_photo_path = f"/data/faces/{photo_filename}"

    # 2. Insert into users table
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            cursor = await db.execute("""
                INSERT INTO users (roll_number, name, role, department, year, email, photo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (roll_number.strip(), name.strip(), role, department, year, email, relative_photo_path))
            user_id = cursor.lastrowid
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"User with Roll Number '{roll_number}' already exists or DB error: {e}")

        # 3. Store Front Template
        await db.execute("""
            INSERT INTO user_embeddings (user_id, embedding, angle, quality_score)
            VALUES (?, ?, 'front', ?);
        """, (user_id, serialize_embedding(front_emb), front_qual))

        # 4. Process Left Photo (Optional)
        if left_photo:
            left_bytes = await left_photo.read()
            left_res = extract_face_embedding_from_bytes(left_bytes)
            if left_res:
                left_emb, left_qual, _ = left_res
                await db.execute("""
                    INSERT INTO user_embeddings (user_id, embedding, angle, quality_score)
                    VALUES (?, ?, 'left', ?);
                """, (user_id, serialize_embedding(left_emb), left_qual))

        # 5. Process Right Photo (Optional)
        if right_photo:
            right_bytes = await right_photo.read()
            right_res = extract_face_embedding_from_bytes(right_bytes)
            if right_res:
                right_emb, right_qual, _ = right_res
                await db.execute("""
                    INSERT INTO user_embeddings (user_id, embedding, angle, quality_score)
                    VALUES (?, ?, 'right', ?);
                """, (user_id, serialize_embedding(right_emb), right_qual))

        # 6. Audit Log
        await db.execute("""
            INSERT INTO audit_logs (action, actor, details)
            VALUES ('Enroll User', 'Admin', ?);
        """, (f"Enrolled {name} ({roll_number}) in {department}",))

        await db.commit()

    # Immediately hot-reload in-memory embeddings so camera detects person instantly!
    await camera_manager.reload_vectors()

    return {"status": "success", "message": f"Successfully enrolled {name}", "user_id": user_id}

@router.post("/quick-enroll")
async def quick_enroll_user(
    name: str = Form(...),
    roll_number: str = Form(...),
    department: str = Form("Computer Science"),
    role: str = Form("student"),
    year: str = Form("1st Year"),
    email: Optional[str] = Form(None),
    photo_file: Optional[UploadFile] = File(None),
    photo_base64: Optional[str] = Form(None)
):
    """
    Fast 1-Click Enrollment:
    Upload a photo or submit a webcam snapshot (base64).
    Extracts ArcFace embedding, inserts into SQLite, and immediately reloads
    active camera matchers so the person is instantly detectable on live CCTV.
    """
    image_bytes = None
    if photo_file:
        image_bytes = await photo_file.read()
    elif photo_base64:
        # Strip data:image/...;base64, prefix if present
        b64_str = photo_base64.split(",")[-1] if "," in photo_base64 else photo_base64
        try:
            image_bytes = base64.b64decode(b64_str)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {e}")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="No photo file or camera snapshot provided.")

    res = extract_face_embedding_from_bytes(image_bytes)
    if not res:
        raise HTTPException(status_code=400, detail="No clear face detected in provided photo. Please ensure face is centered and clearly visible.")

    emb, qual, aligned = res
    clean_roll = roll_number.strip().replace(" ", "_")
    photo_filename = f"{clean_roll}_front.jpg"
    photo_path = FACES_DIR / photo_filename
    cv2.imwrite(str(photo_path), aligned)
    rel_path = f"/data/faces/{photo_filename}"

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            cursor = await db.execute("""
                INSERT INTO users (roll_number, name, role, department, year, email, photo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (roll_number.strip(), name.strip(), role, department, year, email, rel_path))
            user_id = cursor.lastrowid

            await db.execute("""
                INSERT INTO user_embeddings (user_id, embedding, angle, quality_score)
                VALUES (?, ?, 'front', ?);
            """, (user_id, serialize_embedding(emb), qual))

            await db.execute("""
                INSERT INTO audit_logs (action, actor, details)
                VALUES ('Quick Enroll', 'Admin', ?);
            """, (f"Quick enrolled {name} ({roll_number}) in {department}",))

            await db.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"User with ID/Roll Number '{roll_number}' already exists or DB error: {e}")

    # Immediately hot-reload in-memory embeddings so camera detects person instantly!
    await camera_manager.reload_vectors()

    return {
        "status": "success",
        "message": f"Successfully enrolled {name} ({roll_number})! Camera is now actively detecting them.",
        "user_id": user_id,
        "name": name,
        "roll_number": roll_number
    }

@router.post("/enroll-bulk-zip")
async def enroll_bulk_zip(
    zip_file: UploadFile = File(...),
    default_department: str = Form("Computer Science"),
    default_role: str = Form("student")
):
    """
    Bulk Batch Enrollment via ZIP archive.
    Extracts images named 'RollNo_Name.jpg' (or 'RollNo.jpg'), detects faces,
    extracts embeddings, and bulk inserts into SQLite.
    """
    contents = await zip_file.read()
    success_count = 0
    failed_count = 0
    errors = []

    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as z:
            for filename in z.namelist():
                if filename.startswith("__MACOSX") or not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue

                basename = filename.split("/")[-1]
                name_without_ext = basename.rsplit(".", 1)[0]
                parts = name_without_ext.split("_")
                
                roll_number = parts[0].strip()
                name = parts[1].strip().replace("-", " ") if len(parts) > 1 else roll_number

                image_bytes = z.read(filename)
                res = extract_face_embedding_from_bytes(image_bytes)
                if not res:
                    failed_count += 1
                    errors.append(f"{basename}: No face detected")
                    continue

                emb, qual, aligned = res
                photo_filename = f"{roll_number}_bulk.jpg"
                photo_path = FACES_DIR / photo_filename
                cv2.imwrite(str(photo_path), aligned)
                rel_path = f"/data/faces/{photo_filename}"

                async with aiosqlite.connect(DB_PATH) as db:
                    try:
                        cursor = await db.execute("""
                            INSERT INTO users (roll_number, name, role, department, year, photo_path)
                            VALUES (?, ?, ?, ?, '1st Year', ?);
                        """, (roll_number, name, default_role, default_department, rel_path))
                        user_id = cursor.lastrowid

                        await db.execute("""
                            INSERT INTO user_embeddings (user_id, embedding, angle, quality_score)
                            VALUES (?, ?, 'bulk', ?);
                        """, (user_id, serialize_embedding(emb), qual))
                        await db.commit()
                        success_count += 1
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"{basename}: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ZIP archive: {e}")

    if success_count > 0:
        await camera_manager.reload_vectors()

    return {
        "status": "completed",
        "enrolled_count": success_count,
        "failed_count": failed_count,
        "errors": errors[:10]
    }

@router.delete("/{user_id}")
async def delete_user(user_id: int):
    """Deletes user and cascades to all embedding templates, photos, and logs."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # Get photo_path before deleting to clean up files
        async with db.execute("SELECT photo_path FROM users WHERE id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            photo_rel_path = row[0]
            if photo_rel_path:
                try:
                    fname = Path(photo_rel_path).name
                    fpath = FACES_DIR / fname
                    if fpath.exists():
                        fpath.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete photo file for user {user_id}: {e}")

        # Explicitly delete all associated templates and events to guarantee clean DB
        await db.execute("DELETE FROM user_embeddings WHERE user_id = ?;", (user_id,))
        await db.execute("DELETE FROM attendance_events WHERE user_id = ?;", (user_id,))
        await db.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        
        await db.execute("""
            INSERT INTO audit_logs (action, actor, details)
            VALUES ('Delete User', 'Admin', ?);
        """, (f"Deleted user ID {user_id}",))
        await db.commit()

    # Immediately hot-reload in-memory embeddings across all active camera pipelines
    await camera_manager.reload_vectors()
    return {"status": "success", "message": f"Deleted user {user_id}"}
