// useBackend.js
// OmniScan Phase 3
//
// Extends the Phase 2 hook with:
//   - isRealMode state (true when webcam + YOLO are active)
//   - startRealCamera() / stopRealCamera() actions
//   - Handles new WebSocket message types: real_detection, camera_status
//   - yoloReady, webcamActive derived state
//
// All Phase 2 behaviour is preserved: zone state, event log, backendConnected,
// overallStatus, activeZoneCount, detectionCount, clearEventLog.

import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchHealth, fetchCameras, fetchEvents, startRealCamera, stopRealCamera } from '../services/api';
import { createWebSocketService } from '../services/websocket';
import {
  getInitialZoneState,
  computeOverallStatus,
  getActiveZoneCount,
  getDetectionCount,
} from '../data/demoData';

// How often to check backend health when disconnected (ms)
const HEALTH_POLL_INTERVAL_MS = 5000;

/**
 * Convert a backend camera object (snake_case) to the shape the existing
 * React components expect (camelCase, matching demoData).
 * Phase 3: also maps `mode` and `detections`.
 */
function normaliseZone(backendZone) {
  return {
    id:                backendZone.id,
    label:             backendZone.label,
    status:            backendZone.status,
    riskLevel:         backendZone.risk_level,
    detectedObject:    backendZone.detected_object,
    confidence:        backendZone.confidence,
    lastDetectionTime: backendZone.last_detection_time,
    source:            backendZone.source || 'SIMULATED_BACKEND',
    mode:              backendZone.mode   || 'simulated',
    detections:        backendZone.detections || [],
    frameWidth:        backendZone.frame_width || 640,
    frameHeight:       backendZone.frame_height || 480,
  };
}

/** Convert an array of backend camera objects into the zones map shape. */
function normaliseZones(backendCameras) {
  const result = getInitialZoneState(); // safe default
  for (const cam of backendCameras) {
    if (result[cam.id] !== undefined) {
      result[cam.id] = normaliseZone(cam);
    }
  }
  return result;
}

/** Convert a backend event object to the shape EventHistory expects. */
function normaliseEvent(backendEvent) {
  return {
    id:          backendEvent.timestamp + '-' + Math.random(),
    time:        backendEvent.timestamp,
    zone:        backendEvent.zone,
    description: backendEvent.description || backendEvent.zone + ' event',
    severity:    backendEvent.risk || 'SAFE',
    source:      backendEvent.source || 'SIMULATED_BACKEND',
  };
}

export function useBackend() {
  const [backendConnected, setBackendConnected] = useState(false);
  const [zones, setZones]     = useState(getInitialZoneState());
  const [eventLog, setEventLog] = useState([]);

  // Phase 3 state
  const [isRealMode,   setIsRealMode]   = useState(false);
  const [yoloReady,    setYoloReady]    = useState(false);
  const [webcamActive, setWebcamActive] = useState(false);

  const wsServiceRef   = useRef(null);
  const healthTimerRef = useRef(null);

  // ─── Zone / event setters ─────────────────────────────────────────────────

  const applyZoneUpdate = useCallback((backendZone) => {
    setZones((prev) => ({
      ...prev,
      [backendZone.id]: normaliseZone(backendZone),
    }));
  }, []);

  const addEvent = useCallback((backendEvent) => {
    setEventLog((prev) => [normaliseEvent(backendEvent), ...prev].slice(0, 100));
  }, []);

  const clearEventLog = useCallback(() => setEventLog([]), []);

  // ─── WebSocket message handler ────────────────────────────────────────────

  const handleMessage = useCallback((msg) => {
    const { type, payload } = msg;
    switch (type) {
      case 'initial_state':
        // Full snapshot sent right after connection
        if (payload.cameras) setZones(normaliseZones(payload.cameras));
        if (payload.events)  setEventLog(payload.events.map(normaliseEvent));
        // Phase 3 fields
        if (payload.yolo_ready    !== undefined) setYoloReady(payload.yolo_ready);
        if (payload.webcam_active !== undefined) setWebcamActive(payload.webcam_active);
        break;

      case 'zone_update':
        // Single zone changed (simulated or real)
        if (payload) applyZoneUpdate(payload);
        break;

      case 'event_log':
        // New event to prepend
        if (payload) addEvent(payload);
        break;

      case 'status_update':
        // Overall status — derived from zones in the UI, no action needed
        break;

      // ── Phase 3 message types ─────────────────────────────────────────────

      case 'real_detection':
        // YOLO result for FRONT zone — update FRONT zone detections and record event
        if (payload) {
          addEvent(payload);
          setZones((prev) => ({
            ...prev,
            FRONT: {
              ...prev.FRONT,
              detectedObject: payload.object,
              confidence: payload.confidence,
              riskLevel: payload.risk || 'SAFE',
              detections: payload.detections || [],
              frameWidth: payload.frame_width || 640,
              frameHeight: payload.frame_height || 480,
              lastDetectionTime: payload.timestamp || prev.FRONT.lastDetectionTime,
              mode: 'real',
              source: 'YOLO_REAL',
            },
          }));
        }
        break;

      case 'camera_status':
        // Webcam started / stopped
        if (payload) {
          setWebcamActive(!!payload.webcam_active);
          setIsRealMode(payload.mode === 'real');
          if (payload.yolo_ready !== undefined) setYoloReady(payload.yolo_ready);
        }
        break;

      default:
        // Unknown message type — ignore safely
        break;
    }
  }, [applyZoneUpdate, addEvent]);

  // ─── Connect to backend ───────────────────────────────────────────────────

  const connectToBackend = useCallback(async () => {
    const { error } = await fetchHealth();
    if (error) return; // Backend not reachable

    const { data: camData } = await fetchCameras();
    if (camData?.cameras) setZones(normaliseZones(camData.cameras));

    const { data: evtData } = await fetchEvents();
    if (evtData?.events) setEventLog(evtData.events.map(normaliseEvent));

    if (wsServiceRef.current) wsServiceRef.current.disconnect();
    wsServiceRef.current = createWebSocketService(
      handleMessage,
      (connected) => setBackendConnected(connected),
    );
  }, [handleMessage]);

  // ─── Poll for backend availability when disconnected ──────────────────────

  useEffect(() => {
    connectToBackend();
    healthTimerRef.current = setInterval(async () => {
      if (!backendConnected) await connectToBackend();
    }, HEALTH_POLL_INTERVAL_MS);

    return () => {
      clearInterval(healthTimerRef.current);
      wsServiceRef.current?.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Phase 3 actions ──────────────────────────────────────────────────────

  const handleStartRealCamera = useCallback(async () => {
    const { data, error } = await startRealCamera();
    if (error || !data?.success) {
      console.warn('[OmniScan] Failed to start webcam:', error || data?.message);
      return;
    }
    // The backend will broadcast camera_status which updates isRealMode + webcamActive
    if (data.yolo_ready !== undefined) setYoloReady(data.yolo_ready);
  }, []);

  const handleStopRealCamera = useCallback(async () => {
    await stopRealCamera();
    // Backend broadcasts camera_status → isRealMode = false
  }, []);

  // ─── Derived state (same shape as useDemoSimulation) ─────────────────────

  const overallStatus   = computeOverallStatus(zones);
  const activeZoneCount = getActiveZoneCount(zones);
  const detectionCount  = getDetectionCount(zones);

  return {
    // Phase 2
    backendConnected,
    zones,
    eventLog,
    overallStatus,
    activeZoneCount,
    detectionCount,
    clearEventLog,
    // Phase 3
    isRealMode,
    yoloReady,
    webcamActive,
    startRealCamera: handleStartRealCamera,
    stopRealCamera:  handleStopRealCamera,
  };
}
