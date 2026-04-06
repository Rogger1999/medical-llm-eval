

# Medical RAG Evaluator

A research prototype that evaluates how well LLMs handle medical literature — specifically open-access papers on malnutrition and undernutrition interventions in children. It fetches papers from Europe PMC, parses and chunks them, runs LLM tasks (summarisation, extraction, QA), and scores the outputs across eight evaluation categories.

## What it does

1. **Fetches papers** from [Europe PMC](https://europepmc.org/) based on a configurable topic query (default: malnutrition/undernutrition interventions).
2. **Downloads and parses** full-text PDFs into plain text, then chunks them for retrieval.
3. **Runs LLM tasks** on each document using Claude (primary) and GPT-4o-mini (checker):
   - **Summarisation** — structured summary of the paper
   - **Extraction** — key numeric and clinical data pulled out as JSON
   - **Grounded QA** — answers a question using BM25-retrieved chunks as context
4. **Evaluates** outputs across 8 categories, each weighted differently:

   | Category | Weight | What it checks |
   |---|---|---|
   | `ingest` | 1.0 | Document ingested and chunked correctly |
   | `retrieval` | 1.5 | BM25 retrieval returns relevant chunks |
   | `grounding` | 2.0 | Answer is supported by source text |
   | `hallucination` | 2.0 | Output does not invent facts |
   | `numeric` | 1.5 | Numbers in output match the source |
   | `abstention` | 1.0 | Model refuses unanswerable questions |
   | `adversarial` | 1.5 | Resistant to misleading inputs |
   | `overclaiming` | 2.0 | No unsupported certainty in conclusions |

5. **Aggregates** scores into a pass/fail summary per evaluation run (pass threshold: 0.6).

## Stack

- **Backend**: FastAPI + SQLAlchemy (async) + SQLite/aiosqlite
- **LLMs**: Anthropic Claude (primary), OpenAI GPT-4o-mini (checker/validator)
- **Retrieval**: BM25 keyword search over sentence-preserving chunks
- **Frontend**: Static HTML/JS served at `/app`

## Requirements

- Python 3.11+
- `ANTHROPIC_API_KEY` environment variable
- `OPENAI_API_KEY` environment variable

## Setup

```bash
pip install -r requirements.txt
cp key.yaml.example .env   # or set env vars directly

# Run locally
./run.sh
```

The server starts at `http://localhost:8000`. API docs are at `/docs`. The frontend is at `/app`.

## Configuration

All settings live in `config.yaml`. Key sections:

- `topic_defaults` — Europe PMC query, max results, date range, filters
- `models` — Claude and OpenAI model names, token limits, temperature
- `chunking` — chunk size (default 512 tokens), overlap (64), sentence preservation
- `retrieval` — BM25 top-k (5), minimum relevance score
- `evaluation` — subset fraction (10%), category weights, pass threshold

API keys are injected via `${ANTHROPIC_API_KEY}` / `${OPENAI_API_KEY}` in `config.yaml`.

## API overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/documents/fetch` | Fetch papers from Europe PMC |
| `POST` | `/processing/parse` | Parse PDFs to text |
| `POST` | `/processing/chunk` | Chunk parsed documents |
| `POST` | `/tasks/summarize` | Summarise a document |
| `POST` | `/tasks/summarize-all` | Batch summarise all chunked docs |
| `POST` | `/tasks/extract` | Extract structured data |
| `POST` | `/tasks/qa` | Grounded question answering |
| `POST` | `/evaluations/run` | Run full evaluation pipeline |
| `GET` | `/evaluations` | List evaluation results |
| `GET` | `/metrics` | Aggregated scores |

## Deployment note

SQLite is used by default. In production, run with a **single worker** (`uvicorn ... --workers 1`) or switch the `database.url` in `config.yaml` to a PostgreSQL connection string (`postgresql+asyncpg://...`). Multiple workers + SQLite will cause lock contention.
