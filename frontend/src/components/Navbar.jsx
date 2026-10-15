// Navbar.jsx
// Top navigation bar — shows logo, project info, clock, and backend connection status.
// Phase 2: Accepts backendConnected prop and shows BACKEND CONNECTED / DISCONNECTED.

import { useState, useEffect } from 'react';
import { ScanEye, Wifi, WifiOff } from 'lucide-react';

export default function Navbar({ backendConnected = false, isRealMode = false }) {
  const [now, setNow] = useState(new Date());

  // Update clock every second
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  const timeStr = now.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });

  return (
    <nav className="navbar" role="banner">
      {/* Brand */}
      <div className="navbar-brand">
        <div className="navbar-logo" aria-hidden="true">
          <ScanEye size={20} strokeWidth={1.8} />
        </div>
        <div className="navbar-titles">
          <span className="navbar-name">OmniScan</span>
          <span className="navbar-subtitle">AI-Based Vehicle Surround Monitoring System</span>
        </div>
      </div>

      {/* Right section */}
      <div className="navbar-right">
        {/* Mode badge */}
        {isRealMode ? (
          <span
            className="demo-badge"
            aria-label="Real camera mode active"
            style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)' }}
          >
            ● REAL MODE
          </span>
        ) : (
          <span className="demo-badge" aria-label="Demo mode active">⚠ DEMO MODE</span>
        )}

        {/* Backend connection status */}
        <div
          className="connection-status"
          aria-label={backendConnected ? 'Backend connected' : 'Backend disconnected'}
        >
          {backendConnected ? (
            <>
              <span className="connection-dot" style={{ background: 'var(--safe)' }} />
              <Wifi size={12} />
              <span style={{ color: 'var(--safe)' }}>BACKEND CONNECTED</span>
            </>
          ) : (
            <>
              <span className="connection-dot" style={{ background: 'var(--text-muted)' }} />
              <WifiOff size={12} />
              <span>BACKEND DISCONNECTED</span>
            </>
          )}
        </div>

        {/* Date/time */}
        <div className="navbar-clock mono" aria-label="Current date and time">
          {dateStr} &nbsp;·&nbsp; {timeStr}
        </div>
      </div>
    </nav>
  );
}
