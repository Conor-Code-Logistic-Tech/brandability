"""
Error handling tests.

This module tests the error handling capabilities of the trademark_core functions
and API endpoints, including handling of invalid inputs, API errors, timeouts,
and malformed responses.
"""

import asyncio
import os
from unittest import mock

import pytest
from google.api_core.exceptions import GoogleAPIError, InvalidArgument, ResourceExhausted

from tests.fixtures import SIMILAR_MARKS
from trademark_core import models
from trademark_core.llm import (
    batch_process_goods_services,
    generate_mark_similarity_assessment,
)


@pytest.mark.asyncio
async def test_api_error_handling():
    """Test handling of Google API errors."""
    applicant_mark, opponent_mark = SIMILAR_MARKS

    # Use mock.patch directly instead of trying to modify an existing mock
    with mock.patch(
        "trademark_core.llm.generate_structured_content", side_effect=GoogleAPIError("API error")
    ):
        with pytest.raises(GoogleAPIError):
            await generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=0.6,
                aural_score=0.7,
            )


@pytest.mark.asyncio
async def test_rate_limiting_error_handling():
    """Test handling of rate limiting errors."""
    applicant_mark, opponent_mark = SIMILAR_MARKS

    # Use mock.patch directly instead of trying to modify an existing mock
    with mock.patch(
        "trademark_core.llm.generate_structured_content",
        side_effect=ResourceExhausted("Rate limit exceeded"),
    ):
        with pytest.raises(ResourceExhausted):
            await generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=0.6,
                aural_score=0.7,
            )


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test handling of API timeouts."""
    applicant_mark, opponent_mark = SIMILAR_MARKS

    # Use mock.patch directly instead of trying to modify an existing mock
    with mock.patch(
        "trademark_core.llm.generate_structured_content",
        side_effect=asyncio.TimeoutError("Request timed out"),
    ):
        with pytest.raises(asyncio.TimeoutError):
            await generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=0.6,
                aural_score=0.7,
            )


@pytest.mark.asyncio
async def test_invalid_model_parameter_handling():
    """Test handling of invalid model parameter."""
    applicant_mark, opponent_mark = SIMILAR_MARKS
    invalid_model = "nonexistent-model-123"

    # Use mock.patch directly instead of trying to modify an existing mock
    with mock.patch(
        "trademark_core.llm.generate_structured_content",
        side_effect=InvalidArgument(f"Model {invalid_model} not found"),
    ):
        with pytest.raises(InvalidArgument):
            await generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=0.6,
                aural_score=0.7,
                model=invalid_model,
            )


@pytest.mark.asyncio
async def test_validation_error_handling():
    """Test handling of validation errors from malformed LLM responses."""
    applicant_mark, opponent_mark = SIMILAR_MARKS

    # This is what generate_mark_similarity_assessment calls.
    # We need it to return a malformed structure.
    incomplete_response_dict = {
        "visual": "moderate",
        "aural": "moderate",
        # Missing required fields: conceptual, overall, reasoning
    }

    class MalformedResult:
        def model_dump(self):
            return incomplete_response_dict

    # Use mock.patch directly with a return_value
    with mock.patch(
        "trademark_core.llm.generate_structured_content", return_value=MalformedResult()
    ):
        # The generate_mark_similarity_assessment function should catch the
        # pydantic.ValidationError from model_validate(result.model_dump())
        # and re-raise it as a ValueError.
        with pytest.raises(ValueError) as excinfo:
            await generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=0.6,
                aural_score=0.7,
            )
        assert "validation" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_batch_processing_error_handling():
    """Test error handling within batch processing."""
    prev = os.environ.get("TEST_RAISE_EXCEPTIONS")
    os.environ["TEST_RAISE_EXCEPTIONS"] = "1"
    try:
        applicant_goods = [
            models.GoodService(term="Software", nice_class=9),
            models.GoodService(term="Clothing", nice_class=25),
        ]
        opponent_goods = [
            models.GoodService(term="Computer software", nice_class=9),
            models.GoodService(term="Apparel", nice_class=25),
        ]
        mark_similarity = models.MarkSimilarityOutput(
            visual="moderate",
            aural="moderate",
            conceptual="moderate",
            overall="moderate",
            reasoning="Test reasoning",
        )

        # Keep track of calls for the side_effect logic
        mock_call_count = 0

        async def mock_gs_assessment_side_effect_local(*args, **kwargs):
            nonlocal mock_call_count
            mock_call_count += 1
            if mock_call_count == 1:
                return models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.8,
                    likelihood_of_confusion=True,
                    confusion_type="direct",
                )
            else:
                raise GoogleAPIError("Error on second item")

        # Use mock.patch directly with the side_effect function
        with mock.patch(
            "trademark_core.llm.generate_gs_likelihood_assessment",
            side_effect=mock_gs_assessment_side_effect_local,
        ):
            # The batch_process_goods_services function should propagate the error
            # when TEST_RAISE_EXCEPTIONS=1 is set in llm.py.
            with pytest.raises(GoogleAPIError):
                await batch_process_goods_services(
                    applicant_goods=applicant_goods,
                    opponent_goods=opponent_goods,
                    mark_similarity=mark_similarity,
                )
    finally:
        if prev is not None:
            os.environ["TEST_RAISE_EXCEPTIONS"] = prev
        else:
            del os.environ["TEST_RAISE_EXCEPTIONS"]


@pytest.mark.asyncio
async def test_extremely_long_input_handling():
    """Test handling of extremely long inputs."""
    # Create very long mark names (exceeding typical limits)
    very_long_mark = "A" * 10000  # 10,000 characters
    applicant_mark = models.Mark(wordmark=very_long_mark)
    opponent_mark = models.Mark(wordmark=very_long_mark)

    # Create a mock result that has model_dump method
    mock_result = models.MarkSimilarityOutput(
        visual="identical",
        aural="identical",
        conceptual="identical",
        overall="identical",
        reasoning="Very long identical marks",
    )

    # Patch the generate_structured_content function directly
    with mock.patch("trademark_core.llm.generate_structured_content", return_value=mock_result):
        # Should handle long input without error
        result = await generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=1.0,
            aural_score=1.0,
        )

        assert result.overall == "identical"


@pytest.mark.asyncio
async def test_special_characters_handling():
    """Test handling of special characters and Unicode in inputs."""
    # Create marks with special characters
    special_mark1 = models.Mark(wordmark="★彡ＳＴＡＲ彡★")
    special_mark2 = models.Mark(wordmark="☆STAR☆")

    # Create a proper mock result
    mock_result = models.MarkSimilarityOutput(
        visual="moderate",
        aural="high",
        conceptual="high",
        overall="moderate",
        reasoning="Similar concept despite different characters",
    )

    # Mock response for special characters
    with mock.patch("trademark_core.llm.generate_structured_content", return_value=mock_result):
        result = await generate_mark_similarity_assessment(
            applicant_mark=special_mark1,
            opponent_mark=special_mark2,
            visual_score=0.5,
            aural_score=0.8,
        )

        assert result.overall == "moderate"
