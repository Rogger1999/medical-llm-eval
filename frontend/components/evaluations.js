/* Evaluations tab component */
const EvaluationsComponent = (() => {
  function render() {
    const pane = document.getElementById('tab-evaluations');
    pane.innerHTML = `
      <div class="help-hint mb-3">
        <strong>🔬 Evaluations — Step 3.</strong>
        The system auto-selects a stratified 10 % sample of documents and runs 8 test categories on them.
        Each test returns PASS/FAIL + a score + detailed evidence.
        Checks combine rule-based logic, LLM-as-judge (OpenAI), and hybrid approaches.
        <span class="hint-step">Step 3 of 4</span>
      </div>
      <div class="row">
        <div class="col-md-3">
          <div class="form-section">
            <h6>Run Evaluation</h6>
            <div class="mb-2">
              <label class="form-label">Subset Size</label>
              <input id="eval-subset" type="number" class="form-control form-control-sm"
                value="" placeholder="Default (10%)"/>
            </div>
            <div class="mb-3">
              <label class="form-label">Categories</label>
              <div id="eval-categories">
                ${['ingest','retrieval','grounding','hallucination','numeric','abstention','adversarial','overclaiming']
                  .map(c => `<div class="form-check form-check-sm">
                    <input class="form-check-input cat-check" type="checkbox" value="${c}" id="cat-${c}" checked>
                    <label class="form-check-label" for="cat-${c}">${c}</label>
                  </div>`).join('')}
              </div>
            </div>
            <button id="btn-run-eval" class="btn btn-primary btn-sm w-100">Run Evaluation</button>
            <small class="text-muted d-block mt-1">Runs in background. Results appear in 30–120 s.</small>
          </div>
          <div class="form-section mt-2">
            <h6>Filter Results</h6>
            <select id="eval-doc-filter" class="form-select form-select-sm mb-2">
              <option value="">All documents</option>
            </select>
            <select id="eval-cat-filter" class="form-select form-select-sm">
              <option value="">All categories</option>
              ${['ingest','retrieval','grounding','hallucination','numeric','abstention','adversarial','overclaiming']
                .map(c => `<option value="${c}">${c}</option>`).join('')}
            </select>
          </div>
        </div>
        <div class="col-md-9">
          <div id="eval-result-area">${App.spinner()}</div>
        </div>
      </div>`;

    loadEvaluations();
    populateDocFilter();
    document.getElementById('btn-run-eval').addEventListener('click', handleRunEval);
    document.getElementById('eval-doc-filter').addEventListener('change', loadEvaluations);
    document.getElementById('eval-cat-filter').addEventListener('change', loadEvaluations);
  }

  async function loadEvaluations() {
    const area = document.getElementById('eval-result-area');
    if (!area) return;
    area.innerHTML = App.spinner();
    const docFilter = document.getElementById('eval-doc-filter')?.value || '';
    const catFilter = document.getElementById('eval-cat-filter')?.value || '';
    const params = new URLSearchParams();
    if (docFilter) params.append('document_id', docFilter);
    if (catFilter) params.append('category', catFilter);
    try {
      const evals = await App.apiFetch(`/evaluations?${params}`);
      area.innerHTML = renderEvalTable(evals);
      attachExpandEvents();
    } catch (err) {
      area.innerHTML = `<div class="alert alert-danger">Failed: ${err.message}</div>`;
    }
  }

  function renderEvalTable(evals) {
    if (!evals.length) return '<div class="alert alert-info">No evaluation results yet.</div>';
    const rows = evals.map(e => `
      <tr>
        <td><span class="text-monospace small">${e.document_id.substring(0,8)}...</span></td>
        <td><span class="badge bg-secondary">${e.eval_category}</span></td>
        <td>${App.passBadge(e.pass_fail)}</td>
        <td>${e.score !== null ? renderScoreCircle(e.score) : '—'}</td>
        <td><span class="badge bg-light text-dark">${e.evaluator_type}</span></td>
        <td>
          <button class="btn btn-xs btn-outline-secondary btn-sm py-0 btn-expand-detail"
            data-details='${escapeAttr(e.details || "{}")}'>Details</button>
        </td>
      </tr>
      <tr class="detail-row d-none" id="detail-${e.id}">
        <td colspan="6">
          <pre class="bg-light p-2 mb-0 small" style="max-height:200px;overflow-y:auto">${formatDetails(e.details)}</pre>
        </td>
      </tr>`).join('');
    return `<div class="card"><div class="card-body p-0">
      <table class="table table-sm table-hover mb-0">
        <thead><tr>
          <th>Document</th>
          <th>Category <span title="ingest=parsing quality, retrieval=chunk recall, grounding=citations, hallucination=invented facts, numeric=number accuracy, abstention=uncertainty handling, adversarial=injection/abuse, overclaiming=causation errors" style="cursor:help">ℹ️</span></th>
          <th>Result</th>
          <th>Score</th>
          <th>Type <span title="rule=deterministic rule, llm=LLM-as-judge (OpenAI), hybrid=rule + LLM" style="cursor:help">ℹ️</span></th>
          <th></th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table></div></div>`;
  }

  function renderScoreCircle(score) {
    const pct = Math.round(score * 100);
    const cls = score >= 0.7 ? 'score-high' : score >= 0.4 ? 'score-mid' : 'score-low';
    return `<span class="score-circle ${cls}">${pct}%</span>`;
  }

  function formatDetails(raw) {
    try { return JSON.stringify(JSON.parse(raw || '{}'), null, 2); }
    catch { return raw || ''; }
  }

  function escapeAttr(s) { return s.replace(/'/g, '&#39;').replace(/"/g, '&quot;'); }

  function attachExpandEvents() {
    document.querySelectorAll('.btn-expand-detail').forEach(btn => {
      btn.addEventListener('click', e => {
        const row = e.target.closest('tr');
        const detailRow = row?.nextElementSibling;
        detailRow?.classList.toggle('d-none');
      });
    });
  }

  async function handleRunEval() {
    const subsetInput = document.getElementById('eval-subset').value;
    const checked = [...document.querySelectorAll('.cat-check:checked')].map(c => c.value);
    const body = { force_rerun: false };
    if (subsetInput) body.subset_size = parseInt(subsetInput);
    if (checked.length < 8) body.categories = checked;
    try {
      await App.apiPost('/evaluations/run', body);
      App.showToast('Evaluation run started', 'success');
      setTimeout(loadEvaluations, 3000);
    } catch (err) { App.showToast(`Failed: ${err.message}`, 'error'); }
  }

  async function populateDocFilter() {
    try {
      const data = await App.apiFetch('/documents?page_size=100');
      const sel = document.getElementById('eval-doc-filter');
      if (!sel) return;
      data.items.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.id;
        const title = (d.title || 'Untitled').substring(0, 80);
        const year  = d.year ? ` (${d.year})` : '';
        const id    = d.id.substring(0, 8);
        opt.textContent = `${title}${year} — ${id}`;
        opt.title = d.title || d.id;
        sel.appendChild(opt);
      });
    } catch {}
  }

  return { render };
})();
