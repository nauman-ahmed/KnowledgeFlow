# KnowledgeFlow Backend

FastAPI service for RAG chat, ingestion, and agent workflows.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp ../.env.example .env     # optional; defaults work with docker-compose
```

Start infrastructure from repo root:

```bash
docker compose up -d
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

- Health: http://localhost:8000/health
- OpenAPI: http://localhost:8000/docs

## Lint & test

```bash
ruff check app tests
ruff format --check app tests
pytest
```
