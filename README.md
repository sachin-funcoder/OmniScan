# OmniScan — AI-Based Vehicle Surround Monitoring System

## Current Phase: Phase 3 — Real-Time YOLO Object Detection (Laptop Webcam)

OmniScan is a vehicle surround-monitoring prototype for four camera zones: **FRONT**, **REAR**, **LEFT**, and **RIGHT**.

- **FRONT zone**: Physical laptop webcam connected to real-time YOLOv8 object detection with GPU/CPU acceleration.
- **REAR, LEFT, and RIGHT zones**: Simulated surround-monitoring zones providing contextual multi-angle alerts.
- **Switchable Modes**: Switch seamlessly between **DEMO MODE** and **REAL CAMERA MODE** directly from the UI dashboard.

> [!NOTE]
> Risk classification on the real webcam is **experimental** and heuristic (based on object classes and screen bounding-box size). It does not measure physical distance and is not a certified automotive safety system.

---

## Architecture

```
OmniScan/
  frontend/     ← React + Vite dashboard (JavaScript, plain CSS dark automotive theme)
  backend/      ← FastAPI + OpenCV + Ultralytics YOLOv8 (CUDA/CPU fallback)
  README.md
```

### Video & Data Pipeline
```
[Laptop Webcam] ──> [OpenCV Background Thread] ──> [MJPEG Stream /video/front] ──> React Front Panel <img>
                            │
                            └──> [YOLOv8 Inference (GPU/CPU)]
                                         │
                                         ▼
                               [FastAPI WebSocket /ws] ──> React Bbox Canvas Overlay + Risk Status
```

---

## Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | React 18 + Vite | Pure JavaScript (no TypeScript, no Tailwind), dark automotive theme |
| **Icons & Audio** | Lucide React · Web Audio API | Synth-based spatial warning chimes |
| **Backend** | Python 3.13 · FastAPI · Uvicorn | Async REST endpoints & WebSocket server |
| **Camera Capture** | OpenCV (`cv2.VideoCapture`) | Dedicated background thread with thread-safe JPEG double-buffer |
| **Object Detection** | Ultralytics YOLOv8 (`yolov8n.pt`) | Hardware accelerated (NVIDIA RTX 2050 CUDA / CPU fallback) |
| **Video Streaming** | MJPEG (`multipart/x-mixed-replace`) | Low-latency HTTP stream displayed in native browser `<img>` |
| **Testing** | pytest · pytest-asyncio · httpx | Comprehensive unit & integration tests (mocked, no hardware needed) |

---

## Hardware & Acceleration

- **Detected GPU**: NVIDIA GeForce RTX 2050 (4 GB VRAM)
- **CUDA Runtime**: PyTorch with CUDA 12.4 (`torch==2.6.0+cu124`)
- **Inference Speed**: ~18 ms per frame on RTX 2050
- **Fallback**: Automatic fallback to CPU if CUDA is unavailable

---

## Quick Start (Windows PowerShell)

### Step 1 — Setup & Start the Backend

Open a PowerShell terminal:

```powershell
# Navigate to the backend directory
cd "C:\Users\sachi\OneDrive\Desktop\OS\backend"

# (Optional) Create & activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# For NVIDIA GPU acceleration (RTX 2050):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# Start the FastAPI server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend will be available at:
- **REST API:** `http://127.0.0.1:8000`
- **Swagger Docs:** `http://127.0.0.1:8000/docs`
- **WebSocket:** `ws://127.0.0.1:8000/ws`
- **Front MJPEG Stream:** `http://127.0.0.1:8000/video/front`

---

### Step 2 — Start the Frontend

Open a **second** PowerShell terminal:

```powershell
# Navigate to the frontend directory
cd "C:\Users\sachi\OneDrive\Desktop\OS\frontend"

# Install node dependencies (if not already installed)
npm install

# Start Vite dev server
npm run dev
```

Open your browser at:
`http://localhost:5173`

---

## How to Use Real Camera Mode

1. Ensure the FastAPI backend is running in Terminal 1 and frontend in Terminal 2.
2. In the browser dashboard (`http://localhost:5173`), confirm the navbar displays `● BACKEND CONNECTED`.
3. In the bottom-right **Controls** card, under **Phase 3 — Real Camera**, you will see:
   - `● YOLO ready`
   - `Webcam off`
4. Click the **Start Real Camera** button:
   - The laptop webcam opens cleanly in a background thread.
   - The **FRONT** camera panel switches from the simulated scene to the **live webcam video**.
   - Real-time YOLO detection boxes and class confidence tags (e.g. `Person 88%`, `Car 94%`) are rendered directly over the video stream.
   - The top navbar badge switches to `● REAL MODE`.
   - The camera grid badge displays `● FRONT: LIVE WEBCAM` while clearly marking `REAR / LEFT / RIGHT: SIMULATED`.
5. To return to simulated demo mode, click **Stop Real Camera**:
   - The webcam is released immediately.
   - The FRONT zone reverts to the simulated scene and scripted data.
   - The navbar badge returns to `⚠ DEMO MODE`.

---

## Running Backend Tests

Tests are non-blocking and do not require a webcam, GPU, or internet access:

```powershell
cd "C:\Users\sachi\OneDrive\Desktop\OS\backend"
python -m pytest tests/ -v
```

### Test Coverage (20 tests passed):
- `test_health_endpoint`
- `test_cameras_endpoint_returns_four_zones`
- `test_cameras_zone_fields`
- `test_status_endpoint`
- `test_events_endpoint`
- `test_websocket_initial_state`
- `test_yolo_detector_fallback_when_not_loaded`
- `test_yolo_detector_fallback_on_none_frame`
- `test_yolo_detector_with_mocked_model`
- `test_yolo_risk_inference`
- `test_webcam_capture_fails_gracefully_when_no_camera`
- `test_webcam_capture_stop_is_safe_when_not_started`
- `test_webcam_get_frame_returns_none_before_start`
- `test_camera_start_endpoint_webcam_unavailable`
- `test_camera_stop_endpoint`
- `test_camera_status_endpoint`
- `test_camera_manager_set_front_mode`
- `test_camera_manager_simulated_update_skips_real_zone`
- `test_camera_manager_update_from_yolo`
- `test_webcam_stop_releases_capture`

---

## API Reference

### Phase 2 Endpoints (Preserved)
- `GET /api/health` — Backend health status
- `GET /api/cameras` — Status and detections for all 4 camera zones
- `GET /api/status` — Aggregated risk level and zone summary
- `GET /api/events` — Recent event log history
- `WS /ws` — WebSocket for real-time state and detection streams

### Phase 3 Endpoints (Added)
- `POST /api/camera/start` — Initializes laptop webcam capture and starts YOLO inference loop
- `POST /api/camera/stop` — Safely releases webcam hardware and returns FRONT zone to simulated mode
- `GET /api/camera/status` — Reports webcam status and YOLO model/device info
- `GET /video/front` — Low-latency multipart MJPEG video stream from the webcam
