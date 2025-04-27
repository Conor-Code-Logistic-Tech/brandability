import os

os.environ["TEST_MODE"] = "1"
import dotenv

dotenv.load_dotenv(dotenv_path=".env.local", override=True)
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    """Fixture providing a FastAPI test client for high-level API tests."""
    return TestClient(app)
