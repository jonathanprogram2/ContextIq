# ContextIQ

Local-first document intelligence with verifiable source citations. This repository is a portfolio prototype, not a production multi-tenant service.

## Phase 1

React/TypeScript dashboard, FastAPI health/readiness API, PostgreSQL with pgvector, and local Azurite blob emulator. PDF uploads, RAG, evaluation, and PyTorch reranking are **not implemented yet**.

## Requirements

Windows PowerShell, Python 3.11+, Node.js 20+, Docker Desktop, Git. No paid accounts or cloud resources.

## Run

```powershell
Copy-Item .env.example .env
# Edit .env if you change local credentials
# Start Docker Desktop first
docker compose up -d
docker compose ps
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173, API docs at http://localhost:8000/docs.

## Verify

```powershell
# from backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
# from frontend
npm run lint
npm run build
# from repository root
docker compose exec postgres psql -U contextiq -d contextiq -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

## Cost and privacy

All services run on your own machine. Azure storage is **emulated with Azurite**, not deployed on Azure. No hosted inference or paid APIs. Only shareable test documents should be committed.

## Roadmap

1. Foundation (current)
2. PDF upload and local blob storage
3. Embeddings, pgvector search and grounded Qwen RAG
4. Hybrid search and evaluation
5. PyTorch reranking experiments
6. Optional measured fine-tuning
7. Documentation and portfolio polish
