# Claude Prompt — Small-File Medical LLM Eval Prototype

Use the prompt below directly in Claude.

---

## MASTER PROMPT

You are a senior AI engineer and system architect.

I want you to design and implement a complete prototype project for evaluating hallucinations, grounding quality, extraction reliability, and overclaiming behavior of LLMs on medical/scientific PDF documents.

This must be a **realistic engineering project**, not just a conceptual design.

---

# Core objective

Build a prototype system that:

1. downloads a batch of medical/scientific documents about **one focused topic**,
2. stores and parses them,
3. runs LLM-based summarization / extraction / grounded QA,
4. evaluates hallucinations and source-grounding quality,
5. compares a **primary model** vs a **secondary evaluator/checker**,
6. exposes everything through a **FastAPI backend served by Uvicorn**,
7. provides a simple frontend for controlling the workflow and inspecting results,
8. is intentionally organized into **many small files** so future edits are cheap and safe.

---

# Very important implementation constraints

## 1. Keep files small
This is a hard requirement.

Design the repo so that source files stay **small and focused**.

Target:
- preferably **80–180 lines per file**
- avoid giant files over ~250 lines unless absolutely necessary
- split code by feature and responsibility
- prefer many small modules over a few large files

Examples:
- one router per domain
- one service per responsibility
- one client per provider
- one evaluator per evaluation category
- one schema file per domain group
- one config loader file
- one database model file or small grouped model files
- one utility file per narrow concern

Do **not** create huge “god files” like:
- `app.py` with everything
- `services.py`
- `utils.py` with 50 unrelated helpers
- one giant `evaluation.py`
- one giant `llm.py`

The entire project must be optimized for later editing with low token usage.

## 2. Every file must be easy to modify independently
Each file should have:
- one clear purpose
- minimal coupling
- clean imports
- simple interfaces
- docstrings where useful

## 3. Documentation must explicitly describe every file
I need detailed documentation that tells me:
- what each file does
- why it exists
- what can be edited there
- what depends on it
- what to be careful about when changing it

This is critical.

---

# Domain/topic requirements

Use **one coherent topic only** so evaluation stays consistent.

Default topic:
**malnutrition / undernutrition interventions in children**

Examples inside the topic:
- severe acute malnutrition
- ready-to-use therapeutic food (RUTF)
- micronutrient supplementation
- treatment outcomes in children
- interventions relevant to low-resource settings / Africa

You may refine it slightly if needed, but keep it narrow and coherent.

The system must download documents only for this one topic or a user-specified narrow variant of it.

---

# Tech stack requirements

## Backend
- Python
- FastAPI
- Uvicorn
- modular architecture
- REST endpoints
- async/background processing where helpful
- structured logging
- config from `config.yaml`

## Frontend
- any simple usable frontend
- prefer the simplest good choice
- must be clean and easy to edit
- frontend files must also stay small

## LLM providers
Support:
- **Claude** as primary model
- **OpenAI** as secondary evaluator/checker

Both must be configured via `config.yaml`.

Do not hardcode:
- API keys
- model names
- provider settings

---

# Product principle

This system is **not** meant to manually validate every document.

Instead:
- it may download e.g. 500–1000 documents,
- process all of them,
- create a **smaller stratified evaluation subset** such as 50–100 documents,
- run deeper evaluations on that subset,
- and run cheaper broad checks across the larger batch.

This principle must be explicit in both architecture and documentation.

---

# Functional requirements

## A. Document download
Implement backend endpoints that:
- accept a topic/query,
- fetch documents only related to that topic,
- store metadata locally,
- download PDFs where available,
- gracefully handle cases where only metadata or abstract is available,
- avoid duplicates,
- track source and retrieval metadata.

Use practical public sources suitable for medical/scientific literature, for example:
- Europe PMC
- PubMed / PMC
- optionally WHO / UNICEF reports if practical

Suggested endpoints:
- `POST /documents/download`
- `GET /documents`
- `GET /documents/{document_id}`

## B. Document ingestion / parsing
Implement:
- file storage
- metadata normalization
- PDF/text parsing
- chunking
- source attribution
- handling broken/unreadable/empty files
- optional fallback when PDF extraction fails

## C. LLM tasks
Implement at least:
- summarization
- structured extraction
- grounded QA

Structured extraction should aim to capture fields like:
- title
- population
- intervention
- comparator if present
- outcomes
- numeric values
- adverse events
- conclusion
- evidence snippets / citations

Use structured outputs whenever possible.

## D. Evaluation framework
Implement a layered evaluation framework covering at least:

### 1. Ingest / parsing checks
Examples:
- empty text
- parser failure
- suspiciously short extraction
- missing metadata
- duplicate document
- chunking issues

### 2. Retrieval checks
Examples:
- whether relevant chunks were retrieved
- whether top-k retrieval includes correct evidence
- whether answer used the correct document/chunk

### 3. Grounding / citation checks
Examples:
- every key claim should be linked to evidence
- evidence snippet should support the claim
- answer should not be stronger than the source

### 4. Hallucination / unsupported claim checks
Examples:
- answer invents facts
- answer invents numbers
- answer uses world knowledge not found in source

### 5. Numeric exactness checks
Examples:
- sample size
- percentages
- durations
- dosages
- mortality / outcomes

### 6. Abstention checks
Examples:
- if evidence is missing, answer should say so
- if retrieval is poor, avoid confident fabrication

### 7. Adversarial checks
Examples:
- prompt injection hidden in a chunk
- fake instructions in source text
- unrelated question such as “Who won the World Cup 2030?”
- fabricated drug/disease name
- contradictory chunks

### 8. Medical-risk / overclaiming checks
Examples:
- correlation presented as causation
- animal study presented as human evidence
- weak evidence presented as definitive result
- adverse effects ignored

For each evaluation category, define:
- objective
- failure modes
- concrete tests
- evaluator type:
  - rule-based
  - LLM-as-judge
  - hybrid
- metrics
- pass/fail logic

## E. Dual-model design
Implement:
- Claude as the main model
- OpenAI as secondary evaluator/checker

But do not treat the second model as absolute truth.

The final design must combine:
- deterministic/rule-based checks
- evidence-grounding checks
- second-model evaluation
- escalation logic
- confidence-aware handling

## F. Config
Use `config.yaml` for all configuration.

Include sections such as:
- server
- paths
- database
- logging
- document_sources
- downloader
- topic_defaults
- parsing
- chunking
- retrieval
- evaluation
- models
- claude
- openai
- frontend

Support environment variables for secrets where sensible.

## G. Storage
Use simple local storage unless there is a strong reason otherwise.

Suggested:
- local files for PDFs and parsed text
- SQLite for metadata, tasks, results, evaluations

Do not overengineer.

## H. Frontend
Build a minimal but usable frontend that allows:
- setting topic and download count
- starting download
- browsing documents
- viewing document metadata
- triggering process/evaluation runs
- comparing primary output vs checker output
- inspecting fail cases
- viewing summary metrics

Keep frontend files small too.

## I. Testing
Implement:
- unit tests
- integration tests
- regression-test scaffolding

Cover:
- config loading
- downloader logic
- parser behavior
- chunking
- API endpoints
- evaluation logic
- fail-case storage

---

# Architecture and code generation requirements

I do not want a vague answer.

I want you to produce an implementation-oriented result with code and structure.

Return:

1. architecture overview
2. realistic repository tree
3. detailed explanation of all modules
4. `config.yaml` example
5. backend code
6. frontend code
7. downloader implementation
8. parser/chunker design
9. Claude/OpenAI adapters
10. evaluation engine
11. prompts
12. example request/response payloads
13. tests
14. exact local run instructions
15. production-hardening notes

---

# Extremely important documentation requirement

In addition to code and architecture, provide a **detailed file-by-file documentation section**.

For **every significant file in the repo**, document:

- file path
- purpose
- what lives in this file
- what can be safely edited here
- what other files depend on it
- what to watch out for when changing it
- whether it is high-risk or low-risk to edit
- examples of likely future edits

I want this so that later I can edit features without wasting tokens or accidentally touching unrelated logic.

This documentation must be thorough and practical.

---

# Required repository design style

Use a structure similar to this philosophy:

- `app/main.py` only bootstraps FastAPI
- routers are separate small files
- schemas are separate small files
- services are separate small files
- provider clients are separate files
- evaluators are separate files per evaluation type
- prompts are separated by task
- config logic is isolated
- DB/session setup is isolated
- models are cleanly organized
- frontend components are small and composable

You may choose the exact structure, but it must follow the “small files, narrow responsibility” principle.

---

# Preferred backend endpoint groups

At minimum support something like:

## Documents
- `POST /documents/download`
- `GET /documents`
- `GET /documents/{document_id}`

## Processing
- `POST /documents/{document_id}/process`
- `POST /documents/process-batch`

## Tasks
- `POST /tasks/summarize`
- `POST /tasks/extract`
- `POST /tasks/qa`

## Evaluations
- `POST /evaluations/run`
- `GET /evaluations`
- `GET /evaluations/{evaluation_id}`
- `GET /metrics/summary`

## System
- `GET /health`
- `GET /config/public`

You may improve naming if needed, but keep it pragmatic.

---

# Prompt requirements

Also provide prompt templates for:
- extraction
- summarization
- grounded QA
- grounding check
- hallucination check
- overclaiming check
- abstention check

Put prompts in separate files, not inline in giant source files.

---

# Output formatting requirements

Return your answer in this exact order:

1. Executive summary
2. Architecture overview
3. Repository tree
4. File-by-file documentation
5. `config.yaml` example
6. Backend implementation
7. Frontend implementation
8. Data/storage design
9. Downloader implementation
10. Parsing/chunking implementation
11. LLM integration
12. Evaluation engine
13. Prompt files
14. API request/response examples
15. Testing approach
16. Local run instructions
17. Production-hardening suggestions

If the answer becomes too large:
- continue in multiple parts
- keep the same order
- do not skip the file-by-file documentation
- do not collapse many files into one giant file
- prefer many small code blocks mapped to many small files

---

# Additional engineering preferences

- prefer Pydantic models for request/response validation
- prefer SQLAlchemy or SQLModel with SQLite for simplicity
- keep async boundaries sensible
- use typed Python where practical
- use dependency injection lightly, not ceremonially
- log important events and failures
- make evaluator results inspectable
- keep interfaces explicit
- avoid hidden magic

---

# Final reminder

The most important constraints are:
1. **small files**
2. **clear file-by-file documentation**
3. **FastAPI + Uvicorn backend**
4. **config.yaml**
5. **topic-based document download**
6. **Claude main + OpenAI checker**
7. **strong evaluation framework**
8. **easy future editing with low token cost**

Please produce the implementation and documentation accordingly.
