// RiskIndicator.jsx
// Bar-graph style indicator showing SAFE / WARNING / DANGER / CRITICAL level.

export default function RiskIndicator({ riskLevel }) {
  return (
    <div className={`risk-indicator risk-level-${riskLevel}`} aria-label={`Risk level: ${riskLevel}`}>
      <div className="risk-bar-group" role="img" aria-hidden="true">
        <div className="risk-bar" />
        <div className="risk-bar" />
        <div className="risk-bar" />
        <div className="risk-bar" />
      </div>
      <span
        className={`badge risk-${riskLevel.toLowerCase()}`}
        aria-live="polite"
      >
        {riskLevel}
      </span>
    </div>
  );
}
