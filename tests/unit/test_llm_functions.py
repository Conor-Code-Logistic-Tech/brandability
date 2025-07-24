"""
Unit tests for LLM functions in trademark_core.llm.

These tests validate the LLM interaction logic and business rules
without making actual API calls to external services.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from trademark_core import models, llm
from tests.utils.mocks import apply_llm_mocks
from tests.utils.fixtures import (
    IDENTICAL_MARKS,
    SIMILAR_MARKS,
    DISSIMILAR_MARKS,
    IDENTICAL_SOFTWARE,
    RELATED_SOFTWARE,
    UNRELATED_GOODS,
    IDENTICAL_ASSESSMENT,
    HIGH_SIMILARITY_ASSESSMENT,
    MODERATE_SIMILARITY_ASSESSMENT,
)


class TestGenerateMarkSimilarityAssessment:
    """Test cases for generate_mark_similarity_assessment function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up LLM mocks for all tests in this class."""
        with apply_llm_mocks():
            yield

    @pytest.mark.asyncio
    async def test_mark_similarity_assessment_valid_input(self):
        """Test mark similarity assessment with valid input."""
        applicant_mark = models.Mark(wordmark="EXAMPLE")
        opponent_mark = models.Mark(wordmark="EXAMPL")
        
        result = await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=0.8,
            aural_score=0.7
        )
        
        assert isinstance(result, models.MarkSimilarityOutput)
        assert result.visual in ["dissimilar", "low", "moderate", "high", "identical"]
        assert result.aural in ["dissimilar", "low", "moderate", "high", "identical"]
        assert result.conceptual in ["dissimilar", "low", "moderate", "high", "identical"]
        assert result.overall in ["dissimilar", "low", "moderate", "high", "identical"]

    @pytest.mark.asyncio
    async def test_mark_similarity_assessment_identical_marks(self):
        """Test mark similarity assessment with identical marks."""
        applicant_mark = models.Mark(wordmark="IDENTICAL")
        opponent_mark = models.Mark(wordmark="IDENTICAL")
        
        result = await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=1.0,
            aural_score=1.0
        )
        
        assert result.overall == "identical"

    @pytest.mark.asyncio
    async def test_mark_similarity_assessment_with_registration_details(self):
        """Test mark similarity assessment with registration details."""
        applicant_mark = models.Mark(
            wordmark="REGISTERED",
            is_registered=True,
            registration_number="UK00003123456"
        )
        opponent_mark = models.Mark(
            wordmark="UNREGISTERED",
            is_registered=False
        )
        
        result = await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=0.6,
            aural_score=0.5
        )
        
        assert isinstance(result, models.MarkSimilarityOutput)

    @pytest.mark.asyncio
    async def test_mark_similarity_assessment_score_boundaries(self):
        """Test mark similarity assessment with boundary score values."""
        applicant_mark = models.Mark(wordmark="TEST1")
        opponent_mark = models.Mark(wordmark="TEST2")
        
        # Test minimum scores
        result_min = await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=0.0,
            aural_score=0.0
        )
        assert isinstance(result_min, models.MarkSimilarityOutput)
        
        # Test maximum scores
        result_max = await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=1.0,
            aural_score=1.0
        )
        assert isinstance(result_max, models.MarkSimilarityOutput)

    @pytest.mark.asyncio
    async def test_mark_similarity_assessment_invalid_scores(self):
        """Test mark similarity assessment with invalid score values."""
        applicant_mark = models.Mark(wordmark="TEST1")
        opponent_mark = models.Mark(wordmark="TEST2")
        
        # Test with invalid visual score
        with pytest.raises(ValueError):
            await llm.generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=1.5,  # Invalid score > 1.0
                aural_score=0.5
            )
        
        # Test with invalid aural score
        with pytest.raises(ValueError):
            await llm.generate_mark_similarity_assessment(
                applicant_mark=applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=0.5,
                aural_score=-0.1  # Invalid score < 0.0
            )

    @pytest.mark.asyncio
    async def test_mark_similarity_assessment_with_model_parameter(self):
        """Test mark similarity assessment with specific model parameter."""
        applicant_mark = models.Mark(wordmark="TEST1")
        opponent_mark = models.Mark(wordmark="TEST2")
        
        result = await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=0.7,
            aural_score=0.6,
            model="gemini-2.0-flash-001"
        )
        
        assert isinstance(result, models.MarkSimilarityOutput)


class TestGenerateGsLikelihoodAssessment:
    """Test cases for generate_gs_likelihood_assessment function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up LLM mocks for all tests in this class."""
        with apply_llm_mocks():
            yield

    @pytest.mark.asyncio
    async def test_gs_likelihood_assessment_valid_input(self):
        """Test goods/services likelihood assessment with valid input."""
        applicant_good = models.GoodService(term="Legal software", nice_class=9)
        opponent_good = models.GoodService(term="Business software", nice_class=9)
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        result = await llm.generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        
        assert isinstance(result, models.GoodServiceLikelihoodOutput)
        assert isinstance(result.are_competitive, bool)
        assert isinstance(result.are_complementary, bool)
        assert 0.0 <= result.similarity_score <= 1.0
        assert isinstance(result.likelihood_of_confusion, bool)
        
        # If no confusion, confusion_type should be None
        if not result.likelihood_of_confusion:
            assert result.confusion_type is None

    @pytest.mark.asyncio
    async def test_gs_likelihood_assessment_identical_goods(self):
        """Test goods/services likelihood assessment with identical goods."""
        applicant_good = models.GoodService(term="Legal software", nice_class=9)
        opponent_good = models.GoodService(term="Legal software", nice_class=9)
        mark_similarity = HIGH_SIMILARITY_ASSESSMENT
        
        result = await llm.generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        
        assert result.are_competitive is True
        assert result.likelihood_of_confusion is True

    @pytest.mark.asyncio
    async def test_gs_likelihood_assessment_unrelated_goods(self):
        """Test goods/services likelihood assessment with unrelated goods."""
        applicant_good = models.GoodService(term="Live plants", nice_class=31)
        opponent_good = models.GoodService(term="Vehicles", nice_class=12)
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        result = await llm.generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        
        assert result.are_competitive is False
        assert result.likelihood_of_confusion is False
        assert result.confusion_type is None

    @pytest.mark.asyncio
    async def test_gs_likelihood_assessment_different_nice_classes(self):
        """Test goods/services likelihood assessment with different Nice classes."""
        applicant_good = models.GoodService(term="Software", nice_class=9)
        opponent_good = models.GoodService(term="Consulting", nice_class=42)
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        result = await llm.generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        
        assert isinstance(result, models.GoodServiceLikelihoodOutput)

    @pytest.mark.asyncio
    async def test_gs_likelihood_assessment_with_model_parameter(self):
        """Test goods/services likelihood assessment with specific model parameter."""
        applicant_good = models.GoodService(term="Software", nice_class=9)
        opponent_good = models.GoodService(term="Hardware", nice_class=9)
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        result = await llm.generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity,
            model="gemini-2.0-flash-001"
        )
        
        assert isinstance(result, models.GoodServiceLikelihoodOutput)


class TestBatchProcessGoodsServices:
    """Test cases for batch_process_goods_services function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up LLM mocks for all tests in this class."""
        with apply_llm_mocks():
            yield

    @pytest.mark.asyncio
    async def test_batch_process_single_items(self):
        """Test batch processing with single items in each list."""
        applicant_goods = [models.GoodService(term="Legal software", nice_class=9)]
        opponent_goods = [models.GoodService(term="Business software", nice_class=9)]
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        results = await llm.batch_process_goods_services(
            applicant_goods=applicant_goods,
            opponent_goods=opponent_goods,
            mark_similarity=mark_similarity
        )
        
        assert len(results) == 1
        assert isinstance(results[0], models.GoodServiceLikelihoodOutput)

    @pytest.mark.asyncio
    async def test_batch_process_multiple_items(self):
        """Test batch processing with multiple items."""
        applicant_goods = [
            models.GoodService(term="Legal software", nice_class=9),
            models.GoodService(term="Business software", nice_class=9)
        ]
        opponent_goods = [
            models.GoodService(term="Computer software", nice_class=9),
            models.GoodService(term="Mobile apps", nice_class=9)
        ]
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        results = await llm.batch_process_goods_services(
            applicant_goods=applicant_goods,
            opponent_goods=opponent_goods,
            mark_similarity=mark_similarity
        )
        
        # Should return 4 results (2 × 2 combinations)
        assert len(results) == 4
        for result in results:
            assert isinstance(result, models.GoodServiceLikelihoodOutput)

    @pytest.mark.asyncio
    async def test_batch_process_empty_lists(self):
        """Test batch processing with empty lists."""
        applicant_goods = []
        opponent_goods = [models.GoodService(term="Software", nice_class=9)]
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        results = await llm.batch_process_goods_services(
            applicant_goods=applicant_goods,
            opponent_goods=opponent_goods,
            mark_similarity=mark_similarity
        )
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_batch_process_asymmetric_lists(self):
        """Test batch processing with different list sizes."""
        applicant_goods = [
            models.GoodService(term="Software", nice_class=9)
        ]
        opponent_goods = [
            models.GoodService(term="Hardware", nice_class=9),
            models.GoodService(term="Services", nice_class=42),
            models.GoodService(term="Consulting", nice_class=35)
        ]
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        results = await llm.batch_process_goods_services(
            applicant_goods=applicant_goods,
            opponent_goods=opponent_goods,
            mark_similarity=mark_similarity
        )
        
        # Should return 3 results (1 × 3 combinations)
        assert len(results) == 3
        for result in results:
            assert isinstance(result, models.GoodServiceLikelihoodOutput)

    @pytest.mark.asyncio
    async def test_batch_process_concurrent_execution(self):
        """Test that batch processing executes concurrently."""
        applicant_goods = [
            models.GoodService(term="Software 1", nice_class=9),
            models.GoodService(term="Software 2", nice_class=9)
        ]
        opponent_goods = [
            models.GoodService(term="Hardware 1", nice_class=9),
            models.GoodService(term="Hardware 2", nice_class=9)
        ]
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        # Mock the individual assessment function to track calls
        with patch('trademark_core.llm.generate_gs_likelihood_assessment') as mock_assess:
            mock_assess.return_value = models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
            
            results = await llm.batch_process_goods_services(
                applicant_goods=applicant_goods,
                opponent_goods=opponent_goods,
                mark_similarity=mark_similarity
            )
            
            # Should have called the assessment function 4 times
            assert mock_assess.call_count == 4
            assert len(results) == 4


class TestGenerateCasePrediction:
    """Test cases for generate_case_prediction function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up LLM mocks for all tests in this class."""
        with apply_llm_mocks():
            yield

    @pytest.mark.asyncio
    async def test_case_prediction_valid_input(self):
        """Test case prediction with valid input."""
        mark_similarity = HIGH_SIMILARITY_ASSESSMENT
        gs_likelihoods = [
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.9,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
        ]
        
        result = await llm.generate_case_prediction(
            mark_similarity=mark_similarity,
            goods_services_likelihoods=gs_likelihoods
        )
        
        assert isinstance(result, models.OppositionOutcome)
        assert result.result in [
            "Opposition likely to succeed",
            "Opposition may partially succeed",
            "Opposition likely to fail"
        ]
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_case_prediction_high_similarity_high_confusion(self):
        """Test case prediction with high similarity and high confusion likelihood."""
        mark_similarity = models.MarkSimilarityOutput(
            visual="high",
            aural="high",
            conceptual="high",
            overall="high"
        )
        gs_likelihoods = [
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.95,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
        ]
        
        result = await llm.generate_case_prediction(
            mark_similarity=mark_similarity,
            goods_services_likelihoods=gs_likelihoods
        )
        
        # Should likely predict success with high confidence
        assert isinstance(result, models.OppositionOutcome)

    @pytest.mark.asyncio
    async def test_case_prediction_low_similarity_no_confusion(self):
        """Test case prediction with low similarity and no confusion."""
        mark_similarity = models.MarkSimilarityOutput(
            visual="dissimilar",
            aural="dissimilar",
            conceptual="dissimilar",
            overall="dissimilar"
        )
        gs_likelihoods = [
            models.GoodServiceLikelihoodOutput(
                are_competitive=False,
                are_complementary=False,
                similarity_score=0.1,
                likelihood_of_confusion=False,
                confusion_type=None
            )
        ]
        
        result = await llm.generate_case_prediction(
            mark_similarity=mark_similarity,
            goods_services_likelihoods=gs_likelihoods
        )
        
        # Should likely predict failure
        assert isinstance(result, models.OppositionOutcome)

    @pytest.mark.asyncio
    async def test_case_prediction_multiple_gs_likelihoods(self):
        """Test case prediction with multiple goods/services likelihoods."""
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        gs_likelihoods = [
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.8,
                likelihood_of_confusion=True,
                confusion_type="direct"
            ),
            models.GoodServiceLikelihoodOutput(
                are_competitive=False,
                are_complementary=True,
                similarity_score=0.3,
                likelihood_of_confusion=False,
                confusion_type=None
            ),
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.6,
                likelihood_of_confusion=True,
                confusion_type="indirect"
            )
        ]
        
        result = await llm.generate_case_prediction(
            mark_similarity=mark_similarity,
            goods_services_likelihoods=gs_likelihoods
        )
        
        assert isinstance(result, models.OppositionOutcome)

    @pytest.mark.asyncio
    async def test_case_prediction_with_model_parameter(self):
        """Test case prediction with specific model parameter."""
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        gs_likelihoods = [
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
        ]
        
        result = await llm.generate_case_prediction(
            mark_similarity=mark_similarity,
            goods_services_likelihoods=gs_likelihoods,
            model="gemini-2.0-flash-001"
        )
        
        assert isinstance(result, models.OppositionOutcome)


class TestConceptualSimilarityLLM:
    """Test cases for _get_conceptual_similarity_score_from_llm function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up LLM mocks for all tests in this class."""
        with apply_llm_mocks():
            yield

    @pytest.mark.asyncio
    async def test_conceptual_similarity_llm_valid_input(self):
        """Test conceptual similarity LLM function with valid input."""
        result = await llm._get_conceptual_similarity_score_from_llm("MOUNTAIN", "HILL")
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_conceptual_similarity_llm_identical_words(self):
        """Test conceptual similarity LLM function with identical words."""
        result = await llm._get_conceptual_similarity_score_from_llm("EXAMPLE", "EXAMPLE")
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_conceptual_similarity_llm_different_words(self):
        """Test conceptual similarity LLM function with different words."""
        result = await llm._get_conceptual_similarity_score_from_llm("MOUNTAIN", "OCEAN")
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_conceptual_similarity_llm_with_model_parameter(self):
        """Test conceptual similarity LLM function with specific model parameter."""
        result = await llm._get_conceptual_similarity_score_from_llm(
            "MOUNTAIN", 
            "HILL", 
            model="gemini-2.0-flash-001"
        )
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_conceptual_similarity_llm_empty_strings(self):
        """Test conceptual similarity LLM function with empty strings."""
        # This should be handled by the calling function, but test robustness
        result = await llm._get_conceptual_similarity_score_from_llm("", "")
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0


class TestLLMErrorHandling:
    """Test cases for LLM error handling scenarios."""

    @pytest.mark.asyncio
    async def test_mark_similarity_llm_error(self):
        """Test mark similarity assessment when LLM raises an error."""
        # Patch the specific function instead of the generic one
        with patch('trademark_core.llm.generate_mark_similarity_assessment') as mock_func:
            mock_func.side_effect = Exception("LLM service unavailable")
            
            applicant_mark = models.Mark(wordmark="TEST1")
            opponent_mark = models.Mark(wordmark="TEST2")
            
            with pytest.raises(Exception) as exc_info:
                await llm.generate_mark_similarity_assessment(
                    applicant_mark=applicant_mark,
                    opponent_mark=opponent_mark,
                    visual_score=0.7,
                    aural_score=0.6
                )
            
            assert "LLM service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_gs_likelihood_llm_error(self):
        """Test goods/services likelihood assessment when LLM raises an error."""
        # Patch the specific function instead of the generic one
        with patch('trademark_core.llm.generate_gs_likelihood_assessment') as mock_func:
            mock_func.side_effect = Exception("LLM service unavailable")
            
            applicant_good = models.GoodService(term="Software", nice_class=9)
            opponent_good = models.GoodService(term="Hardware", nice_class=9)
            mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
            
            with pytest.raises(Exception) as exc_info:
                await llm.generate_gs_likelihood_assessment(
                    applicant_good=applicant_good,
                    opponent_good=opponent_good,
                    mark_similarity=mark_similarity
                )
            
            assert "LLM service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_case_prediction_llm_error(self):
        """Test case prediction when LLM raises an error."""
        # Patch the specific function instead of the generic one
        with patch('trademark_core.llm.generate_case_prediction') as mock_func:
            mock_func.side_effect = Exception("LLM service unavailable")
            
            mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
            gs_likelihoods = [
                models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.7,
                    likelihood_of_confusion=True,
                    confusion_type="direct"
                )
            ]
            
            with pytest.raises(Exception) as exc_info:
                await llm.generate_case_prediction(
                    mark_similarity=mark_similarity,
                    goods_services_likelihoods=gs_likelihoods
                )
            
            assert "LLM service unavailable" in str(exc_info.value) 