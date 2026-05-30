import pytest

from app.core.auth import get_current_user_id
from app.main import app


@pytest.fixture(autouse=True)
def override_auth() -> None:
    app.dependency_overrides[get_current_user_id] = lambda: "test-user"
    yield
    app.dependency_overrides.clear()
