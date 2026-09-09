import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.ai_engine.tracker import TrackState
from backend.app.ai_engine.temporal_engine import TemporalConfirmationEngine
import numpy as np

def test_temporal_state_machine():
    engine = TemporalConfirmationEngine()
    landmarks = np.zeros((5, 2), dtype=np.float32)
    
    # 1. Test genuine enrolled user entering
    track_enrolled = TrackState(track_id=1, bbox=[100, 100, 80, 80], landmarks=landmarks, quality_score=60.0)
    
    # Frame 1: High confidence match (0.88)
    state1 = engine.evaluate(track_enrolled, user_id=11, label="SHIVANAND", confidence=0.88, quality=60.0, threshold=0.50)
    print(f"Frame 1 (Initial detection): State = {state1} (Expected CANDIDATE)")
    assert state1 == "CANDIDATE", f"Expected CANDIDATE on frame 1, got {state1}"
    
    # Frame 2: Second consistent high confidence match (0.89)
    state2 = engine.evaluate(track_enrolled, user_id=11, label="SHIVANAND", confidence=0.89, quality=62.0, threshold=0.50)
    print(f"Frame 2 (Multi-frame agreement): State = {state2} (Expected CONFIRMED)")
    assert state2 == "CONFIRMED", f"Expected CONFIRMED on frame 2, got {state2}"
    assert track_enrolled.confirmed_user_id == 11
    
    # 2. Test unenrolled stranger
    track_stranger = TrackState(track_id=2, bbox=[200, 200, 80, 80], landmarks=landmarks, quality_score=50.0)
    
    # Frame 1: No match (below threshold)
    s1 = engine.evaluate(track_stranger, user_id=None, label="Unknown", confidence=0.22, quality=50.0, threshold=0.50)
    assert s1 == "UNKNOWN", f"Expected UNKNOWN, got {s1}"
    
    # Frame 2: No match
    s2 = engine.evaluate(track_stranger, user_id=None, label="Unknown", confidence=0.18, quality=52.0, threshold=0.50)
    assert s2 == "UNKNOWN", f"Expected UNKNOWN, got {s2}"
    
    # Frame 3: Random artifact 1-frame fluke
    s3 = engine.evaluate(track_stranger, user_id=1, label="Basavaraj", confidence=0.60, quality=50.0, threshold=0.50)
    assert s3 == "CANDIDATE", f"Expected CANDIDATE on 1-frame fluke, got {s3}"
    
    # Frame 4: Next frame returns to no match
    s4 = engine.evaluate(track_stranger, user_id=None, label="Unknown", confidence=0.15, quality=50.0, threshold=0.50)
    assert s4 == "UNKNOWN", f"Expected UNKNOWN after fluke drops, got {s4}"
    
    print("\nALL TEMPORAL ENGINE TESTS PASSED!")

if __name__ == "__main__":
    test_temporal_state_machine()
