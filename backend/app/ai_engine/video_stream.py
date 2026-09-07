import cv2
import time
import threading
import numpy as np
import logging
from typing import Union, Optional

logger = logging.getLogger(__name__)

class ThreadedVideoCapture:
    """
    High-performance, multi-threaded video stream grabber for Webcams and RTSP IP CCTV cameras.
    Runs frame decoding in a background thread and always returns the latest frame,
    eliminating RTSP buffer lag and blocking operations.
    """
    def __init__(self, source: Union[int, str] = 0):
        self.source = source
        self.cap = None
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_jpeg: Optional[bytes] = None
        self.is_running = False
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.fps = 0.0
        self.frame_count = 0
        self._start_capture()

    def _parse_source(self, src: Union[int, str]):
        if isinstance(src, str) and src.isdigit():
            return int(src)
        return src

    def _start_capture(self):
        parsed = self._parse_source(self.source)
        try:
            # DirectShow on Windows for faster webcam initialization if integer
            if isinstance(parsed, int):
                self.cap = cv2.VideoCapture(parsed, cv2.CAP_DSHOW)
            else:
                self.cap = cv2.VideoCapture(parsed)

            if not self.cap.isOpened():
                # Fallback standard backend
                self.cap = cv2.VideoCapture(parsed)

            if self.cap.isOpened():
                # Request MJPG fourcc to avoid uncompressed YUY2 USB bandwidth bottleneck on Windows
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                # Configure resolution
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                logger.info(f"Video capture opened successfully on source: {self.source}")
            else:
                logger.warning(f"Could not open video source {self.source}. Will provide standby test frame.")
        except Exception as e:
            logger.error(f"Error opening video capture source {self.source}: {e}")

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()

    def _capture_worker(self):
        last_time = time.time()
        while self.is_running:
            if self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    # Pre-encode JPEG once in background thread to avoid per-client compression CPU load
                    ret_jpg, jpeg_buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    with self.lock:
                        self.latest_frame = frame
                        if ret_jpg:
                            self.latest_jpeg = jpeg_buf.tobytes()
                    self.frame_count += 1
                    
                    # Calculate FPS every 30 frames
                    if self.frame_count % 30 == 0:
                        now = time.time()
                        self.fps = 30.0 / max(0.001, (now - last_time))
                        last_time = now
                else:
                    # Stream disconnected or frame read failed
                    with self.lock:
                        self.latest_frame = None
                        self.latest_jpeg = None
                    self.fps = 0.0
                    time.sleep(0.1)
            else:
                with self.lock:
                    self.latest_frame = None
                    self.latest_jpeg = None
                self.fps = 0.0
                time.sleep(0.2)

    def read(self) -> Optional[np.ndarray]:
        """Returns the most recent decoded video frame (thread-safe, non-blocking)."""
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def read_jpeg(self) -> Optional[bytes]:
        """Returns the latest pre-encoded JPEG bytes (instant, zero CPU encoding)."""
        with self.lock:
            return self.latest_jpeg

    def change_source(self, new_source: Union[int, str]):
        """Switches video source dynamically."""
        logger.info(f"Switching video stream source to: {new_source}")
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.cap is not None:
            self.cap.release()

        self.source = new_source
        self._start_capture()

    def release(self):
        """Releases the physical camera hardware handle and stops background thread."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=0.5)
            except Exception:
                pass
        with self.lock:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception as e:
                    logger.error(f"Error releasing camera capture: {e}")
                self.cap = None
            self.latest_frame = None
            self.latest_jpeg = None
            self.fps = 0.0
        logger.info(f"Released camera hardware handle for source: {self.source}")
