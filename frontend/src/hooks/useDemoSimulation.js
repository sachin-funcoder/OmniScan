// useDemoSimulation.js
// Custom hook that drives the OmniScan demo simulation loop.
// All detections here are simulated and NOT real camera observations.

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  getInitialZoneState,
  SIMULATION_SCRIPT,
  buildEventDescription,
  computeOverallStatus,
  getActiveZoneCount,
  getDetectionCount,
} from '../data/demoData';

const TICK_INTERVAL_MS = 3000; // How often the simulation advances (3 seconds)

export function useDemoSimulation() {
  const [zones, setZones] = useState(getInitialZoneState());
  const [isRunning, setIsRunning] = useState(false);
  const [eventLog, setEventLog] = useState([]);
  const [stepIndex, setStepIndex] = useState(0);

  const timerRef = useRef(null);
  const stepRef = useRef(0); // Keep a ref in sync so the interval callback always reads the latest value

  // ─── Helpers ────────────────────────────────────────────────────────────────

  function formatTimestamp() {
    return new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  }

  function addEvent(zone, object, risk) {
    const newEvent = {
      id: Date.now() + Math.random(),
      time: formatTimestamp(),
      zone,
      description: buildEventDescription(zone, object, risk),
      severity: risk,
    };
    setEventLog((prev) => [newEvent, ...prev].slice(0, 50)); // keep latest 50 events
  }

  // ─── Simulation tick ─────────────────────────────────────────────────────────

  const tick = useCallback(() => {
    const step = SIMULATION_SCRIPT[stepRef.current % SIMULATION_SCRIPT.length];
    const { zone, object, confidence, risk } = step;
    const detectionTime = formatTimestamp();

    setZones((prev) => ({
      ...prev,
      [zone]: {
        ...prev[zone],
        riskLevel: risk,
        detectedObject: object,
        confidence,
        lastDetectionTime: object ? detectionTime : prev[zone].lastDetectionTime,
      },
    }));

    addEvent(zone, object, risk);

    stepRef.current += 1;
    setStepIndex(stepRef.current);
  }, []);

  // ─── Start / Pause / Reset ───────────────────────────────────────────────────

  const startDemo = useCallback(() => {
    if (timerRef.current) return; // already running
    setIsRunning(true);
    timerRef.current = setInterval(tick, TICK_INTERVAL_MS);
  }, [tick]);

  const pauseDemo = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRunning(false);
  }, []);

  const resetDemo = useCallback(() => {
    pauseDemo();
    setZones(getInitialZoneState());
    setEventLog([]);
    stepRef.current = 0;
    setStepIndex(0);
  }, [pauseDemo]);

  const clearEventLog = useCallback(() => {
    setEventLog([]);
  }, []);

  // ─── Cleanup on unmount ───────────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // ─── Derived state ────────────────────────────────────────────────────────────

  const overallStatus = computeOverallStatus(zones);
  const activeZoneCount = getActiveZoneCount(zones);
  const detectionCount = getDetectionCount(zones);

  return {
    zones,
    isRunning,
    eventLog,
    stepIndex,
    overallStatus,
    activeZoneCount,
    detectionCount,
    startDemo,
    pauseDemo,
    resetDemo,
    clearEventLog,
  };
}
