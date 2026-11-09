# ContextIQ Phase 2 upgrade

1. Back up your existing `backend/app/main.py`, `frontend/src/App.tsx`, and `frontend/src/App.css`.
2. Copy the included patch folders over your existing project root. It does not include compose.yaml, .env, or vite.config.ts, preserving your port changes.
3. In `backend/app/main.py`, import and include `documents_router` as described in `backend/app/main_phase2_integration.txt`.
4. Append this line to the end of `frontend/src/App.css`: `@import './phase2.css';` **instead** add the CSS import at the top of `frontend/src/App.tsx`: `import './phase2.css'` (preferred).
5. Install backend packages: `cd backend; .\.venv\Scripts\python.exe -m pip install -r requirements.txt`
6. Run schema creation: ` .\.venv\Scripts\python.exe -m app.scripts.init_documents ` (script package must have __init__.py).
7. Restart FastAPI and Vite using your existing commands, preserving PostgreSQL on 5433, FastAPI on 8001.
8. Upload a text-based PDF in Documents. Validate via the endpoints and/or database queries.

Limitations: Single-user local prototype; 10 MB PDFs and 200 pages; synchronous processing; no OCR, chunking or embeddings until Phase 3. The API download endpoint is unprotected and intended for loopback-only use.
