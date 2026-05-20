import os

import pytest
from fastapi.testclient import TestClient

from app.main import app  # noqa: E402
from app.middleware.rate_limit import limiter

os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-123")
os.environ.setdefault("OPENAI_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """
    Disable rate limiting globally for all tests to prevent 429 errors
    during functional testing.
    """
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)
