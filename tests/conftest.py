import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["TEST_MODE"] = "1"
import dotenv

dotenv.load_dotenv(dotenv_path=".env.local", override=True)
import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.mocks import apply_llm_mocks

# Apply LLM mocks before any tests run
apply_llm_mocks()


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    """Fixture providing a FastAPI test client for high-level API tests."""
    return TestClient(app)
