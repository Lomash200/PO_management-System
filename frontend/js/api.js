/**
 * API Client — PO Management System
 * Centralised fetch wrapper with JWT auth
 */

const API_BASE = 'http://localhost:8000/api';

const API = {
  // ── Helpers ──────────────────────────────────────────────

  _getToken() {
    return localStorage.getItem('po_token');
  },

  async _request(path, options = {}) {
    const token = this._getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    } catch (err) {
      throw new Error('Network error — is the backend running?');
    }

    if (response.status === 401) {
      localStorage.removeItem('po_token');
      localStorage.removeItem('po_user');
      window.location.href = '/pages/login.html';
      return;
    }

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        detail = err.detail || JSON.stringify(err);
      } catch (_) {}
      throw new Error(detail);
    }

    if (response.status === 204) return null;
    return response.json();
  },

  _get(path) { return this._request(path, { method: 'GET' }); },
  _post(path, body) { return this._request(path, { method: 'POST', body: JSON.stringify(body) }); },
  _put(path, body) { return this._request(path, { method: 'PUT', body: JSON.stringify(body) }); },
  _patch(path, body) { return this._request(path, { method: 'PATCH', body: JSON.stringify(body) }); },
  _delete(path) { return this._request(path, { method: 'DELETE' }); },

  // ── Auth ────────────────────────────────────────────────

  async login(email, password) {
    return this._post('/auth/login', { email, password });
  },
  async register(full_name, email, password) {
    return this._post('/auth/register', { full_name, email, password });
  },

  // ── Vendors ─────────────────────────────────────────────

  getVendors(search = '') {
    const q = search ? `?search=${encodeURIComponent(search)}` : '';
    return this._get(`/vendors/${q}`);
  },
  getVendor(id) { return this._get(`/vendors/${id}`); },
  createVendor(data) { return this._post('/vendors/', data); },
  updateVendor(id, data) { return this._put(`/vendors/${id}`, data); },
  deleteVendor(id) { return this._delete(`/vendors/${id}`); },

  // ── Products ─────────────────────────────────────────────

  getProducts(search = '', category = '') {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    const q = params.toString() ? `?${params}` : '';
    return this._get(`/products/${q}`);
  },
  getProduct(id) { return this._get(`/products/${id}`); },
  createProduct(data) { return this._post('/products/', data); },
  updateProduct(id, data) { return this._put(`/products/${id}`, data); },
  deleteProduct(id) { return this._delete(`/products/${id}`); },
  generateAIDescription(productId) {
    return this._post(`/products/${productId}/generate-description`, {});
  },
  previewAIDescription(name, category) {
    return this._post('/products/generate-description/preview', { product_name: name, category });
  },

  // ── Purchase Orders ──────────────────────────────────────

  getPurchaseOrders(status = '', vendorId = '') {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (vendorId) params.set('vendor_id', vendorId);
    const q = params.toString() ? `?${params}` : '';
    return this._get(`/purchase-orders/${q}`);
  },
  getPurchaseOrder(id) { return this._get(`/purchase-orders/${id}`); },
  createPurchaseOrder(data) { return this._post('/purchase-orders/', data); },
  updatePOStatus(id, status, notes = '') {
    return this._patch(`/purchase-orders/${id}/status`, { status, notes: notes || undefined });
  },
  deletePurchaseOrder(id) { return this._delete(`/purchase-orders/${id}`); },
};

// ── Auth Guard ─────────────────────────────────────────────

function requireAuth() {
  const token = localStorage.getItem('po_token');
  if (!token) {
    window.location.href = '/pages/login.html';
    return null;
  }
  return JSON.parse(localStorage.getItem('po_user') || '{}');
}

function getCurrentUser() {
  return JSON.parse(localStorage.getItem('po_user') || '{}');
}

function logout() {
  localStorage.removeItem('po_token');
  localStorage.removeItem('po_user');
  window.location.href = '/pages/login.html';
}

// ── Currency Formatter ─────────────────────────────────────

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:2 }).format(amount);
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' });
}

function statusBadge(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}

function starRating(rating) {
  const full = Math.floor(rating);
  const half = rating % 1 >= 0.5;
  let html = '';
  for (let i = 0; i < 5; i++) {
    if (i < full) html += '★';
    else if (i === full && half) html += '½';
    else html += '☆';
  }
  return `<span class="stars" title="${rating}/5">${html}</span> <span style="color:var(--text-muted);font-size:.8rem">${rating.toFixed(1)}</span>`;
}
