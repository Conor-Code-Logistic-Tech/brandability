"""
Mock implementations for external services used in tests.

This module provides mock versions of external service functions to avoid
making actual API calls during testing.
"""

from unittest.mock import AsyncMock, patch
import sys
import os
from typing import Any, Dict, Type, Optional

from trademark_core import models

class MockLLM:
    """
    Mock implementation of LLM services for testing.
    This class provides predefined responses for LLM calls to avoid
    actual API calls during testing.
    """
    
    @staticmethod
    async def mock_mark_similarity_assessment(
        applicant_mark: models.Mark,
        opponent_mark: models.Mark,
        visual_score: float,
        aural_score: float
    ) -> models.MarkSimilarityOutput:
        """Mock implementation of generate_mark_similarity_assessment."""
        print(f"Mock LLM called for marks: '{applicant_mark.wordmark}' vs '{opponent_mark.wordmark}'")
        # If identical marks, return "identical" for all categories
        if applicant_mark.wordmark.lower() == opponent_mark.wordmark.lower():
            return models.MarkSimilarityOutput(
                visual="identical",
                aural="identical",
                conceptual="identical",
                overall="identical",
                reasoning="The marks are identical in all aspects."
            )
        
        # If very different marks
        if "ZOOPLANKTON" in applicant_mark.wordmark and "BUTTERFLY" in opponent_mark.wordmark or \
           "BUTTERFLY" in applicant_mark.wordmark and "ZOOPLANKTON" in opponent_mark.wordmark:
            return models.MarkSimilarityOutput(
                visual="dissimilar",
                aural="dissimilar",
                conceptual="low",
                overall="dissimilar",
                reasoning="The marks are very different in appearance and sound."
            )
        
        # Default: moderate similarity for most cases
        return models.MarkSimilarityOutput(
            visual="moderate",
            aural="moderate",
            conceptual="moderate",
            overall="moderate",
            reasoning="The marks share some similarities but have distinguishing features."
        )
    
    @staticmethod
    async def mock_gs_likelihood_assessment(
        applicant_good: models.GoodService,
        opponent_good: models.GoodService,
        mark_similarity: models.MarkSimilarityOutput
    ) -> models.GoodServiceLikelihoodOutput:
        """Mock implementation of generate_gs_likelihood_assessment."""
        print(f"Mock G/S assessment called: '{applicant_good.term}' vs '{opponent_good.term}'")
        
        # Identical legal software case for full workflow test
        if "Identical legal software" in applicant_good.term and "Identical legal software" in opponent_good.term:
            return models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.95,
                likelihood_of_confusion=True,
                confusion_type="direct"
            )
        
        # Identical goods case
        if applicant_good.term.lower() == opponent_good.term.lower() and applicant_good.nice_class == opponent_good.nice_class:
            # Identical goods with high/identical mark similarity -> confusion
            if mark_similarity.overall in ["high", "identical"]:
                return models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.95,
                    likelihood_of_confusion=True,
                    confusion_type="direct"
                )
        
        # Dissimilar goods case - specifically for Live plants vs Vehicles
        if ("Live plants" in applicant_good.term and "Vehicles" in opponent_good.term) or \
           ("Vehicles" in applicant_good.term and "Live plants" in opponent_good.term):
            return models.GoodServiceLikelihoodOutput(
                are_competitive=False,
                are_complementary=False,
                similarity_score=0.1,
                likelihood_of_confusion=False,
                confusion_type=None
            )
        
        # Same nice class but different terms -> competitive
        if applicant_good.nice_class == opponent_good.nice_class:
            return models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=mark_similarity.overall in ["moderate", "high", "identical"],
                confusion_type="indirect" if mark_similarity.overall == "moderate" else "direct"
            )
        
        # Default: different nice classes -> non-competitive, no confusion
        return models.GoodServiceLikelihoodOutput(
            are_competitive=False,
            are_complementary=True,
            similarity_score=0.3,
            likelihood_of_confusion=False,
            confusion_type=None
        )
    
    @staticmethod
    async def mock_structured_content(
        prompt: str,
        schema: Type[Any],
        **kwargs
    ) -> Any:
        """Mock implementation of generate_structured_content."""
        # Extract marks from the prompt for MarkSimilarityOutput
        if schema == models.MarkSimilarityOutput:
            # Special handling based on prompt content
            if "IDENTICAL" in prompt and "IDENTICAL" in prompt:
                # Identical marks case specifically for the full workflow test
                return models.MarkSimilarityOutput(
                    visual="identical",
                    aural="identical",
                    conceptual="identical",
                    overall="identical",
                    reasoning="The marks are identical in all aspects."
                )
            elif "EXAMPLIA" in prompt and "EXAMPLIA" in prompt:
                # Identical marks case
                return models.MarkSimilarityOutput(
                    visual="identical",
                    aural="identical",
                    conceptual="identical",
                    overall="identical",
                    reasoning="The marks are identical in all aspects."
                )
            elif "ZOOPLANKTON" in prompt and "BUTTERFLY" in prompt:
                # Dissimilar marks case
                return models.MarkSimilarityOutput(
                    visual="dissimilar",
                    aural="dissimilar",
                    conceptual="low",
                    overall="dissimilar",
                    reasoning="The marks are very different in appearance and sound."
                )
            else:
                # Default case - moderate similarity
                return models.MarkSimilarityOutput(
                    visual="moderate",
                    aural="moderate", 
                    conceptual="moderate",
                    overall="moderate",
                    reasoning="This is a mock response for testing."
                )
        elif schema == models.GoodServiceLikelihoodOutput:
            # Special handling based on prompt content
            if "Identical legal software" in prompt:
                # Identical legal software case for full workflow test
                return models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.95,
                    likelihood_of_confusion=True,
                    confusion_type="direct"
                )
            elif "Legal software" in prompt and "Legal software" in prompt:
                # Identical goods case
                return models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.95,
                    likelihood_of_confusion=True,
                    confusion_type="direct"
                )
            elif "Cloud computing" in prompt and "Cloud computing" in prompt:
                # Identical goods case for full workflow test
                return models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.95,
                    likelihood_of_confusion=True,
                    confusion_type="direct"
                )
            elif "Live plants" in prompt and "Vehicles" in prompt:
                # Dissimilar goods case
                return models.GoodServiceLikelihoodOutput(
                    are_competitive=False,
                    are_complementary=False,
                    similarity_score=0.1,
                    likelihood_of_confusion=False,
                    confusion_type=None
                )
            else:
                # Default case
                return models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.7,
                    likelihood_of_confusion=True,
                    confusion_type="direct"
                )
        elif schema == models.ConceptualSimilarityScore:
            return models.ConceptualSimilarityScore(score=0.5)
        else:
            # If we don't know how to handle this schema, create an empty instance
            return schema()


def apply_llm_mocks():
    """
    Patch all LLM-related functions for testing.
    
    This function applies patches to all the LLM functions that would normally
    call external APIs to instead use mock implementations.
    """
    # Path to the llm module to be patched
    llm_module_path = "trademark_core.llm"
    
    # Apply patches
    patch(f"{llm_module_path}.generate_mark_similarity_assessment", 
          new=MockLLM.mock_mark_similarity_assessment).start()
    
    patch(f"{llm_module_path}.generate_gs_likelihood_assessment", 
          new=MockLLM.mock_gs_likelihood_assessment).start()
    
    patch(f"{llm_module_path}.generate_structured_content", 
          new=MockLLM.mock_structured_content).start()
    
    patch(f"{llm_module_path}._get_conceptual_similarity_score_from_llm", 
          new=AsyncMock(return_value=0.5)).start()
    
    print("Applied LLM mocks for testing") 