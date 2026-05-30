# KnowledgeFlow

ChatGPT-style AI assistant backed by a **single curated document library**. Documents live in `content/` and are ingested by the system (not uploaded by end users). Users chat and receive grounded, cited answers via RAG and a LangGraph agent.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, React, Tailwind, Clerk |
| Backend | FastAPI, LangGraph, LangChain |
| Data | PostgreSQL + pgvector, Redis |
| Observability | Langfuse |
| Eval | RAGAS + LLM faithfulness judge |
| Deploy | Vercel (frontend), Render (API) |

**Docs:** [`doc/PROJECT_GUIDE.md`](./doc/PROJECT_GUIDE.md) · [`doc/architecture.md`](./doc/architecture.md) · [`doc/PROGRESS.md`](./doc/PROGRESS.md)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Next.js (Vercel)  —  ChatGPT UI + Clerk auth           │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS / SSE
┌──────────────────────────▼──────────────────────────────┐
│  FastAPI  —  LangGraph agent, RAG, guardrails, Langfuse │
└───────┬─────────────────┬───────────────────────────────┘
        │                 │
   PostgreSQL          Redis
   + pgvector          (sessions)
        ▲
   content/ → python -m app.ingest
```

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
# Edit .env — Clerk, DashScope/Qwen keys (see doc/openai.md), Langfuse (optional)

ln -sf ../.env frontend/.env.local
```

### 3. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/health

### 4. Frontend

```bash
cd frontend
npm install && npm run dev
```

App: http://localhost:3000

## Content library & ingest

Add PDF, DOCX, TXT, or Markdown files to [`content/`](./content/), then:

```bash
cd backend && source .venv/bin/activate
python -m app.ingest              # ingest all files
python -m app.ingest --changed-only  # skip unchanged (content hash)
```

List documents: `GET /api/v1/documents`

## Evaluation

Golden Q&A pairs: [`eval/dataset.json`](./eval/dataset.json)

```bash
cd backend
pip install -e ".[eval]"   # optional RAGAS metrics
python -m app.eval --output ../eval-report.json
```

Reports context hit rate and faithfulness scores per question.

## Observability

Set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL` in `.env`. Each chat request creates a Langfuse trace with agent step spans and retrieval metadata.

## Deployment

| Service | Platform | Config |
|---------|----------|--------|
| Frontend | [Vercel](https://vercel.com) | Root directory: `frontend/`; set `NEXT_PUBLIC_API_URL` |
| API | [Render](https://render.com) | `render.yaml` + `backend/Dockerfile` |
| Postgres | Render / Supabase | Enable pgvector |
| Redis | Upstash / Render | Session memory |

Set `CORS_ORIGINS=https://your-app.vercel.app` on the API.

See [`doc/architecture.md`](./doc/architecture.md) for full deployment notes.

## Lint & test

```bash
cd backend && ruff check app tests && pytest
cd frontend && npm run lint && npm run build
```

## Project status

All milestones **M0–M6** complete. See [`doc/PROGRESS.md`](./doc/PROGRESS.md) for the live checklist.

## Repository layout

```
KnowledgeFlow/
├── content/          # Curated source documents
├── eval/             # Golden Q&A eval dataset
├── frontend/         # Next.js app
├── backend/          # FastAPI + LangGraph
├── docker/           # DB init scripts
├── doc/              # Specs, architecture, progress
└── docker-compose.yml
```
