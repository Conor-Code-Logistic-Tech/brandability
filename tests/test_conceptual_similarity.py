"""
Tests for conceptual similarity calculations.

This module tests the functionality of the conceptual similarity calculations
in the trademark_core.similarity and trademark_core.llm modules.
"""

from unittest import mock

import pytest

from tests.fixtures import DISSIMILAR_MARKS, IDENTICAL_MARKS, SIMILAR_MARKS
from trademark_core.similarity import calculate_conceptual_similarity


@pytest.mark.asyncio
async def test_conceptual_similarity_identical_marks(use_mocks):
    """Test conceptual similarity calculation with identical marks.

    Note: Per the prompt instructions, if the marks are made-up words without clear
    meaning, they should return 0.0 even if identical.
    """
    applicant_mark, opponent_mark = IDENTICAL_MARKS

    if use_mocks:
        # Mock the LLM call for identical made-up marks
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.0
        ):
            result = await calculate_conceptual_similarity(
                applicant_mark.wordmark, opponent_mark.wordmark
            )

            # For identical made-up words, expect 0.0 per the prompt rules
            assert result == 0.0
    else:
        # Real LLM call for identical made-up marks
        result = await calculate_conceptual_similarity(
            applicant_mark.wordmark, opponent_mark.wordmark
        )

        # For made-up words, expect 0.0 per the prompt rules
        assert result == 0.0


@pytest.mark.asyncio
async def test_conceptual_similarity_similar_marks(use_mocks):
    """Test conceptual similarity calculation with similar marks.

    Note: Per the prompt instructions, if either mark is a made-up word without clear
    meaning, they should return 0.0 even if structurally similar.
    """
    applicant_mark, opponent_mark = SIMILAR_MARKS

    if use_mocks:
        # Mock the LLM call for similar made-up marks
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.0
        ):
            result = await calculate_conceptual_similarity(
                applicant_mark.wordmark, opponent_mark.wordmark
            )

            # For similar made-up words, expect 0.0 per the prompt rules
            assert result == 0.0
    else:
        # Real LLM call for similar made-up marks
        result = await calculate_conceptual_similarity(
            applicant_mark.wordmark, opponent_mark.wordmark
        )

        # For made-up words, expect 0.0 per the prompt rules
        assert result == 0.0


@pytest.mark.asyncio
async def test_conceptual_similarity_dissimilar_marks(use_mocks):
    """Test conceptual similarity calculation with dissimilar marks."""
    applicant_mark, opponent_mark = DISSIMILAR_MARKS

    if use_mocks:
        # Mock the LLM call for dissimilar marks
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.2
        ):
            result = await calculate_conceptual_similarity(
                applicant_mark.wordmark, opponent_mark.wordmark
            )

            assert result == 0.2
    else:
        # Real LLM call for dissimilar marks
        result = await calculate_conceptual_similarity(
            applicant_mark.wordmark, opponent_mark.wordmark
        )

        assert 0 <= result <= 0.4  # Allowing some flexibility in real LLM responses


@pytest.mark.asyncio
async def test_conceptual_similarity_culturally_specific(use_mocks):
    """Test conceptual similarity with culturally specific concepts."""
    # Examples with culturally specific meaning
    mark1 = "RED DRAGON"  # Associated with China/East Asian culture
    mark2 = "GOLDEN PHOENIX"  # Associated with rebirth/transformation

    if use_mocks:
        # Mock the LLM call for cultural concepts
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.6
        ):
            result = await calculate_conceptual_similarity(mark1, mark2)

            assert result == 0.6
    else:
        # Real LLM call for cultural concepts
        result = await calculate_conceptual_similarity(mark1, mark2)

        # These concepts should have some relation in meaning
        assert 0.4 <= result <= 0.8  # Allowing some flexibility in real LLM responses


@pytest.mark.asyncio
async def test_conceptual_similarity_homonyms(use_mocks):
    """Test conceptual similarity with homonyms (same pronunciation, different meaning)."""
    mark1 = "NIGHT"  # Time of day
    mark2 = "KNIGHT"  # Medieval warrior

    if use_mocks:
        # Mock the LLM call for homonyms
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.3
        ):
            result = await calculate_conceptual_similarity(mark1, mark2)

            assert result == 0.3
    else:
        # Real LLM call for homonyms
        result = await calculate_conceptual_similarity(mark1, mark2)

        # Homonyms should have low conceptual similarity despite sounding the same
        assert 0 <= result <= 0.5  # Allowing some flexibility in real LLM responses


@pytest.mark.asyncio
async def test_conceptual_similarity_translation(use_mocks):
    """Test conceptual similarity with translations."""
    mark1 = "ROYAL"  # English
    mark2 = "REGAL"  # Similar Latin-derived word

    if use_mocks:
        # Mock the LLM call for translations
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.85
        ):
            result = await calculate_conceptual_similarity(mark1, mark2)

            assert result == 0.85
    else:
        # Real LLM call for translations
        result = await calculate_conceptual_similarity(mark1, mark2)

        # Translations should have high conceptual similarity
        assert 0.7 <= result <= 1.0  # Allowing some flexibility in real LLM responses


@pytest.mark.asyncio
async def test_conceptual_similarity_non_english(use_mocks):
    """Test conceptual similarity with non-English content."""
    mark1 = "SCHNELL"  # German for "fast"
    mark2 = "RAPIDE"  # French for "fast"

    if use_mocks:
        # Mock the LLM call for non-English content
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.8
        ):
            result = await calculate_conceptual_similarity(mark1, mark2)

            assert result == 0.8
    else:
        # Real LLM call for non-English content
        result = await calculate_conceptual_similarity(mark1, mark2)

        # These should have high conceptual similarity despite different languages
        assert 0.6 <= result <= 1.0  # Allowing some flexibility in real LLM responses


@pytest.mark.asyncio
async def test_conceptual_similarity_real_words_identical_concept(use_mocks):
    """Test conceptual similarity with real words having identical concepts."""
    mark1 = "COOLBRAND"  # Contains the concept "cool"
    mark2 = "KOOL BRAND"  # Contains the same concept with different spelling

    if use_mocks:
        # Mock the LLM call for real words with identical concepts
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.9
        ):
            result = await calculate_conceptual_similarity(mark1, mark2)

            assert result == 0.9
    else:
        # Real LLM call for real words with identical concepts
        result = await calculate_conceptual_similarity(mark1, mark2)

        # These should have high conceptual similarity
        assert 0.7 <= result <= 1.0  # Allowing some flexibility in real LLM responses


@pytest.mark.asyncio
async def test_conceptual_similarity_mixed_real_and_made_up(use_mocks):
    """Test conceptual similarity where one mark has a concept and the other doesn't."""
    mark1 = "COOLBRAND"  # Contains the concept "cool"
    mark2 = "CORLBRAN"  # Made-up word with no clear meaning

    if use_mocks:
        # Mock the LLM call for mixed real and made-up words
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.0
        ):
            result = await calculate_conceptual_similarity(mark1, mark2)

            # If either mark is a made-up word, expect 0.0 per the prompt rules
            assert result == 0.0
    else:
        # Real LLM call for mixed real and made-up words
        result = await calculate_conceptual_similarity(mark1, mark2)

        # If either mark is a made-up word, expect 0.0 per the prompt rules
        assert result == 0.0


@pytest.mark.asyncio
async def test_conceptual_similarity_both_made_up(use_mocks):
    """Test conceptual similarity where neither mark has a clear concept."""
    mark1 = "CHAX"  # Made-up word with no clear meaning
    mark2 = "CHAQ"  # Made-up word with no clear meaning

    if use_mocks:
        # Mock the LLM call for two made-up words
        with mock.patch(
            "trademark_core.similarity._get_conceptual_similarity_score_from_llm", return_value=0.0
        ):
            result = await calculate_conceptual_similarity(mark1, mark2)

            # If both marks are made-up words, expect 0.0 per the prompt rules
            assert result == 0.0
    else:
        # Real LLM call for two made-up words
        result = await calculate_conceptual_similarity(mark1, mark2)

        # If both marks are made-up words, expect 0.0 per the prompt rules
        assert result == 0.0
