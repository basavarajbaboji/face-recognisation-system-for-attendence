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
            if track.identity_state == "CONFIRMED":
                # Decay identity if last 3 frames continuously fail to match
                recent_samples = list(track.match_history)[-3:]
                non_matches = sum(1 for m in recent_samples if m[0] is None or m[0] != track.confirmed_user_id)
                if non_matches >= 3:
                    track.identity_state = "UNKNOWN"
                    track.confirmed_user_id = None
                    track.confirmed_user_label = None
                    track.confirmed_confidence = 0.0
            else:
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
        # BULLETPROOF RULE: Never confirm identity on a single frame!
        # - High confidence (>= 0.80): requires at least 2 consistent frames in window
        # - Standard confidence (>= threshold): requires at least min_matches (3) consistent frames in window
        is_strong_consistent = (top_user_id == user_id and match_count >= 2 and confidence >= 0.80)
        is_standard_consistent = (top_user_id == user_id and match_count >= self.min_matches and confidence >= threshold)

        if is_strong_consistent or is_standard_consistent:
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
