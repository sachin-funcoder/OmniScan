// api.js
// OmniScan Phase 3
//
// Phase 3 adds startRealCamera() and stopRealCamera() API calls.
// All Phase 2 exports are unchanged.

const BASE_URL = 'http://127.0.0.1:8000';

/**
 * Generic fetch helper.
 * Returns { data, error } — never throws.
 */
async function apiFetch(path, options = {}) {
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      headers: { Accept: 'application/json' },
      ...options,
    });
    if (!response.ok) {
      return { data: null, error: `HTTP ${response.status}: ${response.statusText}` };
    }
    const data = await response.json();
    return { data, error: null };
  } catch (err) {
    return { data: null, error: err.message };
  }
}

// ── Phase 2 exports (unchanged) ───────────────────────────────────────────────

/** GET /api/health — check if the backend is alive */
export async function fetchHealth() {
  return apiFetch('/api/health');
}

/** GET /api/cameras — fetch all four camera zone states */
export async function fetchCameras() {
  return apiFetch('/api/cameras');
}

/** GET /api/status — fetch overall risk status summary */
export async function fetchStatus() {
  return apiFetch('/api/status');
}

/** GET /api/events — fetch event history */
export async function fetchEvents() {
  return apiFetch('/api/events');
}

// ── Phase 3 exports ───────────────────────────────────────────────────────────

/** POST /api/camera/start — open the laptop webcam and begin YOLO inference */
export async function startRealCamera() {
  return apiFetch('/api/camera/start', { method: 'POST' });
}

/** POST /api/camera/stop — stop the webcam and return FRONT zone to simulated mode */
export async function stopRealCamera() {
  return apiFetch('/api/camera/stop', { method: 'POST' });
}

/** GET /api/camera/status — webcam + YOLO status */
export async function fetchCameraStatus() {
  return apiFetch('/api/camera/status');
}
