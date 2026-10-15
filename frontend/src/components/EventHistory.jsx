// EventHistory.jsx
// Timestamped log of all simulated detection and status events.

import { History, Trash2 } from 'lucide-react';

// Colour dot per risk level
const RISK_DOT_COLORS = {
  SAFE:     'var(--safe)',
  WARNING:  'var(--warning)',
  DANGER:   'var(--danger)',
  CRITICAL: 'var(--critical)',
};

export default function EventHistory({ eventLog, onClear }) {
  return (
    <section className="card" aria-label="Event history log" style={{ flex: 1 }}>
      {/* Header */}
      <div className="event-history-header">
        <div className="card-header" style={{ margin: 0 }}>
          <History size={14} color="var(--text-secondary)" />
          <span className="card-title">Event History</span>
          <span
            className="badge"
            style={{
              background: 'var(--bg-raised)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
          >
            {eventLog.length}
          </span>
        </div>
        <button
          className="btn btn-ghost"
          onClick={onClear}
          id="btn-clear-events"
          aria-label="Clear event history"
          style={{ padding: '5px 10px', fontSize: '12px' }}
        >
          <Trash2 size={13} />
          Clear
        </button>
      </div>

      {/* Event list */}
      <div className="event-list" aria-live="polite" aria-relevant="additions">
        {eventLog.length === 0 ? (
          <p className="event-empty">No events yet. Start the demo to see events.</p>
        ) : (
          eventLog.map((event) => (
            <div key={event.id} className="event-item" role="listitem">
              <div
                className="event-dot"
                style={{ background: RISK_DOT_COLORS[event.severity] || 'var(--text-muted)' }}
                aria-hidden="true"
              />
              <div className="event-body">
                <p className="event-desc">{event.description}</p>
                <div className="event-meta">
                  <span className="event-time">{event.time}</span>
                  <span className="event-zone">{event.zone}</span>
                  <span
                    className={`badge risk-${event.severity.toLowerCase()}`}
                    style={{ fontSize: '9px', padding: '1px 6px' }}
                  >
                    {event.severity}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
