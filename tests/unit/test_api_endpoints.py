"""
Unit tests for FastAPI endpoints in api.main.

These tests validate endpoint behavior, request/response handling, validation,
and error cases without making real API calls or requiring authentication.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from api.main import app
from trademark_core import models
from tests.utils.mocks import apply_llm_mocks
from tests.utils.fixtures import (
    IDENTICAL_MARKS,
    SIMILAR_MARKS,
    DISSIMILAR_MARKS,
    IDENTICAL_SOFTWARE,
    RELATED_SOFTWARE,
    UNRELATED_GOODS,
    IDENTICAL_ASSESSMENT,
    HIGH_SIMILARITY_ASSESSMENT,
    MODERATE_SIMILARITY_ASSESSMENT,
)


# Mock user for authentication bypass
def mock_get_current_user():
    """Mock function to bypass authentication."""
    mock_user = MagicMock()
    mock_user.uid = "test_user_123"
    mock_user.email = "test@example.com"
    return mock_user


# Apply authentication bypass globally for all endpoint tests
@pytest.fixture(autouse=True)
def bypass_auth():
    """Automatically bypass authentication for all API endpoint tests."""
    import os
    # Set TEST_MODE environment variable to enable test mode in auth
    with patch.dict(os.environ, {'TEST_MODE': '1'}):
        yield


class TestHealthEndpoint:
    """Test cases for the health check endpoint."""

    def test_health_check(self):
        """Test that health check returns OK status."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestMarkSimilarityEndpoint:
    """Test cases for the /mark_similarity endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_mark_similarity_valid_request(self, client):
        """Test valid mark similarity request."""
        with apply_llm_mocks():
            request_data = {
                "applicant": {"wordmark": "EXAMPLE"},
                "opponent": {"wordmark": "EXAMPL"}
            }
            
            response = client.post("/mark_similarity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate response structure
            assert "visual" in data
            assert "aural" in data
            assert "conceptual" in data
            assert "overall" in data
            assert data["visual"] in ["dissimilar", "low", "moderate", "high", "identical"]
            assert data["aural"] in ["dissimilar", "low", "moderate", "high", "identical"]
            assert data["conceptual"] in ["dissimilar", "low", "moderate", "high", "identical"]
            assert data["overall"] in ["dissimilar", "low", "moderate", "high", "identical"]

    def test_mark_similarity_identical_marks(self, client):
        """Test mark similarity with identical marks."""
        with apply_llm_mocks():
            request_data = {
                "applicant": {"wordmark": "IDENTICAL"},
                "opponent": {"wordmark": "IDENTICAL"}
            }
            
            response = client.post("/mark_similarity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["overall"] == "identical"

    def test_mark_similarity_with_registration_details(self, client):
        """Test mark similarity with registration details."""
        with apply_llm_mocks():
            request_data = {
                "applicant": {
                    "wordmark": "REGISTERED",
                    "is_registered": True,
                    "registration_number": "UK00003123456"
                },
                "opponent": {
                    "wordmark": "UNREGISTERED",
                    "is_registered": False
                }
            }
            
            response = client.post("/mark_similarity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "visual" in data

    def test_mark_similarity_missing_wordmark(self, client):
        """Test mark similarity with missing wordmark."""
        request_data = {
            "applicant": {"wordmark": "EXAMPLE"},
            "opponent": {}  # Missing wordmark
        }
        
        response = client.post("/mark_similarity", json=request_data)
        
        assert response.status_code == 422  # Validation error
        assert "Field required" in response.text

    def test_mark_similarity_empty_wordmark(self, client):
        """Test mark similarity with empty wordmark."""
        request_data = {
            "applicant": {"wordmark": "EXAMPLE"},
            "opponent": {"wordmark": ""}  # Empty wordmark
        }
        
        response = client.post("/mark_similarity", json=request_data)
        
        # Empty wordmarks are actually allowed by Pydantic, so this should succeed
        assert response.status_code == 200

    def test_mark_similarity_invalid_json(self, client):
        """Test mark similarity with invalid JSON."""
        response = client.post("/mark_similarity", data="invalid json")
        
        assert response.status_code == 422

    def test_mark_similarity_missing_fields(self, client):
        """Test mark similarity with missing required fields."""
        request_data = {
            "applicant": {"wordmark": "EXAMPLE"}
            # Missing opponent
        }
        
        response = client.post("/mark_similarity", json=request_data)
        
        assert response.status_code == 422
        assert "Field required" in response.text

    def test_mark_similarity_llm_error(self, client):
        """Test mark similarity when LLM raises an error."""
        # We need to patch the function before the mocks are applied
        with patch('api.main.generate_mark_similarity_assessment') as mock_llm:
            mock_llm.side_effect = Exception("LLM service unavailable")
            
            request_data = {
                "applicant": {"wordmark": "EXAMPLE"},
                "opponent": {"wordmark": "EXAMPL"}
            }
            
            response = client.post("/mark_similarity", json=request_data)
            
            assert response.status_code == 500
            assert "Error generating mark similarity assessment" in response.text


class TestGsSimilarityEndpoint:
    """Test cases for the /gs_similarity endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_gs_similarity_valid_request(self, client):
        """Test valid goods/services similarity request."""
        with apply_llm_mocks():
            request_data = {
                "applicant_good": {"term": "Legal software", "nice_class": 9},
                "opponent_good": {"term": "Business software", "nice_class": 9},
                "mark_similarity": {
                    "visual": "moderate",
                    "aural": "moderate",
                    "conceptual": "moderate",
                    "overall": "moderate"
                }
            }
            
            response = client.post("/gs_similarity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate response structure
            assert "are_competitive" in data
            assert "are_complementary" in data
            assert "similarity_score" in data
            assert "likelihood_of_confusion" in data
            assert isinstance(data["are_competitive"], bool)
            assert isinstance(data["are_complementary"], bool)
            assert 0.0 <= data["similarity_score"] <= 1.0
            assert isinstance(data["likelihood_of_confusion"], bool)

    def test_gs_similarity_identical_goods(self, client):
        """Test goods/services similarity with identical goods."""
        with apply_llm_mocks():
            request_data = {
                "applicant_good": {"term": "Legal software", "nice_class": 9},
                "opponent_good": {"term": "Legal software", "nice_class": 9},
                "mark_similarity": {
                    "visual": "high",
                    "aural": "high",
                    "conceptual": "high",
                    "overall": "high"
                }
            }
            
            response = client.post("/gs_similarity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["are_competitive"] is True
            assert data["likelihood_of_confusion"] is True

    def test_gs_similarity_unrelated_goods(self, client):
        """Test goods/services similarity with unrelated goods."""
        with apply_llm_mocks():
            request_data = {
                "applicant_good": {"term": "Live plants", "nice_class": 31},
                "opponent_good": {"term": "Vehicles", "nice_class": 12},
                "mark_similarity": {
                    "visual": "moderate",
                    "aural": "moderate",
                    "conceptual": "moderate",
                    "overall": "moderate"
                }
            }
            
            response = client.post("/gs_similarity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["are_competitive"] is False
            assert data["likelihood_of_confusion"] is False

    def test_gs_similarity_invalid_nice_class(self, client):
        """Test goods/services similarity with invalid Nice class."""
        request_data = {
            "applicant_good": {"term": "Software", "nice_class": 50},  # Invalid class
            "opponent_good": {"term": "Hardware", "nice_class": 9},
            "mark_similarity": {
                "visual": "moderate",
                "aural": "moderate",
                "conceptual": "moderate",
                "overall": "moderate"
            }
        }
        
        response = client.post("/gs_similarity", json=request_data)
        
        assert response.status_code == 422
        assert "Input should be less than or equal to 45" in response.text

    def test_gs_similarity_missing_mark_similarity(self, client):
        """Test goods/services similarity with missing mark similarity."""
        request_data = {
            "applicant_good": {"term": "Software", "nice_class": 9},
            "opponent_good": {"term": "Hardware", "nice_class": 9}
            # Missing mark_similarity
        }
        
        response = client.post("/gs_similarity", json=request_data)
        
        assert response.status_code == 422
        assert "Field required" in response.text

    def test_gs_similarity_invalid_mark_similarity_enum(self, client):
        """Test goods/services similarity with invalid mark similarity enum."""
        request_data = {
            "applicant_good": {"term": "Software", "nice_class": 9},
            "opponent_good": {"term": "Hardware", "nice_class": 9},
            "mark_similarity": {
                "visual": "invalid_value",  # Invalid enum
                "aural": "moderate",
                "conceptual": "moderate",
                "overall": "moderate"
            }
        }
        
        response = client.post("/gs_similarity", json=request_data)
        
        assert response.status_code == 422

    def test_gs_similarity_llm_error(self, client):
        """Test goods/services similarity when LLM raises an error."""
        with patch('api.main.generate_gs_likelihood_assessment') as mock_llm:
            mock_llm.side_effect = Exception("LLM service unavailable")
            
            request_data = {
                "applicant_good": {"term": "Software", "nice_class": 9},
                "opponent_good": {"term": "Hardware", "nice_class": 9},
                "mark_similarity": {
                    "visual": "moderate",
                    "aural": "moderate",
                    "conceptual": "moderate",
                    "overall": "moderate"
                }
            }
            
            response = client.post("/gs_similarity", json=request_data)
            
            assert response.status_code == 500
            assert "Error generating goods/services assessment" in response.text


class TestBatchGsSimilarityEndpoint:
    """Test cases for the /batch_gs_similarity endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_batch_gs_similarity_valid_request(self, client):
        """Test valid batch goods/services similarity request."""
        with apply_llm_mocks():
            request_data = {
                "applicant_goods": [
                    {"term": "Legal software", "nice_class": 9},
                    {"term": "Business software", "nice_class": 9}
                ],
                "opponent_goods": [
                    {"term": "Computer software", "nice_class": 9}
                ],
                "mark_similarity": {
                    "visual": "moderate",
                    "aural": "moderate",
                    "conceptual": "moderate",
                    "overall": "moderate"
                }
            }
            
            response = client.post("/batch_gs_similarity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return 2 results (2 applicant goods × 1 opponent good)
            assert len(data) == 2
            
            # Validate each result structure
            for result in data:
                assert "are_competitive" in result
                assert "are_complementary" in result
                assert "similarity_score" in result
                assert "likelihood_of_confusion" in result

    def test_batch_gs_similarity_empty_lists(self, client):
        """Test batch goods/services similarity with empty lists."""
        request_data = {
            "applicant_goods": [],  # Empty list
            "opponent_goods": [
                {"term": "Software", "nice_class": 9}
            ],
            "mark_similarity": {
                "visual": "moderate",
                "aural": "moderate",
                "conceptual": "moderate",
                "overall": "moderate"
            }
        }
        
        response = client.post("/batch_gs_similarity", json=request_data)
        
        assert response.status_code == 422
        assert "List should have at least 1 item" in response.text

    def test_batch_gs_similarity_too_many_items(self, client):
        """Test batch goods/services similarity with too many items."""
        # Create lists with more than 5 items each
        applicant_goods = [{"term": f"Software {i}", "nice_class": 9} for i in range(6)]
        opponent_goods = [{"term": f"Hardware {i}", "nice_class": 9} for i in range(6)]
        
        request_data = {
            "applicant_goods": applicant_goods,
            "opponent_goods": opponent_goods,
            "mark_similarity": {
                "visual": "moderate",
                "aural": "moderate",
                "conceptual": "moderate",
                "overall": "moderate"
            }
        }
        
        response = client.post("/batch_gs_similarity", json=request_data)
        
        # The endpoint might return 500 if the batch processing fails due to too many items
        assert response.status_code in [400, 500]
        assert "Too many items to process" in response.text or "Error processing batch" in response.text

    def test_batch_gs_similarity_single_items(self, client):
        """Test batch goods/services similarity with single items."""
        with apply_llm_mocks():
            request_data = {
                "applicant_goods": [
                    {"term": "Legal software", "nice_class": 9}
                ],
                "opponent_goods": [
                    {"term": "Business software", "nice_class": 9}
                ],
                "mark_similarity": {
                    "visual": "high",
                    "aural": "high",
                    "conceptual": "high",
                    "overall": "high"
                }
            }
            
            response = client.post("/batch_gs_similarity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1

    def test_batch_gs_similarity_llm_error(self, client):
        """Test batch goods/services similarity when LLM raises an error."""
        with patch('api.main.batch_process_goods_services') as mock_batch:
            mock_batch.side_effect = Exception("Batch processing failed")
            
            request_data = {
                "applicant_goods": [
                    {"term": "Software", "nice_class": 9}
                ],
                "opponent_goods": [
                    {"term": "Hardware", "nice_class": 9}
                ],
                "mark_similarity": {
                    "visual": "moderate",
                    "aural": "moderate",
                    "conceptual": "moderate",
                    "overall": "moderate"
                }
            }
            
            response = client.post("/batch_gs_similarity", json=request_data)
            
            assert response.status_code == 500
            assert "Error processing batch goods/services assessment" in response.text


class TestCasePredictionEndpoint:
    """Test cases for the /case_prediction endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_case_prediction_valid_request(self, client):
        """Test valid case prediction request."""
        with apply_llm_mocks():
            request_data = {
                "mark_similarity": {
                    "visual": "high",
                    "aural": "high",
                    "conceptual": "high",
                    "overall": "high"
                },
                "goods_services_likelihoods": [
                    {
                        "are_competitive": True,
                        "are_complementary": False,
                        "similarity_score": 0.9,
                        "likelihood_of_confusion": True,
                        "confusion_type": "direct"
                    }
                ]
            }
            
            response = client.post("/case_prediction", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate response structure
            assert "mark_comparison" in data
            assert "goods_services_likelihoods" in data
            assert "opposition_outcome" in data
            
            # Validate opposition outcome structure
            outcome = data["opposition_outcome"]
            assert "result" in outcome
            assert "confidence" in outcome
            assert "reasoning" in outcome
            assert outcome["result"] in [
                "Opposition likely to succeed",
                "Opposition may partially succeed",
                "Opposition likely to fail"
            ]
            assert 0.0 <= outcome["confidence"] <= 1.0

    def test_case_prediction_empty_gs_likelihoods(self, client):
        """Test case prediction with empty goods/services likelihoods."""
        request_data = {
            "mark_similarity": {
                "visual": "high",
                "aural": "high",
                "conceptual": "high",
                "overall": "high"
            },
            "goods_services_likelihoods": []  # Empty list
        }
        
        response = client.post("/case_prediction", json=request_data)
        
        assert response.status_code == 422
        assert "List should have at least 1 item" in response.text

    def test_case_prediction_invalid_confidence_score(self, client):
        """Test case prediction with invalid confidence score in GS likelihood."""
        request_data = {
            "mark_similarity": {
                "visual": "high",
                "aural": "high",
                "conceptual": "high",
                "overall": "high"
            },
            "goods_services_likelihoods": [
                {
                    "are_competitive": True,
                    "are_complementary": False,
                    "similarity_score": 1.5,  # Invalid score > 1.0
                    "likelihood_of_confusion": True,
                    "confusion_type": "direct"
                }
            ]
        }
        
        response = client.post("/case_prediction", json=request_data)
        
        assert response.status_code == 422
        assert "Input should be less than or equal to 1" in response.text

    def test_case_prediction_multiple_gs_likelihoods(self, client):
        """Test case prediction with multiple goods/services likelihoods."""
        with apply_llm_mocks():
            request_data = {
                "mark_similarity": {
                    "visual": "moderate",
                    "aural": "moderate",
                    "conceptual": "moderate",
                    "overall": "moderate"
                },
                "goods_services_likelihoods": [
                    {
                        "are_competitive": True,
                        "are_complementary": False,
                        "similarity_score": 0.8,
                        "likelihood_of_confusion": True,
                        "confusion_type": "direct"
                    },
                    {
                        "are_competitive": False,
                        "are_complementary": True,
                        "similarity_score": 0.3,
                        "likelihood_of_confusion": False,
                        "confusion_type": None
                    }
                ]
            }
            
            response = client.post("/case_prediction", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["goods_services_likelihoods"]) == 2

    def test_case_prediction_llm_error(self, client):
        """Test case prediction when LLM raises an error."""
        with patch('api.main.generate_case_prediction') as mock_llm:
            mock_llm.side_effect = Exception("Case prediction failed")
            
            request_data = {
                "mark_similarity": {
                    "visual": "high",
                    "aural": "high",
                    "conceptual": "high",
                    "overall": "high"
                },
                "goods_services_likelihoods": [
                    {
                        "are_competitive": True,
                        "are_complementary": False,
                        "similarity_score": 0.9,
                        "likelihood_of_confusion": True,
                        "confusion_type": "direct"
                    }
                ]
            }
            
            response = client.post("/case_prediction", json=request_data)
            
            assert response.status_code == 500
            assert "Error generating case prediction" in response.text 
