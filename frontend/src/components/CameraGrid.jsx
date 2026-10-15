// CameraGrid.jsx
// OmniScan Phase 3
//
// Renders the 2×2 grid of camera panels.
// Phase 3: passes isRealMode prop to each CameraPanel and updates the badge
// to reflect whether the FRONT zone is live.

import CameraPanel from './CameraPanel';

const ZONE_ORDER = ['FRONT', 'REAR', 'LEFT', 'RIGHT'];

export default function CameraGrid({ zones, isRealMode }) {
  return (
    <section aria-label="Camera zone grid">
      <div className="card-header" style={{ marginBottom: '12px' }}>
        <span className="card-title">Camera Zones</span>

        {isRealMode ? (
          <>
            <span
              className="badge"
              style={{
                background: 'rgba(34,197,94,0.12)',
                border: '1px solid rgba(34,197,94,0.35)',
                color: '#22c55e',
              }}
            >
              ● FRONT: LIVE WEBCAM
            </span>
            <span
              className="badge"
              style={{
                background: 'rgba(77,166,255,0.08)',
                border: '1px solid rgba(77,166,255,0.20)',
                color: 'var(--text-muted)',
                marginLeft: 6,
              }}
            >
              REAR / LEFT / RIGHT: SIMULATED
            </span>
          </>
        ) : (
          <span
            className="badge"
            style={{
              background: 'rgba(77,166,255,0.08)',
              border: '1px solid rgba(77,166,255,0.20)',
              color: 'var(--accent)',
            }}
          >
            4 ZONES — SIMULATED
          </span>
        )}
      </div>

      <div className="camera-grid">
        {ZONE_ORDER.map((zoneId) => (
          <CameraPanel
            key={zoneId}
            zone={zones[zoneId]}
            isRealMode={isRealMode}
          />
        ))}
      </div>
    </section>
  );
}
