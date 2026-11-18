from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import check_database, init_db
from app.core.redis_client import check_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def api_docs_urls(enabled: bool) -> dict[str, str | None]:
    """Swagger UI, ReDoc and the OpenAPI schema, or none of them."""
    if enabled:
        return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
    return {"docs_url": None, "redoc_url": None, "openapi_url": None}


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    **api_docs_urls(settings.enable_api_docs),
)

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
    status = "ok" if db_ok and redis_ok else "degraded"
    return {
        "status": status,
        "service": "knowledgeflow-api",
        "checks": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    }
