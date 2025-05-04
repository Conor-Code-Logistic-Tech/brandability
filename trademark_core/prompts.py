"""
Central repository for LLM prompts used in the Trademark-AI application.

This module stores formatted string constants for prompts sent to the Gemini LLM,
ensuring consistency and easy modification.
"""

MARK_SIMILARITY_PROMPT_TEMPLATE = """
You are a trademark law expert specializing in UK/EU trademark opposition proceedings.

**Input Data:**
*   **Applicant Mark:** `{applicant_wordmark}`
*   **Opponent Mark:** `{opponent_wordmark}`
*   **Pre-calculated Similarity Scores (0.0-1.0):**
    *   Visual (Levenshtein): {visual_score:.2f}
    *   Aural (Metaphone): {aural_score:.2f}

**Your Task:**

Perform a global assessment of mark similarity following UK/EU trademark law principles, resulting in a structured JSON response. Assess each dimension (visual, aural, conceptual, overall) using ONLY one of these categories: "dissimilar", "low", "moderate", "high", or "identical".

**Specific Instructions:**

1.  **Visual Similarity:**
    *   Use the provided Levenshtein score as guidance, not a deterministic rule.
    *   Consider length, structure, and distinctive/dominant elements.
    *   Assess as per UK/EU case law standards.

2.  **Aural Similarity:**
    *   Use the provided Metaphone score as guidance, not a deterministic rule.
    *   Consider pronunciation, syllable count, stress patterns, and phonetic elements.
    *   Assess as per UK/EU case law standards.

3.  **Conceptual Similarity:**
    *   Analyze any semantic meanings, translations, or conceptual associations.
    *   Consider whether the marks evoke similar or different concepts.
    *   If either mark is a made-up word without clear meaning, they are conceptually dissimilar.
    *   Assess as per UK/EU case law standards.

4.  **Overall Similarity:**
    *   Perform a global assessment considering all dimensions.
    *   Use the interdependence principle: a higher similarity in one aspect may compensate for less similarity in another.
    *   Consider the distinctive and dominant elements of each mark.
    *   Provide a brief reasoning for your overall assessment.

Generate a JSON object conforming exactly to the `MarkSimilarityOutput` schema.

**Output ONLY the valid JSON object, with no other text before or after it.**
"""
"""
Purpose: Global assessment of mark similarity across multiple dimensions based on UK/EU standards.
Input Args: applicant_wordmark (str), opponent_wordmark (str), visual_score (float), aural_score (float)
Expected Output Schema: models.MarkSimilarityOutput
"""

GS_LIKELIHOOD_PROMPT_TEMPLATE = """
You are a trademark law expert specializing in goods/services comparisons and likelihood of confusion assessments for UK/EU trademark opposition proceedings.

**Input Data:**
*   **Applicant Good/Service:** `{applicant_term}` (Class {applicant_nice_class})
*   **Opponent Good/Service:** `{opponent_term}` (Class {opponent_nice_class})
*   **Mark Similarity Context:**
    *   Visual: "{mark_visual}"
    *   Aural: "{mark_aural}"
    *   Conceptual: "{mark_conceptual}" 
    *   Overall: "{mark_overall}"

**Your Task:**

Assess the relationship between the specific goods/services and determine the likelihood of confusion considering the interdependence with the mark similarity context. Generate a structured JSON response.

**Specific Instructions:**

1.  **Goods/Services Relationship:**
    *   Assess if the goods/services are **competitive** (true/false): Could they directly compete in the marketplace?
    *   Assess if the goods/services are **complementary** (true/false): Are they used together or in conjunction?
    *   Assign a **similarity score** (0.0-1.0) based on:
        *   Nature and purpose of the goods/services
        *   Distribution channels and points of sale
        *   Relevant consumers and end users
        *   Whether they are in the same or different Nice classes

2.  **Likelihood of Confusion Assessment:**
    *   Consider the **interdependence principle**: A higher degree of similarity between marks can offset a lower degree of similarity between goods/services, and vice versa.
    *   Taking into account the provided mark similarity context, determine if there is a **likelihood of confusion** (true/false) for this specific G/S pair.
    *   If likelihood is true, determine the **type of confusion** ("direct" or "indirect"):
        *   Direct: Consumer might confuse one mark for the other
        *   Indirect: Consumer might believe there is an economic connection between marks (e.g., licensing, same corporate group)
    *   If no likelihood, set confusion_type to null.

3.  **UK/EU Consumer Perspective:**
    *   Make your assessment from the perspective of the average consumer in the UK/EU.
    *   Consider the level of attention the average consumer would pay to these goods/services.

Generate a JSON object conforming exactly to the `GoodServiceLikelihoodOutput` schema.

**Output ONLY the valid JSON object, with no other text before or after it.**
"""
"""
Purpose: Assessment of goods/services relationship and likelihood of confusion with mark similarity context.
Input Args: applicant_term (str), applicant_nice_class (int), opponent_term (str), opponent_nice_class (int),
            mark_visual (EnumStr), mark_aural (EnumStr), mark_conceptual (EnumStr), mark_overall (EnumStr)
Expected Output Schema: models.GoodServiceLikelihoodOutput
"""

CONCEPTUAL_SIMILARITY_PROMPT_TEMPLATE = """
Analyze the conceptual similarity between Mark 1: '{mark1}' and Mark 2: '{mark2}'.
Consider meaning, shared concepts, and overall commercial impression.
Provide a single decimal score between 0.0 (dissimilar) and 1.0 (identical). If either mark is devoid of clear meaning and concept, i.e. is a made-up word, return a score of 0.0.

Return a score where:
- 0.0 means completely different concepts with no relation, or one or both marks are devoid of clear meaning and concept, i.e. are made-up words
- 0.1-0.3 means low conceptual similarity (distant relation)
- 0.4-0.6 means moderate conceptual similarity (some overlapping concepts)
- 0.7-0.8 means high conceptual similarity (strongly related concepts)
- 0.9-1.0 means identical or nearly identical concepts, even if the marks are textually different. For example, "AQUA" vs "WATER" would be visually dissimilar but conceptually identical.

Generate a JSON object containing only the 'score' field, conforming to the ConceptualSimilarityScore schema.
"""
"""
Purpose: Generate a numerical score for conceptual similarity between two wordmarks.
Input Args: mark1 (str), mark2 (str)
Expected Output Schema: models.ConceptualSimilarityScore
"""
