"""
Unit tests for Pydantic models in trademark_core.models.

These tests validate the single source of truth (SSoT) data models,
ensuring proper validation, serialization, and edge case handling.
"""

import pytest
from pydantic import ValidationError

from trademark_core import models


class TestMark:
    """Test cases for the Mark model."""

    def test_mark_creation_valid(self):
        """Test creating a valid Mark instance."""
        mark = models.Mark(wordmark="EXAMPLE")
        assert mark.wordmark == "EXAMPLE"
        assert mark.is_registered is False
        assert mark.registration_number is None

    def test_mark_with_registration(self):
        """Test creating a Mark with registration details."""
        mark = models.Mark(
            wordmark="REGISTERED MARK",
            is_registered=True,
            registration_number="UK00003123456"
        )
        assert mark.wordmark == "REGISTERED MARK"
        assert mark.is_registered is True
        assert mark.registration_number == "UK00003123456"

    def test_mark_empty_wordmark_accepted(self):
        """Test that empty wordmark is accepted (Pydantic allows empty strings by default)."""
        mark = models.Mark(wordmark="")
        assert mark.wordmark == ""
        assert mark.is_registered is False
        assert mark.registration_number is None

    def test_mark_missing_wordmark_fails(self):
        """Test that missing wordmark raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.Mark()
        assert "Field required" in str(exc_info.value)

    def test_mark_case_sensitivity(self):
        """Test that wordmark preserves case sensitivity."""
        mark = models.Mark(wordmark="CaSeSeNsItIvE")
        assert mark.wordmark == "CaSeSeNsItIvE"


class TestGoodService:
    """Test cases for the GoodService model."""

    def test_good_service_creation_valid(self):
        """Test creating a valid GoodService instance."""
        good = models.GoodService(term="Computer software", nice_class=9)
        assert good.term == "Computer software"
        assert good.nice_class == 9

    def test_good_service_nice_class_boundaries(self):
        """Test Nice class validation boundaries."""
        # Valid boundaries
        good1 = models.GoodService(term="Goods", nice_class=1)
        good45 = models.GoodService(term="Services", nice_class=45)
        assert good1.nice_class == 1
        assert good45.nice_class == 45

    def test_good_service_nice_class_below_range_fails(self):
        """Test that Nice class below 1 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.GoodService(term="Invalid", nice_class=0)
        assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_good_service_nice_class_above_range_fails(self):
        """Test that Nice class above 45 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.GoodService(term="Invalid", nice_class=46)
        assert "Input should be less than or equal to 45" in str(exc_info.value)

    def test_good_service_empty_term_accepted(self):
        """Test that empty term is accepted (Pydantic allows empty strings by default)."""
        good = models.GoodService(term="", nice_class=9)
        assert good.term == ""
        assert good.nice_class == 9


class TestConceptualSimilarityScore:
    """Test cases for the ConceptualSimilarityScore model."""

    def test_conceptual_score_valid_range(self):
        """Test valid score range (0.0 to 1.0)."""
        score_min = models.ConceptualSimilarityScore(score=0.0)
        score_mid = models.ConceptualSimilarityScore(score=0.5)
        score_max = models.ConceptualSimilarityScore(score=1.0)
        
        assert score_min.score == 0.0
        assert score_mid.score == 0.5
        assert score_max.score == 1.0

    def test_conceptual_score_below_range_fails(self):
        """Test that score below 0.0 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.ConceptualSimilarityScore(score=-0.1)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_conceptual_score_above_range_fails(self):
        """Test that score above 1.0 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.ConceptualSimilarityScore(score=1.1)
        assert "Input should be less than or equal to 1" in str(exc_info.value)


class TestMarkSimilarityOutput:
    """Test cases for the MarkSimilarityOutput model."""

    def test_mark_similarity_output_valid(self):
        """Test creating a valid MarkSimilarityOutput instance."""
        output = models.MarkSimilarityOutput(
            visual="high",
            aural="moderate",
            conceptual="low",
            overall="moderate",
            reasoning="Test reasoning"
        )
        assert output.visual == "high"
        assert output.aural == "moderate"
        assert output.conceptual == "low"
        assert output.overall == "moderate"
        assert output.reasoning == "Test reasoning"

    def test_mark_similarity_output_without_reasoning(self):
        """Test creating MarkSimilarityOutput without optional reasoning."""
        output = models.MarkSimilarityOutput(
            visual="identical",
            aural="identical",
            conceptual="identical",
            overall="identical"
        )
        assert output.reasoning is None

    def test_mark_similarity_output_invalid_enum_fails(self):
        """Test that invalid enum values raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.MarkSimilarityOutput(
                visual="invalid",
                aural="moderate",
                conceptual="low",
                overall="moderate"
            )
        assert "Input should be" in str(exc_info.value)

    def test_mark_similarity_output_all_enum_values(self):
        """Test all valid enum values for similarity categories."""
        valid_values = ["dissimilar", "low", "moderate", "high", "identical"]
        
        for value in valid_values:
            output = models.MarkSimilarityOutput(
                visual=value,
                aural=value,
                conceptual=value,
                overall=value
            )
            assert output.visual == value
            assert output.aural == value
            assert output.conceptual == value
            assert output.overall == value


class TestGoodServiceLikelihoodOutput:
    """Test cases for the GoodServiceLikelihoodOutput model."""

    def test_gs_likelihood_output_valid_with_confusion(self):
        """Test creating valid GoodServiceLikelihoodOutput with confusion."""
        output = models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.8,
            likelihood_of_confusion=True,
            confusion_type="direct"
        )
        assert output.are_competitive is True
        assert output.are_complementary is False
        assert output.similarity_score == 0.8
        assert output.likelihood_of_confusion is True
        assert output.confusion_type == "direct"

    def test_gs_likelihood_output_valid_without_confusion(self):
        """Test creating valid GoodServiceLikelihoodOutput without confusion."""
        output = models.GoodServiceLikelihoodOutput(
            are_competitive=False,
            are_complementary=True,
            similarity_score=0.2,
            likelihood_of_confusion=False,
            confusion_type=None
        )
        assert output.are_competitive is False
        assert output.are_complementary is True
        assert output.similarity_score == 0.2
        assert output.likelihood_of_confusion is False
        assert output.confusion_type is None

    def test_gs_likelihood_similarity_score_boundaries(self):
        """Test similarity score validation boundaries."""
        # Valid boundaries
        output_min = models.GoodServiceLikelihoodOutput(
            are_competitive=False,
            are_complementary=False,
            similarity_score=0.0,
            likelihood_of_confusion=False
        )
        output_max = models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=1.0,
            likelihood_of_confusion=True,
            confusion_type="direct"
        )
        assert output_min.similarity_score == 0.0
        assert output_max.similarity_score == 1.0

    def test_gs_likelihood_similarity_score_invalid_fails(self):
        """Test that invalid similarity scores raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=1.5,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
        assert "Input should be less than or equal to 1" in str(exc_info.value)

    def test_gs_likelihood_confusion_type_values(self):
        """Test valid confusion type enum values."""
        valid_types = ["direct", "indirect"]
        
        for confusion_type in valid_types:
            output = models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=True,
                confusion_type=confusion_type
            )
            assert output.confusion_type == confusion_type

    def test_gs_likelihood_invalid_confusion_type_fails(self):
        """Test that invalid confusion type raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=True,
                confusion_type="invalid"
            )
        assert "Input should be" in str(exc_info.value)


class TestOppositionOutcome:
    """Test cases for the OppositionOutcome model."""

    def test_opposition_outcome_valid(self):
        """Test creating a valid OppositionOutcome instance."""
        outcome = models.OppositionOutcome(
            result="Opposition likely to succeed",
            confidence=0.85,
            reasoning="Strong mark similarity and identical goods."
        )
        assert outcome.result == "Opposition likely to succeed"
        assert outcome.confidence == 0.85
        assert outcome.reasoning == "Strong mark similarity and identical goods."

    def test_opposition_outcome_all_result_values(self):
        """Test all valid result enum values."""
        valid_results = [
            "Opposition likely to succeed",
            "Opposition may partially succeed", 
            "Opposition likely to fail"
        ]
        
        for result in valid_results:
            outcome = models.OppositionOutcome(
                result=result,
                confidence=0.7,
                reasoning="Test reasoning"
            )
            assert outcome.result == result

    def test_opposition_outcome_confidence_boundaries(self):
        """Test confidence score validation boundaries."""
        # Valid boundaries
        outcome_min = models.OppositionOutcome(
            result="Opposition likely to fail",
            confidence=0.0,
            reasoning="No similarity found."
        )
        outcome_max = models.OppositionOutcome(
            result="Opposition likely to succeed",
            confidence=1.0,
            reasoning="Identical marks and goods."
        )
        assert outcome_min.confidence == 0.0
        assert outcome_max.confidence == 1.0

    def test_opposition_outcome_invalid_confidence_fails(self):
        """Test that invalid confidence scores raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.OppositionOutcome(
                result="Opposition likely to succeed",
                confidence=1.5,
                reasoning="Invalid confidence"
            )
        assert "Input should be less than or equal to 1" in str(exc_info.value)

    def test_opposition_outcome_invalid_result_fails(self):
        """Test that invalid result values raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            models.OppositionOutcome(
                result="Invalid result",
                confidence=0.7,
                reasoning="Test reasoning"
            )
        assert "Input should be" in str(exc_info.value)


class TestRequestModels:
    """Test cases for request models."""

    def test_mark_similarity_request_valid(self):
        """Test creating a valid MarkSimilarityRequest."""
        applicant = models.Mark(wordmark="APPLICANT")
        opponent = models.Mark(wordmark="OPPONENT")
        
        request = models.MarkSimilarityRequest(
            applicant=applicant,
            opponent=opponent
        )
        assert request.applicant.wordmark == "APPLICANT"
        assert request.opponent.wordmark == "OPPONENT"

    def test_gs_similarity_request_valid(self):
        """Test creating a valid GsSimilarityRequest."""
        applicant_good = models.GoodService(term="Software", nice_class=9)
        opponent_good = models.GoodService(term="Hardware", nice_class=9)
        mark_similarity = models.MarkSimilarityOutput(
            visual="moderate",
            aural="moderate", 
            conceptual="moderate",
            overall="moderate"
        )
        
        request = models.GsSimilarityRequest(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        assert request.applicant_good.term == "Software"
        assert request.opponent_good.term == "Hardware"
        assert request.mark_similarity.overall == "moderate"

    def test_batch_gs_similarity_request_valid(self):
        """Test creating a valid BatchGsSimilarityRequest."""
        applicant_goods = [
            models.GoodService(term="Software", nice_class=9),
            models.GoodService(term="Apps", nice_class=9)
        ]
        opponent_goods = [
            models.GoodService(term="Hardware", nice_class=9)
        ]
        mark_similarity = models.MarkSimilarityOutput(
            visual="moderate",
            aural="moderate",
            conceptual="moderate", 
            overall="moderate"
        )
        
        request = models.BatchGsSimilarityRequest(
            applicant_goods=applicant_goods,
            opponent_goods=opponent_goods,
            mark_similarity=mark_similarity
        )
        assert len(request.applicant_goods) == 2
        assert len(request.opponent_goods) == 1
        assert request.mark_similarity.overall == "moderate"

    def test_batch_gs_similarity_request_empty_lists_fail(self):
        """Test that empty goods lists raise validation error."""
        mark_similarity = models.MarkSimilarityOutput(
            visual="moderate",
            aural="moderate",
            conceptual="moderate",
            overall="moderate"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            models.BatchGsSimilarityRequest(
                applicant_goods=[],
                opponent_goods=[models.GoodService(term="Test", nice_class=9)],
                mark_similarity=mark_similarity
            )
        assert "List should have at least 1 item" in str(exc_info.value)

    def test_case_prediction_request_valid(self):
        """Test creating a valid CasePredictionRequest."""
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
                similarity_score=0.9,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
        ]
        
        request = models.CasePredictionRequest(
            mark_similarity=mark_similarity,
            goods_services_likelihoods=gs_likelihoods
        )
        assert request.mark_similarity.overall == "high"
        assert len(request.goods_services_likelihoods) == 1
        assert request.goods_services_likelihoods[0].likelihood_of_confusion is True

    def test_case_prediction_request_empty_gs_likelihoods_fails(self):
        """Test that empty goods/services likelihoods list raises validation error."""
        mark_similarity = models.MarkSimilarityOutput(
            visual="high",
            aural="high", 
            conceptual="high",
            overall="high"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            models.CasePredictionRequest(
                mark_similarity=mark_similarity,
                goods_services_likelihoods=[]
            )
        assert "List should have at least 1 item" in str(exc_info.value)


class TestCasePredictionResult:
    """Test cases for the CasePredictionResult model."""

    def test_case_prediction_result_valid(self):
        """Test creating a valid CasePredictionResult."""
        mark_comparison = models.MarkSimilarityOutput(
            visual="high",
            aural="high",
            conceptual="high", 
            overall="high"
        )
        gs_likelihoods = [
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.9,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
        ]
        opposition_outcome = models.OppositionOutcome(
            result="Opposition likely to succeed",
            confidence=0.9,
            reasoning="High mark similarity and direct confusion."
        )
        
        result = models.CasePredictionResult(
            mark_comparison=mark_comparison,
            goods_services_likelihoods=gs_likelihoods,
            opposition_outcome=opposition_outcome
        )
        
        assert result.mark_comparison.overall == "high"
        assert len(result.goods_services_likelihoods) == 1
        assert result.opposition_outcome.result == "Opposition likely to succeed"
        assert result.opposition_outcome.confidence == 0.9 