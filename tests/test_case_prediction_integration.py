"""
Integration tests for the /case_prediction endpoint.

These tests verify that the /case_prediction endpoint correctly processes
requests and returns valid responses with proper aggregation logic.
"""

from trademark_core import models


def make_valid_case_prediction_request() -> dict:
    """Helper to construct a valid CasePredictionRequest as dict for the /case_prediction endpoint."""
    # Create a mark similarity output
    mark_similarity = models.MarkSimilarityOutput(
        visual="moderate",
        aural="moderate",
        conceptual="low",
        overall="moderate",
        reasoning="The marks share some visual and aural elements but have different meanings."
    )
    
    # Create some G/S likelihood outputs
    gs_likelihoods = [
        models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.85,
            likelihood_of_confusion=True,
            confusion_type="direct"
        ),
        models.GoodServiceLikelihoodOutput(
            are_competitive=False,
            are_complementary=True,
            similarity_score=0.4,
            likelihood_of_confusion=False,
            confusion_type=None
        )
    ]
    
    return models.CasePredictionRequest(
        mark_similarity=mark_similarity,
        goods_services_likelihoods=gs_likelihoods
    ).model_dump()


def test_case_prediction_success(test_client):
    """Test /case_prediction endpoint with valid input returns HTTP 200 and CasePredictionResult structure."""
    payload = make_valid_case_prediction_request()
    response = test_client.post("/case_prediction", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Check that response matches CasePredictionResult structure
    expected_keys = {"mark_comparison", "goods_services_likelihoods", "opposition_outcome"}
    assert set(data.keys()) == expected_keys
    
    # Check opposition_outcome structure
    outcome = data["opposition_outcome"]
    assert set(outcome.keys()) == {"result", "confidence", "reasoning"}
    assert outcome["result"] in ["Opposition likely to succeed", "Opposition may partially succeed", "Opposition likely to fail"]
    assert 0.0 <= outcome["confidence"] <= 1.0
    assert outcome["reasoning"]  # Not empty
    
    # Verify input data is preserved in the response
    assert data["mark_comparison"] == payload["mark_similarity"]
    assert len(data["goods_services_likelihoods"]) == len(payload["goods_services_likelihoods"])


def test_case_prediction_all_confusion(test_client):
    """Test /case_prediction endpoint when all G/S pairs have likelihood of confusion."""
    mark_similarity = models.MarkSimilarityOutput(
        visual="high", aural="high", conceptual="high", overall="high"
    )
    
    # All G/S pairs with likelihood of confusion
    gs_likelihoods = [
        models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.9,
            likelihood_of_confusion=True,
            confusion_type="direct"
        ),
        models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.8,
            likelihood_of_confusion=True,
            confusion_type="direct"
        )
    ]
    
    payload = models.CasePredictionRequest(
        mark_similarity=mark_similarity,
        goods_services_likelihoods=gs_likelihoods
    ).model_dump()
    
    response = test_client.post("/case_prediction", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # All confusion should result in "likely to succeed"
    assert data["opposition_outcome"]["result"] == "Opposition likely to succeed"
    assert data["opposition_outcome"]["confidence"] >= 0.8


def test_case_prediction_no_confusion(test_client):
    """Test /case_prediction endpoint when no G/S pairs have likelihood of confusion."""
    mark_similarity = models.MarkSimilarityOutput(
        visual="low", aural="low", conceptual="low", overall="low"
    )
    
    # No G/S pairs with likelihood of confusion
    gs_likelihoods = [
        models.GoodServiceLikelihoodOutput(
            are_competitive=False,
            are_complementary=False,
            similarity_score=0.2,
            likelihood_of_confusion=False,
            confusion_type=None
        ),
        models.GoodServiceLikelihoodOutput(
            are_competitive=False,
            are_complementary=False,
            similarity_score=0.1,
            likelihood_of_confusion=False,
            confusion_type=None
        )
    ]
    
    payload = models.CasePredictionRequest(
        mark_similarity=mark_similarity,
        goods_services_likelihoods=gs_likelihoods
    ).model_dump()
    
    response = test_client.post("/case_prediction", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # No confusion should result in "likely to fail"
    assert data["opposition_outcome"]["result"] == "Opposition likely to fail"
    assert data["opposition_outcome"]["confidence"] >= 0.8


def test_case_prediction_partial_confusion(test_client):
    """Test /case_prediction endpoint when some but not all G/S pairs have likelihood of confusion."""
    mark_similarity = models.MarkSimilarityOutput(
        visual="moderate", aural="moderate", conceptual="moderate", overall="moderate"
    )
    
    # Mixed G/S confusion
    gs_likelihoods = [
        models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.75,
            likelihood_of_confusion=True,
            confusion_type="direct"
        ),
        models.GoodServiceLikelihoodOutput(
            are_competitive=False,
            are_complementary=False,
            similarity_score=0.3,
            likelihood_of_confusion=False,
            confusion_type=None
        )
    ]
    
    payload = models.CasePredictionRequest(
        mark_similarity=mark_similarity,
        goods_services_likelihoods=gs_likelihoods
    ).model_dump()
    
    response = test_client.post("/case_prediction", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Partial confusion should result in "may partially succeed"
    assert data["opposition_outcome"]["result"] == "Opposition may partially succeed"


def test_case_prediction_invalid_input(test_client):
    """Test /case_prediction endpoint with invalid input returns HTTP 422."""
    # Remove required field 'mark_similarity' from payload
    payload = make_valid_case_prediction_request()
    del payload["mark_similarity"]
    response = test_client.post("/case_prediction", json=payload)
    assert response.status_code == 422 