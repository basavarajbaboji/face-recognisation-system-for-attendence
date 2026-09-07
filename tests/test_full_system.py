import asyncio
import numpy as np
import cv2
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.config import DB_PATH, SNAPSHOTS_DIR
from backend.app.database import init_db, serialize_embedding, deserialize_embedding, load_all_enrolled_templates_sync
from backend.app.ai_engine.detector import YuNetFaceDetector
from backend.app.ai_engine.aligner import FaceAlignerAndQuality
from backend.app.ai_engine.embedder import ArcFaceEmbedder
from backend.app.ai_engine.tracker import ByteTracker, TrackState
from backend.app.ai_engine.matcher import MultiTemplateVectorMatcher
from backend.app.ai_engine.temporal_engine import TemporalConfirmationEngine
from backend.app.ai_engine.unknown_manager import UnknownVisitorManager

async def run_all_tests():
    print("==================================================")
    print("[RUNNING] SMART CAMPUS ATTENDANCE SYSTEM TESTS")
    print("==================================================")

    # Test 1: Database Init & Serialization
    print("\n[Test 1/7] Testing Database Init & Vector Serialization...")
    await init_db()
    test_vec = np.random.randn(512).astype(np.float32)
    test_vec = test_vec / np.linalg.norm(test_vec)
    blob = serialize_embedding(test_vec)
    assert len(blob) == 512 * 4, f"Expected 2048 bytes, got {len(blob)}"
    deserialized = deserialize_embedding(blob)
    assert np.allclose(test_vec, deserialized, atol=1e-5), "Deserialized vector mismatch"
    print("[PASS] Database Init & Vector BLOB Serialization passed.")

    # Test 2: AI Face Detector
    print("\n[Test 2/7] Testing YuNet Face Detector...")
    detector = YuNetFaceDetector()
    assert detector.detector is not None, "YuNet detector failed to load ONNX model"
    # Create test image with face-like structure
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(test_frame, (320, 240), 60, (200, 200, 200), -1)
    dets = detector.detect(test_frame)
    print(f"[PASS] YuNet Detector initialized and processed frame (found {len(dets)} detections on synthetic circle).")

    # Test 3: Face Aligner & Quality Scorer
    print("\n[Test 3/7] Testing Face Aligner & Quality Assessment...")
    aligner = FaceAlignerAndQuality()
    fake_landmarks = np.array([[38, 51], [73, 51], [56, 71], [41, 92], [70, 92]], dtype=np.float32)
    aligned = aligner.align_face(test_frame, fake_landmarks)
    assert aligned.shape == (112, 112, 3), f"Aligned shape mismatch: {aligned.shape}"
    qual = aligner.calculate_quality(test_frame, [260, 180, 120, 120], fake_landmarks)
    assert isinstance(qual, float), "Quality calculation failed"
    print(f"[PASS] Face Aligner warped to (112, 112, 3) and computed quality ({qual:.2f}).")

    # Test 4: ArcFace ONNX Embedder
    print("\n[Test 4/7] Testing ArcFace 512-d Feature Extractor...")
    embedder = ArcFaceEmbedder()
    assert embedder.session is not None, "ArcFace ONNX session failed to load"
    dummy_crop = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
    emb = embedder.extract_embedding(dummy_crop)
    assert emb.shape == (512,), f"Embedding shape mismatch: {emb.shape}"
    norm = np.linalg.norm(emb)
    assert np.isclose(norm, 1.0, atol=1e-3), f"L2 norm is not 1.0 (got {norm})"
    print(f"[PASS] ArcFace Embedder produced 512-d vector with L2 Norm = {norm:.4f}.")

    # Test 5: Vector Matcher (Multi-Template)
    print("\n[Test 5/7] Testing In-Memory Multi-Template Vector Matcher...")
    matcher = MultiTemplateVectorMatcher()
    # Inject synthetic user templates into matcher
    user1_emb1 = np.random.randn(512).astype(np.float32)
    user1_emb1 /= np.linalg.norm(user1_emb1)
    
    user1_emb2 = user1_emb1 + np.random.randn(512).astype(np.float32) * 0.05
    user1_emb2 /= np.linalg.norm(user1_emb2)

    matcher.user_ids = [101, 101]
    matcher.labels = ["Rahul Sharma (CS101)", "Rahul Sharma (CS101)"]
    matcher.embedding_matrix = np.vstack([user1_emb1, user1_emb2])

    # Query with close vector
    u_id, lbl, sim, _ = matcher.match_single(user1_emb1, threshold=0.60)
    assert u_id == 101, f"Expected user 101, got {u_id}"
    assert sim > 0.95, f"Expected high similarity, got {sim}"
    print(f"[PASS] Multi-template matcher identified User #101 with max similarity = {sim:.4f}.")

    # Test 6: Temporal Confirmation State Machine
    print("\n[Test 6/7] Testing Temporal Confirmation Engine (K-Frame Verification)...")
    temporal_engine = TemporalConfirmationEngine(window_size=5, min_matches=3)
    track = TrackState(track_id=1, bbox=[100, 100, 80, 80], landmarks=fake_landmarks, quality_score=50.0)
    
    assert track.identity_state == "UNKNOWN"
    
    # Frame 1: Match 1
    st1 = temporal_engine.evaluate(track, user_id=101, label="Rahul", confidence=0.75, quality=50.0, threshold=0.60)
    assert st1 == "CANDIDATE", f"Expected CANDIDATE, got {st1}"
    
    # Frame 2: Match 2
    st2 = temporal_engine.evaluate(track, user_id=101, label="Rahul", confidence=0.78, quality=52.0, threshold=0.60)
    assert st2 == "CANDIDATE", f"Expected CANDIDATE, got {st2}"
    
    # Frame 3: Match 3 -> Should transition to CONFIRMED
    st3 = temporal_engine.evaluate(track, user_id=101, label="Rahul", confidence=0.82, quality=55.0, threshold=0.60)
    assert st3 == "CONFIRMED", f"Expected CONFIRMED, got {st3}"
    assert track.confirmed_user_id == 101
    print("[PASS] Temporal state machine passed: UNKNOWN -> CANDIDATE -> CONFIRMED.")

    # Test 7: Unknown Visitor Deduplication Manager
    print("\n[Test 7/7] Testing Deduplicated Unknown Visitor Manager...")
    unknown_mgr = UnknownVisitorManager(min_hits=3)
    unknown_track = TrackState(track_id=99, bbox=[50, 50, 70, 70], landmarks=fake_landmarks, quality_score=40.0, face_crop=dummy_crop)
    unknown_track.hits = 4
    
    await unknown_mgr.process_unknown_track(unknown_track)
    assert 99 in unknown_mgr.active_unknowns, "Unknown track was not recorded in manager"
    print("[PASS] Unknown deduplication manager created single tracked record.")

    print("\n==================================================")
    print("[SUCCESS] ALL 7 SYSTEM TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
