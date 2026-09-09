import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import cv2
import numpy as np
from backend.app.ai_engine.detector import YuNetFaceDetector
from backend.app.ai_engine.aligner import FaceAlignerAndQuality
from backend.app.ai_engine.embedder import ArcFaceEmbedder
from backend.app.ai_engine.matcher import MultiTemplateVectorMatcher
from backend.app.config import DEFAULT_SIMILARITY_THRESHOLD

def run_tests():
    print("==================================================")
    print("Running Face Recognition Accuracy & Rejection Tests")
    print(f"Configured Similarity Threshold: {DEFAULT_SIMILARITY_THRESHOLD}")
    print("==================================================")

    detector = YuNetFaceDetector()
    aligner = FaceAlignerAndQuality()
    embedder = ArcFaceEmbedder()
    matcher = MultiTemplateVectorMatcher()

    print(f"Loaded {len(matcher.labels)} templates across {len(set(matcher.user_ids))} users.")
    assert len(matcher.labels) >= 9, "Expected at least 9 enrolled users!"

    # TEST 1: Enrolled users matching themselves accurately
    print("\n--- TEST 1: Enrolled Face Verification ---")
    faces_dir = BASE_DIR / "backend" / "data" / "faces"
    passed_enrolled = 0
    total_tested = 0

    for user_id, label in zip(matcher.user_ids, matcher.labels):
        roll = label.split(" (")[1].rstrip(")") if " (" in label else ""
        expected_name = label.split(" (")[0]
        
        # Find photo file
        matching_files = list(faces_dir.glob(f"*{roll}*.jpg"))
        if not matching_files:
            continue

        photo_path = matching_files[0]
        total_tested += 1
        img = cv2.imread(str(photo_path))
        dets = detector.detect(img)
        if dets:
            aligned = aligner.align_face(img, dets[0]["landmarks"])
        else:
            aligned = cv2.resize(img, (112, 112))

        emb = embedder.extract_embedding(aligned)
        matched_uid, matched_label, conf, top_matches = matcher.match_single(emb, threshold=DEFAULT_SIMILARITY_THRESHOLD)

        is_correct = (matched_uid == user_id)
        status = "PASS" if is_correct else "FAIL"
        print(f"[{status}] {expected_name} -> Matched: '{matched_label}' with Confidence: {conf:.2%}")
        if is_correct:
            passed_enrolled += 1

    print(f"Enrolled faces accuracy: {passed_enrolled} / {total_tested} ({passed_enrolled/total_tested:.1%})")
    assert passed_enrolled == total_tested, f"Failed: only {passed_enrolled}/{total_tested} matched correctly!"

    # TEST 2: Stranger / Unenrolled faces must be strictly UNKNOWN
    print("\n--- TEST 2: Unenrolled Stranger Rejection ---")
    # Generate synthetic random face variations and stranger patterns
    np.random.seed(42)
    stranger_rejected = 0
    for i in range(10):
        # Noise / stranger image
        stranger_crop = np.random.randint(40, 220, (112, 112, 3), dtype=np.uint8)
        emb = embedder.extract_embedding(stranger_crop)
        matched_uid, matched_label, conf, top = matcher.match_single(emb, threshold=DEFAULT_SIMILARITY_THRESHOLD)
        if matched_uid is None and matched_label == "Unknown":
            stranger_rejected += 1
        else:
            print(f"[FAIL] Stranger {i} falsely matched as: {matched_label} ({conf:.2%})")

    print(f"Stranger Rejection: {stranger_rejected} / 10 successfully marked Unknown.")
    assert stranger_rejected == 10, "Failed: Some strangers were falsely recognized!"

    # TEST 3: Wall and Non-Face Geometry Rejection in Detector
    print("\n--- TEST 3: Wall & Artifact Rejection in Detector ---")
    # A tall vertical door/wall panel with ratio 0.40
    door_rect = np.full((300, 100, 3), (180, 200, 190), dtype=np.uint8)
    dets = detector.detect(door_rect)
    print(f"Detections on plain vertical panel: {len(dets)} (Expected 0)")
    assert len(dets) == 0, "Failed: Detector detected a plain panel as a face!"

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY (100% ACCURACY)!")

if __name__ == "__main__":
    run_tests()
