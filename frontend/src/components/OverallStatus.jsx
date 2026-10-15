// OverallStatus.jsx
// Prominent panel showing the aggregate vehicle risk status and stats.
// Phase 2: Shows backend vs local data source badge.

import { ShieldCheck, ShieldAlert, AlertTriangle, Siren } from 'lucide-react';

// Maps risk level to display config
const STATUS_CONFIG = {
  SAFE: {
    icon: ShieldCheck,
    color: 'var(--safe)',
    bg:   'var(--safe-bg)',
    border: 'var(--safe-border)',
  },
  WARNING: {
    icon: AlertTriangle,
    color: 'var(--warning)',
    bg:   'var(--warning-bg)',
    border: 'var(--warning-border)',
  },
  DANGER: {
    icon: ShieldAlert,
    color: 'var(--danger)',
    bg:   'var(--danger-bg)',
    border: 'var(--danger-border)',
  },
  CRITICAL: {
    icon: Siren,
    color: 'var(--critical)',
    bg:   'var(--critical-bg)',
    border: 'var(--critical-border)',
  },
};

export default function OverallStatus({
  overallStatus,
  activeZoneCount,
  detectionCount,
  isRunning,
  backendConnected,
  isRealMode,
}) {
  const cfg = STATUS_CONFIG[overallStatus] || STATUS_CONFIG.SAFE;
  const Icon = cfg.icon;

  const lastEvent = isRunning
    ? new Date().toLocaleTimeString('en-US', { hour12: true })
    : '—';

  return (
    <section className="card" aria-label="Overall vehicle status">
      <div className="card-header">
        <span className="card-title">Vehicle Status Overview</span>

        {/* Data-source badge */}
        {backendConnected ? (
          <span
            className="badge"
            style={{
              background: 'var(--safe-bg)',
              border: '1px solid var(--safe-border)',
              color: 'var(--safe)',
            }}
          >
            ● FASTAPI BACKEND
          </span>
        ) : (
          <span
            className="badge"
            style={{
              background: 'rgba(77,166,255,0.10)',
              border: '1px solid rgba(77,166,255,0.25)',
              color: 'var(--accent)',
            }}
          >
            LOCAL DEMO
          </span>
        )}

        <span
          className="badge"
          style={{
            background: isRealMode ? 'rgba(34,197,94,0.08)' : 'rgba(77,166,255,0.06)',
            border: `1px solid ${isRealMode ? 'rgba(34,197,94,0.25)' : 'rgba(77,166,255,0.15)'}`,
            color: isRealMode ? '#22c55e' : 'var(--text-muted)',
          }}
        >
          {isRealMode ? 'PHASE 3 — LIVE YOLO' : 'PHASE 3 PROTOTYPE'}
        </span>
      </div>

      <div className="status-panel">
        {/* Primary status display */}
        <div className="status-main">
          <div
            className="status-icon-wrap"
            style={{
              background: cfg.bg,
              border: `1px solid ${cfg.border}`,
            }}
          >
            <Icon size={28} color={cfg.color} strokeWidth={1.8} />
          </div>
          <div className="status-text-group">
            <span className="status-label">Overall Risk Status</span>
            <span className="status-value" style={{ color: cfg.color }}>
              {overallStatus}
            </span>
            <span className="status-timestamp">
              Last event: {lastEvent}
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className="status-stats">
          <div className="stat-box">
            <span className="stat-label">Active Zones</span>
            <span className="stat-value">{activeZoneCount} / 4</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Detections</span>
            <span className="stat-value">{detectionCount}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Data Source</span>
            <span
              className="stat-value"
              style={{
                fontSize: '11px',
                fontFamily: 'inherit',
                color: backendConnected ? 'var(--safe)' : 'var(--accent)',
                lineHeight: '1.3',
              }}
            >
              {backendConnected ? 'FastAPI' : 'Local Sim'}
            </span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Sim Status</span>
            <span
              className="stat-value"
              style={{
                fontSize: '13px',
                fontFamily: 'inherit',
                color: isRunning ? 'var(--safe)' : 'var(--text-muted)',
              }}
            >
              {isRunning ? '● RUNNING' : '○ PAUSED'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
