# detector.py
# OmniScan Phase 3 — Debugged & Enhanced Object Detector
#
# Contains two detector implementations:
#   1. Detector        — original scripted simulation (Phase 2, unchanged)
#   2. YOLODetector    — real YOLO inference using Ultralytics (Phase 3)
#
# Fixes applied:
#   - Removed class filter whitelist: all COCO detected classes (including
#     'cell phone', 'bottle', 'person', vehicles, etc.) are now returned.
#   - Lowered default confidence threshold to 0.25 for responsive detection.
#   - Added clear backend debug logs showing detected classes & confidence scores.
#   - Uses Ultralytics normalized xyxyn coordinates with boundary clamping.

import logging
import os
from datetime import datetime
from typing import Optional
import itertools

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — original scripted simulator (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

# The ordered simulation script — mirrors the Phase 1 frontend script so behaviour
# is consistent whether the demo or the backend is driving the UI.
SIMULATION_SCRIPT = [
    {"zone": "FRONT", "object": "Car",        "confidence": 92, "risk": "WARNING"},
    {"zone": "LEFT",  "object": "Person",     "confidence": 87, "risk": "WARNING"},
    {"zone": "REAR",  "object": "Bicycle",    "confidence": 78, "risk": "DANGER"},
    {"zone": "FRONT", "object": "Truck",      "confidence": 95, "risk": "CRITICAL"},
    {"zone": "RIGHT", "object": "Motorcycle", "confidence": 81, "risk": "WARNING"},
    {"zone": "LEFT",  "object": None,         "confidence": None, "risk": "SAFE"},
    {"zone": "REAR",  "object": "Person",     "confidence": 90, "risk": "DANGER"},
    {"zone": "FRONT", "object": None,         "confidence": None, "risk": "SAFE"},
    {"zone": "RIGHT", "object": None,         "confidence": None, "risk": "SAFE"},
    {"zone": "REAR",  "object": None,         "confidence": None, "risk": "SAFE"},
]


def _build_description(zone: str, obj: Optional[str], risk: str) -> str:
    """Build a human-readable event description."""
    if obj:
        return f"[SIMULATED] {obj} detected in {zone} zone — Risk: {risk}"
    return f"{zone} zone returned to SAFE"


class Detector:
    """
    Cycles through the simulation script and produces detection events.
    Each call to next_event() advances to the next step and loops back
    to the beginning when the script is exhausted.
    """

    def __init__(self):
        # itertools.cycle makes the script loop indefinitely
        self._cycle = itertools.cycle(SIMULATION_SCRIPT)
        self._step_index: int = 0

    def next_event(self) -> dict:
        """
        Return the next simulated detection event as a structured dictionary.
        The 'source' field is always 'SIMULATED_BACKEND' to clearly mark the data.
        """
        step = next(self._cycle)
        self._step_index += 1

        return {
            "zone":        step["zone"],
            "object":      step["object"],
            "confidence":  step["confidence"],
            "risk":        step["risk"],
            "description": _build_description(step["zone"], step["object"], step["risk"]),
            "timestamp":   datetime.now().strftime("%I:%M:%S %p"),
            "source":      "SIMULATED_BACKEND",   # Never "YOLO" in simulated mode
        }

    def reset(self) -> None:
        """Restart the simulation script from the beginning."""
        self._cycle = itertools.cycle(SIMULATION_SCRIPT)
        self._step_index = 0

    @property
    def step_index(self) -> int:
        return self._step_index


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — YOLO detector (real inference)
# ─────────────────────────────────────────────────────────────────────────────

# Configurable confidence threshold: default 0.25 for testing & responsive detection
DEFAULT_CONFIDENCE_THRESHOLD = float(os.environ.get("YOLO_CONF_THRESHOLD", "0.25"))

# Default model filename — downloaded automatically by Ultralytics on first run
DEFAULT_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "yolov8n.pt")


def _infer_risk(detections: list[dict]) -> str:
    """
    Assign a basic EXPERIMENTAL risk level from YOLO detections.

    This uses class name and bounding-box size — no distance sensors.
    It is labelled experimental and should NOT be treated as a certified safety system.

    Rules (conservative):
      - CRITICAL  : large car/truck/bus (bbox area > 40% of frame)
      - DANGER    : car/truck/bus at any size
      - WARNING   : person, bicycle, motorcycle, dog
      - SAFE      : personal items (cell phone, bottle, cup) or no objects
    """
    if not detections:
        return "SAFE"

    highest = "SAFE"
    risk_order = ["SAFE", "WARNING", "DANGER", "CRITICAL"]

    for det in detections:
        cls = det["class_name"].lower()
        bbox_norm = det.get("bbox_norm", [0, 0, 0, 0])
        # Approximate area as fraction of frame
        area = (bbox_norm[2] - bbox_norm[0]) * (bbox_norm[3] - bbox_norm[1])

        if cls in {"car", "truck", "bus"}:
            if area > 0.40:
                candidate = "CRITICAL"
            else:
                candidate = "DANGER"
        elif cls in {"person", "bicycle", "motorcycle", "dog"}:
            candidate = "WARNING"
        else:
            # Personal items (cell phone, bottle, backpack, etc.) are informational
            candidate = "SAFE"

        if risk_order.index(candidate) > risk_order.index(highest):
            highest = candidate

    return highest


class YOLODetector:
    """
    Runs YOLOv8 inference on frames supplied by WebcamCapture.

    GPU is used automatically when torch.cuda.is_available() returns True.
    Falls back to CPU otherwise — no configuration required.

    Usage:
        yolo = YOLODetector()
        yolo.load()                    # loads model; call once at startup
        result = yolo.detect(frame)    # numpy BGR frame → detection dict
    """

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        self._model_path   = model_path
        self._conf         = confidence_threshold
        self._model        = None
        self._device       = "cpu"
        self._loaded       = False
        self._load_error:  Optional[str] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self) -> dict:
        """
        Load the YOLO model.  Call once during application startup.
        Downloads the model weights automatically if not present.
        Returns {"success": bool, "device": str, "error": str|None}.
        """
        try:
            import torch
            from ultralytics import YOLO  # noqa: import-outside-toplevel

            # Pick the inference device
            if torch.cuda.is_available():
                self._device = "cuda"
                logger.info("CUDA available — YOLO will run on GPU (%s).", torch.cuda.get_device_name(0))
            else:
                self._device = "cpu"
                logger.info("CUDA not available — YOLO will run on CPU.")

            logger.info("Loading YOLO model: %s (confidence threshold: %.2f)", self._model_path, self._conf)
            self._model = YOLO(self._model_path)

            # Warm up: run a tiny dummy inference so the first real call is fast
            import numpy as np
            dummy = np.zeros((64, 64, 3), dtype=np.uint8)
            self._model(dummy, device=self._device, verbose=False)

            self._loaded     = True
            self._load_error = None
            logger.info("YOLO model loaded successfully on device=%s.", self._device)

        except ImportError as exc:
            self._load_error = f"ultralytics/torch not installed: {exc}"
            logger.error(self._load_error)
        except Exception as exc:
            self._load_error = f"YOLO model load failed: {exc}"
            logger.error(self._load_error)

        return {
            "success": self._loaded,
            "device":  self._device,
            "model":   self._model_path,
            "error":   self._load_error,
        }

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def device(self) -> str:
        return self._device

    @property
    def confidence_threshold(self) -> float:
        return self._conf

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def detect(self, frame) -> dict:
        """
        Run YOLO inference on a BGR numpy frame.

        Returns all detected objects across standard COCO classes (including
        cell phone, bottle, person, vehicles, etc.) with confidence >= threshold.

        Returns a dict with keys:
          - zone            : "FRONT"
          - detections      : list of detection dicts (sorted by confidence descending)
          - object          : best (highest confidence) class name
          - confidence      : best confidence percentage (0-100)
          - risk            : EXPERIMENTAL risk label (SAFE/WARNING/DANGER/CRITICAL)
          - frame_width     : int
          - frame_height    : int
          - mode            : "real"
          - inference_device: str
          - timestamp       : str
          - description     : str
          - source          : "YOLO_REAL"

        If the model is not loaded, returns a safe fallback dict.
        """
        if not self._loaded or self._model is None:
            return self._fallback_result("Model not loaded")

        if frame is None:
            return self._fallback_result("No frame available")

        try:
            h, w = frame.shape[:2]
            results = self._model(
                frame,
                device=self._device,
                conf=self._conf,
                verbose=False,
            )

            detections = []
            if results and results[0].boxes is not None and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                has_xyxyn = hasattr(boxes, "xyxyn") and boxes.xyxyn is not None

                for i in range(len(boxes)):
                    cls_id   = int(boxes.cls[i].item())
                    cls_name = self._model.names.get(cls_id, str(cls_id))
                    conf_val = float(boxes.conf[i].item())
                    xyxy     = boxes.xyxy[i].tolist()   # [x1, y1, x2, y2] in pixels

                    # Use normalized coordinates [x1n, y1n, x2n, y2n]
                    if has_xyxyn:
                        raw_norm = boxes.xyxyn[i].tolist()
                        x1n, y1n, x2n, y2n = raw_norm[0], raw_norm[1], raw_norm[2], raw_norm[3]
                    else:
                        xywhn = boxes.xywhn[i].tolist()
                        x1n = xywhn[0] - xywhn[2] / 2
                        y1n = xywhn[1] - xywhn[3] / 2
                        x2n = xywhn[0] + xywhn[2] / 2
                        y2n = xywhn[1] + xywhn[3] / 2

                    # Clamp normalized coordinates safely between 0.0 and 1.0
                    x1n = max(0.0, min(1.0, float(x1n)))
                    y1n = max(0.0, min(1.0, float(y1n)))
                    x2n = max(0.0, min(1.0, float(x2n)))
                    y2n = max(0.0, min(1.0, float(y2n)))

                    detections.append({
                        "class_name":  cls_name,
                        "confidence":  round(conf_val, 3),
                        "bbox":        [round(float(v), 1) for v in xyxy],
                        "bbox_norm":   [round(v, 4) for v in [x1n, y1n, x2n, y2n]],
                    })

            # Sort detections by confidence descending so the highest confidence object is primary
            detections.sort(key=lambda d: d["confidence"], reverse=True)

            risk = _infer_risk(detections)
            best = detections[0] if detections else None

            # ── Backend Debug Logging ──────────────────────────────────────────
            if detections:
                det_summary = ", ".join(f"{d['class_name']}: {d['confidence']:.2f}" for d in detections)
                logger.info("[YOLO Real] %dx%d frame | Detected %d object(s): [%s]", w, h, len(detections), det_summary)
            else:
                logger.debug("[YOLO Real] %dx%d frame | No objects detected (conf >= %.2f)", w, h, self._conf)

            return {
                "zone":             "FRONT",
                "detections":       detections,
                "object":           best["class_name"].title() if best else None,
                "confidence":       round(best["confidence"] * 100) if best else None,
                "risk":             risk,
                "frame_width":      w,
                "frame_height":     h,
                "mode":             "real",
                "inference_device": self._device,
                "timestamp":        datetime.now().strftime("%I:%M:%S %p"),
                "description":      self._build_description(detections, risk),
                "source":           "YOLO_REAL",
            }

        except Exception as exc:
            logger.error("YOLO inference error: %s", exc)
            return self._fallback_result(str(exc))

    # ── Private ───────────────────────────────────────────────────────────────

    def _fallback_result(self, reason: str) -> dict:
        """Return a safe SAFE-state dict when inference cannot run."""
        return {
            "zone":             "FRONT",
            "detections":       [],
            "object":           None,
            "confidence":       None,
            "risk":             "SAFE",
            "frame_width":      0,
            "frame_height":     0,
            "mode":             "real",
            "inference_device": self._device,
            "timestamp":        datetime.now().strftime("%I:%M:%S %p"),
            "description":      f"[YOLO unavailable: {reason}]",
            "source":           "YOLO_REAL",
        }

    @staticmethod
    def _build_description(detections: list[dict], risk: str) -> str:
        if not detections:
            return "FRONT zone — no objects detected"
        names = ", ".join(d["class_name"].title() for d in detections[:3])
        suffix = f" (+{len(detections)-3} more)" if len(detections) > 3 else ""
        return f"[REAL] {names}{suffix} detected in FRONT — Risk: {risk}"
