<div align="center">

# ContextIQ

### Local-first AI document intelligence

**Turn PDFs into searchable knowledge with agentic retrieval, evidence-grounded answers, and private on-device inference.**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React + TypeScript](https://img.shields.io/badge/React-TypeScript-149ECA?logo=react&logoColor=white)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Inference-Ollama-222222)](https://ollama.com/)
[![PostgreSQL + pgvector](https://img.shields.io/badge/Search-pgvector-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Docker Compose](https://img.shields.io/badge/Infrastructure-Docker_Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

**[Architecture](#system-architecture) · [Screenshots](#screenshots) · [Performance](#performance-benchmarks) · [Install](#local-installation) · [Evaluation](#retrieval-evaluation) · [Security](#security-and-reliability)**

</div>

---

> [!NOTE]
> **Project scope:** ContextIQ is a local-first **engineering portfolio prototype**, not a deployed or security-certified production multi-tenant service. AI inference and document storage run on local services. The Azure-compatible storage layer is **Azurite**, not Microsoft Azure hosting.

## At a glance

|                       |                                                                                                                                                  |
| :-------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it does**      | Uploads text-based PDFs, indexes their contents, searches across owned documents, and provides responses backed by retrieved page-level evidence |
| **AI architecture**   | LangGraph-controlled corrective RAG; local Qwen3 generation; `nomic-embed-text` embeddings                                                       |
| **Data architecture** | PostgreSQL + pgvector, Azure-compatible local blob emulation, Redis job broker                                                                   |
| **Engineering focus** | Authenticated data isolation, asynchronous processing, observability, reliability safeguards, tests and CI                                       |
| **Cloud cost**        | **$0 required for the documented local development configuration**                                                                               |

## Screenshots

A dedicated gallery for actual application captures. **Add real screenshots to `docs/screenshots/`** and uncomment the image links below. The image filenames are proposed; no screenshots are included or represented as real in this README yet.

<!--
When you have real captures, remove this comment wrapper to display the gallery.

<table>
  <tr>
    <td width="50%" align="center">
      <img src="docs/screenshots/overview.png" alt="ContextIQ overview dashboard showing service readiness" width="100%"/>
      <br/><strong>01 · Overview</strong>
    </td>
    <td width="50%" align="center">
      <img src="docs/screenshots/documents.png" alt="ContextIQ document upload and library" width="100%"/>
      <br/><strong>02 · Document library</strong>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="docs/screenshots/ask-contextiq.png" alt="Grounded answer with citations in the Ask ContextIQ interface" width="100%"/>
      <br/><strong>03 · Agentic document Q&A</strong>
    </td>
    <td align="center">
      <img src="docs/screenshots/grafana.png" alt="ContextIQ Prometheus metrics displayed in Grafana" width="100%"/>
      <br/><strong>04 · Observability</strong>
    </td>
  </tr>
</table>

Optional additional screenshots:
- docs/screenshots/login.png
- docs/screenshots/indexing-job.png
- docs/screenshots/github-actions.png
-->

**Suggested captures:** overview dashboard, PDF library, cited question-answer interface, successful indexing job, Grafana monitoring, and green GitHub Actions checks. Use non-sensitive test documents and hide usernames or secrets.

## Why this project

A basic "chat with PDF" demo often stops at sending a prompt to a model. ContextIQ extends that workflow with a persistent data model, source attribution, authenticated boundaries, background jobs, failure handling, and metrics.

Its purpose is to demonstrate **AI application engineering**, not just prompt design.

### Core capabilities

| Capability              | Implementation                                                                              |
| :---------------------- | :------------------------------------------------------------------------------------------ |
| **Document intake**     | PDF validation, text extraction, page records, local blob storage                           |
| **Semantic retrieval**  | Ollama embeddings and pgvector cosine similarity                                            |
| **Hybrid retrieval**    | Vector similarity combined with PostgreSQL text search                                      |
| **Agentic reasoning**   | LangGraph retrieval → evidence grading → bounded query rewrite → answer/abstain             |
| **Background indexing** | Celery task worker + Redis broker + persistent PostgreSQL job state                         |
| **Identity and access** | Argon2 password hashes, signed cookie sessions, CSRF checks and owner-scoped queries        |
| **Monitoring**          | Prometheus counters/histograms and Grafana dashboards                                       |
| **Validation**          | Pytest, Ruff, React lint/build, Locust, Python and npm dependency audits                    |
| **Experimentation**     | Reproducible retrieval evaluation and a separate PyTorch cross-encoder reranking experiment |

## Technology stack

| Layer               | Technologies                                                     |
| :------------------ | :--------------------------------------------------------------- |
| Web application     | React 19, TypeScript, Vite                                       |
| API                 | Python 3.12, FastAPI, Uvicorn                                    |
| RAG orchestration   | LangGraph                                                        |
| Local LLM           | Ollama + `qwen3:1.7b`                                            |
| Embeddings          | Ollama + `nomic-embed-text` (768-dimensional vectors)            |
| Storage and search  | PostgreSQL 16 + pgvector, PostgreSQL text search                 |
| Background tasks    | Celery, Redis                                                    |
| Binary storage      | Azurite (local Azure Blob Storage emulator)                      |
| Observability       | Prometheus, Grafana                                              |
| QA and load testing | Pytest, Ruff, Locust                                             |
| Automation          | GitHub Actions, Docker Compose                                   |
| Research tooling    | PyTorch, Sentence Transformers, standalone reranking experiments |

## System architecture

The frontend, authenticated API, data layer, indexing worker, inference host, and monitoring services are separated so individual components can be tested and operated independently.

```mermaid
flowchart TB
    B["Browser<br/>React + TypeScript"] --> API["FastAPI<br/>Auth · Documents · RAG · Jobs"]

    API --> AUTH["Sessions · CSRF<br/>Ownership checks"]
    API --> AZ["Azurite<br/>PDF blob storage"]
    API --> DB[("PostgreSQL + pgvector<br/>Users · Documents · Chunks · Jobs")]
    API --> LG["LangGraph<br/>Retrieve · Grade · Rewrite · Answer"]
    API --> JOBS["Indexing job API"]

    JOBS --> DB
    JOBS --> REDIS["Redis broker"]
    REDIS --> WORKER["Celery worker"]
    WORKER --> DB
    WORKER --> OLLAMA["Ollama<br/>Qwen3 · Embeddings"]

    LG --> DB
    LG --> OLLAMA

    API --> METRICS["/metrics"]
    METRICS --> PROM["Prometheus"]
    PROM --> GRAFANA["Grafana"]

    classDef ui fill:#dcefff,stroke:#2274a5,color:#102a43
    classDef ai fill:#ece4ff,stroke:#8156ca,color:#291549
    classDef storage fill:#dff8e8,stroke:#2e8b57,color:#174b30
    classDef ops fill:#fff2d4,stroke:#cb8c24,color:#573706
    class B,API ui
    class LG,OLLAMA ai
    class AZ,DB,REDIS storage
    class WORKER,METRICS,PROM,GRAFANA ops
```

_Diagram is a logical architecture, not a claim that every component is remotely deployed or containerized. FastAPI and Ollama run on the development host; Docker Compose provides the local infrastructure._

<details>
<summary><strong>Component responsibilities</strong></summary>

- **React / TypeScript:** Displays authentication, document management, system readiness, indexing status and grounded Q&A.
- **FastAPI:** Routes requests, enforces authentication, validates documents, handles job submission and calls retrieval workflows.
- **PostgreSQL + pgvector:** Holds users, document metadata, extracted pages, embeddings, and indexing state. Vector search supports semantic similarity.
- **LangGraph:** Coordinates retrieval, evidence sufficiency grading, bounded search-query reformulation, answer generation and abstention.
- **Ollama:** Hosts the local embedding and Qwen3 generation models.
- **Redis + Celery:** Executes document indexing outside synchronous HTTP request handling.
- **Azurite:** Stores PDFs with an Azure Blob-compatible local API; it is not hosted Azure storage.
- **Prometheus + Grafana:** Collects and displays HTTP, latency and indexing-job metrics.

</details>

### Document ingestion and indexing

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React
    participant API as FastAPI
    participant Blob as Azurite
    participant DB as PostgreSQL
    participant Redis
    participant Worker as Celery
    participant AI as Ollama

    User->>UI: Upload text-based PDF
    UI->>API: Authenticated upload
    API->>API: Validate and extract text
    API->>Blob: Store PDF
    API->>DB: Store document metadata and pages
    API-->>UI: Document created
    User->>UI: Start indexing
    UI->>API: Submit indexing request
    API->>DB: Record queued job
    API->>Redis: Enqueue task
    Redis->>Worker: Deliver indexing task
    Worker->>DB: Claim job atomically
    Worker->>AI: Request chunk embeddings
    AI-->>Worker: Return vectors
    Worker->>DB: Persist vector chunks and job result
    UI->>API: Poll job status
    API-->>UI: Job status
```

The API persists job state, while the background worker handles embedding generation and writes searchable vectors. Duplicate-job protections and manual stale-job recovery are addressed under [Security and reliability](#security-and-reliability).

### Agentic question answering

```mermaid
flowchart TD
    Q["Authenticated question"] --> R["Owner-scoped hybrid retrieval"]
    R --> G{"Evidence sufficient?"}
    G -->|Yes| A["Generate answer with Qwen3"]
    G -->|No: first attempt| W["Rewrite search query"]
    W --> R
    G -->|No: retry exhausted| X["Abstain"]
    A --> S["Answer + server-retrieved source references"]
    X --> N["Insufficient-evidence response"]
    classDef positive fill:#e0f6ea,stroke:#2b9562,color:#154830
    classDef caution fill:#fff0df,stroke:#c38b29,color:#5b3a10
    class A,S positive
    class G,X,N caution
```

The graph uses a maximum of **two retrieval attempts**. Source references are derived from retrieved server records, not invented model-generated page numbers. Evidence grading is model-assisted and therefore **not guaranteed to be correct**.

## Performance benchmarks

### Local API load test · Locust

<div align="center">

| **577** requests |  **0** failures   | **65 ms** average |    **140 ms** p95    | **4.83** req/s |
| :--------------: | :---------------: | :---------------: | :------------------: | :------------: |
|  Total traffic   | Recorded failures |   HTTP latency    | Overall HTTP latency |   Throughput   |

</div>

> [!IMPORTANT]
> This is a **10-simulated-user, 120-second, authenticated/read-heavy API test**. It is **not** an Ollama token-generation benchmark, an indexing-throughput test, or proof of production scalability. Results depend on local hardware and workload.

| Test parameter  | Value                                                                |
| :-------------- | :------------------------------------------------------------------- |
| Simulated users | 10                                                                   |
| Duration        | 120 seconds                                                          |
| Environment     | Windows + local FastAPI and Docker services                          |
| Tool            | Locust                                                               |
| Failure rate    | 0%                                                                   |
| Workload        | Authentication, document list, RAG index status and health endpoints |

#### Endpoint breakdown

| API endpoint           | Requests | Mean latency | p95 latency |
| :--------------------- | -------: | -----------: | ----------: |
| `GET /api/documents`   |      279 |        79 ms |      150 ms |
| `GET /api/rag/status`  |      189 |        75 ms |      130 ms |
| `GET /api/health`      |       99 |         4 ms |       12 ms |
| `POST /api/auth/login` |       10 |        84 ms |      130 ms |

The recorded workload completed without HTTP failures. The lighter health endpoint was faster than the authenticated document/status endpoints.

**Reproduction:** see `backend/tests/load/locustfile.py` for the workload and `docs/results/` for saved artifacts, where present. For an apples-to-apples comparison, preserve user count, duration, hardware, test dataset and authentication behavior.

### Reliability testing

| Scenario            | Engineering safeguard                                                           | Important limit                                        |
| :------------------ | :------------------------------------------------------------------------------ | :----------------------------------------------------- |
| Redis unavailable   | Submission error reporting rather than falsely claiming a queued task succeeded | A broker outage still interrupts new work              |
| Duplicate indexing  | PostgreSQL-backed states and atomic job claim                                   | Does not promise mathematically exactly-once execution |
| Stale worker state  | Operator diagnostics and manual recovery script                                 | Operators must confirm conflicting workers are stopped |
| User data isolation | Owner-scoped access checks and regression tests                                 | Not independently audited for public multi-tenancy     |

**Not measured by the benchmark:** concurrent answer generation, maximum PDF throughput, high-volume multi-user ingestion, public network deployment, extended uptime or arbitrary worker termination.

### Metrics and dashboards

- Prometheus exposes HTTP request totals, histogram-based latency and indexing-job state metrics.
- Prometheus scrapes the API `/metrics` endpoint; Grafana can display them.
- Actual screenshots from your locally configured Grafana dashboard can be placed in the [Screenshots](#screenshots) gallery.

## Security and reliability

ContextIQ uses layered controls rather than treating a hidden frontend route as access control:

- **Authentication:** database-backed users, Argon2 password hashes, signed cookie sessions.
- **Request protection:** CSRF token checks for authenticated state-changing operations, restricted login origins, security-focused response headers.
- **Authorization:** owner-scoped documents, pages, retrieval and indexing records.
- **Jobs:** persisted queue states, atomic claiming, duplicate-job protections and operator-initiated stale-job recovery.
- **Verification:** Pytest/Ruff, React lint/build, Python dependency auditing and npm audit in GitHub Actions.

These measures reduce identified risks but do not establish security certification or guarantee safety under an internet-exposed deployment. Cookie security settings and network exposure must be revisited before any real production use.

## Retrieval evaluation

Retrieval quality should be measured using **verified relevance labels**, not fabricated scores. The evaluation file `datasets/evaluation/questions.json` is intentionally empty until real or synthetic documents have been indexed and labeled.

### Build a labeled evaluation set

1. Index a non-sensitive public or synthetic PDF.
2. Query the actual chunk identifiers from PostgreSQL:

   ```powershell
   docker compose exec postgres psql -U contextiq -d contextiq -c "SELECT c.id, d.filename, c.page_number, left(c.text_content, 110) AS excerpt FROM document_chunks c JOIN documents d ON c.document_id=d.id ORDER BY c.id;"
   ```

3. Read the source PDF and stored text, then assign relevant chunk IDs to questions.
4. Add at least five questions, mixing paraphrased and exact-keyword queries.

Example dataset entry (**illustrative ID only; do not publish as a measured label**):

```json
[
  {
    "question": "What exercise does the guide recommend for warmup?",
    "relevant_chunk_ids": [123]
  }
]
```

### Run evaluation

From the project root, with the backend environment installed:

```powershell
$env:PYTHONPATH = (Resolve-Path .\backend).Path
.\backend\.venv312\Scripts\python.exe .\scripts\evaluate_retrieval.py --dataset .\datasets\evaluation\questions.json --k 4
```

The evaluation uses:

| Metric            | Meaning                                                                  |
| :---------------- | :----------------------------------------------------------------------- |
| Recall@k          | Proportion of relevant chunks found within the top `k`                   |
| Precision@k       | Proportion of retrieved top-`k` results that are relevant                |
| Reciprocal rank   | `1 / rank` of the first relevant result                                  |
| MRR               | Mean reciprocal rank across evaluated questions                          |
| Retrieval latency | Local embedding and database retrieval time; **not** LLM generation time |

Compare different retrieval configurations using the **same** labeled questions, source corpus and hardware. No Ragas metrics or measured answer-faithfulness scores are claimed here; model-based evidence grading remains fallible.

## PyTorch reranking experiment

A standalone experiment evaluates a pretrained **cross-encoder reranker** against the base retrieval ordering. This research path **does not replace or modify live LangGraph answer generation**.

The project includes `torch` and `sentence-transformers` in its backend requirements. For resource-constrained machines, run the comparison on CPU:

```powershell
# From the project root
$env:PYTHONPATH = (Resolve-Path .\backend).Path
.\backend\.venv312\Scripts\python.exe .\scripts\evaluate_reranking.py --k 1 2 4 --candidate-k 12 --device cpu
```

The experiment writes `docs/results/reranking_comparison.json` and may download public model weights on first run.

<details>
<summary><strong>Experiment methodology and limitations</strong></summary>

- This is **pretrained PyTorch inference**, not fine-tuning or model training.
- Cross-encoder relevance scores are **not probabilities of factual correctness**.
- An original 15-question dataset was relatively easy; reranking need not improve results.
- Retrieval latency and end-to-end reranking evaluation time are different metrics.
- The experiment performs a separate first-stage embedding/search operation for each variant; any latency delta is an **end-to-end comparison**, not isolated reranker overhead.
- No external paid LLM APIs are required. Downloading model weights on first use does require internet connectivity.

</details>

## Local installation

<details>
<summary><strong>Expand: complete Windows setup, database initialization, services and verification</strong></summary>

### Prerequisites

Install and launch where applicable:

- Windows with PowerShell, Git, and Docker Desktop (Linux containers)
- Python **3.12** (`py -3.12 --version`)
- Node.js **22** with npm (`node --version`, `npm --version`)
- [Ollama](https://ollama.com/) (`ollama --version`)
- Sufficient disk space for Python dependencies, Docker images, and Ollama models

The UI uses React/Vite on port **5173**, FastAPI on **8081**, PostgreSQL on **5433**, Redis on **6379**, Azurite on **10000**, Prometheus on **9091**, and Grafana on **3001**. These are **local host ports**; check for conflicts with other projects, particularly CloudForge.

### Download the repository

```powershell
git clone https://github.com/jonathanprogram2/ContextIq.git
cd ContextIq
```

For an existing clone, use `git pull --ff-only origin main` only if you are on `main` and have no conflicting local changes.

### Configure environment variables

From the repository root:

```powershell
Copy-Item .env.example .env
notepad .env
```

Update `.env` to include the following **local development** settings (replace the placeholder secrets with your own; keep PostgreSQL settings consistent with Docker Compose):

```dotenv
POSTGRES_DB=contextiq
POSTGRES_USER=contextiq
POSTGRES_PASSWORD=localdev_only_change_me
DATABASE_URL=postgresql://contextiq:localdev_only_change_me@127.0.0.1:5433/contextiq

AZURITE_BLOB_URL=http://127.0.0.1:10000/devstoreaccount1
OLLAMA_URL=http://127.0.0.1:11434
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
FRONTEND_ORIGIN=http://127.0.0.1:5173

CONTEXTIQ_SESSION_SECRET=REPLACE_WITH_GENERATED_SECRET
CONTEXTIQ_ADMIN_PASSWORD_HASH=REPLACE_WITH_GENERATED_ARGON2_HASH
GRAFANA_ADMIN_PASSWORD=REPLACE_WITH_A_UNIQUE_LOCAL_PASSWORD
```

Generate a session secret with Python after creating the virtual environment in the next step:

```powershell
.\backend\.venv312\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate a password hash interactively (the password itself will not be echoed):

```powershell
.\backend\.venv312\Scripts\python.exe -c "import getpass; from pwdlib import PasswordHash; print(PasswordHash.recommended().hash(getpass.getpass('Admin password: ')))"
```

Paste the generated secret and **Argon2 hash**, not the plain-text password, into `.env`. The initial administrator username is `local-admin`. Treat `.env` as a local secret and **never commit it**. If your password has URL-special characters, URL-encode it in `DATABASE_URL`. For reproducibility, use the provided local-development database password in a disposable environment; never reuse it for a network-facing deployment.

### Install Python and frontend dependencies

From the repository root:

```powershell
py -3.12 -m venv backend\.venv312
.\backend\.venv312\Scripts\python.exe -m pip install --upgrade pip
.\backend\.venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
.\backend\.venv312\Scripts\python.exe -m pip check

cd frontend
npm ci
cd ..
```

The Python AI stack contains large dependencies and may take substantial disk space. `.venv312/`, `.env`, and `frontend/node_modules/` must not be committed.

### Start Docker services and local AI models

Ensure Docker Desktop is running, then from the repository root:

```powershell
docker compose config --quiet
docker compose up -d
docker compose ps
```

Wait for PostgreSQL and Redis to be healthy. Initialize pgvector only through the existing Docker initialization script when the database volume is first created; the script is mounted from `infrastructure/docker/init.sql`.

In a separate terminal:

```powershell
ollama pull nomic-embed-text
ollama pull qwen3:1.7b
ollama list
```

The first model downloads may require internet access. Ollama should be available at `http://127.0.0.1:11434`.

> Docker Compose persists data in named volumes. **Do not** use `docker compose down -v` as a troubleshooting shortcut; it removes persistent data.

### Initialize the database (first installation)

Before this step, `.env` must contain a valid `CONTEXTIQ_ADMIN_PASSWORD_HASH` and the Docker PostgreSQL service must be running.

Open PowerShell in the repository root, then:

```powershell
cd backend

.\.venv312\Scripts\python.exe -m app.scripts.init_documents
.\.venv312\Scripts\python.exe -m app.scripts.init_rag
.\.venv312\Scripts\python.exe -m app.scripts.init_users
.\.venv312\Scripts\python.exe -m app.scripts.init_index_jobs

cd ..
```

**Order matters:** document tables → RAG chunks → users/ownership → indexing jobs. `init_users` creates the `local-admin` account and assigns ownership to any existing unowned documents.

To create an ordinary account after initialization:

```powershell
cd backend
.\.venv312\Scripts\python.exe -m app.scripts.create_user testuser
cd ..
```

The user-creation script prompts for a password of at least 12 characters. No public signup endpoint is provided.

To confirm the vector extension is installed:

```powershell
docker compose exec postgres psql -U contextiq -d contextiq -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

If you changed the local database username or database name, adjust the `psql` command accordingly.

### Start FastAPI, Celery, and React

Use **three separate PowerShell terminals** and leave all three running.

**Terminal A — FastAPI:**

```powershell
cd backend
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8081
```

**Terminal B — Celery** (start from repository root or use the backend directory in a new terminal):

```powershell
cd backend
.\.venv312\Scripts\python.exe -m celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo --concurrency=1
```

**Terminal C — Frontend:**

```powershell
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173** and sign in as `local-admin` with the password corresponding to the hash you generated, or as a separately created test user.

> `cd backend` and `cd frontend` above assume each terminal starts in the repository root. If a terminal is already inside another directory, first `cd` to the repository root.

### Verify services and document workflows

Service URLs:

| Service            | Local URL                        |
| ------------------ | -------------------------------- |
| React frontend     | http://127.0.0.1:5173            |
| FastAPI health     | http://127.0.0.1:8081/api/health |
| FastAPI Swagger    | http://127.0.0.1:8081/docs       |
| Prometheus metrics | http://127.0.0.1:8081/metrics    |
| Prometheus targets | http://127.0.0.1:9091/targets    |
| Grafana            | http://127.0.0.1:3001            |

For an end-to-end smoke test:

1. Sign in using a local test account.
2. Upload a **small, non-sensitive, text-based PDF** in **Documents**. Scanned/image-only PDFs are not supported without OCR.
3. Submit an indexing job; confirm the UI reports success and Celery logs show processing.
4. In **Ask ContextIQ**, ask a question answerable from that PDF. Inspect the returned source and page references.
5. Ask a question unsupported by the PDF; confirm the app can abstain.
6. In Prometheus, confirm `contextiq-api` shows **UP**. Grafana requires a Prometheus data source pointing to `http://prometheus:9090` on the internal Docker network. Grafana dashboard provisioning is not automatic in this guide; use an exported dashboard JSON if available.

### Run automated tests and audits

From the `backend` directory:

```powershell
.\.venv312\Scripts\python.exe -m ruff check app tests
.\.venv312\Scripts\python.exe -m pytest -q
.\.venv312\Scripts\python.exe -m pip check
```

Optional dependency audit:

```powershell
.\.venv312\Scripts\python.exe -m pip install pip-audit
.\.venv312\Scripts\python.exe -m pip_audit --progress-spinner off
```

From `frontend`:

```powershell
npm run lint
npm run build
npm audit --audit-level=high
```

The repository's GitHub Actions pipeline executes Python lint/tests, React lint/build, and Python/JavaScript vulnerability checks. These checks do not certify production security.

### Operational notes and troubleshooting

- **API won't start:** Confirm `.env` contains `CONTEXTIQ_SESSION_SECRET`; confirm port 8081 is not occupied.
- **Database unavailable:** Check `docker compose ps`, the `5433` published port, and `DATABASE_URL`.
- **Indexing stuck or failed:** Check Redis, Celery, and `document_index_jobs`. Use `python -m app.scripts.check_index_jobs` from the backend environment to identify stale records. `recover_index_job` is a controlled **manual** operation requiring workers to be stopped before mutation.
- **Prometheus target DOWN:** On Docker Desktop, verify the `host.docker.internal` mapping and that the FastAPI listener is reachable from the container. Do not expose the API to an untrusted network simply to make scraping work.
- **Grafana password:** The environment value initializes a new Grafana database; changing it after first startup may not reset an existing account.
- **Evaluation/reranking:** Standalone scripts exist under `scripts/`. A PyTorch reranker experiment is separate from the live LangGraph answer path; see [Reranking experiment](#pytorch-reranking-experiment).

### Known limitations

This is a **local portfolio prototype**, not a publicly deployed or production-certified multi-tenant service. A clean installation on a different machine, automatic abandoned-job recovery, and concurrent LLM-inference scaling have not been independently verified by this guide. Models, dependency resolution, and platform differences may affect setup.

</details>

## Repository guide

```text
ContextIq/
├── README.md                     # This consolidated project guide
├── compose.yaml                  # PostgreSQL, Azurite, Redis, Prometheus, Grafana
├── .env.example                  # Local environment template
├── backend/
│   ├── app/
│   │   ├── main.py               # API entry point
│   │   ├── auth.py               # Sessions and identity
│   │   ├── agentic.py            # LangGraph corrective RAG
│   │   ├── retrieval.py          # Hybrid retrieval
│   │   ├── rag.py                # Embeddings and vector index
│   │   ├── jobs.py               # Indexing job API
│   │   ├── index_tasks.py        # Celery tasks
│   │   ├── metrics.py            # Prometheus exporter
│   │   └── scripts/              # Schema, user and recovery utilities
│   └── tests/                    # Python tests and load workloads
├── frontend/                     # React + TypeScript application
├── infrastructure/               # Docker database init and observability config
├── scripts/                      # Evaluation and reranking tooling
├── datasets/                     # Retrieval evaluation cases
└── docs/
    ├── screenshots/              # Add real UI screenshots here
    └── results/                  # Load/evaluation results, where present
```

## Known limitations and project status

- **Local prototype:** no claim of production-hosted infrastructure, audited security, or production uptime.
- **Documents:** text-based PDFs only; scanned PDFs require OCR, which is not enabled.
- **Models:** Ollama and cross-encoder performance depends on local hardware.
- **Reliability:** operator-guided stale-job recovery; not automatic arbitrary-failure recovery.
- **Benchmark interpretation:** current Locust results describe authenticated HTTP endpoints, not end-to-end AI answer performance.
- **Retrieval quality:** no fabricated relevance scores; curated ground truth is required.
- **Reranking:** a separate evaluation experiment, not live answer-serving functionality.
- **Installation:** documentation is based on the repository and development setup; a fresh installation on an independent machine remains to be verified.

## Project goals

**ContextIQ demonstrates end-to-end AI engineering:** information retrieval, orchestration, distributed job processing, security boundaries, local infrastructure, observability, and measurable testing.

The design prioritizes a reproducible, low-cloud-cost development environment and transparent limitations over unverified production claims.

---

<div align="center">

**ContextIQ · Built for local-first, evidence-grounded document intelligence**

[Back to top](#contextiq)

</div>
