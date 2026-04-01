/* Guide tab — full system documentation in English */
const HelpComponent = (() => {
  function render() {
    const pane = document.getElementById('tab-help');
    pane.innerHTML = `
<div class="row justify-content-center">
<div class="col-lg-9">

<h3 class="mb-1">📖 System Guide — Medical RAG Evaluator</h3>
<p class="text-muted mb-4">
  A prototype for evaluating hallucinations, grounding quality, extraction reliability, and
  overclaiming behaviour of LLMs on medical/scientific literature.<br>
  Default topic: <strong>malnutrition / undernutrition interventions in children</strong>
  (severe acute malnutrition, RUTF, micronutrient supplementation, low-resource settings).
</p>

<!-- ARCHITECTURE -->
<div class="card mb-4">
  <div class="card-header fw-bold">🏗️ System Architecture</div>
  <div class="card-body">
    <p>
      The system is intentionally split into <strong>many small files</strong> (&lt;200 lines each)
      to keep future edits cheap and safe. It uses:
    </p>
    <ul>
      <li><strong>FastAPI + Uvicorn</strong> — async REST backend</li>
      <li><strong>SQLite + SQLAlchemy (async)</strong> — local storage for documents, tasks, evaluations</li>
      <li><strong>Europe PMC REST API</strong> — source of open-access scientific papers</li>
      <li><strong>Claude (Anthropic)</strong> — primary LLM for summarisation, extraction, grounded Q&amp;A</li>
      <li><strong>OpenAI GPT</strong> — independent checker / LLM-as-judge for all evaluation categories</li>
      <li><strong>BM25 keyword retrieval</strong> — selects the most relevant chunks for each query</li>
      <li><strong>Vanilla JS + Bootstrap 5</strong> — minimal frontend served as static files</li>
    </ul>
    <p class="mb-0">
      All configuration lives in <code>config.yaml</code>. API keys are set directly in that file
      (or via environment variables). Restart the server after any config change.
    </p>
  </div>
</div>

<!-- DATA FLOW -->
<div class="card mb-4">
  <div class="card-header fw-bold">🔄 End-to-End Data Flow</div>
  <div class="card-body">
    <ol class="mb-0">
      <li class="mb-2">
        <strong>Download</strong> — You provide a topic query. The backend calls Europe PMC,
        fetches metadata + PDFs for up to N papers, deduplicates by source ID, and stores
        everything locally. Documents start in state <code>pending</code> → <code>downloaded</code>.
      </li>
      <li class="mb-2">
        <strong>Parse</strong> — PyPDF2 extracts plain text from each PDF.
        If extraction fails or yields &lt;100 chars, the system falls back to the abstract.
        State advances to <code>parsed</code>.
      </li>
      <li class="mb-2">
        <strong>Chunk</strong> — Text is split into overlapping ~512-token windows
        (sentence boundaries are preserved, 64-token overlap). Chunks are saved as JSON
        alongside the parsed text. State advances to <code>chunked</code>.
      </li>
      <li class="mb-2">
        <strong>LLM Task</strong> — For a chosen document, the system retrieves the top-k
        most relevant chunks via BM25, builds a prompt, calls Claude, then calls OpenAI
        to check/critique the output. Both responses are stored in the Task record.
      </li>
      <li class="mb-2">
        <strong>Evaluate</strong> — A stratified 10 % subset of documents is selected
        (prioritising failures, spread across years/journals). Each document runs through
        all 8 evaluators. Results are stored as individual Evaluation records.
      </li>
      <li>
        <strong>Metrics</strong> — The aggregator computes pass rates, average scores,
        and a risk-weighted composite score across all categories.
      </li>
    </ol>
  </div>
</div>

<!-- TAB: DOCUMENTS -->
<div class="card mb-4">
  <div class="card-header fw-bold">📄 Tab: Documents</div>
  <div class="card-body">
    <h6>Left panel — Download Documents</h6>
    <ul>
      <li><strong>Topic / Query</strong> — Keywords sent to Europe PMC (English).
        Default: <em>malnutrition undernutrition children interventions</em>.
        Keep it focused — the narrower the topic, the more consistent the evaluation.</li>
      <li><strong>Max Results</strong> — How many papers to fetch (1–200).
        Start with 10–20 for a quick test run.</li>
      <li><strong>Download button</strong> — Fires a background job. A green toast confirms it started.
        Refresh the document list after 5–30 seconds.</li>
    </ul>
    <h6 class="mt-3">Left panel — Filter &amp; Process</h6>
    <ul>
      <li><strong>Status filter</strong> — Show only documents in a given state.</li>
      <li><strong>Process All Downloaded</strong> — Batch-parses all <code>downloaded</code> documents
        and creates chunks. Run this once after every download session.</li>
    </ul>
    <h6 class="mt-3">Document status lifecycle</h6>
    <table class="table table-sm table-bordered">
      <thead><tr><th>Status</th><th>Meaning</th><th>Next action</th></tr></thead>
      <tbody>
        <tr><td><span class="status-badge badge-pending">pending</span></td>
            <td>Queued; download in progress</td><td>Wait, then refresh</td></tr>
        <tr><td><span class="status-badge badge-downloaded">downloaded</span></td>
            <td>PDF saved to disk</td><td>Click <strong>Process</strong> or <strong>Process All Downloaded</strong></td></tr>
        <tr><td><span class="status-badge badge-parsed">parsed</span></td>
            <td>Text extracted from PDF</td><td>Chunking runs automatically next</td></tr>
        <tr><td><span class="status-badge badge-chunked">chunked</span></td>
            <td>Split into chunks — ready for LLM tasks</td><td>Go to <em>Tasks</em></td></tr>
        <tr><td><span class="status-badge badge-failed">failed</span></td>
            <td>Error (corrupt PDF, timeout, empty text)</td><td>Retry or skip</td></tr>
      </tbody>
    </table>
    <p class="mb-0">
      <strong>View</strong> opens a detail modal (authors, abstract, DOI, journal, year).<br>
      <strong>Process</strong> runs parse + chunk for that single document only.
    </p>
  </div>
</div>

<!-- TAB: TASKS -->
<div class="card mb-4">
  <div class="card-header fw-bold">🤖 Tab: Tasks</div>
  <div class="card-body">
    <p>Run an LLM task on one document at a time.
      <strong>The document must have status <code>chunked</code>.</strong>
      Relevant chunks are retrieved via BM25 and injected into the prompt as context.</p>
    <h6>Task types</h6>
    <table class="table table-sm table-bordered">
      <thead><tr><th>Type</th><th>What Claude does</th><th>Output</th></tr></thead>
      <tbody>
        <tr>
          <td><strong>Summarize</strong></td>
          <td>Produces a structured narrative summary of the paper</td>
          <td>Paragraph covering background, method, findings, conclusions</td>
        </tr>
        <tr>
          <td><strong>Extract</strong></td>
          <td>Extracts structured fields from the paper</td>
          <td>JSON: population, intervention, comparator, outcomes, numeric values, adverse events, conclusion, evidence snippets</td>
        </tr>
        <tr>
          <td><strong>Q&amp;A</strong></td>
          <td>Answers your specific question using only the document text</td>
          <td>Answer with inline citations to source chunks</td>
        </tr>
      </tbody>
    </table>
    <h6 class="mt-3">Reading the results</h6>
    <ul>
      <li><strong>Primary Output (Claude)</strong> — the main model's response.</li>
      <li><strong>Checker Output (OpenAI)</strong> — independent review: flags unsupported claims,
        numeric mismatches, or hedging failures.</li>
      <li>If both models agree → output is likely reliable.</li>
      <li>If they diverge → inspect the details; likely a hallucination or citation gap.</li>
    </ul>
    <p class="mb-0 text-muted">
      <strong>Lookup Task by ID</strong> — paste any task UUID to reload a previous result.
    </p>
  </div>
</div>

<!-- TAB: EVALUATIONS -->
<div class="card mb-4">
  <div class="card-header fw-bold">🔬 Tab: Evaluations</div>
  <div class="card-body">
    <p>Automated quality testing across 8 risk categories.
      The system selects a stratified ~10 % sample (min 5, max 50 documents),
      prioritising documents that already have known failures and spreading across
      publication years and journals.</p>
    <h6>The 8 evaluation categories</h6>
    <table class="table table-sm table-bordered">
      <thead><tr><th>Category</th><th>What it tests</th><th>Method</th><th>Risk weight</th></tr></thead>
      <tbody>
        <tr><td><strong>ingest</strong></td>
            <td>Parsing quality — empty text, too short, missing metadata, duplicates</td>
            <td>Rule</td><td>1×</td></tr>
        <tr><td><strong>retrieval</strong></td>
            <td>Whether retrieved chunks contain the keywords needed to answer</td>
            <td>Rule (BM25 recall@k)</td><td>1.5×</td></tr>
        <tr><td><strong>grounding</strong></td>
            <td>Every key claim is backed by a source chunk citation</td>
            <td>LLM judge (OpenAI)</td><td>2×</td></tr>
        <tr><td><strong>hallucination</strong></td>
            <td>Model does not invent facts, names, or numbers absent from the source</td>
            <td>LLM judge (OpenAI)</td><td>2×</td></tr>
        <tr><td><strong>numeric</strong></td>
            <td>Sample sizes, percentages, dosages, and durations match the source text exactly</td>
            <td>Hybrid (regex + LLM)</td><td>1.5×</td></tr>
        <tr><td><strong>abstention</strong></td>
            <td>When evidence is weak or missing, the model says so instead of fabricating</td>
            <td>Rule (hedging phrases)</td><td>1×</td></tr>
        <tr><td><strong>adversarial</strong></td>
            <td>Prompt injection in chunks is ignored; unrelated questions get a refusal</td>
            <td>Rule (regex patterns)</td><td>1.5×</td></tr>
        <tr><td><strong>overclaiming</strong></td>
            <td>Correlation not presented as causation; animal evidence not generalised to humans</td>
            <td>LLM judge (OpenAI)</td><td>2×</td></tr>
      </tbody>
    </table>
    <h6 class="mt-3">Reading the results table</h6>
    <ul>
      <li><span class="status-badge badge-pass">PASS</span> — score ≥ 0.6 or rule satisfied.</li>
      <li><span class="status-badge badge-fail">FAIL</span> — click <strong>Details</strong>
        to see exactly which claims failed, which numbers mismatched, or which injection was detected.</li>
      <li><strong>Score circle</strong>: green ≥ 70 %, yellow 40–70 %, red &lt; 40 %.</li>
      <li><strong>Type</strong>: <code>rule</code> = deterministic; <code>llm</code> = OpenAI judge;
        <code>hybrid</code> = rule first, then LLM for ambiguous cases.</li>
    </ul>
    <p class="mb-0 text-muted">
      Leave <em>Subset Size</em> blank to use the default 10 % auto-selection.
      Uncheck categories to run only a specific subset of tests.
    </p>
  </div>
</div>

<!-- TAB: METRICS -->
<div class="card mb-4">
  <div class="card-header fw-bold">📊 Tab: Metrics</div>
  <div class="card-body">
    <h6>KPI cards (top row)</h6>
    <ul>
      <li><strong>Overall Pass Rate</strong> — percentage of all tests that passed. Target: &gt;70 %.</li>
      <li><strong>Total Evaluations</strong> — cumulative count of individual test runs.</li>
      <li><strong>Passed / Failed</strong> — absolute counts.</li>
    </ul>
    <h6 class="mt-3">Category Breakdown table</h6>
    <p>Per-category pass rate with inline bar chart.
      Rows in red indicate categories where the LLM is systematically failing —
      these are the areas to investigate first.</p>
    <h6 class="mt-3">Weighted Score</h6>
    <p>A risk-adjusted composite score. Categories with higher medical risk
      (hallucination, grounding, overclaiming) count 2× in the final score.
      Low-risk categories (ingest, abstention) count 1×.
      Higher = safer system.</p>
    <h6 class="mt-3">Recent Failures</h6>
    <p class="mb-0">
      The 20 most recent failed evaluations with document title, category,
      score, and a short description. Use this list to pick documents for
      manual inspection in the <em>Tasks</em> tab.
    </p>
  </div>
</div>

<!-- QUICK START -->
<div class="card mb-4">
  <div class="card-header fw-bold">⚡ Quick Start</div>
  <div class="card-body">
    <ol>
      <li class="mb-1">Go to <strong>Documents</strong>. Set Max Results = 10. Click <strong>Download</strong>.</li>
      <li class="mb-1">Wait ~15 s, then click <strong>Process All Downloaded</strong>.</li>
      <li class="mb-1">Wait for documents to reach status <code>chunked</code> (refresh the list).</li>
      <li class="mb-1">Go to <strong>Tasks</strong>. Select a document → <em>Summarize</em> → <strong>Run Task</strong>.</li>
      <li class="mb-1">Read the Claude output and the OpenAI checker side by side.</li>
      <li class="mb-1">Go to <strong>Evaluations</strong>. Click <strong>Run Evaluation</strong>. Wait ~60 s.</li>
      <li>Go to <strong>Metrics</strong> to see pass rates and failures.</li>
    </ol>
  </div>
</div>

<!-- CONFIG -->
<div class="card mb-4">
  <div class="card-header fw-bold">🔧 Key Configuration (config.yaml)</div>
  <div class="card-body">
    <table class="table table-sm table-bordered mb-0">
      <thead><tr><th>Section</th><th>What to change</th></tr></thead>
      <tbody>
        <tr><td><code>models.claude</code></td><td>API key, model name (default: claude-opus-4-5), max_tokens, temperature</td></tr>
        <tr><td><code>models.openai</code></td><td>API key, model name (default: gpt-4o-mini), max_tokens</td></tr>
        <tr><td><code>topic_defaults</code></td><td>Default search query, year range, open-access filter</td></tr>
        <tr><td><code>chunking</code></td><td>Chunk size (tokens), overlap, minimum chunk size</td></tr>
        <tr><td><code>evaluation</code></td><td>Subset fraction (10 %), category risk weights, pass threshold (0.6)</td></tr>
        <tr><td><code>retrieval</code></td><td>Top-k chunks returned per query, minimum BM25 score</td></tr>
        <tr><td><code>paths</code></td><td>Where PDFs, parsed text, chunks, and logs are stored</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- TROUBLESHOOTING -->
<div class="card mb-3">
  <div class="card-header fw-bold">❓ Troubleshooting</div>
  <div class="card-body">
    <dl class="mb-0">
      <dt>Documents stay in <code>pending</code></dt>
      <dd class="mb-2">Download runs in background. Refresh after 30 s. If stuck, check server logs.</dd>
      <dt>Task fails with 422 or "no chunks found"</dt>
      <dd class="mb-2">Document is not yet <code>chunked</code>. Run <strong>Process</strong> or <strong>Process All Downloaded</strong> first.</dd>
      <dt>401 / authentication error</dt>
      <dd class="mb-2">Check API keys in <code>config.yaml</code> under <code>models.claude.api_key</code> and <code>models.openai.api_key</code>.</dd>
      <dt>Evaluation shows "No results yet"</dt>
      <dd class="mb-2">Need at least one <code>chunked</code> document. Click <strong>Run Evaluation</strong> and wait 30–120 s for background jobs to finish.</dd>
      <dt>PDF fails to parse → status <code>failed</code></dt>
      <dd>System automatically falls back to the abstract. If abstract is also missing, the document is skipped. This is expected for some papers.</dd>
    </dl>
  </div>
</div>

<p class="text-muted small text-center mb-4">
  Medical RAG Evaluator v1.0 &nbsp;·&nbsp;
  Backend: FastAPI + SQLite &nbsp;·&nbsp;
  Primary LLM: Claude (Anthropic) &nbsp;·&nbsp;
  Checker: OpenAI GPT &nbsp;·&nbsp;
  Data source: Europe PMC
</p>
</div>
</div>`;
  }

  return { render };
})();
