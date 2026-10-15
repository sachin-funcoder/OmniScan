// demoData.js
// All simulated data for OmniScan Phase 1 demo.
// Nothing here is real camera data — this is purely illustrative.

export const ZONES = ['FRONT', 'REAR', 'LEFT', 'RIGHT'];

export const RISK_LEVELS = {
  SAFE: 'SAFE',
  WARNING: 'WARNING',
  DANGER: 'DANGER',
  CRITICAL: 'CRITICAL',
};

// Objects that might appear in a vehicle surround-monitoring scenario
export const DETECTABLE_OBJECTS = [
  'Car',
  'Person',
  'Bicycle',
  'Motorcycle',
  'Truck',
  'Bus',
  'Traffic Cone',
  'Dog',
  'Scooter',
];

// Initial state for all four zones
export function getInitialZoneState() {
  return {
    FRONT: {
      id: 'FRONT',
      label: 'Front Camera',
      status: 'connected',
      riskLevel: RISK_LEVELS.SAFE,
      detectedObject: null,
      confidence: null,
      lastDetectionTime: null,
    },
    REAR: {
      id: 'REAR',
      label: 'Rear Camera',
      status: 'connected',
      riskLevel: RISK_LEVELS.SAFE,
      detectedObject: null,
      confidence: null,
      lastDetectionTime: null,
    },
    LEFT: {
      id: 'LEFT',
      label: 'Left Camera',
      status: 'connected',
      riskLevel: RISK_LEVELS.SAFE,
      detectedObject: null,
      confidence: null,
      lastDetectionTime: null,
    },
    RIGHT: {
      id: 'RIGHT',
      label: 'Right Camera',
      status: 'connected',
      riskLevel: RISK_LEVELS.SAFE,
      detectedObject: null,
      confidence: null,
      lastDetectionTime: null,
    },
  };
}

// Pre-scripted simulation events — executed in order then looped
export const SIMULATION_SCRIPT = [
  { zone: 'FRONT', object: 'Car', confidence: 92, risk: RISK_LEVELS.WARNING },
  { zone: 'LEFT', object: 'Person', confidence: 87, risk: RISK_LEVELS.WARNING },
  { zone: 'REAR', object: 'Bicycle', confidence: 78, risk: RISK_LEVELS.DANGER },
  { zone: 'FRONT', object: 'Truck', confidence: 95, risk: RISK_LEVELS.CRITICAL },
  { zone: 'RIGHT', object: 'Motorcycle', confidence: 81, risk: RISK_LEVELS.WARNING },
  { zone: 'LEFT', object: null, confidence: null, risk: RISK_LEVELS.SAFE },
  { zone: 'REAR', object: 'Person', confidence: 90, risk: RISK_LEVELS.DANGER },
  { zone: 'FRONT', object: null, confidence: null, risk: RISK_LEVELS.SAFE },
  { zone: 'RIGHT', object: null, confidence: null, risk: RISK_LEVELS.SAFE },
  { zone: 'REAR', object: null, confidence: null, risk: RISK_LEVELS.SAFE },
];

// Map risk level to a human-readable event description
export function buildEventDescription(zone, object, risk) {
  if (object) {
    return `[SIMULATED] ${object} detected in ${zone} zone — Risk: ${risk}`;
  }
  return `${zone} zone returned to SAFE`;
}

// Compute the overall vehicle status from all zone risk levels
export function computeOverallStatus(zones) {
  const levels = Object.values(zones).map((z) => z.riskLevel);
  if (levels.includes(RISK_LEVELS.CRITICAL)) return RISK_LEVELS.CRITICAL;
  if (levels.includes(RISK_LEVELS.DANGER)) return RISK_LEVELS.DANGER;
  if (levels.includes(RISK_LEVELS.WARNING)) return RISK_LEVELS.WARNING;
  return RISK_LEVELS.SAFE;
}

// Return current active zone count (all four zones are always active in this phase)
export function getActiveZoneCount(zones) {
  return Object.values(zones).filter((z) => z.status === 'connected').length;
}

// Count how many zones currently have a detection
export function getDetectionCount(zones) {
  return Object.values(zones).filter((z) => z.detectedObject !== null).length;
}
