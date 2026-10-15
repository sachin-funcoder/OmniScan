// App.jsx
// OmniScan Phase 3
//
// Threads isRealMode, yoloReady, webcamActive, and camera control actions
// from useBackend down to CameraGrid and DemoControls.
// All Phase 2 logic is preserved verbatim.

import './index.css';
import Navbar        from './components/Navbar';
import OverallStatus from './components/OverallStatus';
import CameraGrid    from './components/CameraGrid';
import AudioControls from './components/AudioControls';
import EventHistory  from './components/EventHistory';
import DemoControls  from './components/DemoControls';
import { useDemoSimulation } from './hooks/useDemoSimulation';
import { useBackend }        from './hooks/useBackend';

export default function App() {
  // ── Backend hook (always running, reconnects automatically) ────────────────
  const backend = useBackend();

  // ── Local demo simulation (fallback / manual override) ─────────────────────
  const demo = useDemoSimulation();

  // ── Mode selection ──────────────────────────────────────────────────────────
  // When the backend is connected, its data drives the UI.
  // When offline, the local demo simulation is the data source.
  const useBackendData = backend.backendConnected;

  const zones           = useBackendData ? backend.zones          : demo.zones;
  const overallStatus   = useBackendData ? backend.overallStatus  : demo.overallStatus;
  const activeZoneCount = useBackendData ? backend.activeZoneCount: demo.activeZoneCount;
  const detectionCount  = useBackendData ? backend.detectionCount : demo.detectionCount;
  const eventLog        = useBackendData ? backend.eventLog       : demo.eventLog;
  const clearEventLog   = useBackendData ? backend.clearEventLog  : demo.clearEventLog;

  return (
    <div className="app-layout">
      {/* A. Top Navigation Bar */}
      <Navbar
        backendConnected={backend.backendConnected}
        isRealMode={backend.isRealMode}
      />

      <main className="main-content" id="main-content">
        {/* B. Overall Vehicle Status */}
        <OverallStatus
          overallStatus={overallStatus}
          activeZoneCount={activeZoneCount}
          detectionCount={detectionCount}
          isRunning={useBackendData ? true : demo.isRunning}
          backendConnected={backend.backendConnected}
          isRealMode={backend.isRealMode}
        />

        {/* C & D. Four Camera Panels with Risk Indicators */}
        <CameraGrid
          zones={zones}
          isRealMode={backend.isRealMode}
        />

        {/* E, F, G. Bottom row */}
        <div className="bottom-row">
          {/* E. Audio Controls */}
          <AudioControls overallStatus={overallStatus} />

          {/* F. Event History */}
          <EventHistory eventLog={eventLog} onClear={clearEventLog} />

          {/* G. Controls — demo + real camera mode */}
          <DemoControls
            isRunning={demo.isRunning}
            onStart={demo.startDemo}
            onPause={demo.pauseDemo}
            onReset={demo.resetDemo}
            backendConnected={backend.backendConnected}
            // Phase 3 props
            isRealMode={backend.isRealMode}
            onStartRealCamera={backend.startRealCamera}
            onStopRealCamera={backend.stopRealCamera}
            yoloReady={backend.yoloReady}
            webcamActive={backend.webcamActive}
          />
        </div>
      </main>
    </div>
  );
}
