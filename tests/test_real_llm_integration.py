"""
Real LLM integration tests.

This module contains integration tests that use real LLM calls instead of mocks.
These tests are skipped when running with mocks enabled.
"""

import pytest

from tests.fixtures import (
    DISSIMILAR_MARKS,
    IDENTICAL_MARKS,
    IDENTICAL_SOFTWARE,
    MODERATE_SIMILARITY_ASSESSMENT,
    SIMILAR_CONCEPT_MARKS,
    UNRELATED_GOODS,
)
from trademark_core import models
from trademark_core.llm import (
    generate_gs_likelihood_assessment,
    generate_mark_similarity_assessment,
)


@pytest.mark.asyncio
async def test_real_mark_similarity_identical(use_mocks):
    """Test real mark similarity assessment with identical marks.

    Note: Per the prompt instructions, purely random letter marks like 'XQZPVY' should be
    considered conceptually dissimilar even when identical, as they have no inherent meaning.
    """
    if use_mocks:
        pytest.skip("This test requires real LLM calls")

    applicant_mark, opponent_mark = IDENTICAL_MARKS

    # Call with real LLM
    result = await generate_mark_similarity_assessment(
        applicant_mark=applicant_mark,
        opponent_mark=opponent_mark,
        visual_score=1.0,
        aural_score=1.0,
    )

    # Check that the result makes sense for identical marks
    assert result.visual in ["high", "identical"]
    assert result.aural in ["high", "identical"]
    # For random letter marks, expect "dissimilar" conceptually per the prompt rules
    assert result.conceptual in ["dissimilar", "low"]
    # Even with conceptual dissimilarity, the overall should be high due to visual/aural identity
    assert result.overall in ["high", "identical"]
    assert result.reasoning is not None and len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_real_mark_similarity_dissimilar(use_mocks):
    """Test real mark similarity assessment with dissimilar marks."""
    if use_mocks:
        pytest.skip("This test requires real LLM calls")

    applicant_mark, opponent_mark = DISSIMILAR_MARKS

    # Call with real LLM
    result = await generate_mark_similarity_assessment(
        applicant_mark=applicant_mark,
        opponent_mark=opponent_mark,
        visual_score=0.1,
        aural_score=0.2,
    )

    # Check that the result makes sense for dissimilar marks
    assert result.visual in ["dissimilar", "low"]
    assert result.aural in ["dissimilar", "low"]
    # Even dissimilar marks might have some conceptual similarity
    assert result.overall in ["dissimilar", "low"]
    assert result.reasoning is not None and len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_real_gs_likelihood_identical(use_mocks):
    """Test real goods/services likelihood assessment with identical goods."""
    if use_mocks:
        pytest.skip("This test requires real LLM calls")

    applicant_good, opponent_good = IDENTICAL_SOFTWARE

    # Call with real LLM
    result = await generate_gs_likelihood_assessment(
        applicant_good=applicant_good,
        opponent_good=opponent_good,
        mark_similarity=MODERATE_SIMILARITY_ASSESSMENT,
    )

    # Check that the result makes sense for identical goods
    assert result.are_competitive is True
    assert result.similarity_score > 0.7  # Should be high for identical goods
    # With moderate mark similarity and identical goods, should have confusion
    assert result.likelihood_of_confusion is True
    assert result.confusion_type in ["direct", "indirect"]


@pytest.mark.asyncio
async def test_real_gs_likelihood_unrelated(use_mocks):
    """Test real goods/services likelihood assessment with unrelated goods."""
    if use_mocks:
        pytest.skip("This test requires real LLM calls")

    applicant_good, opponent_good = UNRELATED_GOODS

    # Call with real LLM
    result = await generate_gs_likelihood_assessment(
        applicant_good=applicant_good,
        opponent_good=opponent_good,
        mark_similarity=MODERATE_SIMILARITY_ASSESSMENT,
    )

    # Check that the result makes sense for unrelated goods
    assert result.similarity_score < 0.5  # Should be low for unrelated goods
    # With moderate mark similarity but unrelated goods, confusion unlikely
    if result.likelihood_of_confusion is False:
        assert result.confusion_type is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [
        "identical_marks_identical_goods",
        "identical_marks_unrelated_goods",
        "dissimilar_marks_identical_goods",
        "dissimilar_marks_unrelated_goods",
    ],
)
async def test_comprehensive_cases(use_mocks, test_case):
    """Test comprehensive trademark opposition scenarios with real LLM calls."""
    if use_mocks:
        pytest.skip("This test requires real LLM calls")

    # Set up test case parameters
    if test_case == "identical_marks_identical_goods":
        applicant_mark, opponent_mark = IDENTICAL_MARKS
        applicant_good, opponent_good = IDENTICAL_SOFTWARE
        visual_score, aural_score = 1.0, 1.0
        expected_confusion = True
    elif test_case == "identical_marks_unrelated_goods":
        applicant_mark, opponent_mark = IDENTICAL_MARKS
        applicant_good, opponent_good = UNRELATED_GOODS
        visual_score, aural_score = 1.0, 1.0
        expected_confusion = None  # Could go either way
    elif test_case == "dissimilar_marks_identical_goods":
        applicant_mark, opponent_mark = DISSIMILAR_MARKS
        applicant_good, opponent_good = IDENTICAL_SOFTWARE
        visual_score, aural_score = 0.1, 0.2
        expected_confusion = None  # Could go either way
    elif test_case == "dissimilar_marks_unrelated_goods":
        applicant_mark, opponent_mark = DISSIMILAR_MARKS
        applicant_good, opponent_good = UNRELATED_GOODS
        visual_score, aural_score = 0.1, 0.2
        expected_confusion = False

    # First, get the mark similarity assessment
    mark_result = await generate_mark_similarity_assessment(
        applicant_mark=applicant_mark,
        opponent_mark=opponent_mark,
        visual_score=visual_score,
        aural_score=aural_score,
    )

    # Then, use the mark similarity to assess G/S likelihood
    gs_result = await generate_gs_likelihood_assessment(
        applicant_good=applicant_good, opponent_good=opponent_good, mark_similarity=mark_result
    )

    # Verify results match the expected pattern
    if expected_confusion is not None:
        assert gs_result.likelihood_of_confusion == expected_confusion

    # All results should have proper schema and data types
    assert isinstance(mark_result, models.MarkSimilarityOutput)
    assert isinstance(gs_result, models.GoodServiceLikelihoodOutput)
    assert mark_result.reasoning is not None and len(mark_result.reasoning) > 0
    assert 0 <= gs_result.similarity_score <= 1


@pytest.mark.asyncio
async def test_real_mark_similarity_real_words(use_mocks):
    """Test real mark similarity assessment with marks having clear concepts."""
    if use_mocks:
        pytest.skip("This test requires real LLM calls")

    # Use real words with clear concepts from our fixtures
    applicant_mark, opponent_mark = SIMILAR_CONCEPT_MARKS

    # Call with real LLM
    result = await generate_mark_similarity_assessment(
        applicant_mark=applicant_mark,
        opponent_mark=opponent_mark,
        visual_score=0.3,  # Visually different
        aural_score=0.4,  # Aurally different
    )

    # Check that real words with similar concepts have conceptual similarity
    assert result.conceptual in ["moderate", "high"]
    assert result.reasoning is not None and len(result.reasoning) > 0
