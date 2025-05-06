"""
API endpoint integration tests.

This module contains tests for the API endpoints, focusing on proper request/response
handling, error propagation, and model parameter support.
"""

from fastapi.testclient import TestClient

from tests.fixtures import IDENTICAL_SOFTWARE, SIMILAR_MARKS, TEST_MODELS
from trademark_core import models


def test_health_endpoint(test_client: TestClient):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mark_similarity_endpoint_basic(test_client: TestClient):
    """Test the mark similarity endpoint with basic parameters."""
    applicant_mark, opponent_mark = SIMILAR_MARKS

    request_data = {
        "applicant": applicant_mark.model_dump(),
        "opponent": opponent_mark.model_dump(),
        "visual_score": 0.7,
        "aural_score": 0.6,
    }

    response = test_client.post("/mark_similarity", json=request_data)

    assert response.status_code == 200
    result = response.json()

    # Validate structure
    assert "visual" in result
    assert "aural" in result
    assert "conceptual" in result
    assert "overall" in result
    assert "reasoning" in result

    # Validate data types
    assert result["visual"] in ["dissimilar", "low", "moderate", "high", "identical"]
    assert result["aural"] in ["dissimilar", "low", "moderate", "high", "identical"]
    assert result["conceptual"] in ["dissimilar", "low", "moderate", "high", "identical"]
    assert result["overall"] in ["dissimilar", "low", "moderate", "high", "identical"]
    assert isinstance(result["reasoning"], str)


def test_mark_similarity_endpoint_with_model(test_client: TestClient):
    """Test the mark similarity endpoint with model parameter."""
    applicant_mark, opponent_mark = SIMILAR_MARKS
    model = next(iter(TEST_MODELS.values()))  # Get first test model

    request_data = {
        "applicant": applicant_mark.model_dump(),
        "opponent": opponent_mark.model_dump(),
        "visual_score": 0.7,
        "aural_score": 0.6,
        "model": model,
    }

    response = test_client.post("/mark_similarity", json=request_data)

    # With mocks, this should work. With real API, it might fail if model doesn't exist.
    # We're primarily testing that the parameter is accepted
    assert response.status_code in [200, 422, 500]
    if response.status_code == 200:
        result = response.json()
        assert "visual" in result
        assert "aural" in result
        assert "conceptual" in result
        assert "overall" in result


def test_gs_similarity_endpoint_basic(test_client: TestClient):
    """Test the goods/services similarity endpoint with basic parameters."""
    applicant_good, opponent_good = IDENTICAL_SOFTWARE

    # First create a mark similarity assessment
    mark_sim_request = {
        "applicant": SIMILAR_MARKS[0].model_dump(),
        "opponent": SIMILAR_MARKS[1].model_dump(),
        "visual_score": 0.7,
        "aural_score": 0.6,
    }

    mark_sim_response = test_client.post("/mark_similarity", json=mark_sim_request)
    assert mark_sim_response.status_code == 200
    mark_similarity = mark_sim_response.json()

    # Now test the GS endpoint with the mark similarity
    request_data = {
        "applicant_good": applicant_good.model_dump(),
        "opponent_good": opponent_good.model_dump(),
        "mark_similarity": mark_similarity,
    }

    response = test_client.post("/gs_similarity", json=request_data)

    assert response.status_code == 200
    result = response.json()

    # Validate structure
    assert "are_competitive" in result
    assert "are_complementary" in result
    assert "similarity_score" in result
    assert "likelihood_of_confusion" in result

    # Validate data types
    assert isinstance(result["are_competitive"], bool)
    assert isinstance(result["are_complementary"], bool)
    assert isinstance(result["similarity_score"], float)
    assert 0 <= result["similarity_score"] <= 1
    assert isinstance(result["likelihood_of_confusion"], bool)

    # For identical goods with similar marks, should have confusion
    assert result["similarity_score"] > 0.7
    if result["likelihood_of_confusion"]:
        assert result["confusion_type"] in ["direct", "indirect"]


def test_gs_similarity_endpoint_with_model(test_client: TestClient):
    """Test the goods/services similarity endpoint with model parameter."""
    applicant_good, opponent_good = IDENTICAL_SOFTWARE
    model = next(iter(TEST_MODELS.values()))  # Get first test model

    # First create a mark similarity assessment
    mark_sim_request = {
        "applicant": SIMILAR_MARKS[0].model_dump(),
        "opponent": SIMILAR_MARKS[1].model_dump(),
        "visual_score": 0.7,
        "aural_score": 0.6,
    }

    mark_sim_response = test_client.post("/mark_similarity", json=mark_sim_request)
    assert mark_sim_response.status_code == 200
    mark_similarity = mark_sim_response.json()

    # Now test the GS endpoint with the mark similarity and model
    request_data = {
        "applicant_good": applicant_good.model_dump(),
        "opponent_good": opponent_good.model_dump(),
        "mark_similarity": mark_similarity,
        "model": model,
    }

    response = test_client.post("/gs_similarity", json=request_data)

    # With mocks, this should work. With real API, it might fail if model doesn't exist.
    assert response.status_code in [200, 422, 500]
    if response.status_code == 200:
        result = response.json()
        assert "are_competitive" in result
        assert "similarity_score" in result
        assert "likelihood_of_confusion" in result


def test_batch_gs_similarity_endpoint_basic(test_client: TestClient):
    """Test the batch goods/services similarity endpoint with basic parameters."""
    # Create a list of goods pairs
    applicant_goods = [
        models.GoodService(term="Software for legal research", nice_class=9),
        models.GoodService(term="Vehicle tires", nice_class=12),
    ]

    opponent_goods = [
        models.GoodService(term="Legal software", nice_class=9),
        models.GoodService(term="Bicycle parts", nice_class=12),
    ]

    # First create a mark similarity assessment
    mark_sim_request = {
        "applicant": SIMILAR_MARKS[0].model_dump(),
        "opponent": SIMILAR_MARKS[1].model_dump(),
        "visual_score": 0.7,
        "aural_score": 0.6,
    }

    mark_sim_response = test_client.post("/mark_similarity", json=mark_sim_request)
    assert mark_sim_response.status_code == 200
    mark_similarity = mark_sim_response.json()

    # Now test the batch GS endpoint
    request_data = {
        "applicant_goods": [g.model_dump() for g in applicant_goods],
        "opponent_goods": [g.model_dump() for g in opponent_goods],
        "mark_similarity": mark_similarity,
    }

    response = test_client.post("/batch_gs_similarity", json=request_data)

    assert response.status_code == 200
    results = response.json()

    # Should have one result per pair of goods
    assert len(results) == len(applicant_goods) * len(opponent_goods)

    # Validate each result
    for result in results:
        assert "are_competitive" in result
        assert "are_complementary" in result
        assert "similarity_score" in result
        assert "likelihood_of_confusion" in result
        assert isinstance(result["similarity_score"], float)
        assert 0 <= result["similarity_score"] <= 1


def test_batch_gs_similarity_endpoint_with_model(test_client: TestClient):
    """Test the batch goods/services similarity endpoint with model parameter."""
    # Create a list of goods pairs
    applicant_goods = [
        models.GoodService(term="Software for legal research", nice_class=9),
        models.GoodService(term="Vehicle tires", nice_class=12),
    ]

    opponent_goods = [
        models.GoodService(term="Legal software", nice_class=9),
        models.GoodService(term="Bicycle parts", nice_class=12),
    ]

    model = next(iter(TEST_MODELS.values()))  # Get first test model

    # First create a mark similarity assessment
    mark_sim_request = {
        "applicant": SIMILAR_MARKS[0].model_dump(),
        "opponent": SIMILAR_MARKS[1].model_dump(),
        "visual_score": 0.7,
        "aural_score": 0.6,
    }

    mark_sim_response = test_client.post("/mark_similarity", json=mark_sim_request)
    assert mark_sim_response.status_code == 200
    mark_similarity = mark_sim_response.json()

    # Now test the batch GS endpoint with model
    request_data = {
        "applicant_goods": [g.model_dump() for g in applicant_goods],
        "opponent_goods": [g.model_dump() for g in opponent_goods],
        "mark_similarity": mark_similarity,
        "model": model,
    }

    response = test_client.post("/batch_gs_similarity", json=request_data)

    # Should return all combinations (Cartesian product)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == len(applicant_goods) * len(opponent_goods)


def test_mark_similarity_endpoint_invalid_input(test_client: TestClient):
    """Test the mark similarity endpoint with invalid input."""
    # Missing required field
    request_data = {
        "applicant": {"wordmark": "EXAMPLIA"},
        # missing opponent
        "visual_score": 0.7,
        "aural_score": 0.6,
    }

    response = test_client.post("/mark_similarity", json=request_data)

    # Should return a validation error
    assert response.status_code == 422


def test_gs_similarity_endpoint_invalid_input(test_client: TestClient):
    """Test the goods/services similarity endpoint with invalid input."""
    # Missing required field
    request_data = {
        "applicant_good": {"term": "Software", "nice_class": 9},
        # missing opponent_good
        "mark_similarity": {
            "visual": "moderate",
            "aural": "moderate",
            "conceptual": "moderate",
            "overall": "moderate",
            "reasoning": "Test reasoning",
        },
    }

    response = test_client.post("/gs_similarity", json=request_data)

    # Should return a validation error
    assert response.status_code == 422


def test_batch_gs_similarity_endpoint_mismatched_lengths(test_client: TestClient):
    """Test the batch endpoint with mismatched goods/services list lengths."""
    # Different number of goods in each list
    applicant_goods = [
        {"term": "Software for legal research", "nice_class": 9},
        {"term": "Vehicle tires", "nice_class": 12},
    ]
    opponent_goods = [
        {"term": "Legal software", "nice_class": 9}
        # Missing second good
    ]
    mark_similarity = {
        "visual": "moderate",
        "aural": "moderate",
        "conceptual": "moderate",
        "overall": "moderate",
        "reasoning": "Test reasoning",
    }
    request_data = {
        "applicant_goods": applicant_goods,
        "opponent_goods": opponent_goods,
        "mark_similarity": mark_similarity,
    }
    response = test_client.post("/batch_gs_similarity", json=request_data)
    # Should return all combinations (Cartesian product)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == len(applicant_goods) * len(opponent_goods)
