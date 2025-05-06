"""
Tests for batch processing of goods/services comparisons.

This module tests the concurrent processing of multiple goods/services
comparisons using the batch_process_goods_services function.
"""

import pytest
from unittest import mock

from trademark_core import models
from trademark_core.llm import batch_process_goods_services, generate_gs_likelihood_assessment


@pytest.mark.asyncio
async def test_batch_process_goods_services():
    """Test that batch processing of goods/services works correctly."""
    # Create test data
    applicant_goods = [
        models.GoodService(term="Software", nice_class=9),
        models.GoodService(term="Legal services", nice_class=45)
    ]
    
    opponent_goods = [
        models.GoodService(term="Computer software", nice_class=9),
        models.GoodService(term="Business consultancy", nice_class=35)
    ]
    
    mark_similarity = models.MarkSimilarityOutput(
        visual="moderate",
        aural="moderate",
        conceptual="low",
        overall="moderate"
    )
    
    # Mock the generate_gs_likelihood_assessment function to avoid actual API calls
    mock_result = models.GoodServiceLikelihoodOutput(
        are_competitive=True,
        are_complementary=False,
        similarity_score=0.7,
        likelihood_of_confusion=True,
        confusion_type="direct"
    )
    
    with mock.patch('trademark_core.llm.generate_gs_likelihood_assessment', 
                   return_value=mock_result) as mock_generate:
        # Call the batch processing function
        results = await batch_process_goods_services(
            applicant_goods=applicant_goods,
            opponent_goods=opponent_goods,
            mark_similarity=mark_similarity
        )
        
        # Check results
        assert len(results) == 4  # 2x2 combinations
        assert all(isinstance(r, models.GoodServiceLikelihoodOutput) for r in results)
        
        # Verify all combinations were processed
        assert mock_generate.call_count == 4
        
        # Check specific calls
        call_args_list = mock_generate.call_args_list
        
        # Make sure all combinations were called
        combinations = []
        for call in call_args_list:
            app_good = call.kwargs['applicant_good']
            opp_good = call.kwargs['opponent_good']
            combinations.append((app_good.term, opp_good.term))
        
        expected_combinations = [
            ("Software", "Computer software"),
            ("Software", "Business consultancy"),
            ("Legal services", "Computer software"),
            ("Legal services", "Business consultancy")
        ]
        
        for combo in expected_combinations:
            assert combo in combinations


@pytest.mark.asyncio
async def test_batch_process_handles_exceptions():
    """Test that batch processing properly handles exceptions in individual tasks."""
    # Create test data
    applicant_goods = [
        models.GoodService(term="Software", nice_class=9),
        models.GoodService(term="Legal services", nice_class=45)
    ]
    
    opponent_goods = [
        models.GoodService(term="Computer software", nice_class=9),
        models.GoodService(term="Business consultancy", nice_class=35)
    ]
    
    mark_similarity = models.MarkSimilarityOutput(
        visual="moderate",
        aural="moderate",
        conceptual="low",
        overall="moderate"
    )
    
    # Create a mock implementation that raises an exception for one combination
    async def mock_implementation(*args, **kwargs):
        if (kwargs['applicant_good'].term == "Software" and 
            kwargs['opponent_good'].term == "Computer software"):
            raise Exception("Test exception")
        return models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.7,
            likelihood_of_confusion=True,
            confusion_type="direct"
        )
    
    with mock.patch('trademark_core.llm.generate_gs_likelihood_assessment', 
                   side_effect=mock_implementation) as mock_generate:
        # Call the batch processing function
        results = await batch_process_goods_services(
            applicant_goods=applicant_goods,
            opponent_goods=opponent_goods,
            mark_similarity=mark_similarity
        )
        
        # Check results - should have 3 instead of 4 results due to one exception
        assert len(results) == 3
        assert all(isinstance(r, models.GoodServiceLikelihoodOutput) for r in results)
        
        # Verify all combinations were attempted
        assert mock_generate.call_count == 4 


def test_batch_gs_similarity_endpoint(test_client):
    """Test the batch_gs_similarity endpoint processes multiple goods/services comparisons correctly."""
    # Create test data
    mark_similarity = models.MarkSimilarityOutput(
        visual="moderate",
        aural="moderate",
        conceptual="low",
        overall="moderate"
    )
    
    applicant_goods = [
        models.GoodService(term="Software", nice_class=9),
        models.GoodService(term="Legal services", nice_class=45)
    ]
    
    opponent_goods = [
        models.GoodService(term="Computer software", nice_class=9),
        models.GoodService(term="Business consultancy", nice_class=35)
    ]
    
    # Create payload for batch request
    payload = models.BatchGsSimilarityRequest(
        applicant_goods=applicant_goods,
        opponent_goods=opponent_goods,
        mark_similarity=mark_similarity
    ).model_dump()
    
    # Call the batch_gs_similarity endpoint
    response = test_client.post("/batch_gs_similarity", json=payload)
    
    # Assert successful response
    assert response.status_code == 200
    
    # Parse the response
    results = response.json()
    
    # Check the correct number of combinations were processed
    assert len(results) == 4  # 2x2 combinations
    
    # Verify all results have the correct structure
    for result in results:
        assert "are_competitive" in result
        assert "are_complementary" in result
        assert "similarity_score" in result
        assert "likelihood_of_confusion" in result
        
        # Check data types
        assert isinstance(result["are_competitive"], bool)
        assert isinstance(result["are_complementary"], bool)
        assert isinstance(result["similarity_score"], (int, float))
        assert isinstance(result["likelihood_of_confusion"], bool) 