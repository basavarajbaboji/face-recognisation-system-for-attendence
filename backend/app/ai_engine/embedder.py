import cv2
import numpy as np
import onnxruntime as ort
import logging
from pathlib import Path
from typing import Optional
from ..config import ARCFACE_MODEL_PATH

logger = logging.getLogger(__name__)

class ArcFaceEmbedder:
    """
    ArcFace MobileFaceNet ONNX Feature Extractor.
    Extracts 512-dimensional L2-normalized embedding vectors from 112x112 aligned face crops.
    """
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = str(model_path or ARCFACE_MODEL_PATH)
        self.session = None
        self.input_name = None
        self.output_name = None
        self._init_session()

    def _init_session(self):
        try:
            # Set thread options for maximum multicore vector throughput
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 0
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            available = ort.get_available_providers()
            providers = []
            if 'DmlExecutionProvider' in available:
                providers.append('DmlExecutionProvider')
            providers.append('CPUExecutionProvider')

            self.session = ort.InferenceSession(self.model_path, opts, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            logger.info(f"ArcFace ONNX Embedder initialized with providers: {self.session.get_providers()}")
        except Exception as e:
            logger.error(f"Error initializing ArcFace session from {self.model_path}: {e}")
            self.session = None

    def extract_embedding(self, aligned_face_112: np.ndarray) -> np.ndarray:
        """
        Takes a 112x112 RGB or BGR aligned face crop,
        returns 512-dimensional float32 vector normalized to unit length (L2 norm = 1.0).
        """
        if self.session is None:
            # Fallback zero vector if session not loaded
            return np.zeros((512,), dtype=np.float32)

        # Ensure correct size
        if aligned_face_112.shape[:2] != (112, 112):
            aligned_face_112 = cv2.resize(aligned_face_112, (112, 112))

        # Ensure 3-channel RGB float32 in range [0..255]
        # NOTE: This ArcFace ResNet100/MobileFaceNet ONNX expects raw [0..255] float32 RGB.
        # Normalizing via (img - 127.5)/128.0 causes model collapse where all embeddings have >0.98 similarity!
        if len(aligned_face_112.shape) == 2:
            img = cv2.cvtColor(aligned_face_112, cv2.COLOR_GRAY2RGB)
        elif aligned_face_112.shape[2] == 4:
            img = cv2.cvtColor(aligned_face_112, cv2.COLOR_BGRA2RGB)
        else:
            img = cv2.cvtColor(aligned_face_112, cv2.COLOR_BGR2RGB)

        img = img.astype(np.float32)
        blob = np.transpose(img, (2, 0, 1))  # (3, 112, 112)
        blob = np.expand_dims(blob, axis=0)  # (1, 3, 112, 112)

        # Inference
        outputs = self.session.run([self.output_name], {self.input_name: blob})
        embedding = outputs[0][0].astype(np.float32)

        # L2 Normalization (Essential for Cosine Distance = Dot Product)
        norm = np.linalg.norm(embedding)
        if norm > 1e-6:
            embedding = embedding / norm
        else:
            embedding = np.zeros_like(embedding)

        return embedding
