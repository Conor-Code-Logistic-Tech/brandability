"""
Central repository for LLM prompts used in the Trademark-AI application.

This module stores formatted string constants for prompts sent to the Gemini LLM,
ensuring consistency and easy modification.
"""

CONCEPTUAL_SIMILARITY_PROMPT_TEMPLATE = """
Analyze the conceptual similarity between Mark 1: '{mark1}' and Mark 2: '{mark2}'.
Consider meaning, shared concepts, and overall commercial impression.
Provide a single decimal score between 0.0 (dissimilar) and 1.0 (identical).

Return a score where:
- 0.0 means completely different concepts with no relation
- 0.1-0.3 means low conceptual similarity (distant relation)
- 0.4-0.6 means moderate conceptual similarity (some overlapping concepts)
- 0.7-0.8 means high conceptual similarity (strongly related concepts)
- 0.9-1.0 means identical or nearly identical concepts

Generate a JSON object containing only the 'score' field, conforming to the ConceptualSimilarityScore schema.
"""
"""
Purpose: Generate a numerical score for conceptual similarity between two wordmarks.
Input Args: mark1 (str), mark2 (str)
Expected Output Schema: models.ConceptualSimilarityScore
"""


GOODS_SERVICES_COMPARISON_PROMPT_TEMPLATE = """
You are a trademark law expert specializing in goods and services comparisons.
Analyze the relationship between the following two items:

Applicant Good/Service: {applicant_term} (Class {applicant_nice_class})
Opponent Good/Service: {opponent_term} (Class {opponent_nice_class})

Your task is to determine:
1.  **Overall Similarity:** Assess the similarity based on nature, purpose, use, trade channels, and consumers. Use ONLY one category: "dissimilar", "low", "moderate", "high", or "identical".
2.  **Competitiveness:** Are these goods/services directly competitive in the marketplace? (true/false)
3.  **Complementarity:** Are these goods/services complementary (used together or related in consumption)? (true/false)

Consider the Nice class, but focus primarily on the commercial reality and potential for consumer confusion between the terms themselves.

Generate a JSON object conforming to the provided schema, containing 'overall_similarity', 'are_competitive', and 'are_complementary'.
The JSON response should ONLY contain these three fields, correctly populated based on your analysis. Do NOT include the input applicant_good or opponent_good fields in the response JSON.
"""
"""
Purpose: Compare a single pair of applicant and opponent goods/services.
Input Args: applicant_term (str), applicant_nice_class (int), opponent_term (str), opponent_nice_class (int)
Expected Output Schema: models.GoodServiceComparisonOutput
"""


FULL_PREDICTION_PROMPT_TEMPLATE = """
You are TrademarkGPT, a specialized legal AI assistant for trademark lawyers.

**Input Data:**

*   **Applicant Mark:**
    *   Wordmark: `{applicant_wordmark}`
    *   Registration Status: {applicant_status}
    {applicant_reg_num_line}
*   **Opponent Mark:**
    *   Wordmark: `{opponent_wordmark}`
    *   Registration Status: {opponent_status}
    {opponent_reg_num_line}
*   **Pre-calculated Mark Similarity Scores (0.0-1.0):**
    *   Visual: {visual_score:.2f}
    *   Aural: {aural_score:.2f}
    *   Conceptual: {conceptual_score:.2f} (translates to '{conceptual_category}' category)
*   **Goods/Services Input:**
    ```json
    {goods_services_input_json}
    ```

**Your Task:**

Generate a complete JSON object conforming exactly to the `CasePrediction` schema. Use the input data above to populate the fields.

**Specific Instructions:**

1.  **`mark_comparison`:**
    *   Assess `visual`, `aural`, and `overall` similarity categories ('dissimilar', 'low', 'moderate', 'high', 'identical') based *primarily* on the provided scores, but use legal judgment for the overall assessment.
    *   Use the pre-calculated conceptual score to determine the `conceptual` category: '{conceptual_category}'.
2.  **`goods_services_comparisons`:**
    *   Create an array of comparison objects. Generate one object for each potential pairing between an applicant good/service and an opponent good/service from the input JSON.
    *   For **each** object in the array:
        *   **Critically, populate `applicant_good` and `opponent_good` by copying the corresponding `term` and `nice_class` directly from the input JSON.**
        *   Assess `overall_similarity` ('dissimilar', 'low', 'moderate', 'high', 'identical').
        *   Determine `are_competitive` (true/false).
        *   Determine `are_complementary` (true/false).
3.  **`likelihood_of_confusion`:** Assess the overall likelihood (true/false) considering both marks and the goods/services comparisons.
4.  **`opposition_outcome`:** Provide a structured outcome (`result`, `confidence` 0.0-1.0, detailed `reasoning`).

**Output ONLY the valid JSON object conforming to the `CasePrediction` schema, with no other text before or after it.**
"""
"""
Purpose: Generate a full trademark opposition case prediction based on input marks, goods/services, and pre-calculated similarity scores.
Input Args: applicant_wordmark, applicant_status, applicant_reg_num_line,
            opponent_wordmark, opponent_status, opponent_reg_num_line,
            visual_score, aural_score, conceptual_score, conceptual_category,
            goods_services_input_json
Expected Output Schema: models.CasePrediction
"""
