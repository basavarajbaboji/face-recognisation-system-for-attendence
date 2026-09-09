// Centralized API and WebSocket endpoints configuration
// In development, Vite proxy forwards /api, /data, and /presentation to the FastAPI backend (port 8000)
export const API_BASE = import.meta.env.VITE_API_BASE || '';

export const getWsUrl = (path = '/api/camera/ws') => {
  if (import.meta.env.VITE_WS_BASE) {
    return `${import.meta.env.VITE_WS_BASE}${path}`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${path}`;
};
