"""
End-to-end integration tests for the complete trademark opposition prediction workflow.

These tests verify that the complete sequence of API calls functions correctly,
from mark similarity to goods/services assessment to final case prediction.
"""

from trademark_core import models


def test_full_workflow_success(test_client):
    """Test the complete workflow from mark similarity to case prediction."""
    # Step 1: Make a mark similarity request
    mark_similarity_payload = models.MarkSimilarityRequest(
        applicant=models.Mark(wordmark="EXAMPLIA", is_registered=True),
        opponent=models.Mark(wordmark="EXEMPLAR", is_registered=True)
    ).model_dump()
    
    # Call the mark similarity endpoint
    mark_response = test_client.post("/mark_similarity", json=mark_similarity_payload)
    assert mark_response.status_code == 200
    mark_similarity = mark_response.json()
    
    # Step 2: Make goods/services similarity requests using the mark similarity result
    gs_pairs = [
        # Pair 1: Similar software products
        {
            "applicant_good": models.GoodService(term="Software for legal research", nice_class=42).model_dump(),
            "opponent_good": models.GoodService(term="Computer software for legal case management", nice_class=42).model_dump(),
            "mark_similarity": mark_similarity
        },
        # Pair 2: Dissimilar products
        {
            "applicant_good": models.GoodService(term="Printed publications", nice_class=16).model_dump(),
            "opponent_good": models.GoodService(term="Electronic books", nice_class=9).model_dump(),
            "mark_similarity": mark_similarity
        }
    ]
    
    # Call the gs_similarity endpoint for each pair
    gs_likelihoods = []
    for gs_pair in gs_pairs:
        gs_response = test_client.post("/gs_similarity", json=gs_pair)
        assert gs_response.status_code == 200
        gs_likelihoods.append(gs_response.json())
    
    # Step 3: Make the case prediction request with the results from steps 1 and 2
    case_prediction_payload = {
        "mark_similarity": mark_similarity,
        "goods_services_likelihoods": gs_likelihoods
    }
    
    # Call the case prediction endpoint
    case_response = test_client.post("/case_prediction", json=case_prediction_payload)
    assert case_response.status_code == 200
    
    # Verify the case prediction result structure
    case_prediction = case_response.json()
    assert "opposition_outcome" in case_prediction
    assert "result" in case_prediction["opposition_outcome"]
    assert "confidence" in case_prediction["opposition_outcome"]
    assert "reasoning" in case_prediction["opposition_outcome"]
    
    # The result should be one of the valid outcome categories
    assert case_prediction["opposition_outcome"]["result"] in [
        "Opposition likely to succeed", 
        "Opposition may partially succeed", 
        "Opposition likely to fail"
    ]


def test_full_workflow_identical_marks_identical_goods(test_client):
    """Test the workflow with identical marks and identical goods which should result in opposition success."""
    # Step 1: Mark similarity for identical marks
    mark_similarity_payload = models.MarkSimilarityRequest(
        applicant=models.Mark(wordmark="IDENTICAL", is_registered=True),
        opponent=models.Mark(wordmark="IDENTICAL", is_registered=True)
    ).model_dump()
    
    mark_response = test_client.post("/mark_similarity", json=mark_similarity_payload)
    assert mark_response.status_code == 200
    mark_similarity = mark_response.json()
    
    # Verify high similarity for identical marks
    assert mark_similarity["visual"] in ["high", "identical"]
    assert mark_similarity["aural"] in ["high", "identical"]
    assert mark_similarity["overall"] in ["high", "identical"]
    
    # Step 2: G/S similarity for identical goods
    gs_pairs = [
        {
            "applicant_good": models.GoodService(term="Identical legal software", nice_class=9).model_dump(),
            "opponent_good": models.GoodService(term="Identical legal software", nice_class=9).model_dump(),
            "mark_similarity": mark_similarity
        }
    ]
    
    gs_likelihoods = []
    for gs_pair in gs_pairs:
        gs_response = test_client.post("/gs_similarity", json=gs_pair)
        assert gs_response.status_code == 200
        gs_likelihood = gs_response.json()
        gs_likelihoods.append(gs_likelihood)
        
        # Verify high similarity and confusion for identical goods
        assert gs_likelihood["similarity_score"] >= 0.8
        assert gs_likelihood["likelihood_of_confusion"] is True
    
    # Step 3: Case prediction
    case_prediction_payload = {
        "mark_similarity": mark_similarity,
        "goods_services_likelihoods": gs_likelihoods
    }
    
    case_response = test_client.post("/case_prediction", json=case_prediction_payload)
    assert case_response.status_code == 200
    case_prediction = case_response.json()
    
    # With identical marks and goods, opposition should succeed
    assert case_prediction["opposition_outcome"]["result"] == "Opposition likely to succeed"
    assert case_prediction["opposition_outcome"]["confidence"] >= 0.8


def test_full_workflow_dissimilar_marks_dissimilar_goods(test_client):
    """Test the workflow with dissimilar marks and dissimilar goods which should result in opposition failure."""
    # Step 1: Mark similarity for clearly different marks
    mark_similarity_payload = models.MarkSimilarityRequest(
        applicant=models.Mark(wordmark="ZOOPLANKTON", is_registered=True),
        opponent=models.Mark(wordmark="BUTTERFLY", is_registered=True)
    ).model_dump()
    
    mark_response = test_client.post("/mark_similarity", json=mark_similarity_payload)
    assert mark_response.status_code == 200
    mark_similarity = mark_response.json()
    
    # Step 2: G/S similarity for unrelated goods
    gs_pairs = [
        {
            "applicant_good": models.GoodService(term="Live plants", nice_class=31).model_dump(),
            "opponent_good": models.GoodService(term="Vehicles", nice_class=12).model_dump(),
            "mark_similarity": mark_similarity
        }
    ]
    
    gs_likelihoods = []
    for gs_pair in gs_pairs:
        gs_response = test_client.post("/gs_similarity", json=gs_pair)
        assert gs_response.status_code == 200
        gs_likelihood = gs_response.json()
        gs_likelihoods.append(gs_likelihood)
    
    # Step 3: Case prediction
    case_prediction_payload = {
        "mark_similarity": mark_similarity,
        "goods_services_likelihoods": gs_likelihoods
    }
    
    case_response = test_client.post("/case_prediction", json=case_prediction_payload)
    assert case_response.status_code == 200
    case_prediction = case_response.json()
    
    # With dissimilar marks and goods, opposition should fail
    assert case_prediction["opposition_outcome"]["result"] == "Opposition likely to fail" 