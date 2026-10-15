# main.py
# OmniScan FastAPI backend — Phase 3
#
# Phase 3 additions (all Phase 2 endpoints and behaviour preserved):
#   - POST /api/camera/start  — open webcam + start YOLO inference loop
#   - POST /api/camera/stop   — stop webcam, return to simulated mode
#   - GET  /api/camera/status — webcam & YOLO status
#   - GET  /video/front       — MJPEG stream from the laptop webcam
#   - WebSocket messages: "real_detection", "camera_status" (new types)
#   - Background real-detection loop (runs alongside simulation loop)

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Set

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from camera_manager import CameraManager
from detector import Detector, YOLODetector
from risk_engine import build_status_summary
from webcam_capture import WebcamCapture

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Shared application state
# ─────────────────────────────────────────────────────────────────────────────

camera_manager  = CameraManager()
detector        = Detector()       # Phase 2 simulated detector (unchanged)
yolo_detector   = YOLODetector()   # Phase 3 real detector
webcam          = WebcamCapture()  # Phase 3 webcam capture

# Stores all currently connected WebSocket clients
active_connections: Set[WebSocket] = set()

# In-memory event history (most-recent first, capped at 100 entries)
event_history: list[dict] = []

# Controls the background loops
simulation_running   = True
real_detection_running = False    # True only when webcam is active

# Simulation tick interval
SIMULATION_INTERVAL_SECONDS = 3

# Real detection interval — run inference at most every N seconds to avoid
# overloading a CPU-only device.  Adjust for GPU.
REAL_DETECTION_INTERVAL_SECONDS = 0.5   # 2 fps inference on CPU is comfortable


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_message(event_type: str, payload: dict) -> str:
    """
    Build a structured JSON message string.

    Every WebSocket message has three fields:
      - type      : what kind of event this is
      - timestamp : ISO 8601 server timestamp
      - payload   : the event-specific data
    """
    return json.dumps({
        "type":      event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload":   payload,
    })


async def _broadcast(message: str) -> None:
    """Send a message to all connected WebSocket clients."""
    dead: Set[WebSocket] = set()
    for ws in list(active_connections):
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    active_connections.difference_update(dead)


def _record_event(event: dict) -> None:
    """Add an event to the in-memory history, keeping only the latest 100."""
    event_history.insert(0, event)
    if len(event_history) > 100:
        event_history.pop()


# ─────────────────────────────────────────────────────────────────────────────
# Background simulation loop  (Phase 2 — unchanged logic)
# ─────────────────────────────────────────────────────────────────────────────

async def simulation_loop() -> None:
    """
    Runs in the background while the server is alive.
    Every SIMULATION_INTERVAL_SECONDS it advances the scripted simulation for
    non-real zones and broadcasts updates.
    """
    global simulation_running
    while simulation_running:
        await asyncio.sleep(SIMULATION_INTERVAL_SECONDS)

        # Advance the simulation
        event = detector.next_event()

        # In Phase 3, skip the FRONT zone update from simulation if it is in real mode
        front_zone = camera_manager.get_zone("FRONT")
        if event["zone"] == "FRONT" and front_zone and front_zone.get("mode") == "real":
            continue

        camera_manager.update_zone(
            zone_id=event["zone"],
            risk_level=event["risk"],
            detected_object=event["object"],
            confidence=event["confidence"],
        )

        # Record in history
        _record_event(event)

        # Get updated state
        all_zones = camera_manager.get_all_zones()
        status    = build_status_summary(all_zones)

        # Broadcast each message type separately
        zone_data = camera_manager.get_zone(event["zone"])
        await _broadcast(_make_message("zone_update",   zone_data))
        await _broadcast(_make_message("event_log",     event))
        await _broadcast(_make_message("status_update", status))


# ─────────────────────────────────────────────────────────────────────────────
# Background real-detection loop  (Phase 3)
# ─────────────────────────────────────────────────────────────────────────────

async def real_detection_loop() -> None:
    """
    Runs only while the webcam is active.
    Grabs the latest frame from WebcamCapture, runs YOLO inference in a thread
    pool executor (so it doesn't block FastAPI's event loop), updates the FRONT
    zone, and broadcasts a 'real_detection' message.
    """
    global real_detection_running
    loop = asyncio.get_event_loop()

    while real_detection_running:
        await asyncio.sleep(REAL_DETECTION_INTERVAL_SECONDS)

        if not webcam.is_active:
            continue

        frame = webcam.get_latest_frame()
        if frame is None:
            continue

        # Run YOLO inference in a thread pool so the async loop stays responsive
        try:
            result = await loop.run_in_executor(None, yolo_detector.detect, frame)
        except Exception as exc:
            logger.error("Real detection loop error: %s", exc)
            continue

        # Update the FRONT zone with the real detection result
        camera_manager.update_zone_from_yolo(result)

        # Record event
        _record_event(result)

        # Get updated state
        all_zones = camera_manager.get_all_zones()
        status    = build_status_summary(all_zones)
        front     = camera_manager.get_zone("FRONT")

        await _broadcast(_make_message("real_detection", result))
        await _broadcast(_make_message("zone_update",    front))
        await _broadcast(_make_message("status_update",  status))


# ─────────────────────────────────────────────────────────────────────────────
# Application lifespan — start/stop background tasks
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the simulation loop and attempt YOLO model load at startup."""
    global simulation_running
    simulation_running = True

    # Load YOLO model (non-blocking; errors are logged but don't prevent startup)
    loop = asyncio.get_event_loop()
    yolo_status = await loop.run_in_executor(None, yolo_detector.load)
    if yolo_status["success"]:
        logger.info("YOLO ready on device: %s", yolo_status["device"])
    else:
        logger.warning("YOLO not available: %s", yolo_status.get("error"))

    sim_task = asyncio.create_task(simulation_loop())

    yield

    # Shutdown
    simulation_running = False
    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass

    # Stop webcam cleanly if it was running
    if webcam.is_active:
        webcam.stop()
        logger.info("Webcam stopped on server shutdown.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OmniScan API",
    description=(
        "Phase 3 backend for OmniScan — AI-Based Vehicle Surround Monitoring System. "
        "FRONT zone supports real webcam + YOLO detection. "
        "REAR / LEFT / RIGHT zones remain SIMULATED."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 REST endpoints (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """
    GET /api/health
    Returns a simple health check confirming the server is running.
    """
    return {
        "status":  "ok",
        "message": "OmniScan backend is running (Phase 3 — real webcam + YOLO enabled)",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/cameras", tags=["Cameras"])
async def get_cameras():
    """
    GET /api/cameras
    Returns the current status of all four camera zones.
    FRONT will show source='YOLO_REAL' when real mode is active.
    """
    return {
        "cameras": camera_manager.get_all_zones(),
        "source":  "BACKEND",
    }


@app.get("/api/status", tags=["Status"])
async def get_status():
    """
    GET /api/status
    Returns the overall risk status and a summary for each zone.
    """
    all_zones = camera_manager.get_all_zones()
    return build_status_summary(all_zones)


@app.get("/api/events", tags=["Events"])
async def get_events():
    """
    GET /api/events
    Returns the most recent events (newest first, up to 100).
    Mix of simulated and real events depending on mode.
    """
    return {
        "events": event_history,
        "count":  len(event_history),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 REST endpoints — camera control
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/camera/start", tags=["Camera Control"])
async def start_camera():
    """
    POST /api/camera/start
    Open the laptop webcam and begin YOLO inference on the FRONT zone.
    Safe to call when already running (idempotent).
    """
    global real_detection_running

    if webcam.is_active:
        return {"success": True, "message": "Webcam already running.", "status": webcam.get_status()}

    # Start webcam capture
    status = webcam.start()
    if not status["success"]:
        return {
            "success": False,
            "message": f"Failed to open webcam: {status['error']}",
            "status":  status,
        }

    # Switch FRONT zone to real mode
    camera_manager.set_front_mode("real")
    camera_manager.set_front_status("connected")

    # Start the real-detection background loop
    real_detection_running = True
    asyncio.create_task(real_detection_loop())

    # Broadcast camera status change
    front = camera_manager.get_zone("FRONT")
    await _broadcast(_make_message("camera_status", {
        "zone":         "FRONT",
        "webcam_active": True,
        "mode":         "real",
        "error":        None,
        "yolo_device":  yolo_detector.device,
        "yolo_ready":   yolo_detector.is_loaded,
    }))
    await _broadcast(_make_message("zone_update", front))

    return {
        "success":    True,
        "message":    "Webcam started. YOLO inference is active on FRONT zone.",
        "status":     webcam.get_status(),
        "yolo_device": yolo_detector.device,
        "yolo_ready":  yolo_detector.is_loaded,
    }


@app.post("/api/camera/stop", tags=["Camera Control"])
async def stop_camera():
    """
    POST /api/camera/stop
    Stop the webcam and return FRONT zone to simulated mode.
    Safe to call when already stopped.
    """
    global real_detection_running

    real_detection_running = False
    webcam.stop()

    # Return FRONT to simulated mode
    camera_manager.set_front_mode("simulated")
    camera_manager.set_front_status("connected")

    # Broadcast status change
    front = camera_manager.get_zone("FRONT")
    await _broadcast(_make_message("camera_status", {
        "zone":          "FRONT",
        "webcam_active": False,
        "mode":          "simulated",
        "error":         None,
    }))
    await _broadcast(_make_message("zone_update", front))

    return {"success": True, "message": "Webcam stopped. FRONT zone returned to simulated mode."}


@app.get("/api/camera/status", tags=["Camera Control"])
async def camera_status():
    """
    GET /api/camera/status
    Returns the current webcam and YOLO detector status.
    """
    return {
        "webcam":      webcam.get_status(),
        "yolo": {
            "loaded": yolo_detector.is_loaded,
            "device": yolo_detector.device,
            "model":  "yolov8n.pt",
            "error":  yolo_detector.load_error,
        },
        "front_mode":  camera_manager.get_zone("FRONT", ).get("mode", "simulated") if camera_manager.get_zone("FRONT") else "simulated",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — MJPEG video stream
# ─────────────────────────────────────────────────────────────────────────────

async def _mjpeg_generator():
    """
    Async generator that yields MJPEG frames from the webcam capture buffer.
    Delivers a frame every ~33 ms (≈30 fps).  If the webcam is not active,
    yields a placeholder frame so the browser `<img>` doesn't stall.
    """
    # Placeholder: a small solid dark frame shown when the webcam is off
    placeholder = _make_placeholder_jpeg()

    while True:
        if webcam.is_active:
            jpeg = webcam.get_latest_jpeg()
        else:
            jpeg = None

        if jpeg is None:
            jpeg = placeholder

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
        )
        await asyncio.sleep(1 / 30)


def _make_placeholder_jpeg() -> bytes:
    """Return a tiny dark JPEG to display when the webcam is inactive."""
    import numpy as np
    img = np.zeros((240, 320, 3), dtype="uint8")
    cv2.putText(
        img, "WEBCAM INACTIVE", (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2,
    )
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])
    return bytes(buf)


@app.get("/video/front", tags=["Video"])
async def video_front():
    """
    GET /video/front
    MJPEG stream from the laptop webcam.
    Used by the FRONT camera panel in the React dashboard via:
      <img src="http://127.0.0.1:8000/video/front" />

    When the webcam is inactive, a dark placeholder frame is streamed
    so the <img> tag doesn't break.
    """
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint  (Phase 2 base; Phase 3 adds new message types)
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket /ws
    Clients connect here to receive real-time updates.

    Message types (all unchanged from Phase 2 plus Phase 3 additions):
      Phase 2: initial_state, zone_update, event_log, status_update
      Phase 3: real_detection, camera_status  (new)

    On connect, the client receives an 'initial_state' snapshot immediately.
    """
    await websocket.accept()
    active_connections.add(websocket)

    try:
        # Send initial full state snapshot on connect
        all_zones = camera_manager.get_all_zones()
        status    = build_status_summary(all_zones)
        await websocket.send_text(_make_message("initial_state", {
            "cameras":     all_zones,
            "status":      status,
            "events":      event_history[:20],
            "webcam_active": webcam.is_active,
            "yolo_ready":    yolo_detector.is_loaded,
            "yolo_device":   yolo_detector.device,
        }))

        # Keep the connection open; the loops handle broadcasts
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    finally:
        active_connections.discard(websocket)
