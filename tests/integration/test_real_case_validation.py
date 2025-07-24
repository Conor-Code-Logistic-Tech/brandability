"""
End-to-end tests validating trademark predictions against real UKIPO case outcomes.

This module tests the complete trademark prediction pipeline using actual case data
from UK IPO opposition decisions to ensure accuracy and legal validity.
"""

import asyncio
import json
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from trademark_core import models
from trademark_core.llm import (
    generate_mark_similarity_assessment,
    generate_gs_likelihood_assessment,
    generate_case_prediction,
)
from trademark_core.similarity import calculate_visual_similarity, calculate_aural_similarity

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / "test-data" / "case_json"


class RealCaseTestCase:
    """A test case based on real UKIPO opposition data."""
    
    def __init__(self, case_file: Path):
        with open(case_file, 'r', encoding='utf-8') as f:
            self.raw_data = json.load(f)
        self.case_data = self.raw_data["data"]
        self.case_name = case_file.stem
        
    @property
    def applicant_mark(self) -> models.Mark:
        """Extract applicant mark from case data."""
        mark_data = self.case_data["applicant_marks"][0]
        return models.Mark(
            wordmark=mark_data["mark"],
            is_registered=False
        )
    
    @property
    def opponent_marks(self) -> List[models.Mark]:
        """Extract opponent marks from case data."""
        marks = []
        for mark_data in self.case_data["opponent_marks"]:
            marks.append(models.Mark(
                wordmark=mark_data["mark"],
                is_registered=True,
                registration_number=mark_data.get("registration_number")
            ))
        return marks
    
    @property
    def goods_services_comparisons(self) -> List[Dict[str, Any]]:
        """Extract goods/services comparisons from case data."""
        return self.case_data.get("goods_services_comparison", [])
    
    @property
    def actual_opposition_outcome(self) -> str:
        """Get the actual opposition outcome from the case."""
        return self.case_data["opposition_outcome"]
    
    @property
    def actual_mark_similarity(self) -> Dict[str, str]:
        """Get the actual mark similarity assessment."""
        return self.case_data["mark_comparison"]
    
    @property
    def actual_confusion_found(self) -> bool:
        """Get whether confusion was actually found."""
        return self.case_data["likelihood_of_confusion"]["confusion_found"]


def load_test_cases() -> List[RealCaseTestCase]:
    """Load all real case test cases from the test data directory."""
    test_cases = []
    for case_file in TEST_DATA_DIR.glob("*.json"):
        try:
            test_case = RealCaseTestCase(case_file)
            test_cases.append(test_case)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Skipping malformed case file {case_file}: {e}")
            continue
    return test_cases


# Load test cases for parametrization
REAL_TEST_CASES = load_test_cases()
CASE_IDS = [case.case_name for case in REAL_TEST_CASES]


class TestRealCaseValidation:
    """Test trademark predictions against real UKIPO case outcomes."""
    
    @pytest.mark.parametrize("test_case", REAL_TEST_CASES, ids=CASE_IDS)
    @pytest.mark.asyncio
    async def test_mark_similarity_accuracy(self, test_case: RealCaseTestCase):
        """Test mark similarity assessment accuracy against real cases."""
        if not test_case.opponent_marks:
            pytest.skip("No opponent marks in case data")
        
        # Test against first opponent mark (most common scenario)
        opponent_mark = test_case.opponent_marks[0]
        
        # Calculate algorithmic similarities
        visual_score = calculate_visual_similarity(
            test_case.applicant_mark.wordmark, 
            opponent_mark.wordmark
        )
        aural_score = calculate_aural_similarity(
            test_case.applicant_mark.wordmark,
            opponent_mark.wordmark
        )
        
        # Get LLM assessment
        predicted_similarity = await generate_mark_similarity_assessment(
            applicant_mark=test_case.applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=visual_score,
            aural_score=aural_score
        )
        
        # Map actual assessment to our enum format
        actual_visual = self._map_similarity_term(test_case.actual_mark_similarity["visual_similarity"])
        actual_aural = self._map_similarity_term(test_case.actual_mark_similarity["aural_similarity"])
        actual_conceptual = self._map_similarity_term(test_case.actual_mark_similarity["conceptual_similarity"])
        
        # Skip test if any similarity term couldn't be mapped
        if actual_visual is None or actual_aural is None or actual_conceptual is None:
            pytest.skip(f"Could not map similarity terms for case {test_case.case_name}")
        
        # Check if predictions are within reasonable range
        # (exact match not expected due to subjective nature of trademark assessment)
        self._assert_similarity_reasonable(
            predicted_similarity.visual, actual_visual,
            f"Visual similarity mismatch in {test_case.case_name}"
        )
        self._assert_similarity_reasonable(
            predicted_similarity.aural, actual_aural,
            f"Aural similarity mismatch in {test_case.case_name}"
        )
        self._assert_similarity_reasonable(
            predicted_similarity.conceptual, actual_conceptual,
            f"Conceptual similarity mismatch in {test_case.case_name}"
        )
        
        # Ensure reasoning is provided
        assert predicted_similarity.reasoning is not None, "Reasoning should be provided"
        assert len(predicted_similarity.reasoning) > 50, "Reasoning should be substantial"
    
    @pytest.mark.parametrize("test_case", REAL_TEST_CASES, ids=CASE_IDS)
    @pytest.mark.asyncio
    async def test_goods_services_analysis_accuracy(self, test_case: RealCaseTestCase):
        """Test goods/services analysis accuracy against real cases."""
        if not test_case.goods_services_comparisons:
            pytest.skip("No goods/services comparisons in case data")
        
        # Create a basic mark similarity for context
        mark_similarity = models.MarkSimilarityOutput(
            visual="moderate",
            aural="moderate", 
            conceptual="moderate",
            overall="moderate",
            reasoning="Test context"
        )
        
        # Test a sample of goods/services comparisons
        for comparison in test_case.goods_services_comparisons[:3]:  # Limit for performance
            applicant_class = self._extract_class_from_comparison(comparison, "applicant")
            opponent_class = self._extract_class_from_comparison(comparison, "opponent")
            
            # Skip this comparison if we can't determine Nice classes
            if applicant_class is None or opponent_class is None:
                continue
            
            applicant_good = models.GoodService(
                term=comparison["applicant_term"],
                nice_class=applicant_class
            )
            opponent_good = models.GoodService(
                term=comparison["opponent_term"],
                nice_class=opponent_class
            )
            
            predicted_gs = await generate_gs_likelihood_assessment(
                applicant_good=applicant_good,
                opponent_good=opponent_good,
                mark_similarity=mark_similarity
            )
            
            actual_similarity = comparison["similarity"]
            
            # Validate the prediction makes legal sense
            self._assert_gs_assessment_valid(predicted_gs, actual_similarity, comparison)
    
    @pytest.mark.parametrize("test_case", REAL_TEST_CASES, ids=CASE_IDS)
    @pytest.mark.asyncio
    async def test_case_prediction_accuracy(self, test_case: RealCaseTestCase):
        """Test complete case prediction accuracy against real outcomes."""
        if not test_case.opponent_marks or not test_case.goods_services_comparisons:
            pytest.skip("Insufficient case data for complete prediction")
        
        # Generate mark similarity assessment
        opponent_mark = test_case.opponent_marks[0]
        visual_score = calculate_visual_similarity(
            test_case.applicant_mark.wordmark,
            opponent_mark.wordmark
        )
        aural_score = calculate_aural_similarity(
            test_case.applicant_mark.wordmark,
            opponent_mark.wordmark
        )
        
        mark_similarity = await generate_mark_similarity_assessment(
            applicant_mark=test_case.applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=visual_score,
            aural_score=aural_score
        )
        
        # Generate goods/services assessments for key comparisons
        gs_assessments = []
        for comparison in test_case.goods_services_comparisons[:5]:  # Limit for performance
            applicant_class = self._extract_class_from_comparison(comparison, "applicant")
            opponent_class = self._extract_class_from_comparison(comparison, "opponent")
            
            # Skip this comparison if we can't determine Nice classes
            if applicant_class is None or opponent_class is None:
                continue
            
            applicant_good = models.GoodService(
                term=comparison["applicant_term"],
                nice_class=applicant_class
            )
            opponent_good = models.GoodService(
                term=comparison["opponent_term"],
                nice_class=opponent_class
            )
            
            gs_assessment = await generate_gs_likelihood_assessment(
                applicant_good=applicant_good,
                opponent_good=opponent_good,
                mark_similarity=mark_similarity
            )
            gs_assessments.append(gs_assessment)
        
        # Generate final case prediction
        case_prediction = await generate_case_prediction(
            mark_similarity=mark_similarity,
            goods_services_likelihoods=gs_assessments
        )
        
        # Validate the prediction
        actual_outcome = test_case.actual_opposition_outcome
        predicted_outcome = case_prediction.result
        actual_confusion = test_case.actual_confusion_found
        
        # Check if prediction aligns with actual outcome
        self._assert_case_prediction_reasonable(
            predicted_outcome, actual_outcome, actual_confusion, test_case.case_name
        )
        
        # Validate confidence scoring (this should NOT always be 0.9!)
        assert 0.0 <= case_prediction.confidence <= 1.0, "Confidence must be between 0 and 1"
        assert case_prediction.confidence != 0.9, f"Confidence should not always be 0.9! Got {case_prediction.confidence} for {test_case.case_name}"
        
        # Ensure reasoning is comprehensive
        assert len(case_prediction.reasoning) > 100, "Case prediction reasoning should be comprehensive"
    
    @pytest.mark.asyncio
    async def test_confidence_score_variation(self):
        """Test that confidence scores vary appropriately based on case strength."""
        confidence_scores = []
        
        # Test a variety of cases to ensure confidence scores vary
        for test_case in REAL_TEST_CASES[:10]:  # Test 10 cases for performance
            if not test_case.opponent_marks:
                continue
                
            opponent_mark = test_case.opponent_marks[0]
            visual_score = calculate_visual_similarity(
                test_case.applicant_mark.wordmark,
                opponent_mark.wordmark
            )
            aural_score = calculate_aural_similarity(
                test_case.applicant_mark.wordmark,
                opponent_mark.wordmark
            )
            
            mark_similarity = await generate_mark_similarity_assessment(
                applicant_mark=test_case.applicant_mark,
                opponent_mark=opponent_mark,
                visual_score=visual_score,
                aural_score=aural_score
            )
            
            # Create a simple goods assessment
            gs_assessment = models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
            
            case_prediction = await generate_case_prediction(
                mark_similarity=mark_similarity,
                goods_services_likelihoods=[gs_assessment]
            )
            
            confidence_scores.append(case_prediction.confidence)
        
        # Ensure we have variation in confidence scores
        assert len(set(confidence_scores)) > 1, f"Confidence scores should vary! All scores: {confidence_scores}"
        assert min(confidence_scores) < 0.8, "Some cases should have low confidence"
        assert max(confidence_scores) > 0.6, "Some cases should have high confidence"
    
    def _map_similarity_term(self, term: str) -> models.EnumStr:
        """Map actual case similarity terms to our enum values."""
        term_lower = term.lower()
        if "identical" in term_lower:
            return "identical"
        elif "high" in term_lower:
            return "high"
        elif "medium" in term_lower or "moderate" in term_lower:
            return "moderate"
        elif "low" in term_lower:
            return "low"
        elif "dissimilar" in term_lower or "neutral" in term_lower:
            return "dissimilar"
        else:
            # Log warning for unmapped terms
            import warnings
            warnings.warn(f"Unmapped similarity term: '{term}' - returning None", UserWarning)
            return None
    
    def _extract_class_from_comparison(self, comparison: Dict[str, Any], party: str) -> int:
        """Extract Nice class from goods/services comparison data.
        
        Since Nice classes are not directly included in comparison data,
        this attempts to match the term back to the original goods/services data.
        If no match is found, returns None.
        """
        term_to_find = comparison[f"{party}_term"]
        
        # First check if Nice class is directly in comparison (some test data might have it)
        class_key = f"{party}_class"
        if class_key in comparison:
            return comparison[class_key]
        
        # Otherwise, try to find the term in the original goods/services data
        if party == "applicant":
            marks_data = self.case_data.get("applicant_marks", [])
        else:  # opponent
            marks_data = self.case_data.get("opponent_marks", [])
        
        # Search through all marks and their goods/services
        for mark in marks_data:
            for gs in mark.get("goods_services", []):
                nice_class = gs.get("class")
                terms = gs.get("terms", [])
                
                # Check if our term appears in any of the terms for this class
                for class_term in terms:
                    if term_to_find.lower() in class_term.lower() or class_term.lower() in term_to_find.lower():
                        return nice_class
        
        # If no match found, log warning and return None
        import warnings
        warnings.warn(f"Could not find Nice class for {party} term: '{term_to_find}'", UserWarning)
        return None
    
    def _assert_similarity_reasonable(self, predicted: str, actual: str, message: str):
        """Assert that predicted similarity is within reasonable range of actual."""
        similarity_order = ["dissimilar", "low", "moderate", "high", "identical"]
        predicted_idx = similarity_order.index(predicted)
        actual_idx = similarity_order.index(actual)
        
        # Allow for 1-level difference (subjective nature of trademark assessment)
        difference = abs(predicted_idx - actual_idx)
        assert difference <= 1, f"{message}. Predicted: {predicted}, Actual: {actual}, Difference: {difference}"
    
    def _assert_gs_assessment_valid(self, predicted: models.GoodServiceLikelihoodOutput, 
                                   actual_similarity: str, comparison: Dict[str, Any]):
        """Assert that goods/services assessment is legally valid."""
        # Validate similarity score is reasonable
        assert 0.0 <= predicted.similarity_score <= 1.0, "Similarity score must be between 0 and 1"
        
        # Check logical consistency
        if predicted.are_competitive and predicted.similarity_score > 0.8:
            assert predicted.likelihood_of_confusion, "High similarity + competitive should usually = confusion"
        
        if actual_similarity == "identical":
            assert predicted.similarity_score > 0.8, f"Identical goods should have high similarity score. Got {predicted.similarity_score}"
        
        # Ensure confusion type is set appropriately
        if predicted.likelihood_of_confusion:
            assert predicted.confusion_type in ["direct", "indirect"], "Confusion type must be specified when confusion found"
        else:
            assert predicted.confusion_type is None, "Confusion type should be None when no confusion"
    
    def _assert_case_prediction_reasonable(self, predicted: str, actual: str, 
                                         actual_confusion: bool, case_name: str):
        """Assert that case prediction is reasonable given actual outcome."""
        # Map outcomes to success likelihood
        outcome_map = {
            "successful": "Opposition likely to succeed",
            "unsuccessful": "Opposition likely to fail", 
            "partially_successful": "Opposition may partially succeed"
        }
        
        expected_outcome = outcome_map.get(actual, "Opposition likely to fail")
        
        # For unsuccessful oppositions, our prediction should lean towards failure
        if actual == "unsuccessful" and not actual_confusion:
            assert predicted in ["Opposition likely to fail", "Opposition may partially succeed"], \
                f"Case {case_name}: Expected failure prediction for unsuccessful case without confusion"
        
        # For successful oppositions, our prediction should lean towards success
        if actual == "successful" and actual_confusion:
            assert predicted in ["Opposition likely to succeed", "Opposition may partially succeed"], \
                f"Case {case_name}: Expected success prediction for successful case with confusion"


class TestModernTrademarkConsiderations:
    """Test modern trademark considerations not covered in historical cases."""
    
    @pytest.mark.asyncio
    async def test_ecommerce_context_assessment(self):
        """Test that e-commerce context is considered in goods/services assessment."""
        # Online retail vs physical retail
        applicant_good = models.GoodService(term="Online retail services for clothing", nice_class=35)
        opponent_good = models.GoodService(term="Retail store services for clothing", nice_class=35)
        
        mark_similarity = models.MarkSimilarityOutput(
            visual="moderate", aural="moderate", conceptual="moderate", overall="moderate",
            reasoning="Test context"
        )
        
        gs_assessment = await generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        
        # Should recognize these as highly competitive in modern commerce
        assert gs_assessment.are_competitive, "Online and physical retail should be competitive"
        assert gs_assessment.similarity_score > 0.7, "Online/physical retail should have high similarity"
    
    @pytest.mark.asyncio
    async def test_voice_commerce_considerations(self):
        """Test consideration of voice commerce in aural similarity assessment."""
        # Marks that sound very similar (important for Alexa, Siri, etc.)
        applicant_mark = models.Mark(wordmark="ALEXA SHOP")
        opponent_mark = models.Mark(wordmark="ALEXIA SHOP")
        
        visual_score = calculate_visual_similarity(applicant_mark.wordmark, opponent_mark.wordmark)
        aural_score = calculate_aural_similarity(applicant_mark.wordmark, opponent_mark.wordmark)
        
        similarity_assessment = await generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=visual_score,
            aural_score=aural_score
        )
        
        # Should recognize high aural similarity as particularly problematic
        assert similarity_assessment.aural in ["high", "identical"], \
            "Aurally similar marks should be flagged for voice commerce"
        assert "voice" in similarity_assessment.reasoning.lower() or \
               "aural" in similarity_assessment.reasoning.lower(), \
               "Should consider voice commerce implications"
    
    @pytest.mark.asyncio
    async def test_software_services_convergence(self):
        """Test modern convergence of software and services."""
        # SaaS vs traditional software
        applicant_good = models.GoodService(term="Software as a Service (SaaS)", nice_class=42)
        opponent_good = models.GoodService(term="Computer software", nice_class=9)
        
        mark_similarity = models.MarkSimilarityOutput(
            visual="high", aural="high", conceptual="high", overall="high",
            reasoning="Test context"
        )
        
        gs_assessment = await generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        
        # Should recognize modern convergence
        assert gs_assessment.are_competitive or gs_assessment.are_complementary, \
            "SaaS and software should be related in modern commerce"
        assert gs_assessment.similarity_score > 0.6, "Should recognize software/SaaS similarity"


@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """Test the complete end-to-end workflow with realistic data."""
    # Create test data based on common opposition scenario
    applicant_mark = models.Mark(wordmark="TECHFLOW", is_registered=False)
    opponent_mark = models.Mark(wordmark="TECHSTREAM", is_registered=True, registration_number="12345")
    
    # Step 1: Mark similarity assessment
    visual_score = calculate_visual_similarity(applicant_mark.wordmark, opponent_mark.wordmark)
    aural_score = calculate_aural_similarity(applicant_mark.wordmark, opponent_mark.wordmark)
    
    mark_similarity = await generate_mark_similarity_assessment(
        applicant_mark=applicant_mark,
        opponent_mark=opponent_mark,
        visual_score=visual_score,
        aural_score=aural_score
    )
    
    # Step 2: Goods/services assessment
    applicant_goods = [
        models.GoodService(term="Cloud computing services", nice_class=42),
        models.GoodService(term="Software development", nice_class=42)
    ]
    opponent_goods = [
        models.GoodService(term="Computer software", nice_class=9),
        models.GoodService(term="Data processing services", nice_class=42)
    ]
    
    gs_assessments = []
    for app_good in applicant_goods:
        for opp_good in opponent_goods:
            gs_assessment = await generate_gs_likelihood_assessment(
                applicant_good=app_good,
                opponent_good=opp_good,
                mark_similarity=mark_similarity
            )
            gs_assessments.append(gs_assessment)
    
    # Step 3: Final case prediction
    case_prediction = await generate_case_prediction(
        mark_similarity=mark_similarity,
        goods_services_likelihoods=gs_assessments
    )
    
    # Validate complete workflow
    assert mark_similarity.overall in ["dissimilar", "low", "moderate", "high", "identical"]
    assert all(0.0 <= gs.similarity_score <= 1.0 for gs in gs_assessments)
    assert case_prediction.result in [
        "Opposition likely to succeed",
        "Opposition may partially succeed", 
        "Opposition likely to fail"
    ]
    assert 0.0 <= case_prediction.confidence <= 1.0
    assert case_prediction.confidence != 0.9, f"Confidence should not always be 0.9! Got {case_prediction.confidence}"
    
    # Validate reasoning quality
    assert len(mark_similarity.reasoning) > 50, "Mark similarity reasoning should be substantial"
    assert len(case_prediction.reasoning) > 100, "Case prediction reasoning should be comprehensive"


if __name__ == "__main__":
    # Run a quick test to see if everything works
    import asyncio
    
    async def quick_test():
        test_cases = load_test_cases()
        print(f"Loaded {len(test_cases)} real test cases")
        for case in test_cases[:3]:
            print(f"- {case.case_name}: {case.applicant_mark.wordmark} vs {len(case.opponent_marks)} opponents")
    
    asyncio.run(quick_test()) 