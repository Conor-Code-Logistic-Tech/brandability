"""
Tests to verify that mock implementations strictly adhere to data models.

This module contains tests that validate the mock implementations against
the Pydantic models defined in models.py to ensure strict consistency.
"""

import pytest
from pydantic import ValidationError

from tests.fixtures import (
    IDENTICAL_SOFTWARE,
    MODERATE_SIMILARITY_ASSESSMENT,
    SIMILAR_MARKS,
)
from tests.mocks import MockLLM
from trademark_core import models


@pytest.mark.asyncio
async def test_mark_similarity_output_validation():
    """Test that the mark similarity mock produces valid MarkSimilarityOutput models."""
    applicant_mark, opponent_mark = SIMILAR_MARKS

    # Test with valid inputs
    result = await MockLLM.mock_mark_similarity_assessment(
        applicant_mark=applicant_mark,
        opponent_mark=opponent_mark,
        visual_score=0.5,
        aural_score=0.6,
    )

    # Verify result is a valid MarkSimilarityOutput
    assert isinstance(result, models.MarkSimilarityOutput)
    assert result.visual in ["dissimilar", "low", "moderate", "high", "identical"]
    assert result.aural in ["dissimilar", "low", "moderate", "high", "identical"]
    assert result.conceptual in ["dissimilar", "low", "moderate", "high", "identical"]
    assert result.overall in ["dissimilar", "low", "moderate", "high", "identical"]
    assert isinstance(result.reasoning, str)

    # Validate model output with Pydantic
    validated_model = models.MarkSimilarityOutput.model_validate(result.model_dump())
    assert validated_model == result


@pytest.mark.asyncio
async def test_gs_likelihood_output_validation():
    """Test that the goods/services likelihood mock produces valid GoodServiceLikelihoodOutput models."""
    applicant_good, opponent_good = IDENTICAL_SOFTWARE

    # Test with valid inputs
    result = await MockLLM.mock_gs_likelihood_assessment(
        applicant_good=applicant_good,
        opponent_good=opponent_good,
        mark_similarity=MODERATE_SIMILARITY_ASSESSMENT,
    )

    # Verify result is a valid GoodServiceLikelihoodOutput
    assert isinstance(result, models.GoodServiceLikelihoodOutput)
    assert isinstance(result.are_competitive, bool)
    assert isinstance(result.are_complementary, bool)
    assert 0 <= result.similarity_score <= 1
    assert isinstance(result.likelihood_of_confusion, bool)

    # If likelihood_of_confusion is True, confusion_type must be one of the allowed values
    if result.likelihood_of_confusion:
        assert result.confusion_type in ["direct", "indirect"]
    # If likelihood_of_confusion is False, confusion_type must be None
    else:
        assert result.confusion_type is None

    # Validate model output with Pydantic
    validated_model = models.GoodServiceLikelihoodOutput.model_validate(result.model_dump())
    assert validated_model == result


@pytest.mark.asyncio
async def test_structured_content_outputs():
    """Test that the structured content mock produces valid model instances for different schemas."""
    # Test MarkSimilarityOutput
    mark_result = await MockLLM.mock_structured_content(
        prompt="Test for EXAMPLIA vs EXAMPLIA", schema=models.MarkSimilarityOutput
    )
    assert isinstance(mark_result, models.MarkSimilarityOutput)
    validated_model = models.MarkSimilarityOutput.model_validate(mark_result.model_dump())
    assert validated_model == mark_result

    # Test GoodServiceLikelihoodOutput
    gs_result = await MockLLM.mock_structured_content(
        prompt="Test for Legal software vs Legal software",
        schema=models.GoodServiceLikelihoodOutput,
    )
    assert isinstance(gs_result, models.GoodServiceLikelihoodOutput)
    validated_model = models.GoodServiceLikelihoodOutput.model_validate(gs_result.model_dump())
    assert validated_model == gs_result

    # Test ConceptualSimilarityScore
    cs_result = await MockLLM.mock_structured_content(
        prompt="Test conceptual similarity", schema=models.ConceptualSimilarityScore
    )
    assert isinstance(cs_result, models.ConceptualSimilarityScore)
    assert 0 <= cs_result.score <= 1
    validated_model = models.ConceptualSimilarityScore.model_validate(cs_result.model_dump())
    assert validated_model == cs_result

    # Test OppositionOutcome
    opp_result = await MockLLM.mock_structured_content(
        prompt="Test opposition outcome", schema=models.OppositionOutcome
    )
    assert isinstance(opp_result, models.OppositionOutcome)
    assert opp_result.result in [
        "Opposition likely to succeed",
        "Opposition may partially succeed",
        "Opposition likely to fail",
    ]
    assert 0 <= opp_result.confidence <= 1
    assert isinstance(opp_result.reasoning, str)
    validated_model = models.OppositionOutcome.model_validate(opp_result.model_dump())
    assert validated_model == opp_result

    # Test CasePredictionResult
    case_result = await MockLLM.mock_structured_content(
        prompt="Test case prediction", schema=models.CasePredictionResult
    )
    assert isinstance(case_result, models.CasePredictionResult)
    assert isinstance(case_result.mark_comparison, models.MarkSimilarityOutput)
    assert len(case_result.goods_services_likelihoods) > 0
    assert all(
        isinstance(gs, models.GoodServiceLikelihoodOutput)
        for gs in case_result.goods_services_likelihoods
    )
    assert isinstance(case_result.opposition_outcome, models.OppositionOutcome)
    validated_model = models.CasePredictionResult.model_validate(case_result.model_dump())
    assert validated_model == case_result


@pytest.mark.asyncio
async def test_conceptual_similarity_score_validation():
    """Test that the conceptual similarity mock produces valid scores."""
    # Test with valid inputs
    score = await MockLLM.mock_conceptual_similarity_score(
        applicant_mark="EXAMPLIA", opponent_mark="EXAMPLIFY"
    )

    # Verify score is in the valid range
    assert isinstance(score, float)
    assert 0 <= score <= 1

    # Test identical marks (should return 1.0)
    identical_score = await MockLLM.mock_conceptual_similarity_score(
        applicant_mark="IDENTICAL",
        opponent_mark="identical",  # Case-insensitive comparison
    )
    assert identical_score == 1.0

    # Test very different marks (should return a low score)
    different_score = await MockLLM.mock_conceptual_similarity_score(
        applicant_mark="ZOOPLANKTON", opponent_mark="BUTTERFLY"
    )
    assert different_score < 0.5


def test_model_validation_rules():
    """Test that the model definitions have proper validation rules."""
    # Check EnumStr values for MarkSimilarityOutput
    valid_enum_values = ["dissimilar", "low", "moderate", "high", "identical"]

    # Create a mark similarity output and verify it validates
    mark_output = models.MarkSimilarityOutput(
        visual="moderate",
        aural="low",
        conceptual="high",
        overall="moderate",
        reasoning="Test reasoning",
    )

    # Try an invalid enum value and verify it fails validation
    with pytest.raises(ValidationError):
        models.MarkSimilarityOutput(
            visual="invalid_value",  # Not in the allowed enum values
            aural="low",
            conceptual="high",
            overall="moderate",
        )

    # Check OppositionResultEnum values
    valid_outcome_values = [
        "Opposition likely to succeed",
        "Opposition may partially succeed",
        "Opposition likely to fail",
    ]

    # Create an opposition outcome and verify it validates
    opp_outcome = models.OppositionOutcome(
        result="Opposition likely to succeed", confidence=0.8, reasoning="Test reasoning"
    )

    # Try an invalid result value and verify it fails validation
    with pytest.raises(ValidationError):
        models.OppositionOutcome(
            result="Invalid outcome",  # Not in the allowed enum values
            confidence=0.8,
            reasoning="Test reasoning",
        )

    # Check confusion type values for GoodServiceLikelihoodOutput
    # Create a goods/services likelihood with confusion and verify it validates
    gs_with_confusion = models.GoodServiceLikelihoodOutput(
        are_competitive=True,
        are_complementary=False,
        similarity_score=0.8,
        likelihood_of_confusion=True,
        confusion_type="direct",
    )

    # Create a goods/services likelihood without confusion and verify it validates
    gs_without_confusion = models.GoodServiceLikelihoodOutput(
        are_competitive=False,
        are_complementary=True,
        similarity_score=0.3,
        likelihood_of_confusion=False,
        confusion_type=None,
    )

    # Try an invalid confusion type and verify it fails validation
    with pytest.raises(ValidationError):
        models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.8,
            likelihood_of_confusion=True,
            confusion_type="invalid_type",  # Not in the allowed enum values
        )


def test_model_consistency():
    """
    Test that the mock responses are consistent with the models.

    This is a basic test to verify that our mocks return responses
    that comply with the model definitions, focusing on the key
    properties and constraints.
    """
    # Create a dummy instance of each model to verify
    mark = models.Mark(wordmark="TEST")

    # Test basic mock output consistency
    mark_output = models.MarkSimilarityOutput(
        visual="moderate",
        aural="moderate",
        conceptual="moderate",
        overall="moderate",
        reasoning="Test reasoning",
    )

    gs_output = models.GoodServiceLikelihoodOutput(
        are_competitive=True,
        are_complementary=False,
        similarity_score=0.7,
        likelihood_of_confusion=True,
        confusion_type="direct",
    )

    # Verify that the enum values are consistent across the codebase
    valid_enum_values = ["dissimilar", "low", "moderate", "high", "identical"]
    for value in valid_enum_values:
        # Create a valid instance with each enum value
        test_mark = models.MarkSimilarityOutput(
            visual=value, aural=value, conceptual=value, overall=value, reasoning="Test reasoning"
        )
        # Validate that it works
        models.MarkSimilarityOutput.model_validate(test_mark.model_dump())

    # Verify opposition outcome values are consistent
    valid_outcome_values = [
        "Opposition likely to succeed",
        "Opposition may partially succeed",
        "Opposition likely to fail",
    ]
    for value in valid_outcome_values:
        # Create a valid instance with each outcome value
        test_outcome = models.OppositionOutcome(
            result=value, confidence=0.8, reasoning="Test reasoning"
        )
        # Validate that it works
        models.OppositionOutcome.model_validate(test_outcome.model_dump())

    # Verify confusion type values are consistent
    valid_confusion_types = ["direct", "indirect"]
    for value in valid_confusion_types:
        # Create a valid instance with each confusion type
        test_gs = models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.7,
            likelihood_of_confusion=True,
            confusion_type=value,
        )
        # Validate that it works
        models.GoodServiceLikelihoodOutput.model_validate(test_gs.model_dump())
