# KnowledgeFlow

ChatGPT-style AI assistant backed by a **single curated document library**. Documents live in `content/` and are ingested by the system (not uploaded by end users). Users chat and receive grounded, cited answers via RAG.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js, React, Tailwind |
| Backend | FastAPI, Pydantic |
| Data | PostgreSQL + pgvector, Redis |
| Docs | [`doc/PROJECT_GUIDE.md`](./doc/PROJECT_GUIDE.md) (setup → deploy) · [`doc/PROGRESS.md`](./doc/PROGRESS.md) (live checklist) |

## Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose

## Quick start

### 1. Infrastructure

```bash
docker compose up -d
```

Postgres (with pgvector) on `localhost:5433`, Redis on `localhost:6379`.

### 2. Environment

```bash
cp .env.example .env
# Edit .env when adding Clerk / OpenAI keys (later milestones)

# Next.js reads env from frontend/ — link repo root .env (required for Clerk)
ln -sf ../.env frontend/.env.local
```

### 3. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/health

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000 — health: http://localhost:3000/api/health

## Content library

Add files to [`content/`](./content/). Five sample documents are included for future ingest testing. Ingest CLI arrives in **M2**:

```bash
cd backend && python -m app.ingest
```

## Project status

| Milestone | Status |
|-----------|--------|
| M0 Foundation | Done |
| M1 Auth + ChatGPT UI | **In progress** |
| M2 Ingest pipeline | Planned |

- **Handbook (start → finish):** [`doc/PROJECT_GUIDE.md`](./doc/PROJECT_GUIDE.md)  
- **Live checklist:** [`doc/PROGRESS.md`](./doc/PROGRESS.md)

## Lint & test

```bash
# Backend
cd backend && ruff check app tests && pytest

# Frontend
cd frontend && npm run lint
```

## Repository layout

```
KnowledgeFlow/
├── content/          # Curated source documents
├── frontend/         # Next.js app
├── backend/          # FastAPI app
├── docker/           # DB init scripts
├── doc/              # Specs and progress tracker
└── docker-compose.yml
```
