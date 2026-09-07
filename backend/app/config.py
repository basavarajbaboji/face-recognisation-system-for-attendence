import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
FACES_DIR = DATA_DIR / "faces"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "campus_attendance.db"

# Create directories if they do not exist
for directory in [DATA_DIR, MODELS_DIR, SNAPSHOTS_DIR, FACES_DIR, EXPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Model Paths
YUNET_MODEL_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
ARCFACE_MODEL_PATH = MODELS_DIR / "arcface_mobilefacenet.onnx"

# Model URLs (Official OpenCV Zoo & InsightFace ONNX)
YUNET_MODEL_URL = "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
ARCFACE_MODEL_URL = "https://github.com/natanielruiz/arcface-onnx/raw/master/arcface_mobilefacenet.onnx"

# Default Surveillance & Attendance Thresholds
DEFAULT_SIMILARITY_THRESHOLD = 0.55
DEFAULT_MIN_QUALITY_SCORE = 10.0  # Sharpness / Laplacian variance threshold (realistic for live webcam)
DEFAULT_TEMPORAL_WINDOW = 4       # Check last 4 frames
DEFAULT_TEMPORAL_MIN_MATCHES = 2  # Require 2 matches in window for borderline match (instant on strong match)
DEFAULT_ATTENDANCE_COOLDOWN_MINUTES = 10  # 10 min debounce before logging again
DEFAULT_TRACK_RECOG_TTL_FRAMES = 20       # Re-check recognition after 20 frames

# Gate / Camera Config
DEFAULT_CAMERA_SOURCE = "0"  # '0' for default webcam, or 'rtsp://...'
DEFAULT_GATE_NAME = "Main Campus Gate - Entry A"
DEFAULT_LATE_TIME = "09:15"  # 9:15 AM
