/* History tab — full task list with copyable IDs and output preview */
const HistoryComponent = (() => {
  let filterType = '';
  let filterDoc  = '';

  function render() {
    const pane = document.getElementById('tab-history');
    pane.innerHTML = `
      <div class="d-flex gap-2 align-items-center mb-3 flex-wrap">
        <strong>Task History</strong>
        <select id="hist-type-filter" class="form-select form-select-sm" style="width:180px">
          <option value="">All types</option>
          <option value="summarize">Summarize</option>
          <option value="extract">Extract</option>
          <option value="qa">Q&amp;A</option>
        </select>
        <input id="hist-doc-filter" class="form-control form-control-sm" style="width:260px"
          placeholder="Filter by Document ID…" />
        <button id="hist-refresh" class="btn btn-sm btn-outline-secondary">Refresh</button>
        <small class="text-muted ms-auto">Click a row to load it in the Tasks tab. Click ID to copy.</small>
      </div>
      <div id="hist-area">${App.spinner()}</div>`;

    document.getElementById('hist-type-filter').addEventListener('change', e => {
      filterType = e.target.value; load();
    });
    document.getElementById('hist-doc-filter').addEventListener('input', e => {
      filterDoc = e.target.value.trim(); load();
    });
    document.getElementById('hist-refresh').addEventListener('click', load);
    load();
  }

  async function load() {
    const area = document.getElementById('hist-area');
    if (!area) return;
    area.innerHTML = App.spinner();
    try {
      const params = new URLSearchParams({ limit: 100 });
      if (filterType) params.append('task_type', filterType);
      if (filterDoc)  params.append('document_id', filterDoc);
      const tasks = await App.apiFetch(`/tasks?${params}`);
      area.innerHTML = tasks.length ? renderTable(tasks) : '<div class="alert alert-info">No tasks found.</div>';
      attachEvents();
    } catch (err) {
      area.innerHTML = `<div class="alert alert-danger">Failed: ${err.message}</div>`;
    }
  }

  function renderTable(tasks) {
    const rows = tasks.map(t => {
      const preview = (t.primary_output || '').replace(/</g,'&lt;').substring(0, 120);
      const question = t.question ? `<br><small class="text-muted">Q: ${t.question.substring(0,60)}</small>` : '';
      const err = t.error ? `<span class="text-danger" title="${t.error}"> ⚠</span>` : '';
      const ts = t.created_at ? new Date(t.created_at).toLocaleString() : '—';
      return `
        <tr class="hist-row" data-task-id="${t.id}" style="cursor:pointer">
          <td>
            <code class="copy-id" data-id="${t.id}" title="Click to copy full ID"
              style="cursor:copy;font-size:0.78rem">${t.id}</code>
          </td>
          <td><span class="badge bg-secondary">${t.task_type}</span>${err}</td>
          <td>${App.statusBadge(t.status)}</td>
          <td class="text-truncate-cell small text-muted" style="max-width:320px">
            ${preview || '<em>—</em>'}${question}
          </td>
          <td class="small text-muted" style="white-space:nowrap">${ts}</td>
        </tr>`;
    }).join('');

    return `
      <div class="card"><div class="card-body p-0">
        <table class="table table-hover table-sm mb-0">
          <thead><tr>
            <th>Task ID <small class="text-muted">(click to copy)</small></th>
            <th>Type</th><th>Status</th><th>Output preview</th><th>Created</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div></div>`;
  }

  function attachEvents() {
    // Copy ID on code click
    document.querySelectorAll('.copy-id').forEach(el => {
      el.addEventListener('click', e => {
        e.stopPropagation();
        navigator.clipboard.writeText(el.dataset.id).then(() => {
          App.showToast('Task ID copied to clipboard', 'success');
        });
      });
    });

    // Click row → switch to Tasks tab and pre-fill lookup
    document.querySelectorAll('.hist-row').forEach(row => {
      row.addEventListener('click', () => {
        const id = row.dataset.taskId;
        App.state.pendingTaskLoad = id;
        // switch tab
        document.querySelector('[data-tab="tasks"]').click();
      });
    });
  }

  return { render };
})();
