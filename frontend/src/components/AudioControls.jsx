// AudioControls.jsx
// Browser-based audio alert controls.
// Audio does NOT play automatically — the user must interact first (browser policy).
// Uses the Web Audio API to generate simple sine-wave tones for demonstration.

import { useState, useRef, useCallback } from 'react';
import { Volume2, VolumeX, Bell, BellOff } from 'lucide-react';

// Frequency map per risk level
const ALERT_FREQUENCIES = {
  SAFE:     440,   // A4 — calm
  WARNING:  587,   // D5 — moderate
  DANGER:   784,   // G5 — urgent
  CRITICAL: 1047,  // C6 — high urgency
};

// Create or reuse AudioContext (browser requires user gesture first)
let sharedAudioCtx = null;
function getAudioContext() {
  if (!sharedAudioCtx) {
    try {
      sharedAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch {
      return null;
    }
  }
  return sharedAudioCtx;
}

function playTone(frequency, durationMs = 300, volumeGain = 0.3) {
  const ctx = getAudioContext();
  if (!ctx) return;

  const oscillator = ctx.createOscillator();
  const gainNode   = ctx.createGain();

  oscillator.connect(gainNode);
  gainNode.connect(ctx.destination);

  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(frequency, ctx.currentTime);

  gainNode.gain.setValueAtTime(volumeGain, ctx.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + durationMs / 1000);

  oscillator.start(ctx.currentTime);
  oscillator.stop(ctx.currentTime + durationMs / 1000);
}

export default function AudioControls({ overallStatus }) {
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [muted, setMuted]               = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);

  // Allow parent hook to call playAlert when risk changes
  // (for simplicity in Phase 1, we expose a Test Alert button)

  const handleEnableToggle = useCallback(() => {
    setAudioEnabled((prev) => {
      if (!prev) setHasInteracted(true); // first enable = user interaction
      return !prev;
    });
  }, []);

  const handleTestAlert = useCallback(() => {
    if (!audioEnabled || muted) return;
    const freq = ALERT_FREQUENCIES[overallStatus] || ALERT_FREQUENCIES.WARNING;
    // Play two short pulses
    playTone(freq, 250, 0.3);
    setTimeout(() => playTone(freq, 250, 0.25), 320);
    setHasInteracted(true);
  }, [audioEnabled, muted, overallStatus]);

  const noticeText = !audioEnabled
    ? 'Audio alerts are disabled. Enable the toggle to allow demo alert tones.'
    : muted
    ? 'Audio is muted. Unmute to hear alert tones.'
    : 'Audio alerts are active. Use "Test Alert" to hear a demo tone.';

  return (
    <section className="card" aria-label="Audio alert controls">
      <div className="card-header">
        <Bell size={14} color="var(--text-secondary)" />
        <span className="card-title">Audio Alerts</span>
      </div>

      <div className="audio-controls">
        {/* Enable toggle */}
        <div className="audio-row">
          <span className="audio-label">
            {audioEnabled ? <Bell size={14} /> : <BellOff size={14} />}
            Enable Alerts
          </span>
          <label className="toggle" aria-label="Enable audio alerts">
            <input
              type="checkbox"
              checked={audioEnabled}
              onChange={handleEnableToggle}
              id="audio-enable-toggle"
            />
            <div className="toggle-track" />
            <div className="toggle-thumb" />
          </label>
        </div>

        {/* Mute toggle */}
        <div className="audio-row">
          <span className="audio-label">
            {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
            Mute
          </span>
          <label className="toggle" aria-label="Mute audio">
            <input
              type="checkbox"
              checked={muted}
              onChange={() => setMuted((m) => !m)}
              disabled={!audioEnabled}
              id="audio-mute-toggle"
            />
            <div className="toggle-track" />
            <div className="toggle-thumb" />
          </label>
        </div>

        <div className="divider" />

        {/* Test alert */}
        <button
          className="btn btn-secondary"
          onClick={handleTestAlert}
          disabled={!audioEnabled || muted}
          id="btn-test-alert"
          aria-label="Play test audio alert"
        >
          <Volume2 size={14} />
          Test Alert
        </button>

        {/* Status notice */}
        <div className={`audio-notice${audioEnabled && !muted ? ' active' : ''}`} role="status" aria-live="polite">
          {noticeText}
        </div>
      </div>
    </section>
  );
}
