import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["TEST_MODE"] = "True"
import dotenv

dotenv.load_dotenv(dotenv_path=".env.local", override=True)
import pytest
from fastapi.testclient import TestClient

from api.main import app
from mocks import apply_llm_mocks

# Check if we should apply mocks or use real LLM services
USE_MOCKS = os.environ.get("USE_LLM_MOCKS", "1") == "1"

# Apply LLM mocks before any tests run, but only if explicitly requested
if USE_MOCKS:
    apply_llm_mocks()
    print("Using LLM mocks for testing")
else:
    print("Using real LLM services for testing")


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    """Fixture providing a FastAPI test client for high-level API tests."""
    return TestClient(app)


@pytest.fixture
def use_mocks():
    """Fixture that returns whether mocks are being used or not."""
    return USE_MOCKS
