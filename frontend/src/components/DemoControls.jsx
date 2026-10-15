// DemoControls.jsx
// OmniScan Phase 3
//
// Adds a Real Camera Mode toggle button alongside the existing demo controls.
// All Phase 2 demo controls and their behaviour are preserved exactly.

import { Play, Pause, RotateCcw, Activity, Server, Camera, CameraOff } from 'lucide-react';

export default function DemoControls({
  isRunning,
  onStart,
  onPause,
  onReset,
  backendConnected,
  // Phase 3 props
  isRealMode,
  onStartRealCamera,
  onStopRealCamera,
  yoloReady,
  webcamActive,
}) {
  return (
    <section className="card" aria-label="Demo simulation controls">
      <div className="card-header">
        <Activity size={14} color="var(--text-secondary)" />
        <span className="card-title">Controls</span>
      </div>

      <div className="demo-controls">
        {/* ── Data source indicator (Phase 2, unchanged) ── */}
        <div
          className="demo-running-indicator"
          style={{ marginBottom: '4px' }}
          aria-live="polite"
        >
          <Server size={13} color={backendConnected ? 'var(--safe)' : 'var(--text-muted)'} />
          <span style={{ color: backendConnected ? 'var(--safe)' : 'var(--text-muted)' }}>
            {backendConnected ? 'Data source: FastAPI backend' : 'Data source: local simulation'}
          </span>
        </div>

        {/* ── Phase 3: Real Camera Mode toggle ── */}
        {backendConnected && (
          <div
            style={{
              borderTop:    '1px solid rgba(255,255,255,0.06)',
              paddingTop:   8,
              marginTop:    6,
              marginBottom: 6,
            }}
          >
            <div
              style={{
                fontSize: 10,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: 1,
                marginBottom: 6,
              }}
            >
              Phase 3 — Real Camera
            </div>

            {isRealMode ? (
              <button
                className="btn btn-secondary"
                onClick={onStopRealCamera}
                aria-label="Stop webcam and return to demo mode"
                style={{ width: '100%', justifyContent: 'center', gap: 8 }}
              >
                <CameraOff size={14} />
                Stop Real Camera
              </button>
            ) : (
              <button
                className="btn btn-primary"
                onClick={onStartRealCamera}
                aria-label="Start real webcam and YOLO detection on FRONT zone"
                style={{ width: '100%', justifyContent: 'center', gap: 8 }}
              >
                <Camera size={14} />
                Start Real Camera
              </button>
            )}

            {/* YOLO / Webcam status */}
            <div
              style={{
                fontSize: 10,
                color: 'var(--text-muted)',
                marginTop: 5,
                lineHeight: 1.5,
              }}
            >
              {yoloReady
                ? <span style={{ color: '#22c55e' }}>● YOLO ready</span>
                : <span style={{ color: '#ef4444' }}>✕ YOLO not loaded</span>
              }
              {' '}·{' '}
              {webcamActive
                ? <span style={{ color: '#22c55e' }}>● Webcam active</span>
                : <span>Webcam off</span>
              }
            </div>
          </div>
        )}

        {/* ── Phase 2 demo action buttons (unchanged) ── */}
        <div className="demo-controls-row" style={{ marginTop: 6 }}>
          {isRunning ? (
            <button
              className="btn btn-secondary"
              onClick={onPause}
              id="btn-pause-demo"
              aria-label="Pause local demo simulation"
              disabled={backendConnected}
              title={backendConnected ? 'Backend is driving the data — local demo is inactive' : ''}
            >
              <Pause size={14} />
              Pause Demo
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={onStart}
              id="btn-start-demo"
              aria-label="Start local demo simulation"
              disabled={backendConnected}
              title={backendConnected ? 'Backend is driving the data — local demo is inactive' : ''}
            >
              <Play size={14} />
              Start Demo
            </button>
          )}

          <button
            className="btn btn-ghost"
            onClick={onReset}
            id="btn-reset-demo"
            aria-label="Reset local demo simulation"
          >
            <RotateCcw size={14} />
            Reset
          </button>
        </div>

        {/* Running indicator (Phase 2, unchanged) */}
        <div className="demo-running-indicator" aria-live="polite">
          <span
            style={{
              width: 8, height: 8, borderRadius: '50%',
              background: (isRealMode || backendConnected || isRunning) ? 'var(--safe)' : 'var(--text-muted)',
              display: 'inline-block',
              animation: (isRealMode || backendConnected || isRunning) ? 'pulse 1.5s ease-in-out infinite' : 'none',
            }}
          />
          {isRealMode
            ? 'Real camera active — YOLO detection on FRONT'
            : backendConnected
            ? 'Backend simulation running — updates every 3 s'
            : isRunning
            ? 'Local simulation running — updates every 3 s'
            : 'Local simulation paused'}
        </div>

        {/* Disclaimer — updated for Phase 3 */}
        <div className="demo-disclaimer" role="note">
          {isRealMode
            ? <>
                ⚠ FRONT zone shows <strong>real YOLO detections</strong>. Risk labels are{' '}
                <strong>experimental</strong> — no distance sensor. REAR / LEFT / RIGHT are{' '}
                <code>SIMULATED</code>.
              </>
            : <>
                ⚠ All detections are <strong>simulated</strong>. No YOLO inference
                or physical cameras are active. Data is labelled{' '}
                <code>SIMULATED_BACKEND</code> or <code>SIMULATED_LOCAL</code>.
              </>
          }
        </div>
      </div>
    </section>
  );
}
