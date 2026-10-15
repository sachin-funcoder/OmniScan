# tests/test_backend.py
# OmniScan backend tests — Phase 2 + Phase 3
#
# Phase 2 tests: unchanged, still cover health/cameras/status/events/WebSocket.
# Phase 3 tests: cover YOLO output structure, webcam unavailable, mode switching,
#                safe shutdown, and new endpoints.
#
# All tests run without a physical webcam, GPU, or internet access.
# Camera and YOLO are mocked where necessary.
#
# Run with:  pytest tests/ -v

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, PropertyMock
from httpx import AsyncClient, ASGITransport
from httpx_ws.transport import ASGIWebSocketTransport

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
import main as main_module


# ─── Phase 2 REST endpoint tests (unchanged) ─────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /api/health should return status 200 and status='ok'."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "OmniScan" in data["message"]
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_cameras_endpoint_returns_four_zones():
    """GET /api/cameras should return exactly four camera zones."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/cameras")

    assert response.status_code == 200
    data = response.json()

    cameras = data["cameras"]
    assert isinstance(cameras, list)
    assert len(cameras) == 4

    zone_ids = {cam["id"] for cam in cameras}
    assert zone_ids == {"FRONT", "REAR", "LEFT", "RIGHT"}


@pytest.mark.asyncio
async def test_cameras_zone_fields():
    """Each camera zone must have the required fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/cameras")

    cameras = response.json()["cameras"]
    required_fields = {
        "id", "label", "status", "risk_level",
        "detected_object", "confidence", "source", "mode",
    }

    for cam in cameras:
        for field in required_fields:
            assert field in cam, f"Missing field '{field}' in camera {cam.get('id')}"


@pytest.mark.asyncio
async def test_status_endpoint():
    """GET /api/status should return overall_status, active_zones, detection_count, zones."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/status")

    assert response.status_code == 200
    data = response.json()

    assert "overall_status" in data
    assert data["overall_status"] in ("SAFE", "WARNING", "DANGER", "CRITICAL")
    assert "active_zones" in data
    assert "detection_count" in data
    assert "zones" in data
    assert isinstance(data["zones"], dict)
    assert len(data["zones"]) == 4


@pytest.mark.asyncio
async def test_events_endpoint():
    """GET /api/events should return a list of events."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/events")

    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)
    assert "count" in data


# ─── Phase 2 WebSocket test (unchanged) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_websocket_initial_state():
    """
    Connecting to /ws should immediately receive an 'initial_state' message
    with the correct structure.  Phase 3 adds webcam_active / yolo_ready.
    """
    from httpx_ws import aconnect_ws

    async with AsyncClient(
        transport=ASGIWebSocketTransport(app),
        base_url="http://test"
    ) as client:
        async with aconnect_ws("/ws", client) as ws:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            assert msg["type"] == "initial_state"
            assert "timestamp" in msg
            assert "payload" in msg

            payload = msg["payload"]
            assert "cameras" in payload
            assert "status" in payload
            assert "events" in payload
            assert len(payload["cameras"]) == 4

            # Phase 3 additions
            assert "webcam_active" in payload
            assert "yolo_ready" in payload


# ─── Phase 3: YOLO detector output structure ──────────────────────────────────

def test_yolo_detector_fallback_when_not_loaded():
    """YOLODetector.detect() returns a safe SAFE-state dict when not loaded."""
    from detector import YOLODetector
    import numpy as np

    yolo = YOLODetector()
    # Don't call load() — model is not loaded
    result = yolo.detect(np.zeros((480, 640, 3), dtype="uint8"))

    assert result["zone"] == "FRONT"
    assert result["risk"] == "SAFE"
    assert result["detections"] == []
    assert result["source"] == "YOLO_REAL"
    assert result["mode"] == "real"
    assert "timestamp" in result
    assert "inference_device" in result


def test_yolo_detector_fallback_on_none_frame():
    """YOLODetector.detect() returns safe dict when given None frame."""
    from detector import YOLODetector

    yolo = YOLODetector()
    result = yolo.detect(None)

    assert result["zone"] == "FRONT"
    assert result["risk"] == "SAFE"
    assert result["detections"] == []


def test_yolo_detector_with_mocked_model():
    """YOLODetector.detect() correctly maps YOLO results to our output schema."""
    from detector import YOLODetector
    import numpy as np
    import torch

    yolo = YOLODetector()

    # Build tensors that behave exactly as ultralytics Boxes attributes do
    cls_tensor  = torch.tensor([0.0])       # class 0 = "person" in COCO
    conf_tensor = torch.tensor([0.87])
    xyxy_tensor  = torch.tensor([[100.0, 80.0, 200.0, 300.0]])
    xywhn_tensor = torch.tensor([[0.234375, 0.395833, 0.15625, 0.458333]])

    mock_box = MagicMock()
    mock_box.__len__ = MagicMock(return_value=1)
    mock_box.cls   = cls_tensor
    mock_box.conf  = conf_tensor
    mock_box.xyxy  = xyxy_tensor
    mock_box.xywhn = xywhn_tensor

    mock_result = MagicMock()
    mock_result.boxes = mock_box

    mock_model = MagicMock()
    mock_model.names = {0: "person"}
    mock_model.return_value = [mock_result]

    yolo._model  = mock_model
    yolo._loaded = True
    yolo._device = "cpu"

    frame = np.zeros((480, 640, 3), dtype="uint8")
    result = yolo.detect(frame)

    assert result["zone"] == "FRONT"
    assert result["mode"] == "real"
    assert result["source"] == "YOLO_REAL"
    assert isinstance(result["detections"], list)
    assert len(result["detections"]) == 1

    det = result["detections"][0]
    assert det["class_name"] == "person"
    assert 0 < det["confidence"] <= 1.0
    assert len(det["bbox"]) == 4
    assert len(det["bbox_norm"]) == 4


def test_yolo_risk_inference():
    """_infer_risk correctly assigns risk levels based on class name and bbox size."""
    from detector import _infer_risk

    # No detections → SAFE
    assert _infer_risk([]) == "SAFE"

    # Person → WARNING
    assert _infer_risk([{"class_name": "person", "bbox_norm": [0.3, 0.3, 0.5, 0.7]}]) == "WARNING"

    # Small car → DANGER
    assert _infer_risk([{"class_name": "car", "bbox_norm": [0.1, 0.1, 0.3, 0.3]}]) == "DANGER"

    # Large car (fills > 40% of frame) → CRITICAL
    assert _infer_risk([{"class_name": "car", "bbox_norm": [0.0, 0.0, 0.8, 0.7]}]) == "CRITICAL"

    # Bottle and cell phone → SAFE (informational)
    assert _infer_risk([{"class_name": "bottle", "bbox_norm": [0.2, 0.2, 0.4, 0.6]}]) == "SAFE"
    assert _infer_risk([{"class_name": "cell phone", "bbox_norm": [0.3, 0.3, 0.5, 0.5]}]) == "SAFE"


def test_yolo_detects_cell_phone_and_bottle_with_mocked_model():
    """YOLODetector does not filter out cell phone or bottle — all classes are returned."""
    from detector import YOLODetector
    import numpy as np
    import torch

    yolo = YOLODetector(confidence_threshold=0.25)

    # 3 detections: person (0), bottle (39), cell phone (67)
    cls_tensor  = torch.tensor([0.0, 39.0, 67.0])
    conf_tensor = torch.tensor([0.88, 0.65, 0.72])
    xyxy_tensor = torch.tensor([
        [100.0, 50.0, 200.0, 400.0],
        [220.0, 150.0, 280.0, 320.0],
        [300.0, 200.0, 360.0, 310.0],
    ])
    xyxyn_tensor = torch.tensor([
        [0.156, 0.104, 0.312, 0.833],
        [0.344, 0.312, 0.438, 0.667],
        [0.469, 0.417, 0.562, 0.646],
    ])

    mock_box = MagicMock()
    mock_box.__len__ = MagicMock(return_value=3)
    mock_box.cls   = cls_tensor
    mock_box.conf  = conf_tensor
    mock_box.xyxy  = xyxy_tensor
    mock_box.xyxyn = xyxyn_tensor

    mock_result = MagicMock()
    mock_result.boxes = mock_box

    mock_model = MagicMock()
    mock_model.names = {0: "person", 39: "bottle", 67: "cell phone"}
    mock_model.return_value = [mock_result]

    yolo._model  = mock_model
    yolo._loaded = True
    yolo._device = "cpu"

    frame = np.zeros((480, 640, 3), dtype="uint8")
    result = yolo.detect(frame)

    assert result["zone"] == "FRONT"
    assert result["mode"] == "real"
    assert len(result["detections"]) == 3

    detected_classes = [d["class_name"] for d in result["detections"]]
    assert "person" in detected_classes
    assert "bottle" in detected_classes
    assert "cell phone" in detected_classes

    # Verify best is person (highest confidence 0.88)
    assert result["object"] == "Person"
    assert result["confidence"] == 88


def test_yolo_confidence_threshold_configurable():
    """YOLODetector defaults to 0.25 and accepts custom threshold parameter."""
    from detector import YOLODetector

    yolo_default = YOLODetector()
    assert yolo_default.confidence_threshold == 0.25

    yolo_custom = YOLODetector(confidence_threshold=0.35)
    assert yolo_custom.confidence_threshold == 0.35


# ─── Phase 3: Webcam unavailable / disconnected ───────────────────────────────

def test_webcam_capture_fails_gracefully_when_no_camera():
    """WebcamCapture.start() returns success=False when the device can't be opened."""
    from webcam_capture import WebcamCapture
    import cv2

    cap = WebcamCapture(camera_index=99)  # index 99 will not exist

    with patch.object(cv2, "VideoCapture") as mock_vc:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = False
        mock_vc.return_value = mock_instance

        result = cap.start()

    assert result["success"] is False
    assert result["active"] is False
    assert result["error"] is not None


def test_webcam_capture_stop_is_safe_when_not_started():
    """WebcamCapture.stop() does not raise when called before start()."""
    from webcam_capture import WebcamCapture
    cap = WebcamCapture()
    # Should not raise
    cap.stop()
    assert not cap.is_active


def test_webcam_get_frame_returns_none_before_start():
    """get_latest_frame() and get_latest_jpeg() return None before the camera starts."""
    from webcam_capture import WebcamCapture
    cap = WebcamCapture()
    assert cap.get_latest_frame() is None
    assert cap.get_latest_jpeg() is None


# ─── Phase 3: Mode switching endpoints ────────────────────────────────────────

@pytest.mark.asyncio
async def test_camera_start_endpoint_webcam_unavailable():
    """
    POST /api/camera/start should return success=False (not a 500) when the
    webcam cannot be opened.
    """
    with patch("main.webcam") as mock_webcam:
        mock_webcam.is_active = False
        mock_webcam.start.return_value = {
            "success": False,
            "active":  False,
            "error":   "No camera at index 0.",
        }
        mock_webcam.get_status.return_value = {
            "success": False,
            "active":  False,
            "error":   "No camera at index 0.",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/camera/start")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "error" in str(data).lower() or "failed" in str(data).lower()


@pytest.mark.asyncio
async def test_camera_stop_endpoint():
    """POST /api/camera/stop should always return success=True."""
    with patch("main.webcam") as mock_webcam:
        mock_webcam.is_active = False
        mock_webcam.stop.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/camera/stop")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_camera_status_endpoint():
    """GET /api/camera/status returns webcam and YOLO status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/camera/status")

    assert response.status_code == 200
    data = response.json()
    assert "webcam" in data
    assert "yolo" in data
    assert "front_mode" in data


# ─── Phase 3: Camera manager mode switching ────────────────────────────────────

def test_camera_manager_set_front_mode():
    """CameraManager switches FRONT zone between real and simulated modes."""
    from camera_manager import CameraManager

    cm = CameraManager()
    assert cm.get_zone("FRONT")["mode"] == "simulated"

    cm.set_front_mode("real")
    assert cm.get_zone("FRONT")["mode"] == "real"
    assert cm.get_zone("FRONT")["source"] == "YOLO_REAL"

    cm.set_front_mode("simulated")
    assert cm.get_zone("FRONT")["mode"] == "simulated"
    assert cm.get_zone("FRONT")["source"] == "SIMULATED_BACKEND"


def test_camera_manager_simulated_update_skips_real_zone():
    """update_zone() does not overwrite a zone that is in real mode."""
    from camera_manager import CameraManager

    cm = CameraManager()
    cm.set_front_mode("real")

    # Attempt to update FRONT with simulated data
    cm.update_zone("FRONT", "CRITICAL", "Truck", 95)

    zone = cm.get_zone("FRONT")
    # Should still be in real mode (update was ignored)
    assert zone["mode"] == "real"
    assert zone["detected_object"] is None   # simulated update was skipped


def test_camera_manager_update_from_yolo():
    """update_zone_from_yolo() correctly applies a YOLO result to FRONT zone."""
    from camera_manager import CameraManager

    cm = CameraManager()
    cm.set_front_mode("real")

    yolo_result = {
        "zone":       "FRONT",
        "object":     "Person",
        "confidence": 87,
        "risk":       "WARNING",
        "detections": [{"class_name": "person", "confidence": 0.87, "bbox": [10, 20, 100, 200], "bbox_norm": [0.1, 0.1, 0.5, 0.9]}],
        "timestamp":  "08:00:00 AM",
        "source":     "YOLO_REAL",
    }

    cm.update_zone_from_yolo(yolo_result)
    zone = cm.get_zone("FRONT")

    assert zone["risk_level"] == "WARNING"
    assert zone["detected_object"] == "Person"
    assert zone["confidence"] == 87
    assert zone["source"] == "YOLO_REAL"
    assert len(zone["detections"]) == 1


# ─── Phase 3: Safe shutdown ───────────────────────────────────────────────────

def test_webcam_stop_releases_capture():
    """stop() calls release() on the OpenCV VideoCapture."""
    from webcam_capture import WebcamCapture
    import cv2

    cap = WebcamCapture(camera_index=0)

    with patch.object(cv2, "VideoCapture") as mock_vc_cls:
        mock_vc = MagicMock()
        mock_vc.isOpened.return_value = True
        mock_vc.read.return_value = (False, None)  # no frames, just checking lifecycle
        mock_vc_cls.return_value = mock_vc

        cap.start()
        cap.stop()

        mock_vc.release.assert_called_once()
