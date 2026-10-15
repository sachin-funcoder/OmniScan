// websocket.js
// Manages the WebSocket connection to the OmniScan FastAPI backend.
//
// Features:
//   - Auto-reconnect after unexpected disconnection (exponential backoff)
//   - Dispatches parsed message objects to a callback
//   - Clean shutdown via the returned disconnect() function
//   - Notifies the caller of connection state changes

const WS_URL = 'ws://127.0.0.1:8000/ws';

// Maximum reconnect delay in milliseconds (30 seconds)
const MAX_BACKOFF_MS = 30_000;

/**
 * createWebSocketService(onMessage, onStatusChange)
 *
 * @param {(msg: object) => void} onMessage
 *   Called every time a valid JSON message arrives from the server.
 *   The message object always has { type, timestamp, payload }.
 *
 * @param {(connected: boolean) => void} onStatusChange
 *   Called when the connection is established or lost.
 *
 * @returns {{ disconnect: () => void }}
 *   Call disconnect() to permanently close the socket (e.g. on component unmount).
 */
export function createWebSocketService(onMessage, onStatusChange) {
  let socket = null;
  let reconnectTimer = null;
  let backoffMs = 1000;   // Start with a 1-second delay before first reconnect
  let destroyed = false;  // Set to true when the caller wants a permanent shutdown

  function connect() {
    if (destroyed) return;

    try {
      socket = new WebSocket(WS_URL);
    } catch (err) {
      // WebSocket constructor can throw if the URL is invalid
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      backoffMs = 1000; // Reset backoff on successful connection
      onStatusChange(true);
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        onMessage(msg);
      } catch {
        // Ignore malformed messages — don't crash the client
        console.warn('[OmniScan WS] Received non-JSON message:', event.data);
      }
    };

    socket.onerror = () => {
      // onerror is always followed by onclose, so we handle reconnect there
    };

    socket.onclose = () => {
      onStatusChange(false);
      if (!destroyed) {
        scheduleReconnect();
      }
    };
  }

  function scheduleReconnect() {
    if (destroyed) return;
    reconnectTimer = setTimeout(() => {
      backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF_MS);
      connect();
    }, backoffMs);
  }

  function disconnect() {
    destroyed = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (socket) {
      socket.onclose = null; // Prevent the reconnect handler from firing
      socket.close();
      socket = null;
    }
    onStatusChange(false);
  }

  // Open the first connection
  connect();

  return { disconnect };
}
