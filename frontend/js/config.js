// ─── Backend URL Configuration ───────────────────────────────────────────────
// Auto-switches between local dev and the deployed cloud backend.
// After deploying to Render / Railway, replace the URL below with your
// actual backend service URL (e.g. https://job-copilot-api.onrender.com).
// ─────────────────────────────────────────────────────────────────────────────
window.BACKEND_URL = (
  location.hostname === 'localhost' ||
  location.hostname === '127.0.0.1'  ||
  location.hostname === ''
)
  ? 'http://localhost:8000'
  : 'https://YOUR_BACKEND.onrender.com'; // <-- replace after deploying
