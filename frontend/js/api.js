// ===== CONFIGURATION =====
const BASE_URL = 'http://localhost:8000';

// ===== AUTH STATE =====
// Wraps localStorage so all token/user access goes through one object.
// If you switch to sessionStorage or HttpOnly cookies, only change here.
export const auth = {
  getToken:  ()      => localStorage.getItem('token'),
  setToken:  (t)     => localStorage.setItem('token', t),
  getUser:   ()      => { const u = localStorage.getItem('user'); return u ? JSON.parse(u) : null; },
  setUser:   (u)     => localStorage.setItem('user', JSON.stringify(u)),
  clear:     ()      => { localStorage.removeItem('token'); localStorage.removeItem('user'); },
  isLoggedIn: ()     => !!localStorage.getItem('token'),
};

// Redirect to login if not authenticated.
// Called at the top of every protected page (dashboard, new-application, application).
export function requireAuth() {
  if (!auth.isLoggedIn()) {
    window.location.href = 'index.html';
  }
}

// ===== CORE FETCH WRAPPER =====
async function request(method, path, body = null, isFormData = false) {
  const headers = {};

  // Add auth token if logged in
  const token = auth.getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  // Only set Content-Type for JSON (FormData sets its own boundary header automatically)
  if (body && !isFormData) headers['Content-Type'] = 'application/json';

  const options = { method, headers };
  if (body) options.body = isFormData ? body : JSON.stringify(body);

  const res = await fetch(`${BASE_URL}${path}`, options);

  // Auto-logout on 401 (expired token, wrong key, etc.)
  if (res.status === 401) {
    auth.clear();
    window.location.href = 'index.html';
    return;
  }

  // 204 No Content — successful but no body (used by DELETE endpoints)
  if (res.status === 204) return null;

  const data = await res.json();

  // FastAPI returns errors as { "detail": "message" }
  // Some endpoints return arrays of validation errors: { "detail": [{ "msg": "..." }] }
  if (!res.ok) {
    const msg = Array.isArray(data.detail)
      ? data.detail.map(e => e.msg).join(', ')
      : (data.detail || `HTTP ${res.status}`);
    throw new Error(msg);
  }

  return data;
}

// ===== HTTP METHOD SHORTCUTS =====
export const api = {
  get:      (path)              => request('GET',    path),
  post:     (path, body)        => request('POST',   path, body),
  patch:    (path, body)        => request('PATCH',  path, body),
  delete:   (path)              => request('DELETE', path),

  // For file uploads — body must be FormData, not JSON.
  // fetch() automatically sets Content-Type: multipart/form-data with the correct boundary.
  postForm: (path, formData)    => request('POST', path, formData, true),

  // ADDED: For binary file downloads (.docx, PDF).
  // The regular get() calls res.json() which fails on binary responses.
  // getBlob() returns the raw Blob so the caller can create an object URL for download.
  getBlob: async (path) => {
    const headers = {};
    const token = auth.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}${path}`, { method: 'GET', headers });
    if (res.status === 401) {
      auth.clear();
      window.location.href = 'index.html';
      return;
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    return res.blob();
  },
};

// ===== TOAST NOTIFICATIONS =====
// Creates a toast-container div if it doesn't exist, appends a toast, auto-removes after 3s.
export function toast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  container.appendChild(el);

  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

// ===== LOADING OVERLAY =====
export function showLoading(message = 'Loading...') {
  let overlay = document.getElementById('loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
      <div class="loading-spinner"></div>
      <div class="loading-text" id="loading-message">${message}</div>
    `;
    document.body.appendChild(overlay);
  } else {
    document.getElementById('loading-message').textContent = message;
    overlay.classList.remove('hidden');
  }
}

export function hideLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.add('hidden');
}

// ===== UTILITY HELPERS =====

// Formats ISO date string to "Jun 17, 2025"
export function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

// Maps backend enum value → human-readable label
export function statusLabel(status) {
  const map = {
    not_yet:    'Not Applied',
    applied:    'Applied',
    interviewed:'Interviewing',
    rejected:   'Rejected',
    offer:      'Offer Received',
  };
  return map[status] || status;
}

// Maps status → color dot for inline display
export function statusDot(status) {
  const colors = {
    not_yet:    '#64748b',
    applied:    '#3b82f6',
    interviewed:'#f59e0b',
    rejected:   '#ef4444',
    offer:      '#10b981',
  };
  const color = colors[status] || '#64748b';
  return `<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${color}; margin-right:6px;"></span>`;
}

// Escapes HTML special characters to safely render user-provided strings
// WITHOUT this, a job title containing <script> would execute JS
export function escHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str || ''));
  return div.innerHTML;
}

