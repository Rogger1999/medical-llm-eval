/* Tasks tab component */
const TasksComponent = (() => {
  function render() {
    const pane = document.getElementById('tab-tasks');
    pane.innerHTML = `
      <div class="help-hint mb-3">
        <strong>🤖 Tasks — Step 2.</strong>
        Run an LLM task on a specific document. Claude (primary) processes the document;
        OpenAI (checker) independently verifies the output. Both results appear side by side.
        <strong>Document must have status <code>chunked</code>.</strong>
        <span class="hint-step">Step 2 of 4</span>
      </div>
      <div class="row">
        <div class="col-md-4">
          <div class="form-section">
            <h6>Run a Task</h6>
            <div class="mb-2">
              <label class="form-label">Document ID</label>
              <select id="task-doc-select" class="form-select form-select-sm">
                <option value="">Select document...</option>
              </select>
            </div>
            <div class="mb-2">
              <label class="form-label">Task Type</label>
              <select id="task-type" class="form-select form-select-sm">
                <option value="summarize">Summarize — structured summary of the paper</option>
                <option value="extract">Extract — structured data fields (population, outcomes…)</option>
                <option value="qa">Q&amp;A — answer a question grounded in the text</option>
              </select>
            </div>
            <div id="qa-question-row" class="mb-2 d-none">
              <label class="form-label">Question</label>
              <input id="task-question" class="form-control form-control-sm"
                placeholder="What intervention was used?" />
            </div>
            <button id="btn-run-task" class="btn btn-primary btn-sm w-100">Run Task</button>
            <button id="btn-summarize-all" class="btn btn-outline-primary btn-sm w-100 mt-2">Summarize All Docs</button>
            <small class="text-muted d-block mt-1">Calls Claude API + OpenAI API — may take 10–30 s per doc.</small>
          </div>
          <div class="form-section mt-2">
            <h6>Load a Previous Task</h6>
            <select id="task-history-select" class="form-select form-select-sm mb-2">
              <option value="">— select a past task —</option>
            </select>
            <button id="btn-get-task" class="btn btn-outline-secondary btn-sm w-100">Load</button>
          </div>
        </div>
        <div class="col-md-8">
          <div id="task-result-area"><div class="text-muted p-3">Run a task or click one below to load it.</div></div>
          <div class="mt-3">
            <div class="d-flex justify-content-between align-items-center mb-1">
              <strong class="small">Recent Tasks</strong>
              <button id="btn-refresh-history" class="btn btn-xs btn-outline-secondary btn-sm py-0">Refresh</button>
            </div>
            <div id="task-mini-history">${App.spinner()}</div>
          </div>
        </div>
      </div>`;

    populateDocDropdown();

    // If arriving from History tab, auto-load the task
    if (App.state.pendingTaskLoad) {
      const id = App.state.pendingTaskLoad;
      App.state.pendingTaskLoad = null;
      App.apiFetch(`/tasks/${id}`).then(renderTaskResult).catch(() => {});
    }

    document.getElementById('task-type').addEventListener('change', e => {
      const qaRow = document.getElementById('qa-question-row');
      qaRow.classList.toggle('d-none', e.target.value !== 'qa');
    });
    document.getElementById('btn-run-task').addEventListener('click', handleRunTask);
    document.getElementById('btn-summarize-all').addEventListener('click', handleSummarizeAll);
    document.getElementById('btn-get-task').addEventListener('click', handleGetTask);
    document.getElementById('btn-refresh-history').addEventListener('click', () => {
      loadMiniHistory();
      populateHistoryDropdown();
    });
    loadMiniHistory();
    populateHistoryDropdown();
  }

  function populateDocDropdown() {
    const sel = document.getElementById('task-doc-select');
    if (!sel) return;
    function makeDocOption(doc) {
      const opt = document.createElement('option');
      opt.value = doc.id;
      const title = (doc.title || 'Untitled').substring(0, 80);
      const year  = doc.year ? ` (${doc.year})` : '';
      const id    = doc.id.substring(0, 8);
      opt.textContent = `${title}${year} — ${id}`;
      opt.title = doc.title || doc.id;
      return opt;
    }
    App.state.documents.forEach(doc => sel.appendChild(makeDocOption(doc)));
    if (!App.state.documents.length) {
      App.apiFetch('/documents?page_size=100').then(data => {
        data.items.forEach(doc => sel.appendChild(makeDocOption(doc)));
      }).catch(() => {});
    }
  }

  async function handleRunTask() {
    const docId = document.getElementById('task-doc-select').value;
    const taskType = document.getElementById('task-type').value;
    const question = document.getElementById('task-question').value.trim();
    if (!docId) { App.showToast('Please select a document', 'error'); return; }

    const area = document.getElementById('task-result-area');
    area.innerHTML = App.spinner();

    try {
      let result;
      if (taskType === 'summarize') {
        result = await App.apiPost('/tasks/summarize', { document_id: docId });
      } else if (taskType === 'extract') {
        result = await App.apiPost('/tasks/extract', { document_id: docId });
      } else {
        if (!question) { App.showToast('Please enter a question', 'error'); return; }
        result = await App.apiPost('/tasks/qa', { document_id: docId, question });
      }
      renderTaskResult(result);
      App.showToast('Task completed', 'success');
      loadMiniHistory();
      populateHistoryDropdown();
    } catch (err) {
      area.innerHTML = `<div class="alert alert-danger">Task failed: ${err.message}</div>`;
      App.showToast('Task failed', 'error');
    }
  }

  async function loadMiniHistory() {
    const el = document.getElementById('task-mini-history');
    if (!el) return;
    try {
      const tasks = await App.apiFetch('/tasks?limit=30');
      if (!tasks.length) { el.innerHTML = '<div class="text-muted small p-2">No tasks yet.</div>'; return; }
      const rows = tasks.map(t => {
        const ts = t.created_at ? new Date(t.created_at).toLocaleString() : '';
        const preview = (t.primary_output || t.error || '').substring(0, 60).replace(/</g, '&lt;');
        return `
          <tr class="mini-task-row" data-id="${t.id}" style="cursor:pointer" title="Click to load">
            <td><code class="small" style="font-size:0.75rem">${t.id}</code></td>
            <td><span class="badge bg-secondary">${t.task_type}</span></td>
            <td>${App.statusBadge(t.status)}</td>
            <td class="text-muted small text-truncate" style="max-width:180px">${preview}</td>
            <td class="text-muted small" style="white-space:nowrap">${ts}</td>
          </tr>`;
      }).join('');
      el.innerHTML = `
        <div style="max-height:300px;overflow-y:auto">
          <table class="table table-hover table-sm mb-0" style="font-size:0.82rem">
            <thead class="table-light"><tr>
              <th>ID <small class="text-muted">(click row to load)</small></th>
              <th>Type</th><th>Status</th><th>Preview</th><th>Created</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
      el.querySelectorAll('.mini-task-row').forEach(row => {
        row.addEventListener('click', async () => {
          const task = await App.apiFetch(`/tasks/${row.dataset.id}`);
          renderTaskResult(task);
          window.scrollTo(0, 0);
        });
      });
    } catch (err) {
      el.innerHTML = `<div class="alert alert-danger small p-2">Failed: ${err.message}</div>`;
    }
  }

  async function handleSummarizeAll() {
    const btn = document.getElementById('btn-summarize-all');
    btn.disabled = true;
    btn.textContent = 'Starting…';
    try {
      await App.apiPost('/tasks/summarize-all', {});
      App.showToast('Batch summarisation started — check History tab for progress', 'success');
    } catch (err) {
      App.showToast(`Failed: ${err.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Summarize All Docs';
    }
  }

  async function handleGetTask() {
    const sel = document.getElementById('task-history-select');
    const taskId = sel ? sel.value : '';
    if (!taskId) { App.showToast('Select a task first', 'error'); return; }
    try {
      const result = await App.apiFetch(`/tasks/${taskId}`);
      renderTaskResult(result);
    } catch (err) {
      App.showToast(`Task not found: ${err.message}`, 'error');
    }
  }

  async function populateHistoryDropdown() {
    const sel = document.getElementById('task-history-select');
    if (!sel) return;
    try {
      const tasks = await App.apiFetch('/tasks?limit=100');
      tasks.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.id;
        const ts = t.created_at ? new Date(t.created_at).toLocaleString() : '';
        const preview = (t.primary_output || t.error || '—').substring(0, 50);
        opt.textContent = `${t.task_type.toUpperCase()} | ${ts} | ${preview}`;
        opt.title = t.id;
        sel.appendChild(opt);
      });
    } catch {}
  }

  function renderTaskResult(task) {
    const area = document.getElementById('task-result-area');
    const statusBadge = App.statusBadge(task.status);
    const question = task.question ? `<div class="mb-2"><strong>Question:</strong> ${task.question}</div>` : '';
    const ts = task.created_at ? new Date(task.created_at).toLocaleString() : '';
    area.innerHTML = `
      <div class="card">
        <div class="card-header">
          <div class="d-flex justify-content-between align-items-start">
            <span class="fw-bold">Task: ${task.task_type} ${statusBadge}</span>
            <small class="text-muted">${ts}</small>
          </div>
          <div class="mt-1 d-flex align-items-center gap-2">
            <code style="font-size:0.8rem;user-select:all">${task.id}</code>
            <button class="btn btn-xs btn-outline-secondary btn-sm py-0 px-1"
              onclick="navigator.clipboard.writeText('${task.id}').then(()=>App.showToast('Copied','success'))">Copy</button>
          </div>
        </div>
        <div class="card-body">
          ${question}
          <div class="row">
            <div class="col-md-6">
              <h6 class="text-muted">Primary Output (${task.primary_model || 'Claude'})</h6>
              <div class="output-pane">${task.primary_output || '<em>No output</em>'}</div>
            </div>
            <div class="col-md-6">
              <h6 class="text-muted">Checker Output (${task.checker_model || 'OpenAI'})</h6>
              <div class="output-pane">${task.checker_output || '<em>No checker output</em>'}</div>
            </div>
          </div>
          ${task.error ? `<div class="alert alert-danger mt-2">Error: ${task.error}</div>` : ''}
        </div>
      </div>`;
  }

  return { render };
})();
