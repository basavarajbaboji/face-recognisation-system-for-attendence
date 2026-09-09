import os
import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR.parent))

import sqlite3
import cv2
import numpy as np
from backend.app.config import DB_PATH, FACES_DIR, DEFAULT_SIMILARITY_THRESHOLD
from backend.app.ai_engine.detector import YuNetFaceDetector
from backend.app.ai_engine.aligner import FaceAlignerAndQuality
from backend.app.ai_engine.embedder import ArcFaceEmbedder
from backend.app.database import serialize_embedding, deserialize_embedding

def reembed_all_users():
    print("==================================================")
    print("Re-embedding all enrolled users with fixed ArcFace")
    print("==================================================")

    detector = YuNetFaceDetector()
    aligner = FaceAlignerAndQuality()
    embedder = ArcFaceEmbedder()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Update system settings threshold
    c.execute("UPDATE system_settings SET value = ? WHERE key = 'similarity_threshold';", (str(DEFAULT_SIMILARITY_THRESHOLD),))
    print(f"Updated system_settings similarity_threshold to {DEFAULT_SIMILARITY_THRESHOLD}")

    # 2. Fetch all enrolled users
    c.execute("SELECT id, roll_number, name, photo_path FROM users;")
    users = c.fetchall()
    print(f"Found {len(users)} enrolled profiles in database.")

    reembedded_count = 0
    cached_embeddings = {}

    for user_id, roll_number, name, photo_path in users:
        if not photo_path:
            print(f"[SKIP] User ID {user_id} ({name}) has no photo_path.")
            continue

        # Handle leading slash if present
        clean_path = photo_path.lstrip("/\\")
        if clean_path.startswith("data/"):
            disk_path = BASE_DIR / clean_path
        elif clean_path.startswith("backend/"):
            disk_path = BASE_DIR.parent / clean_path
        else:
            disk_path = BASE_DIR / "data" / clean_path

        if not disk_path.exists():
            # Fallback to direct check in FACES_DIR with filename
            filename = Path(clean_path).name
            disk_path = FACES_DIR / filename

        if not disk_path.exists():
            print(f"[WARN] Photo not found on disk: {disk_path} for {name} ({roll_number})")
            continue

        img = cv2.imread(str(disk_path))
        if img is None:
            print(f"[ERROR] Could not read image: {disk_path}")
            continue

        detections = detector.detect(img)
        if detections:
            best_det = max(detections, key=lambda d: d["bbox"][2] * d["bbox"][3])
            quality = aligner.calculate_quality(img, best_det["bbox"], best_det["landmarks"])
            aligned = aligner.align_face(img, best_det["landmarks"])
        else:
            print(f"[INFO] No face detector hit on photo for {name}, using center crop resize")
            aligned = cv2.resize(img, (112, 112))
            quality = 50.0

        new_embedding = embedder.extract_embedding(aligned)
        emb_norm = float(np.linalg.norm(new_embedding))

        if emb_norm < 0.5:
            print(f"[ERROR] Embedding extraction failed for {name} ({roll_number})")
            continue

        # Update or Insert in user_embeddings table
        c.execute("SELECT id FROM user_embeddings WHERE user_id = ? AND angle = 'front';", (user_id,))
        existing_emb = c.fetchone()

        if existing_emb:
            c.execute("""
                UPDATE user_embeddings
                SET embedding = ?, quality_score = ?
                WHERE id = ?;
            """, (serialize_embedding(new_embedding), quality, existing_emb[0]))
        else:
            c.execute("""
                INSERT INTO user_embeddings (user_id, embedding, angle, quality_score)
                VALUES (?, ?, 'front', ?);
            """, (user_id, serialize_embedding(new_embedding), quality))

        cached_embeddings[name] = new_embedding
        reembedded_count += 1
        print(f"[OK] Re-embedded: {name} ({roll_number}) -> L2 norm = {emb_norm:.4f}, Quality = {quality:.1f}")

    conn.commit()
    print(f"\nSuccessfully updated {reembedded_count} / {len(users)} profiles in database!")

    # 3. Print Cross-Similarity Verification Matrix
    print("\n--- Cross-Similarity Verification Matrix ---")
    names = list(cached_embeddings.keys())
    if names:
        ref_name = names[0]
        ref_emb = cached_embeddings[ref_name]
        print(f"Reference user: '{ref_name}'")
        for other_name in names:
            sim = float(np.dot(ref_emb, cached_embeddings[other_name]))
            print(f"  vs {other_name:30s} -> Cosine Similarity: {sim:.4f}")

    conn.close()

if __name__ == "__main__":
    reembed_all_users()
