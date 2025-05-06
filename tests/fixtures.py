"""
Test fixtures and common data for trademark-ai tests.

This module provides standardized test data to be used across multiple test modules
to ensure consistency and reusability.
"""

from trademark_core import models

# ---- Mark fixtures ----

# Identical made-up marks - should return 0.0 for conceptual similarity per trademark law
IDENTICAL_MARKS = (
    models.Mark(wordmark="XQZPVY"),  # Completely random letters with no meaning
    models.Mark(wordmark="XQZPVY"),  # Identical to the first mark
)

# Similar made-up marks - should also return 0.0 for conceptual similarity
SIMILAR_MARKS = (
    models.Mark(wordmark="XQZPVY"),  # Random letters with no meaning
    models.Mark(wordmark="XQZPVN"),  # Similar random letters with one letter changed
)

# Dissimilar marks with real meaning - should have low conceptual similarity
DISSIMILAR_MARKS = (
    models.Mark(wordmark="ZOOPLANKTON"),  # Real word with biological meaning
    models.Mark(wordmark="BUTTERFLY"),  # Real word with different biological meaning
)

# Identical real word marks - should have high conceptual similarity
IDENTICAL_REAL_MARKS = (
    models.Mark(wordmark="MOUNTAIN VIEW"),  # Real words with clear meaning
    models.Mark(wordmark="MOUNTAIN VIEW"),  # Identical to the first mark
)

# Similar concept marks - should have moderate to high conceptual similarity
SIMILAR_CONCEPT_MARKS = (
    models.Mark(wordmark="MOUNTAIN VIEW"),  # Real words with clear meaning
    models.Mark(wordmark="HILL VISTA"),  # Different words with similar meaning
)

# ---- Goods/Services fixtures ----

IDENTICAL_SOFTWARE = (
    models.GoodService(term="Legal software", nice_class=9),
    models.GoodService(term="Legal software", nice_class=9),
)

RELATED_SOFTWARE = (
    models.GoodService(term="Legal software", nice_class=9),
    models.GoodService(term="Business software", nice_class=9),
)

UNRELATED_GOODS = (
    models.GoodService(term="Live plants", nice_class=31),
    models.GoodService(term="Vehicles", nice_class=12),
)

# ---- Mark Similarity Assessment fixtures ----

IDENTICAL_ASSESSMENT = models.MarkSimilarityOutput(
    visual="identical",
    aural="identical",
    conceptual="identical",
    overall="identical",
    reasoning="The marks are identical in all aspects.",
)

HIGH_SIMILARITY_ASSESSMENT = models.MarkSimilarityOutput(
    visual="high",
    aural="high",
    conceptual="high",
    overall="high",
    reasoning="The marks are highly similar in all aspects.",
)

MODERATE_SIMILARITY_ASSESSMENT = models.MarkSimilarityOutput(
    visual="moderate",
    aural="moderate",
    conceptual="moderate",
    overall="moderate",
    reasoning="The marks share some similarities but have distinguishing features.",
)

LOW_SIMILARITY_ASSESSMENT = models.MarkSimilarityOutput(
    visual="low",
    aural="low",
    conceptual="low",
    overall="low",
    reasoning="The marks have only minimal similarities.",
)

DISSIMILAR_ASSESSMENT = models.MarkSimilarityOutput(
    visual="dissimilar",
    aural="dissimilar",
    conceptual="low",
    overall="dissimilar",
    reasoning="The marks are very different in appearance and sound.",
)

# ---- Model parameter fixtures ----

TEST_MODELS = {
    "default": None,  # Use the system default
    "flash": "gemini-2.5-flash-preview-04-17",
    "pro": "gemini-2.5-flash-preview-04-17",
}


# Function to generate a descriptive test ID based on model name
def get_model_test_id(model_name):
    if model_name is None:
        return "default_model"
    return f"model_{model_name.replace('-', '_').replace('.', '_')}"
