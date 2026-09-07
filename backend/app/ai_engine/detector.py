import cv2
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..config import YUNET_MODEL_PATH

logger = logging.getLogger(__name__)

class YuNetFaceDetector:
    """
    Ultra-fast Face Detector using OpenCV YuNet ONNX model (5-10ms per frame).
    Detects bounding boxes and 5 facial landmarks (eyes, nose, mouth corners).
    """
    def __init__(self, model_path: Optional[Path] = None, score_threshold: float = 0.6, nms_threshold: float = 0.3):
        self.model_path = str(model_path or YUNET_MODEL_PATH)
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.detector = None
        self.current_input_size = (320, 320)
        self._init_detector()

    def _init_detector(self):
        try:
            self.detector = cv2.FaceDetectorYN.create(
                model=self.model_path,
                config="",
                input_size=self.current_input_size,
                score_threshold=self.score_threshold,
                nms_threshold=self.nms_threshold,
                top_k=5000
            )
            logger.info("YuNet Face Detector initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing YuNet detector from {self.model_path}: {e}")
            self.detector = None

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces in an RGB/BGR image.
        Returns list of dicts:
            {
                "bbox": [x, y, w, h],
                "score": float,
                "landmarks": np.ndarray shape (5, 2) [[re_x, re_y], [le_x, le_y], [nt_x, nt_y], [rcm_x, rcm_y], [lcm_x, lcm_y]]
            }
        """
        if self.detector is None:
            return []

        h_orig, w_orig = frame.shape[:2]
        
        # Optimize detection speed: downscale for inference if width > 480
        if w_orig > 480:
            scale = 480.0 / w_orig
            det_w = 480
            det_h = int(round(h_orig * scale))
            det_frame = cv2.resize(frame, (det_w, det_h), interpolation=cv2.INTER_LINEAR)
            inv_scale = 1.0 / scale
        else:
            scale = 1.0
            inv_scale = 1.0
            det_w = w_orig
            det_h = h_orig
            det_frame = frame

        if (det_w, det_h) != self.current_input_size:
            self.detector.setInputSize((det_w, det_h))
            self.current_input_size = (det_w, det_h)

        _, faces = self.detector.detect(det_frame)
        if faces is None or len(faces) == 0:
            return []

        raw_boxes = []
        raw_scores = []
        raw_landmarks = []

        for face in faces:
            # Scale coordinates back up to native frame resolution
            x = int(round(face[0] * inv_scale))
            y = int(round(face[1] * inv_scale))
            w = int(round(face[2] * inv_scale))
            h = int(round(face[3] * inv_scale))
            score = float(face[14])
            
            # Minimum size threshold to ignore micro background noise
            if w < 30 or h < 30 or score < 0.55:
                continue

            # Clamp coordinates
            x1 = max(0, x)
            y1 = max(0, y)
            w = min(w_orig - x1, w)
            h = min(h_orig - y1, h)

            if w <= 0 or h <= 0:
                continue

            landmarks = np.array([
                [face[4] * inv_scale, face[5] * inv_scale],   # Right eye
                [face[6] * inv_scale, face[7] * inv_scale],   # Left eye
                [face[8] * inv_scale, face[9] * inv_scale],   # Nose tip
                [face[10] * inv_scale, face[11] * inv_scale], # Right mouth corner
                [face[12] * inv_scale, face[13] * inv_scale]  # Left mouth corner
            ], dtype=np.float32)

            raw_boxes.append([x1, y1, w, h])
            raw_scores.append(score)
            raw_landmarks.append(landmarks)

        if not raw_boxes:
            return []

        # Strict Non-Maximum Suppression (NMS) to eliminate duplicate overlapping face proposals
        indices = cv2.dnn.NMSBoxes(raw_boxes, raw_scores, score_threshold=0.55, nms_threshold=0.30)
        
        results = []
        if len(indices) > 0:
            for i in indices.flatten():
                results.append({
                    "bbox": raw_boxes[i],
                    "score": raw_scores[i],
                    "landmarks": raw_landmarks[i]
                })

        return results
