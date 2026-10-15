// CameraPanel.jsx
// OmniScan Phase 3
//
// Renders one camera zone.
// FRONT zone (when in real mode): shows MJPEG webcam feed with bounding-box
//   canvas overlay drawn from the latest real_detection WebSocket message.
// All other zones (and FRONT in simulated mode): unchanged Phase 2 simulation view.
//
// Phase 2 behaviour is 100% preserved for REAR / LEFT / RIGHT zones.

import { useRef, useEffect } from 'react';
import { Camera } from 'lucide-react';
import RiskIndicator from './RiskIndicator';

const MJPEG_URL = 'http://127.0.0.1:8000/video/front';

// Colour config per risk level
const RISK_COLORS = {
  SAFE:     { main: 'var(--safe)',     border: 'var(--safe-border)'     },
  WARNING:  { main: 'var(--warning)',  border: 'var(--warning-border)'  },
  DANGER:   { main: 'var(--danger)',   border: 'var(--danger-border)'   },
  CRITICAL: { main: 'var(--critical)', border: 'var(--critical-border)' },
};

// Determine which CSS silhouette class to use for a detected object
function getSilhouetteClass(objectName) {
  if (!objectName) return null;
  const lower = objectName.toLowerCase();
  if (lower === 'person') return 'silhouette-person';
  if (lower === 'bicycle' || lower === 'scooter') return 'silhouette-bicycle';
  if (lower === 'car' || lower === 'truck' || lower === 'bus') return 'silhouette-car';
  return 'silhouette-default';
}

// Zone-specific background tint to differentiate panels subtly
const ZONE_TINTS = {
  FRONT: 'radial-gradient(ellipse at 50% 110%, rgba(77,166,255,0.04) 0%, transparent 70%)',
  REAR:  'radial-gradient(ellipse at 50% 110%, rgba(239,68,68,0.04) 0%, transparent 70%)',
  LEFT:  'radial-gradient(ellipse at 50% 110%, rgba(234,179,8,0.04) 0%, transparent 70%)',
  RIGHT: 'radial-gradient(ellipse at 50% 110%, rgba(34,197,94,0.04) 0%, transparent 70%)',
};

// ── Bounding-box canvas overlay for the real webcam feed ────────────────────

function BboxCanvas({ detections, frameWidth = 640, frameHeight = 480 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Match canvas pixel buffer to actual displayed DOM dimensions
    const rect = canvas.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      if (canvas.width !== rect.width || canvas.height !== rect.height) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!detections || detections.length === 0) return;

    const CW = canvas.width;
    const CH = canvas.height;
    if (CW === 0 || CH === 0) return;

    // Aspect ratio calculation to accurately match object-fit: contain
    const fw = frameWidth || 640;
    const fh = frameHeight || 480;
    const frameAspect = fw / fh;
    const containerAspect = CW / CH;

    let renderW = CW;
    let renderH = CH;
    let offsetX = 0;
    let offsetY = 0;

    if (containerAspect > frameAspect) {
      // Container is wider than webcam frame -> pillarbox (black bars on left/right)
      renderH = CH;
      renderW = CH * frameAspect;
      offsetX = (CW - renderW) / 2;
    } else {
      // Container is taller than webcam frame -> letterbox (black bars on top/bottom)
      renderW = CW;
      renderH = CW / frameAspect;
      offsetY = (CH - renderH) / 2;
    }

    detections.forEach((det) => {
      const [x1n, y1n, x2n, y2n] = det.bbox_norm;
      const x  = offsetX + x1n * renderW;
      const y  = offsetY + y1n * renderH;
      const bw = (x2n - x1n) * renderW;
      const bh = (y2n - y1n) * renderH;

      // Choose label colour by class
      const cls = det.class_name.toLowerCase();
      let color = '#4da6ff'; // default blue
      if (cls === 'person') color = '#facc15'; // yellow
      else if (['car', 'truck', 'bus'].includes(cls)) color = '#ef4444'; // red
      else if (['bicycle', 'motorcycle'].includes(cls)) color = '#22c55e'; // green
      else if (['cell phone', 'phone'].includes(cls)) color = '#a855f7'; // purple
      else if (['bottle', 'cup'].includes(cls)) color = '#06b6d4'; // cyan

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth   = 2;
      ctx.strokeRect(x, y, bw, bh);

      // Draw label background + text
      const label   = `${det.class_name} ${Math.round(det.confidence * 100)}%`;
      const fontSize = 11;
      ctx.font      = `bold ${fontSize}px monospace`;
      const textW   = ctx.measureText(label).width + 8;
      const textH   = fontSize + 6;

      const labelY = Math.max(y, textH);
      ctx.fillStyle = color;
      ctx.fillRect(x, labelY - textH, textW, textH);
      ctx.fillStyle = '#000';
      ctx.fillText(label, x + 4, labelY - 4);
    });
  }, [detections, frameWidth, frameHeight]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position:   'absolute',
        top:        0,
        left:       0,
        width:      '100%',
        height:     '100%',
        pointerEvents: 'none',
        zIndex:     2,
      }}
    />
  );
}

// ── Real camera view (FRONT zone when webcam is active) ──────────────────────

function RealCameraView({ zone }) {
  const { riskLevel, detections = [], lastDetectionTime, frameWidth = 640, frameHeight = 480 } = zone;
  const riskColor = RISK_COLORS[riskLevel] || RISK_COLORS.SAFE;

  return (
    <div
      className="camera-scene"
      aria-label="Live FRONT camera feed (YOLO detection active)"
      style={{ position: 'relative', overflow: 'hidden' }}
    >
      {/* MJPEG stream from the FastAPI backend */}
      <img
        src={MJPEG_URL}
        alt="Live webcam feed"
        style={{
          width:    '100%',
          height:   '100%',
          objectFit: 'contain',
          display:  'block',
        }}
      />

      {/* Canvas overlay for bounding boxes */}
      <BboxCanvas
        detections={detections}
        frameWidth={frameWidth}
        frameHeight={frameHeight}
      />

      {/* Corner scan lines (same as simulated view) */}
      <div className="scan-overlay" aria-hidden="true">
        <div className="scan-corner tl" />
        <div className="scan-corner tr" />
        <div className="scan-corner bl" />
        <div className="scan-corner br" />
      </div>

      {/* LIVE badge — replaces "SIMULATED FEED" watermark */}
      <span
        className="sim-watermark"
        aria-hidden="true"
        style={{ color: '#22c55e', fontWeight: 700 }}
      >
        ● LIVE · YOLO
      </span>

      {/* Scene timestamp */}
      <span className="scene-timestamp mono" aria-hidden="true">
        {lastDetectionTime || '-- : -- : --'}
      </span>

      {/* Experimental disclaimer ribbon */}
      <div
        style={{
          position:   'absolute',
          bottom:     24,
          left:       0,
          right:      0,
          textAlign:  'center',
          fontSize:   9,
          color:      'rgba(255,255,255,0.45)',
          pointerEvents: 'none',
          zIndex:     3,
        }}
      >
        ⚠ EXPERIMENTAL · no distance sensor
      </div>
    </div>
  );
}

// ── Simulated camera view (Phase 2, unchanged) ───────────────────────────────

function SimulatedCameraView({ zone }) {
  const { id, riskLevel, detectedObject, lastDetectionTime } = zone;
  const riskColor  = RISK_COLORS[riskLevel] || RISK_COLORS.SAFE;
  const silhouette = getSilhouetteClass(detectedObject);
  const hasDetection = detectedObject !== null;

  return (
    <div
      className="camera-scene"
      aria-label={`Simulated ${id} camera feed`}
    >
      {/* Background gradient */}
      <div
        className="camera-scene-bg"
        style={{ background: ZONE_TINTS[id] || '' }}
      />

      {/* Road perspective */}
      <div className="scene-road"        aria-hidden="true" />
      <div className="scene-lane-left"   aria-hidden="true" />
      <div className="scene-lane-right"  aria-hidden="true" />
      <div className="scene-horizon"     aria-hidden="true" />

      {/* Detected object silhouette */}
      <div className={`scene-object${hasDetection ? ' visible' : ''}`} aria-hidden="true">
        {silhouette && <div className={`object-silhouette ${silhouette}`} />}
      </div>

      {/* Detection bounding box */}
      <div
        className={`detection-box${hasDetection ? ' visible' : ''}`}
        aria-hidden="true"
        style={{
          borderColor: riskColor.main,
          width:  silhouette === 'silhouette-person' ? '28px'  : '80px',
          height: silhouette === 'silhouette-person' ? '60px'  : '54px',
        }}
      >
        {hasDetection && (
          <span
            className="detection-label-overlay"
            style={{ background: riskColor.main, color: '#000' }}
          >
            {detectedObject} {zone.confidence}%
          </span>
        )}
      </div>

      {/* Corner scan lines */}
      <div className="scan-overlay" aria-hidden="true">
        <div className="scan-corner tl" />
        <div className="scan-corner tr" />
        <div className="scan-corner bl" />
        <div className="scan-corner br" />
      </div>

      {/* Simulated feed watermark */}
      <span className="sim-watermark" aria-hidden="true">SIMULATED FEED</span>

      {/* Scene timestamp */}
      <span className="scene-timestamp mono" aria-hidden="true">
        {lastDetectionTime || '-- : -- : --'}
      </span>
    </div>
  );
}

// ── Main CameraPanel export ──────────────────────────────────────────────────

export default function CameraPanel({ zone, isRealMode }) {
  const {
    id, label, status, riskLevel,
    detectedObject, confidence, lastDetectionTime,
    mode,
  } = zone;

  const riskColor    = RISK_COLORS[riskLevel] || RISK_COLORS.SAFE;
  const hasDetection = detectedObject !== null;

  // FRONT zone in real mode uses the live view
  const showRealView = id === 'FRONT' && isRealMode && mode === 'real';

  return (
    <article
      className={`camera-panel risk-${riskLevel.toLowerCase()}`}
      aria-label={`${label} — ${riskLevel}`}
    >
      {/* ── Panel Header ── */}
      <div className="camera-panel-header">
        <div className="camera-zone-id">
          <Camera size={15} color="var(--text-secondary)" />
          <span className="camera-zone-label">{id}</span>
          <span style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 400 }}>
            {label}
          </span>
          {/* Mode badge */}
          {id === 'FRONT' && isRealMode ? (
            <span
              style={{
                fontSize: 9, padding: '1px 5px', borderRadius: 3,
                background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.4)',
                color: '#22c55e', fontWeight: 700, letterSpacing: 1,
              }}
            >
              LIVE
            </span>
          ) : (
            id !== 'FRONT' && (
              <span
                style={{
                  fontSize: 9, padding: '1px 5px', borderRadius: 3,
                  background: 'rgba(77,166,255,0.08)', border: '1px solid rgba(77,166,255,0.20)',
                  color: 'var(--text-muted)', fontWeight: 700, letterSpacing: 1,
                }}
              >
                SIM
              </span>
            )
          )}
        </div>
        <span className="camera-status-pill">
          {status === 'connected' ? '● Connected' : '✕ Offline'}
        </span>
      </div>

      {/* ── Camera Scene ── */}
      {showRealView
        ? <RealCameraView zone={zone} />
        : <SimulatedCameraView zone={zone} />
      }

      {/* ── Panel Footer ── */}
      <div className="camera-panel-footer">
        <div className="detection-info">
          {hasDetection ? (
            <>
              <span className="detection-object">{detectedObject}</span>
              <span className="detection-confidence">Confidence: {confidence}%</span>
            </>
          ) : (
            <span className="detection-none">No detection</span>
          )}
          {/* Simulated label for non-real zones */}
          {!showRealView && id !== 'FRONT' && (
            <span
              style={{
                fontSize: 9, color: 'var(--text-muted)',
                display: 'block', marginTop: 2,
              }}
            >
              ⓘ Simulated data — no physical camera
            </span>
          )}
        </div>
        <RiskIndicator riskLevel={riskLevel} />
      </div>
    </article>
  );
}
