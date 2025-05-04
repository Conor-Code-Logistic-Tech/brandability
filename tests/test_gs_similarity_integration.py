"""
Integration tests for the /gs_similarity endpoint.

These tests verify that the /gs_similarity endpoint correctly processes
requests and returns valid responses, including actual LLM calls.
"""

from trademark_core import models


def make_valid_gs_similarity_request() -> dict:
    """Helper to construct a valid GsSimilarityRequest as dict for the /gs_similarity endpoint."""
    # Create a mark similarity output matching what the /mark_similarity endpoint would return
    mark_similarity = models.MarkSimilarityOutput(
        visual="moderate",
        aural="moderate",
        conceptual="low",
        overall="moderate",
        reasoning="The marks share some visual and aural elements but have different meanings."
    )
    
    return models.GsSimilarityRequest(
        applicant_good=models.GoodService(term="Software for legal research", nice_class=42),
        opponent_good=models.GoodService(term="Computer software for legal case management", nice_class=42),
        mark_similarity=mark_similarity
    ).model_dump()


def test_gs_similarity_success(test_client):
    """Test /gs_similarity endpoint with valid input returns HTTP 200 and GoodServiceLikelihoodOutput structure."""
    payload = make_valid_gs_similarity_request()
    response = test_client.post("/gs_similarity", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Check that response matches GoodServiceLikelihoodOutput structure
    expected_keys = {"are_competitive", "are_complementary", "similarity_score", "likelihood_of_confusion"}
    assert set(data.keys()) >= expected_keys
    
    # Verify types of the returned data
    assert isinstance(data["are_competitive"], bool)
    assert isinstance(data["are_complementary"], bool)
    assert isinstance(data["similarity_score"], (int, float))
    assert isinstance(data["likelihood_of_confusion"], bool)
    assert 0.0 <= data["similarity_score"] <= 1.0
    
    # If confusion_type is present, it should be one of the valid values
    if data["likelihood_of_confusion"] and "confusion_type" in data:
        assert data["confusion_type"] in ["direct", "indirect"]
    elif not data["likelihood_of_confusion"] and "confusion_type" in data:
        assert data["confusion_type"] is None


def test_gs_similarity_identical_goods(test_client):
    """Test /gs_similarity endpoint with identical goods returns appropriate assessment."""
    mark_similarity = models.MarkSimilarityOutput(
        visual="high", aural="high", conceptual="high", overall="high"
    )
    
    payload = models.GsSimilarityRequest(
        applicant_good=models.GoodService(term="Legal software", nice_class=9),
        opponent_good=models.GoodService(term="Legal software", nice_class=9),
        mark_similarity=mark_similarity
    ).model_dump()
    
    response = test_client.post("/gs_similarity", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Identical goods with high mark similarity should be competitive
    # and have a high likelihood of confusion
    assert data["are_competitive"] is True
    assert data["similarity_score"] >= 0.8
    assert data["likelihood_of_confusion"] is True


def test_gs_similarity_dissimilar_goods(test_client):
    """Test /gs_similarity endpoint with clearly different goods returns appropriate assessment."""
    mark_similarity = models.MarkSimilarityOutput(
        visual="low", aural="low", conceptual="low", overall="low"
    )
    
    payload = models.GsSimilarityRequest(
        applicant_good=models.GoodService(term="Live plants", nice_class=31),
        opponent_good=models.GoodService(term="Vehicles", nice_class=12),
        mark_similarity=mark_similarity
    ).model_dump()
    
    response = test_client.post("/gs_similarity", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # These should be non-competitive goods with a low likelihood of confusion
    assert data["are_competitive"] is False
    assert data["similarity_score"] <= 0.3
    # Even with conceptually related marks, these goods are so different
    # that confusion is unlikely


def test_gs_similarity_interdependence_principle(test_client):
    """Test that the interdependence principle is applied correctly - higher mark similarity can offset lower G/S similarity."""
    # High mark similarity
    mark_similarity = models.MarkSimilarityOutput(
        visual="high", aural="high", conceptual="high", overall="high"
    )
    
    payload = models.GsSimilarityRequest(
        # Somewhat related but not identical goods
        applicant_good=models.GoodService(term="Clothing", nice_class=25),
        opponent_good=models.GoodService(term="Footwear", nice_class=25),
        mark_similarity=mark_similarity
    ).model_dump()
    
    response = test_client.post("/gs_similarity", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # With high mark similarity, even somewhat related goods
    # should have a likelihood of confusion
    assert data["likelihood_of_confusion"] is True


def test_gs_similarity_invalid_input(test_client):
    """Test /gs_similarity endpoint with invalid input returns HTTP 422."""
    # Remove required field 'applicant_good' from payload
    payload = make_valid_gs_similarity_request()
    del payload["applicant_good"]
    response = test_client.post("/gs_similarity", json=payload)
    assert response.status_code == 422 