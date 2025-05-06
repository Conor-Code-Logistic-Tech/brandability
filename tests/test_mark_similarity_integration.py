"""
Integration tests for the /mark_similarity endpoint.

These tests verify that the /mark_similarity endpoint correctly processes
requests and returns valid responses, including actual LLM calls.
"""

from trademark_core import models


def make_valid_mark_similarity_request() -> dict:
    """Helper to construct a valid MarkSimilarityRequest as dict for the /mark_similarity endpoint."""
    return models.MarkSimilarityRequest(
        applicant=models.Mark(
            wordmark="EXAMPLIA", is_registered=True, registration_number="1234567"
        ),
        opponent=models.Mark(wordmark="EXEMPLAR", is_registered=False),
    ).model_dump()


def test_mark_similarity_success(test_client):
    """Test /mark_similarity endpoint with valid input returns HTTP 200 and MarkSimilarityOutput structure."""
    payload = make_valid_mark_similarity_request()
    response = test_client.post("/mark_similarity", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Check that response matches MarkSimilarityOutput structure
    assert set(data.keys()) >= {"visual", "aural", "conceptual", "overall"}

    # Verify that each similarity category is a valid EnumStr value
    valid_categories = {"dissimilar", "low", "moderate", "high", "identical"}
    for category in ["visual", "aural", "conceptual", "overall"]:
        assert data[category] in valid_categories

    # If reasoning is present, it should be a non-empty string
    if "reasoning" in data:
        assert isinstance(data["reasoning"], str)
        assert data["reasoning"]  # Not empty


def test_mark_similarity_identical_marks(test_client):
    """Test /mark_similarity endpoint with identical marks returns appropriate similarity ratings."""
    payload = models.MarkSimilarityRequest(
        applicant=models.Mark(wordmark="EXAMPLIA", is_registered=True),
        opponent=models.Mark(wordmark="EXAMPLIA", is_registered=True),
    ).model_dump()

    response = test_client.post("/mark_similarity", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Identical marks should have high or identical visual and aural similarity
    assert data["visual"] in ["high", "identical"]
    assert data["aural"] in ["high", "identical"]
    assert data["overall"] in ["high", "identical"]


def test_mark_similarity_dissimilar_marks(test_client):
    """Test /mark_similarity endpoint with clearly different marks returns appropriate similarity ratings."""
    payload = models.MarkSimilarityRequest(
        applicant=models.Mark(wordmark="ZOOPLANKTON", is_registered=True),
        opponent=models.Mark(wordmark="BUTTERFLY", is_registered=True),
    ).model_dump()

    response = test_client.post("/mark_similarity", json=payload)
    assert response.status_code == 200
    data = response.json()

    # These marks should have low visual and aural similarity
    assert data["visual"] in ["dissimilar", "low"]
    assert data["aural"] in ["dissimilar", "low"]

    # We don't assert on conceptual as it depends on LLM knowledge/interpretation


def test_mark_similarity_invalid_input(test_client):
    """Test /mark_similarity endpoint with invalid input returns HTTP 422."""
    # Remove required field 'applicant' from payload
    payload = make_valid_mark_similarity_request()
    del payload["applicant"]
    response = test_client.post("/mark_similarity", json=payload)
    assert response.status_code == 422
