// ─── Backend URL Configuration ───────────────────────────────────────────────
// Auto-switches between local dev and the deployed cloud backend.
// Update this URL if your Render service uses a different hostname.
// ─────────────────────────────────────────────────────────────────────────────
const isLocalHost = ['localhost', '127.0.0.1', ''].includes(location.hostname);
const defaultBackendUrl = 'https://job-application-copilot-dbo3.onrender.com';

window.BACKEND_URL = window.BACKEND_URL || (isLocalHost ? 'http://localhost:8000' : defaultBackendUrl);
console.log('Using backend URL:', window.BACKEND_URL);