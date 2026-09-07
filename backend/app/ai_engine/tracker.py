import numpy as np
import cv2
from collections import deque
from typing import List, Dict, Any, Optional, Tuple

def calculate_iou(box1: list, box2: list) -> float:
    """Calculate Intersection over Union (IoU) between two [x, y, w, h] boxes."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2

    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)

    inter_width = max(0, xi2 - xi1)
    inter_height = max(0, yi2 - yi1)
    inter_area = inter_width * inter_height

    box1_area = w1 * h1
    box2_area = w2 * h2
    union_area = box1_area + box2_area - inter_area

    if union_area <= 0:
        return 0.0
    return float(inter_area / union_area)


class TrackState:
    """
    State of a single tracked person across video frames.
    Tracks bounding box, movement, face quality, recognition status, and confirmation state.
    """
    def __init__(self, track_id: int, bbox: list, landmarks: np.ndarray, quality_score: float, face_crop: Optional[np.ndarray] = None):
        self.track_id = track_id
        self.bbox = bbox
        self.landmarks = landmarks
        self.history = deque(maxlen=20)
        self.history.append(bbox)
        
        self.age = 1
        self.time_since_update = 0
        self.hits = 1
        
        # State Machine: 'UNKNOWN' -> 'CANDIDATE' -> 'CONFIRMED'
        self.identity_state = "UNKNOWN"
        self.confirmed_user_id: Optional[int] = None
        self.confirmed_user_label: Optional[str] = None
        self.confirmed_confidence: float = 0.0
        
        # Best quality frame tracking for unknown snapshots & re-embedding
        self.best_quality_score = quality_score
        self.best_face_crop = face_crop
        self.best_landmarks = landmarks

        # Temporal Match History: list of (user_id, label, confidence, quality)
        self.match_history = deque(maxlen=8)
        self.frames_since_recognition = 0
        self.recognition_attempts = 0
        self.last_recognized_quality = 0.0
        self.attendance_marked = False

    def update(self, bbox: list, landmarks: np.ndarray, quality_score: float, face_crop: Optional[np.ndarray] = None):
        """Update track position and quality."""
        self.bbox = bbox
        self.landmarks = landmarks
        self.history.append(bbox)
        self.age += 1
        self.time_since_update = 0
        self.hits += 1
        self.frames_since_recognition += 1

        # Keep the best quality face crop
        if quality_score > self.best_quality_score and face_crop is not None:
            self.best_quality_score = quality_score
            self.best_face_crop = face_crop
            self.best_landmarks = landmarks

    def mark_missed(self):
        """Called when no detection matched this track in current frame."""
        self.age += 1
        self.time_since_update += 1
        self.frames_since_recognition += 1

    def record_recognition_attempt(self):
        """Marks that an ArcFace feature extraction was executed for this track."""
        self.frames_since_recognition = 0
        self.recognition_attempts += 1
        self.last_recognized_quality = self.best_quality_score

    def needs_recognition(self, min_quality: float = 8.0) -> bool:
        """
        Fast-response recognition trigger:
        - Runs ArcFace inference immediately on new tracks (initial 4 attempts).
        - Continues running on Candidate tracks without skipping frames to confirm in <0.3s.
        - Checks periodic refresh for unknown tracks every 3 frames (instead of 15 frames).
        - Re-checks confirmed tracks every 30 frames.
        """
        if self.best_quality_score < min_quality:
            return False

        if self.identity_state == "UNKNOWN":
            if self.recognition_attempts < 4:
                return True
            if self.best_quality_score > (self.last_recognized_quality * 1.15):
                return True
            return self.frames_since_recognition >= 3

        if self.identity_state == "CANDIDATE":
            return True

        if self.identity_state == "CONFIRMED":
            return self.frames_since_recognition >= 30

        return False


class ByteTracker:
    """
    Lightweight Multi-Target IoU Tracker for moving crowds.
    Maintains persistent IDs and track states at 30+ FPS.
    """
    def __init__(self, iou_threshold: float = 0.35, max_age: int = 25, min_hits: int = 2):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.next_track_id = 1
        self.tracks: List[TrackState] = []

    def update(self, detections: List[Dict[str, Any]], frame: np.ndarray) -> List[TrackState]:
        """
        Matches incoming face detections to existing tracks using IoU matching.
        """
        # 1. Predict / Age existing tracks
        for track in self.tracks:
            # Simple linear velocity prediction
            if len(track.history) >= 2:
                prev = track.history[-2]
                curr = track.history[-1]
                dx = curr[0] - prev[0]
                dy = curr[1] - prev[1]
                track.bbox = [curr[0] + dx, curr[1] + dy, curr[2], curr[3]]

        # 2. Build IoU Cost Matrix
        num_tracks = len(self.tracks)
        num_dets = len(detections)

        matched_tracks = set()
        matched_dets = set()

        if num_tracks > 0 and num_dets > 0:
            iou_matrix = np.zeros((num_tracks, num_dets), dtype=np.float32)
            for t_idx, track in enumerate(self.tracks):
                for d_idx, det in enumerate(detections):
                    iou_matrix[t_idx, d_idx] = calculate_iou(track.bbox, det["bbox"])

            # Greedy Matching from highest IoU down
            while True:
                max_val = np.max(iou_matrix)
                if max_val < self.iou_threshold:
                    break
                t_idx, d_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                if t_idx in matched_tracks or d_idx in matched_dets:
                    iou_matrix[t_idx, d_idx] = 0.0
                    continue

                matched_tracks.add(t_idx)
                matched_dets.add(d_idx)
                iou_matrix[t_idx, :] = 0.0
                iou_matrix[:, d_idx] = 0.0

                # Update matched track
                det = detections[d_idx]
                bbox = det["bbox"]
                landmarks = det.get("landmarks")
                quality = det.get("quality", 25.0)
                
                # Extract face crop
                x, y, w, h = bbox
                h_img, w_img = frame.shape[:2]
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(w_img, x + w), min(h_img, y + h)
                crop = frame[y1:y2, x1:x2].copy() if (x2 > x1 and y2 > y1) else None

                self.tracks[t_idx].update(bbox, landmarks, quality, crop)

        # 3. Create new tracks for unmatched detections
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_dets:
                bbox = det["bbox"]
                landmarks = det.get("landmarks")
                quality = det.get("quality", 25.0)

                x, y, w, h = bbox
                h_img, w_img = frame.shape[:2]
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(w_img, x + w), min(h_img, y + h)
                crop = frame[y1:y2, x1:x2].copy() if (x2 > x1 and y2 > y1) else None

                new_track = TrackState(self.next_track_id, bbox, landmarks, quality, crop)
                self.next_track_id += 1
                self.tracks.append(new_track)

        # 4. Mark missed tracks
        for t_idx, track in enumerate(self.tracks):
            if t_idx not in matched_tracks and t_idx < num_tracks:
                track.mark_missed()

        # 5. Remove dead or duplicate tracks
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        # 6. Deduplicate overlapping active tracks (if two tracks have IoU > 0.5, keep the older/confirmed one)
        active_now = [t for t in self.tracks if t.time_since_update == 0]
        suppressed_ids = set()
        for i in range(len(active_now)):
            for j in range(i + 1, len(active_now)):
                t1 = active_now[i]
                t2 = active_now[j]
                if calculate_iou(t1.bbox, t2.bbox) > 0.40:
                    # Keep confirmed or older track
                    if t1.identity_state == "CONFIRMED" and t2.identity_state != "CONFIRMED":
                        suppressed_ids.add(t2.track_id)
                    elif t2.identity_state == "CONFIRMED" and t1.identity_state != "CONFIRMED":
                        suppressed_ids.add(t1.track_id)
                    elif t1.hits >= t2.hits:
                        suppressed_ids.add(t2.track_id)
                    else:
                        suppressed_ids.add(t1.track_id)

        # Return active tracks seen in current frame
        return [t for t in active_now if t.track_id not in suppressed_ids]
