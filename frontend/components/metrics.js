/* Metrics dashboard component */
const MetricsComponent = (() => {
  function render() {
    const pane = document.getElementById('tab-metrics');
    pane.innerHTML = `
      <div class="help-hint mb-3">
        <strong>📊 Metrics — Step 4.</strong>
        Aggregate view of all evaluation results. Overall pass rate, per-category breakdown,
        and a list of the worst failures for manual review.
        The Weighted Score applies a risk multiplier per category — hallucination and overclaiming count 2×.
        <span class="hint-step">Step 4 of 4</span>
      </div>
      <div id="metrics-area">${App.spinner()}</div>
      <hr class="my-4" />
      <h5 class="mb-3">Recent Failures <small class="text-muted fs-6">(last 20)</small></h5>
      <div id="fail-area">${App.spinner()}</div>`;
    loadMetrics();
    loadFailCases();
  }

  async function loadMetrics() {
    const area = document.getElementById('metrics-area');
    if (!area) return;
    try {
      const data = await App.apiFetch('/metrics/summary');
      area.innerHTML = renderMetrics(data);
    } catch (err) {
      area.innerHTML = `<div class="alert alert-danger">Failed: ${err.message}</div>`;
    }
  }

  function renderMetrics(data) {
    const overallClass = data.overall_pass_rate >= 0.7 ? 'text-success' :
                         data.overall_pass_rate >= 0.4 ? 'text-warning' : 'text-danger';
    const overallPct = Math.round((data.overall_pass_rate || 0) * 100);
    const weightedPct = data.weighted_score !== null
      ? Math.round((data.weighted_score || 0) * 100) : null;

    const kpiCards = `
      <div class="row mb-4">
        <div class="col-md-3">
          <div class="card text-center p-3">
            <div class="h2 fw-bold ${overallClass}">${overallPct}%</div>
            <div class="text-muted small">Overall Pass Rate</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card text-center p-3">
            <div class="h2 fw-bold">${data.total_evaluations}</div>
            <div class="text-muted small">Total Evaluations</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card text-center p-3">
            <div class="h2 fw-bold text-success">${data.total_passed}</div>
            <div class="text-muted small">Passed</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card text-center p-3">
            <div class="h2 fw-bold text-danger">${data.total_failed}</div>
            <div class="text-muted small">Failed</div>
          </div>
        </div>
      </div>`;

    const cats = Object.values(data.by_category || {});
    if (!cats.length) return kpiCards + '<div class="alert alert-info">No category data yet.</div>';

    const bars = cats.map(c => {
      const pct = Math.round((c.pass_rate || 0) * 100);
      const barClass = pct >= 70 ? 'metric-bar-pass' : pct >= 40 ? 'metric-bar-warn' : 'metric-bar-fail';
      const avgScore = c.avg_score !== null ? `${Math.round((c.avg_score || 0)*100)}%` : '—';
      return `
        <tr>
          <td><span class="badge bg-secondary">${c.category}</span></td>
          <td>${c.total}</td>
          <td class="text-success">${c.passed}</td>
          <td class="text-danger">${c.failed}</td>
          <td style="min-width:140px">
            <div class="metric-bar-container">
              <div class="metric-bar-fill ${barClass}" style="width:${pct}%"></div>
            </div>
          </td>
          <td class="fw-bold">${pct}%</td>
          <td>${avgScore}</td>
        </tr>`;
    }).join('');

    const table = `
      <div class="card"><div class="card-header">Category Breakdown</div>
        <div class="card-body p-0">
          <table class="table table-sm mb-0">
            <thead><tr>
              <th>Category</th><th>Total</th><th>Pass</th><th>Fail</th>
              <th>Pass Rate</th><th>%</th><th>Avg Score</th>
            </tr></thead>
            <tbody>${bars}</tbody>
          </table>
        </div>
      </div>`;

    const wsCard = weightedPct !== null ? `
      <div class="alert alert-secondary mt-2">
        Weighted Score (risk-adjusted): <strong>${weightedPct}%</strong>
      </div>` : '';

    return kpiCards + table + wsCard;
  }

  async function loadFailCases() {
    const area = document.getElementById('fail-area');
    if (!area) return;
    try {
      const cases = await App.apiFetch('/metrics/fail-cases?limit=20');
      area.innerHTML = renderFailCases(cases);
    } catch (err) {
      area.innerHTML = `<div class="alert alert-danger">Failed: ${err.message}</div>`;
    }
  }

  function renderFailCases(cases) {
    if (!cases.length) return '<div class="alert alert-success">No failures found!</div>';
    const rows = cases.map(c => `
      <tr>
        <td class="text-truncate-cell">${c.document_title || c.document_id}</td>
        <td><span class="badge bg-secondary">${c.category}</span></td>
        <td>${c.score !== null ? Math.round((c.score||0)*100)+'%' : '—'}</td>
        <td class="text-truncate-cell small text-muted">${c.details ? c.details.substring(0,80)+'...' : ''}</td>
      </tr>`).join('');
    return `
      <div class="card"><div class="card-body p-0">
        <table class="table table-sm table-hover mb-0">
          <thead><tr><th>Document</th><th>Category</th><th>Score</th><th>Details</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div></div>`;
  }

  return { render };
})();
