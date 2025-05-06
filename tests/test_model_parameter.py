"""
Tests for the model parameter functionality.

This module tests the ability to specify different LLM models for
various functions in the trademark_core.llm module.
"""

from unittest import mock

import pytest

from tests.fixtures import (
    IDENTICAL_SOFTWARE,
    MODERATE_SIMILARITY_ASSESSMENT,
    SIMILAR_MARKS,
    TEST_MODELS,
    get_model_test_id,
)
from trademark_core import models
from trademark_core.llm import (
    generate_gs_likelihood_assessment,
    generate_mark_similarity_assessment,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_name,model_value",
    [(name, value) for name, value in TEST_MODELS.items()],
    ids=[get_model_test_id(model) for model in TEST_MODELS.values()],
)
async def test_mark_similarity_with_model_parameter(use_mocks, model_name, model_value):
    """Test that mark similarity assessment works with different model parameters."""
    applicant_mark, opponent_mark = SIMILAR_MARKS

    # Visual and aural scores (typically calculated elsewhere)
    visual_score = 0.6
    aural_score = 0.7

    if use_mocks:
        # Create a mock that verifies the model parameter is passed through
        async def mock_implementation(*args, **kwargs):
            # Assert that the model parameter was passed correctly
            assert "model" in kwargs
            assert kwargs["model"] == model_value

            return models.MarkSimilarityOutput(
                visual="moderate",
                aural="moderate",
                conceptual="moderate",
                overall="moderate",
                reasoning="This is a mock response for testing.",
            )

        with mock.patch(
            "trademark_core.llm.generate_structured_content", side_effect=mock_implementation
        ):
            # Call the function with the model parameter
            result = await generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=visual_score,
                aural_score=aural_score,
                model=model_value,
            )

            assert isinstance(result, models.MarkSimilarityOutput)
    else:
        # Using real LLM calls
        result = await generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=visual_score,
            aural_score=aural_score,
            model=model_value,
        )

        # Verify the result structure but not the exact content
        assert isinstance(result, models.MarkSimilarityOutput)
        assert hasattr(result, "visual")
        assert hasattr(result, "aural")
        assert hasattr(result, "conceptual")
        assert hasattr(result, "overall")
        assert hasattr(result, "reasoning")

        # All fields should have valid values according to the model schema
        assert result.visual in ["dissimilar", "low", "moderate", "high", "identical"]
        assert result.aural in ["dissimilar", "low", "moderate", "high", "identical"]
        assert result.conceptual in ["dissimilar", "low", "moderate", "high", "identical"]
        assert result.overall in ["dissimilar", "low", "moderate", "high", "identical"]
        assert result.reasoning is not None and len(result.reasoning) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_name,model_value",
    [(name, value) for name, value in TEST_MODELS.items()],
    ids=[get_model_test_id(model) for model in TEST_MODELS.values()],
)
async def test_gs_likelihood_with_model_parameter(use_mocks, model_name, model_value):
    """Test that goods/services likelihood assessment works with different model parameters."""
    applicant_good, opponent_good = IDENTICAL_SOFTWARE
    mark_similarity = MODERATE_SIMILARITY_ASSESSMENT

    if use_mocks:
        # Create a mock that verifies the model parameter is passed through
        async def mock_implementation(*args, **kwargs):
            # Assert that the model parameter was passed correctly
            assert "model" in kwargs
            assert kwargs["model"] == model_value

            return models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=True,
                confusion_type="direct",
            )

        with mock.patch(
            "trademark_core.llm.generate_structured_content", side_effect=mock_implementation
        ):
            # Call the function with the model parameter
            result = await generate_gs_likelihood_assessment(
                applicant_good=applicant_good,
                opponent_good=opponent_good,
                mark_similarity=mark_similarity,
                model=model_value,
            )

            assert isinstance(result, models.GoodServiceLikelihoodOutput)
    else:
        # Using real LLM calls
        result = await generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity,
            model=model_value,
        )

        # Verify the result structure but not the exact content
        assert isinstance(result, models.GoodServiceLikelihoodOutput)
        assert hasattr(result, "are_competitive")
        assert hasattr(result, "are_complementary")
        assert hasattr(result, "similarity_score")
        assert hasattr(result, "likelihood_of_confusion")

        # All fields should have valid values according to the model schema
        assert isinstance(result.are_competitive, bool)
        assert isinstance(result.are_complementary, bool)
        assert 0 <= result.similarity_score <= 1
        assert isinstance(result.likelihood_of_confusion, bool)
        if result.likelihood_of_confusion:
            assert result.confusion_type in ["direct", "indirect"]
        else:
            assert result.confusion_type is None


@pytest.mark.asyncio
async def test_invalid_model_parameter(use_mocks):
    """Test that providing an invalid model name results in an appropriate error."""
    applicant_mark, opponent_mark = SIMILAR_MARKS
    invalid_model = "nonexistent-model-name"

    if use_mocks:
        # Skip this test when using mocks as we can't easily simulate the API error
        pytest.skip("This test requires real LLM calls to test invalid model handling")
    else:
        # Attempt to use an invalid model name
        with pytest.raises(Exception) as excinfo:
            await generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=0.6,
                aural_score=0.7,
                model=invalid_model,
            )

        # Check that the error message mentions the invalid model
        error_message = str(excinfo.value).lower()
        assert (
            "model" in error_message or "nonexistent" in error_message or "invalid" in error_message
        )
