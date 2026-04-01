/* Documents tab component */
const DocumentsComponent = (() => {
  let currentPage = 1;
  let statusFilter = '';

  function render() {
    const pane = document.getElementById('tab-documents');
    pane.innerHTML = `
      <div class="help-hint mb-3">
        <strong>📄 Documents — Step 1.</strong>
        Download scientific papers from Europe PMC, then process them (PDF parsing + chunking).
        Only documents with status <code>chunked</code> can be used in <em>Tasks</em> and <em>Evaluations</em>.
        <span class="hint-step">Step 1 of 4</span>
      </div>
      <div class="row">
        <div class="col-md-4">
          <div class="form-section">
            <h6>Download Documents</h6>
            <div class="mb-2">
              <label class="form-label">Topic / Query</label>
              <input id="dl-topic" class="form-control form-control-sm"
                value="malnutrition undernutrition children interventions" />
            </div>
            <div class="mb-3">
              <label class="form-label">Max Results</label>
              <input id="dl-max" type="number" class="form-control form-control-sm" value="20" min="1" max="200" />
            </div>
            <button id="btn-download" class="btn btn-primary btn-sm w-100">Download</button>
            <small class="text-muted d-block mt-1">Download runs in the background. Refresh the list in a few seconds.</small>
          </div>
          <div class="form-section mt-2">
            <h6>Filter &amp; Process</h6>
            <small class="text-muted d-block mb-2">After downloading, click <strong>Process All Downloaded</strong> to parse PDFs and build chunks.</small>
            <select id="status-filter" class="form-select form-select-sm">
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="downloaded">Downloaded</option>
              <option value="parsed">Parsed</option>
              <option value="chunked">Chunked</option>
              <option value="failed">Failed</option>
            </select>
            <button id="btn-batch-process" class="btn btn-outline-secondary btn-sm w-100 mt-2">
              Process All Downloaded
            </button>
          </div>
        </div>
        <div class="col-md-8">
          <div id="doc-list-area">${App.spinner()}</div>
        </div>
      </div>`;

    document.getElementById('btn-download').addEventListener('click', handleDownload);
    document.getElementById('status-filter').addEventListener('change', e => {
      statusFilter = e.target.value;
      currentPage = 1;
      loadDocuments();
    });
    document.getElementById('btn-batch-process').addEventListener('click', handleBatchProcess);
    loadDocuments();
  }

  async function loadDocuments() {
    const area = document.getElementById('doc-list-area');
    if (!area) return;
    area.innerHTML = App.spinner();
    try {
      const params = new URLSearchParams({ page: currentPage, page_size: 20 });
      if (statusFilter) params.append('status', statusFilter);
      const data = await App.apiFetch(`/documents?${params}`);
      App.state.documents = data.items;
      area.innerHTML = renderDocTable(data);
      attachDocEvents(data);
    } catch (err) {
      area.innerHTML = `<div class="alert alert-danger">Failed to load documents: ${err.message}</div>`;
    }
  }

  function renderDocTable(data) {
    if (!data.items.length) return '<div class="alert alert-info">No documents found.</div>';
    const rows = data.items.map(d => `
      <tr data-doc-id="${d.id}" class="doc-row">
        <td class="text-truncate-cell">${d.title || '<em>No title</em>'}</td>
        <td>${d.year || '—'}</td>
        <td>${App.statusBadge(d.status)}</td>
        <td>
          <button class="btn btn-xs btn-outline-primary btn-sm py-0 btn-view-doc" data-id="${d.id}">View</button>
          <button class="btn btn-xs btn-outline-secondary btn-sm py-0 btn-process-doc" data-id="${d.id}">Process</button>
        </td>
      </tr>`).join('');
    const paging = renderPaging(data);
    return `
      <div class="card"><div class="card-body p-0">
        <div class="d-flex justify-content-between align-items-center px-3 py-2">
          <small class="text-muted">Total: ${data.total} documents</small>
        </div>
        <table class="table table-hover table-sm mb-0">
          <thead><tr><th>Title</th><th>Year</th><th>Status <span title="pending=queued, downloaded=PDF saved, parsed=text extracted, chunked=ready for LLM, failed=error" style="cursor:help">ℹ️</span></th><th>Actions</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div></div>
      ${paging}`;
  }

  function renderPaging(data) {
    const totalPages = Math.ceil(data.total / data.page_size);
    if (totalPages <= 1) return '';
    return `<div class="d-flex gap-2 mt-2">
      <button class="btn btn-sm btn-outline-secondary" id="btn-prev" ${data.page <= 1 ? 'disabled' : ''}>Prev</button>
      <span class="align-self-center small">Page ${data.page} / ${totalPages}</span>
      <button class="btn btn-sm btn-outline-secondary" id="btn-next" ${data.page >= totalPages ? 'disabled' : ''}>Next</button>
    </div>`;
  }

  function attachDocEvents(data) {
    document.querySelectorAll('.btn-view-doc').forEach(btn => {
      btn.addEventListener('click', e => { e.stopPropagation(); showDocDetail(e.target.dataset.id); });
    });
    document.querySelectorAll('.btn-process-doc').forEach(btn => {
      btn.addEventListener('click', e => { e.stopPropagation(); processDoc(e.target.dataset.id); });
    });
    document.getElementById('btn-prev')?.addEventListener('click', () => { currentPage--; loadDocuments(); });
    document.getElementById('btn-next')?.addEventListener('click', () => { currentPage++; loadDocuments(); });
  }

  async function handleDownload() {
    const topic = document.getElementById('dl-topic').value.trim();
    const max = parseInt(document.getElementById('dl-max').value);
    try {
      await App.apiPost('/documents/download', { topic, max_results: max });
      App.showToast('Download job started', 'success');
      setTimeout(loadDocuments, 2000);
    } catch (err) { App.showToast(`Download failed: ${err.message}`, 'error'); }
  }

  async function processDoc(docId) {
    try {
      await App.apiPost(`/documents/${docId}/process`, {});
      App.showToast('Processing started', 'success');
      setTimeout(loadDocuments, 1500);
    } catch (err) { App.showToast(`Process failed: ${err.message}`, 'error'); }
  }

  async function handleBatchProcess() {
    try {
      await App.apiPost('/documents/process-batch', {});
      App.showToast('Batch processing started', 'success');
    } catch (err) { App.showToast(`Batch failed: ${err.message}`, 'error'); }
  }

  async function showDocDetail(docId) {
    try {
      const doc = await App.apiFetch(`/documents/${docId}`);
      document.getElementById('docModalTitle').textContent = doc.title || 'Document Detail';
      document.getElementById('docModalBody').innerHTML = `
        <dl class="row mb-0">
          <dt class="col-sm-3">Status</dt><dd class="col-sm-9">${App.statusBadge(doc.status)}</dd>
          <dt class="col-sm-3">Authors</dt><dd class="col-sm-9">${doc.authors || '—'}</dd>
          <dt class="col-sm-3">Journal</dt><dd class="col-sm-9">${doc.journal || '—'} (${doc.year || '—'})</dd>
          <dt class="col-sm-3">DOI</dt><dd class="col-sm-9">${doc.doi || '—'}</dd>
          <dt class="col-sm-3">Abstract</dt>
          <dd class="col-sm-9"><small>${doc.abstract || 'N/A'}</small></dd>
        </dl>`;
      new bootstrap.Modal(document.getElementById('docModal')).show();
    } catch (err) { App.showToast(`Failed to load doc: ${err.message}`, 'error'); }
  }

  return { render };
})();
