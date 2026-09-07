import cv2
import numpy as np
from typing import Tuple, Optional

# Standard reference landmarks for ArcFace 112x112 aligned crops
# Format: [Right Eye, Left Eye, Nose Tip, Right Mouth, Left Mouth]
ARCFACE_REF_LANDMARKS = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041]
], dtype=np.float32)

class FaceAlignerAndQuality:
    """
    Standardizes face alignment to 112x112 using similarity transform,
    and computes sharpness/quality score using Laplacian variance and geometry.
    """
    @staticmethod
    def align_face(frame: np.ndarray, landmarks: np.ndarray, output_size: Tuple[int, int] = (112, 112)) -> np.ndarray:
        """
        Warps face to standard 112x112 coordinate space using similarity transform.
        """
        try:
            # Estimate partial affine transformation using standard closed-form least squares (fast & exact for 5 points)
            M, _ = cv2.estimateAffinePartial2D(landmarks, ARCFACE_REF_LANDMARKS)
            if M is None:
                # Fallback to simple crop if matrix estimation fails
                return cv2.resize(frame, output_size)
            aligned = cv2.warpAffine(frame, M, output_size, borderValue=0.0)
            return aligned
        except Exception:
            return cv2.resize(frame, output_size)

    @staticmethod
    def calculate_quality(frame: np.ndarray, bbox: list, landmarks: Optional[np.ndarray] = None) -> float:
        """
        Computes an empirical face quality score (0 - 100+).
        Factors:
        - Sharpness: Laplacian variance of gray face crop
        - Resolution: Bounding box area
        - Landmark Symmetry: Eye level alignment
        """
        x, y, w, h = bbox
        h_img, w_img = frame.shape[:2]

        # Clamp bounding box inside image
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(w_img, x + w)
        y2 = min(h_img, y + h)

        if x2 <= x1 or y2 <= y1 or w < 24 or h < 24:
            return 0.0

        face_crop = frame[y1:y2, x1:x2]
        if face_crop.size == 0:
            return 0.0

        # 1. Fast Sharpness via 16-bit Laplacian Variance
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_16S).var())

        # 2. Resolution bonus (Faces > 80x80 get higher weight)
        area = w * h
        res_factor = min(1.5, area / (64.0 * 64.0))

        # 3. Symmetry / Angle penalty if landmarks available
        symmetry_factor = 1.0
        if landmarks is not None and len(landmarks) == 5:
            r_eye, l_eye = landmarks[0], landmarks[1]
            eye_angle = abs(np.arctan2(l_eye[1] - r_eye[1], l_eye[0] - r_eye[0]))
            if eye_angle > 0.4:  # Extreme head tilt
                symmetry_factor = 0.7

        quality_score = laplacian_var * res_factor * symmetry_factor
        return float(quality_score)
