"""
Core similarity calculation functions for trademark comparison.

This module provides functions to calculate visual, aural, and conceptual similarity
between trademarks. Visual and aural similarities are calculated directly, while
conceptual similarity relies on LLM interaction via the `llm` module.
"""

import Levenshtein
from metaphone import doublemetaphone

from trademark_core import models

# Import the LLM function for conceptual similarity calculation
from trademark_core.llm import _get_conceptual_similarity_score_from_llm

# Remove obsolete imports
# from trademark_core.conceptual import (
#     calculate_conceptual_similarity as calculate_conceptual_similarity_impl,
# )
# from trademark_core.llm import calculate_goods_services_similarity_llm


def calculate_visual_similarity(mark1: str, mark2: str) -> float:
    """
    Calculate visual similarity between two trademarks using Levenshtein distance.
    
    Args:
        mark1: First trademark text
        mark2: Second trademark text
        
    Returns:
        float: Similarity score between 0.0 (dissimilar) and 1.0 (identical)
    """
    # Clean and normalize marks
    mark1 = mark1.lower().strip()
    mark2 = mark2.lower().strip()

    # Handle empty strings
    if not mark1 and not mark2:
        return 1.0
    if not mark1 or not mark2:
        return 0.0

    # Calculate Levenshtein ratio
    return Levenshtein.ratio(mark1, mark2)

def calculate_aural_similarity(mark1: str, mark2: str) -> float:
    """
    Calculate aural (phonetic) similarity between two trademarks using Double Metaphone.
    
    Args:
        mark1: First trademark text
        mark2: Second trademark text
        
    Returns:
        float: Similarity score between 0.0 (dissimilar) and 1.0 (identical)
    """
    # Clean and normalize marks
    mark1 = mark1.lower().strip()
    mark2 = mark2.lower().strip()

    # Handle empty strings
    if not mark1 and not mark2:
        return 1.0
    if not mark1 or not mark2:
        return 0.0

    # Get Double Metaphone codes
    code1_primary, code1_alt = doublemetaphone(mark1)
    code2_primary, code2_alt = doublemetaphone(mark2)

    # Calculate similarities using primary and alternate codes
    primary_sim = Levenshtein.ratio(code1_primary, code2_primary)

    # If alternates exist, consider them too
    alt_sims = []
    if code1_alt and code2_alt:
        alt_sims.append(Levenshtein.ratio(code1_alt, code2_alt))
    if code1_primary and code2_alt:
        alt_sims.append(Levenshtein.ratio(code1_primary, code2_alt))
    if code1_alt and code2_primary:
        alt_sims.append(Levenshtein.ratio(code1_alt, code2_primary))

    # Return highest similarity found
    return max([primary_sim] + alt_sims) if alt_sims else primary_sim

async def calculate_conceptual_similarity(mark1: str, mark2: str) -> float:
    """
    Calculate conceptual similarity between two trademarks using Gemini.
    
    This function acts as a wrapper, calling the underlying LLM interaction
    function in the `llm` module.
    
    Args:
        mark1: First trademark text
        mark2: Second trademark text
        
    Returns:
        float: Similarity score between 0.0 (dissimilar) and 1.0 (identical)
    """
    # Call the LLM function directly
    return await _get_conceptual_similarity_score_from_llm(mark1, mark2)

async def calculate_overall_similarity(mark1: models.Mark, mark2: models.Mark) -> models.MarkSimilarityOutput:
    """
    Calculate overall similarity between two trademarks across all dimensions.
    
    Args:
        mark1: First trademark
        mark2: Second trademark
        
    Returns:
        MarkSimilarityOutput: Comparison results for all dimensions
    """
    # Calculate individual similarities
    visual_sim = calculate_visual_similarity(mark1.wordmark, mark2.wordmark)
    aural_sim = calculate_aural_similarity(mark1.wordmark, mark2.wordmark)
    # Use the refactored conceptual similarity function
    conceptual_sim = await calculate_conceptual_similarity(mark1.wordmark, mark2.wordmark)

    # Map float scores to EnumStr values
    def score_to_enum(score: float) -> models.EnumStr:
        if score > 0.9:
            return "identical"
        elif score > 0.7:
            return "high"
        elif score > 0.5:
            return "moderate"
        elif score > 0.3:
            return "low"
        else:
            return "dissimilar"

    # Convert scores to enums
    visual = score_to_enum(visual_sim)
    aural = score_to_enum(aural_sim)
    conceptual = score_to_enum(conceptual_sim)

    # Calculate overall similarity with weights
    weights = {
        'visual': 0.40,
        'aural': 0.35,
        'conceptual': 0.25
    }

    overall_score = (
        weights['visual'] * visual_sim +
        weights['aural'] * aural_sim +
        weights['conceptual'] * conceptual_sim
    )

    overall = score_to_enum(overall_score)

    return models.MarkSimilarityOutput(
        visual=visual,
        aural=aural,
        conceptual=conceptual,
        overall=overall,
        reasoning=f"Calculated from visual ({visual_sim:.2f}), aural ({aural_sim:.2f}), and conceptual ({conceptual_sim:.2f}) similarities"
    )
