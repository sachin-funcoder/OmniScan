# webcam_capture.py
# OmniScan Phase 3 — Laptop Webcam Capture
#
# Runs a background thread that continuously reads frames from the laptop webcam
# using OpenCV.  The latest JPEG-encoded frame is stored in a thread-safe buffer
# so FastAPI routes can serve it without blocking the event loop.
#
# Design decisions:
#   - A single daemon thread owns the capture loop; no other component may call
#     cv2.VideoCapture directly on the same device index.
#   - The latest raw frame (numpy array) is stored for YOLO inference.
#   - The latest JPEG frame is stored for the MJPEG HTTP stream.
#   - All state is protected by a threading.Lock.
#   - start() is idempotent: calling it twice does nothing extra.
#   - stop() releases the camera and joins the thread cleanly.

import threading
import time
import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Default webcam index — 0 is almost always the built-in laptop webcam on Windows
DEFAULT_CAMERA_INDEX = 0

# Target capture resolution (OpenCV will honour this if the webcam supports it)
CAPTURE_WIDTH  = 640
CAPTURE_HEIGHT = 480

# Target frame rate for the capture loop (frames per second)
TARGET_FPS = 30

# JPEG quality for the MJPEG stream (1–100; 80 is a good balance)
JPEG_QUALITY = 80


class WebcamCapture:
    """
    Manages a single laptop webcam.

    Usage:
        cap = WebcamCapture()
        cap.start()          # opens the camera, starts background thread
        frame = cap.get_latest_frame()   # numpy BGR array, or None
        jpeg  = cap.get_latest_jpeg()    # JPEG bytes for MJPEG stream, or None
        cap.stop()           # releases the camera
    """

    def __init__(self, camera_index: int = DEFAULT_CAMERA_INDEX):
        self._camera_index = camera_index
        self._lock         = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running      = False
        self._capture: Optional[cv2.VideoCapture] = None

        # Shared frame buffers — updated by the background thread
        self._latest_frame: Optional[np.ndarray] = None  # BGR numpy array
        self._latest_jpeg:  Optional[bytes]       = None  # JPEG bytes

        # Camera metadata
        self._frame_width:  int = CAPTURE_WIDTH
        self._frame_height: int = CAPTURE_HEIGHT
        self._error:        Optional[str] = None

    # ─── Public API ───────────────────────────────────────────────────────────

    def start(self) -> dict:
        """
        Open the webcam and start the background capture loop.
        Returns a status dict: { "success": bool, "error": str | None, ... }
        """
        with self._lock:
            if self._running:
                return self._make_status()  # Already running — idempotent

        # Open the camera *outside* the lock so we don't block readers during
        # a slow initialisation.
        cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            # Try again without CAP_DSHOW (fallback for some drivers)
            cap.release()
            cap = cv2.VideoCapture(self._camera_index)

        if not cap.isOpened():
            err = (
                f"Could not open webcam at index {self._camera_index}. "
                "Check that no other application is using the camera."
            )
            logger.error(err)
            with self._lock:
                self._error = err
            return {"success": False, "error": err, "active": False}

        # Apply resolution hints (camera may choose a different size)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS,          TARGET_FPS)

        with self._lock:
            self._capture      = cap
            self._running      = True
            self._error        = None
            self._frame_width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self._thread = threading.Thread(
            target=self._capture_loop,
            name="WebcamCaptureThread",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Webcam started: index=%d, resolution=%dx%d",
            self._camera_index, self._frame_width, self._frame_height,
        )
        return self._make_status()

    def stop(self) -> None:
        """
        Stop the capture loop and release the webcam resource.
        Safe to call even if the camera was never started.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False
            cap = self._capture
            self._capture = None

        if cap is not None:
            cap.release()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

        with self._lock:
            self._latest_frame = None
            self._latest_jpeg  = None

        logger.info("Webcam stopped and released.")

    @property
    def is_active(self) -> bool:
        """True while the capture loop is running."""
        with self._lock:
            return self._running

    @property
    def frame_width(self) -> int:
        with self._lock:
            return self._frame_width

    @property
    def frame_height(self) -> int:
        with self._lock:
            return self._frame_height

    @property
    def error(self) -> Optional[str]:
        """Last error message, or None if the camera is healthy."""
        with self._lock:
            return self._error

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Return the most recently captured BGR frame as a numpy array, or None.
        The caller receives a *copy* so inference can run without holding the lock.
        """
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_latest_jpeg(self) -> Optional[bytes]:
        """
        Return the most recently captured frame encoded as JPEG bytes, or None.
        Used by the MJPEG endpoint.
        """
        with self._lock:
            return self._latest_jpeg

    def get_status(self) -> dict:
        """Return a snapshot of the current camera status."""
        return self._make_status()

    # ─── Private ──────────────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """
        Background thread: read frames, encode JPEG, update buffers.
        Exits when _running is set to False by stop().
        """
        interval = 1.0 / TARGET_FPS
        while True:
            with self._lock:
                if not self._running:
                    break
                cap = self._capture

            if cap is None:
                break

            ret, frame = cap.read()
            if not ret:
                # Transient read failure — log once, keep trying
                with self._lock:
                    self._error = "Frame read failed — camera may have disconnected."
                logger.warning("Webcam frame read failed.")
                time.sleep(0.1)
                continue

            # Encode to JPEG for the MJPEG stream
            ok, jpeg_buf = cv2.imencode(
                ".jpg", frame,
                [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY],
            )
            jpeg_bytes = bytes(jpeg_buf) if ok else None

            with self._lock:
                self._latest_frame = frame
                self._latest_jpeg  = jpeg_bytes
                self._error        = None  # Clear any previous error

            time.sleep(interval)

    def _make_status(self) -> dict:
        """Build a status dict from the current locked state (caller must not hold lock)."""
        with self._lock:
            return {
                "success":      self._error is None,
                "active":       self._running,
                "error":        self._error,
                "camera_index": self._camera_index,
                "width":        self._frame_width,
                "height":       self._frame_height,
            }
