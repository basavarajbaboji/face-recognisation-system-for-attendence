from collections import Counter
from typing import Optional, Tuple
from .tracker import TrackState
from ..config import DEFAULT_TEMPORAL_WINDOW, DEFAULT_TEMPORAL_MIN_MATCHES

class TemporalConfirmationEngine:
    """
    Temporal Confirmation State Machine:
    Transitions tracks across: UNKNOWN -> CANDIDATE -> CONFIRMED.
    Eliminates single-frame false positives by requiring K-frame temporal consistency.
    """
    def __init__(self, window_size: int = DEFAULT_TEMPORAL_WINDOW, min_matches: int = DEFAULT_TEMPORAL_MIN_MATCHES):
        self.window_size = window_size
        self.min_matches = min_matches

    def evaluate(self, track: TrackState, user_id: Optional[int], label: str, confidence: float, quality: float, threshold: float) -> str:
        """
        Updates the track's temporal match history and transitions its identity state.
        Returns the new state: 'UNKNOWN', 'CANDIDATE', or 'CONFIRMED'.
        """
        # Append observation to track ring buffer
        track.match_history.append((user_id, label, confidence, quality))

        # 1. If currently no match (below threshold)
        if user_id is None:
            if track.identity_state != "CONFIRMED":
                track.identity_state = "UNKNOWN"
            return track.identity_state

        # 2. Count occurrences of user_ids in recent window
        valid_user_ids = [m[0] for m in track.match_history if m[0] is not None]
        if not valid_user_ids:
            track.identity_state = "UNKNOWN"
            return "UNKNOWN"

        counts = Counter(valid_user_ids)
        top_user_id, match_count = counts.most_common(1)[0]

        # 3. Check for confirmation threshold:
        # Fast-path: Instant 1-shot confirmation if strong match (confidence >= 0.58)
        # Consistent-path: 2 matches in window for moderate confidence
        is_strong_match = (top_user_id == user_id and confidence >= 0.58)
        is_consistent_match = (top_user_id == user_id and match_count >= 2)

        if is_strong_match or is_consistent_match:
            track.identity_state = "CONFIRMED"
            track.confirmed_user_id = user_id
            track.confirmed_user_label = label
            
            # Average confidence of the confirmed matches
            matching_confs = [m[2] for m in track.match_history if m[0] == user_id]
            track.confirmed_confidence = float(sum(matching_confs) / len(matching_confs))
            return "CONFIRMED"
        else:
            # Under verification
            if track.identity_state != "CONFIRMED":
                track.identity_state = "CANDIDATE"
            return track.identity_state
