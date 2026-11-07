# Architecture

Phase 1: React/Vite (5173) calls FastAPI (8000); FastAPI checks PostgreSQL/pgvector (5432) and local Azurite Blob endpoint (10000). Docker exposes infrastructure only on 127.0.0.1. Later phases implement document ingestion and retrieval.
