import os
import urllib.request
import logging
from pathlib import Path
from ..config import (
    YUNET_MODEL_PATH,
    YUNET_MODEL_URL,
    ARCFACE_MODEL_PATH,
    ARCFACE_MODEL_URL,
    MODELS_DIR
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Alternative Mirror URLs for maximum reliability
YUNET_MIRRORS = [
    YUNET_MODEL_URL,
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
]

ARCFACE_MIRRORS = [
    ARCFACE_MODEL_URL,
    "https://huggingface.co/garav/arcface-onnx/resolve/main/arcface_mobilefacenet.onnx",
    "https://github.com/onnx/models/raw/main/validated/vision/body_analysis/arcface/model/arcfaceresnet100-8.onnx"
]

def download_file(urls: list, dest_path: Path) -> bool:
    """Try downloading from mirrors until successful."""
    if dest_path.exists() and dest_path.stat().st_size > 10000:
        logger.info(f"Model already exists at: {dest_path}")
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    for url in urls:
        try:
            logger.info(f"Downloading model from {url} to {dest_path}...")
            # Custom User-Agent to avoid HTTP 403 on GitHub raw
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, 'wb') as out_file:
                out_file.write(response.read())

            if dest_path.stat().st_size > 10000:
                logger.info(f"Successfully downloaded {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")
                return True
            else:
                logger.warning(f"Downloaded file too small from {url}, trying next mirror...")
                dest_path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to download from {url}: {e}")

    return False

def ensure_models_available() -> bool:
    """Ensures YuNet and ArcFace ONNX models exist."""
    yunet_ok = download_file(YUNET_MIRRORS, YUNET_MODEL_PATH)
    arcface_ok = download_file(ARCFACE_MIRRORS, ARCFACE_MODEL_PATH)
    
    if not yunet_ok:
        logger.error(f"YuNet model could not be downloaded. Please place it at {YUNET_MODEL_PATH}")
    if not arcface_ok:
        logger.error(f"ArcFace model could not be downloaded. Please place it at {ARCFACE_MODEL_PATH}")

    return yunet_ok and arcface_ok

if __name__ == "__main__":
    ensure_models_available()
