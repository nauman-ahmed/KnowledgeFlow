from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import check_database, init_db
from app.core.redis_client import check_redis
from app.graph.neo4j_client import check_neo4j, close_neo4j_driver, init_graph_schema

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    init_graph_schema()
    yield
    close_neo4j_driver()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict:
    db_ok = check_database()
    redis_ok = check_redis()
    neo4j_ok = check_neo4j()

    checks: dict[str, str] = {
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
    if neo4j_ok is None:
        checks["neo4j"] = "disabled"
    else:
        checks["neo4j"] = "ok" if neo4j_ok else "error"

    required_ok = db_ok and redis_ok and (neo4j_ok is None or neo4j_ok)
    status = "ok" if required_ok else "degraded"
    return {
        "status": status,
        "service": "knowledgeflow-api",
        "checks": checks,
    }
