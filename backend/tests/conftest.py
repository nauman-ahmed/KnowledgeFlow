from unittest.mock import MagicMock, patch

import pytest

from app.core.auth import get_current_user_id
from app.core.database import init_db
from app.core.observability import _NoOpTrace
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> None:
    """Create tables once. TestClient(app) without a `with` block skips the lifespan
    that normally calls init_db(), so a fresh database (e.g. in CI) has no tables."""
    init_db()


@pytest.fixture(autouse=True)
def override_auth() -> None:
    app.dependency_overrides[get_current_user_id] = lambda: "test-user"
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def noop_langfuse_tracer():
    """Keep tests offline — real Langfuse keys in .env should not affect pytest."""
    mock_tracer = MagicMock()
    mock_tracer.enabled = False
    mock_tracer.trace.return_value.__enter__ = MagicMock(return_value=_NoOpTrace())
    mock_tracer.trace.return_value.__exit__ = MagicMock(return_value=False)
    with patch("app.services.chat_service.get_tracer", return_value=mock_tracer):
        yield mock_tracer
