/* Main application: tab routing, shared fetch helpers, global state */
const App = (() => {
  // Use current origin so it works both locally and on Railway/any deployment
  const API_BASE = window.location.origin;
  const state = { currentTab: 'documents', documents: [], selectedDocId: null };

  function init() {
    renderTab(state.currentTab);
    document.querySelectorAll('[data-tab]').forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        const tab = e.currentTarget.dataset.tab;
        switchTab(tab);
      });
    });
  }

  function switchTab(tab) {
    document.querySelectorAll('[data-tab]').forEach(l => l.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`)?.classList.add('active');
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('d-none'));
    const pane = document.getElementById(`tab-${tab}`);
    if (pane) pane.classList.remove('d-none');
    state.currentTab = tab;
    renderTab(tab);
  }

  function renderTab(tab) {
    switch (tab) {
      case 'documents':   DocumentsComponent.render(); break;
      case 'tasks':       TasksComponent.render(); break;
      case 'evaluations': EvaluationsComponent.render(); break;
      case 'metrics':     MetricsComponent.render(); break;
      case 'history':     HistoryComponent.render(); break;
      case 'help':        HelpComponent.render(); break;
    }
  }

  async function apiFetch(path, options = {}) {
    const url = `${API_BASE}${path}`;
    const resp = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!resp.ok) {
      const err = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${err}`);
    }
    return resp.json();
  }

  async function apiPost(path, body) {
    return apiFetch(path, { method: 'POST', body: JSON.stringify(body) });
  }

  function statusBadge(status) {
    const s = (status || 'unknown').toLowerCase();
    return `<span class="status-badge badge-${s}">${s}</span>`;
  }

  function passBadge(pass) {
    if (pass === null || pass === undefined) return '<span class="status-badge badge-pending">N/A</span>';
    return pass
      ? '<span class="status-badge badge-pass">PASS</span>'
      : '<span class="status-badge badge-fail">FAIL</span>';
  }

  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const id = `toast-${Date.now()}`;
    const bg = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';
    container.insertAdjacentHTML('beforeend', `
      <div id="${id}" class="toast align-items-center text-white ${bg} border-0 show" role="alert">
        <div class="d-flex">
          <div class="toast-body">${message}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>`);
    setTimeout(() => document.getElementById(id)?.remove(), 4000);
  }

  function spinner() {
    return `<div class="spinner-overlay"><div class="spinner-border spinner-border-sm me-2"></div> Loading...</div>`;
  }

  return { init, apiFetch, apiPost, statusBadge, passBadge, showToast, spinner, state, API_BASE };
})();
