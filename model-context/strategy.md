# Refactoring Strategy: LLM-Driven Trademark Similarity and Opposition Prediction (UK/EU Focus)

## 1. Objective

Refactor the trademark similarity and opposition prediction functionality to further leverage Large Language Models (LLMs), specifically Google Gemini via Vertex AI, while adhering to UK/EU trademark opposition principles. The goal is to shift from relying directly on algorithmic scores (Levenshtein, Metaphone) for final outputs to using them as contextual input for more nuanced LLM assessments.

This strategy targets the needs of UK and EU trademark lawyers while ensuring the codebase becomes more elegant, maintainable, and smaller than its current state.

## 2. Current State vs. Proposed State

### Current Workflow:
1.  Client sends `PredictionRequest` (applicant/opponent marks + G/S lists) to `/predict`.
2.  API calculates visual (Levenshtein), aural (Metaphone), and conceptual (LLM) similarity scores (floats).
3.  API makes a **single** call to `generate_full_prediction` (LLM).
4.  This single LLM call receives all inputs (marks, G/S) and the three float scores.
5.  Using the `FULL_PREDICTION_PROMPT_TEMPLATE` and `CasePrediction` schema, the LLM determines:
    *   Mark comparison categories (visual, aural, conceptual, overall).
    *   *All* individual G/S comparison details (similarity, competitive, complementary) within the main call.
    *   Overall likelihood of confusion (boolean).
    *   Final opposition outcome.
6.  API returns the `CasePrediction` object.

### Proposed Workflow:
1.  Introduce **three distinct, asynchronous API routes**:
    *   `/mark_similarity` (POST): Assesses similarity between the two wordmarks.
    *   `/gs_similarity` (POST): Assesses similarity *and likelihood of confusion* for a *single pair* of goods/services, considering the mark similarity context. Must await results of /mark_similarity.
    *   `/case_prediction` (POST): Aggregates results from the above and determines the final opposition outcome.
2.  **`/mark_similarity` Route:**
    *   Input: Applicant Mark, Opponent Mark.
    *   Calculates visual (Levenshtein) and aural (Metaphone) scores (floats).
    *   Calls LLM (using `generate_structured_content`) with a dedicated prompt and new Pydantic schema (`MarkSimilarityOutput`).
    *   Prompt instructs LLM to perform a **global assessment** of mark similarity (visual, aural, conceptual, overall) based on UK/EU standards, using the calculated float scores as *input/guidance*, not deterministic rules.
    *   Output: `MarkSimilarityOutput` (containing visual, aural, conceptual, overall similarity categories, potentially including reasoning).
3.  **`/gs_similarity` Route (Called asyncronously multiple times, once per G/S pair):**
    *   Input: Applicant Good/Service, Opponent Good/Service, `MarkSimilarityOutput` (from `/mark_similarity`).
    *   Calls LLM (using `generate_structured_content`) with a dedicated prompt and new Pydantic schema (`GoodServiceLikelihoodOutput`).
    *   Prompt instructs LLM to:
        *   Assess G/S relationship (competitive, complementary, similarity score/category) based on UK/EU factors (nature, purpose, channels, users, etc.).
        *   Critically, assess the **likelihood of confusion** (true/false) for *this specific G/S pair*, considering the **interdependence** between the provided `MarkSimilarityOutput` and the G/S relationship from the perspective of the relevant UK/EU consumer.
        *   Determine the **type of confusion** (direct/indirect) if likelihood is true.
    *   Output: `GoodServiceLikelihoodOutput` (containing competitive, complementary, similarity score, likelihood\_of\_confusion, confusion\_type).
4.  **`/case_prediction` Route:**
    *   Input: `MarkSimilarityOutput`, Array of `GoodServiceLikelihoodOutput` (one for each G/S pair).
    *   **No direct LLM call needed initially.** Logic resides in the API:
        *   If `likelihood_of_confusion` is `false` for ALL G/S pairs -> `Opposition likely to fail`.
        *   If `likelihood_of_confusion` is `true` for ALL G/S pairs -> `Opposition likely to succeed`.
        *   Otherwise -> `Opposition may partially succeed`.
    *   (Optional Future Enhancement: Could add an LLM call here for final reasoning synthesis based on the aggregated inputs).
    *   Output: `CasePredictionResult` (containing the input `MarkSimilarityOutput`, the input array of `GoodServiceLikelihoodOutput`, and the final `OppositionOutcome` based on the aggregation logic).

## 3. Pydantic Model Changes (`trademark_core/models.py`)

*   **Replace `GoodServiceComparisonOutput` with new `GoodServiceLikelihoodOutput`:**
    *   Keep `are_competitive: bool`.
    *   Keep `are_complementary: bool`.
    *   Add `similarity_score: float` (0.0-1.0, assessed by LLM).
    *   Add `likelihood_of_confusion: bool` (Crucial output based on G/S + Mark context).
    *   Add `confusion_type: Literal["direct", "indirect"] | None` (Enum, only relevant if likelihood is true).
    *   Remove `overall_similarity: EnumStr`.
*   **Create `MarkSimilarityOutput`:**
    *   `visual: EnumStr`
    *   `aural: EnumStr`
    *   `conceptual: EnumStr`
    *   `overall: EnumStr`
    *   `reasoning: str | None = None` (Optional LLM reasoning for mark similarity)
*   **Replace `CasePrediction` with new `CasePredictionResult`:**
    *   Keep `mark_comparison: MarkSimilarityOutput`. (Type adjusted)
    *   Change `goods_services_comparisons: list[GoodServiceComparison]` to `goods_services_likelihoods: list[GoodServiceLikelihoodOutput]`. (Type adjusted)
    *   **Remove** `likelihood_of_confusion: bool` (Now assessed per G/S pair).
    *   Keep `opposition_outcome: OppositionOutcome`.
*   **Modify `OppositionOutcome`:**
    *   Keep `result: OppositionResultEnum`.
    *   Keep `confidence: Annotated[float, Field(ge=0.0, le=1.0)]`.
    *   Keep `reasoning: str`. (This reasoning will now be generated *by the API logic* in `/case_prediction`, or potentially a final LLM call in the future, explaining the aggregation result).
*   **Create new Input Models:**
    *   `MarkSimilarityRequest`
    *   `GsSimilarityRequest`
    *   `CasePredictionRequest`
*   **Code Cleanup:**
    *   **Completely remove** unused models and functions rather than commenting them out.
    *   Ensure unused imports are also removed.
    *   Keep model definitions concise and well-documented with clear field descriptions.

## 4. LLM Integration (`trademark_core/llm.py`, `trademark_core/prompts.py`)

*   **New Prompts:** Create specific prompt templates for:
    *   `MARK_SIMILARITY_PROMPT_TEMPLATE`: Takes applicant/opponent marks and visual/aural float scores. Asks for global assessment (visual, aural, conceptual, overall EnumStr) based on UK/EU standards, using scores as guidance. Outputs `MarkSimilarityOutput`.
    *   `GS_LIKELIHOOD_PROMPT_TEMPLATE`: Takes applicant/opponent G/S details and the full `MarkSimilarityOutput`. Asks for G/S relationship analysis (competitive, complementary, similarity score) and the crucial **likelihood of confusion** assessment (true/false, confusion type) for *that pair*, considering interdependence and UK/EU consumer perspective. Outputs `GoodServiceLikelihoodOutput`.
*   **New Functions:** Create focused functions in `llm.py` to handle calls using these new prompts and schemas:
    *   `generate_mark_similarity_assessment`
    *   `generate_gs_likelihood_assessment`
*   **Leverage Existing Infrastructure:** Continue using the existing helper function `generate_structured_content` for making API calls to Gemini.
*   **Code Cleanup:**
    *   **Completely remove** the old `generate_full_prediction` function and other unused functions.
    *   Remove any obsolete imports.
    *   Ensure prompts are concise and focused on the specific task.
    *   Use descriptive docstrings but avoid redundant comments.

## 5. API Layer (`api/main.py` or new route files)

*   **Implement the three new asynchronous endpoints:**
    *   `/mark_similarity`
    *   `/gs_similarity`
    *   `/case_prediction`
*   **Removal of the old endpoint:**
    *   **Completely remove** the existing `/predict` endpoint.
*   **Clean Implementation:**
    *   Implement endpoints with proper error handling and validation.
    *   Use descriptive docstrings for each endpoint.
    *   Ensure consistent response structure across endpoints.
    *   Keep handler functions focused and concise.

## 6. Code Quality & Maintainability Focus

*   **Complete Removal of Obsolete Code:**
    *   **Do NOT comment out old code** – remove it entirely to prevent bloat.
    *   Remove all related test files and fixtures that are no longer relevant.
    *   Clean up imports throughout the codebase.
*   **Size Reduction:**
    *   The refactoring should result in a smaller codebase by:
        *   Eliminating the monolithic prompt and prediction function.
        *   Creating more focused, smaller functions with single responsibilities.
        *   Removing redundant code paths and logic.
*   **Maintainability Improvements:**
    *   Each component has a clear, single responsibility.
    *   Separation of concerns between mark similarity, goods/services assessment, and final prediction.
    *   More granular, easier-to-test functions.
    *   Explicit dependencies between components.
*   **Documentation:**
    *   Update docstrings and type hints throughout.
    *   Ensure tests clearly document the expected behavior.

## 7. Considerations & Future Enhancements

*   **Asynchronous Flow:** The client application will need to orchestrate the calls: `/mark_similarity` first, then `/gs_similarity` for each G/S pair concurrently, and finally `/case_prediction`.
*   **Distinctiveness:** Explicitly handling the distinctiveness of the opponent's mark could be added later.
*   **Error Handling:** Implement robust error handling for LLM API calls and schema validation.
*   **Testing:** Update existing tests and add new ones for the new routes and components.
*   **Performance:**
    *   Monitor performance, especially latency of multiple LLM calls.
    *   Consider caching strategies for common mark comparisons.
    *   Optimize prompt sizes to reduce token counts and response times.
*   **UK vs. EU Nuances:** Start with a unified approach, but be prepared to adjust for specific jurisdictional differences if needed.

This refactoring separates concerns, creates a more focused and maintainable codebase, and enables more precise LLM prompting aligned with UK/EU legal factors. By completely removing obsolete code rather than commenting it out, we ensure the codebase remains clean and smaller than its current state.

## 8. Implementation Task List

> **Document Maintenance:** As tasks are completed, update this document by checking the corresponding checkboxes below. For each major milestone completed, commit the updated strategy document with a clear message indicating what has been accomplished. This will serve as a living document to track refactoring progress.

### Planning & Preparation
- [x] Review existing codebase to identify all affected components
- [x] Create git branch for refactoring work
- [x] Set up test environment to verify functionality during refactoring

### Pydantic Model Changes
- [x] Create new `MarkSimilarityOutput` model
- [x] Create new `GoodServiceLikelihoodOutput` model
- [x] Create new `CasePredictionResult` model
- [x] Create new request models (`MarkSimilarityRequest`, `GsSimilarityRequest`, `CasePredictionRequest`)
- [x] Update `OppositionOutcome` model if needed
- [x] Add comprehensive docstrings to all new models
- [x] Update any imports in files using these models

### LLM Integration
- [x] Create `MARK_SIMILARITY_PROMPT_TEMPLATE`
- [x] Create `GS_LIKELIHOOD_PROMPT_TEMPLATE`
- [x] Implement `generate_mark_similarity_assessment` function
- [x] Implement `generate_gs_likelihood_assessment` function
- [x] Ensure all new functions have comprehensive error handling
- [x] Add detailed docstrings to all new functions

### API Layer Implementation
- [x] Implement `/mark_similarity` endpoint
- [x] Implement `/gs_similarity` endpoint
- [x] Implement `/case_prediction` endpoint
- [x] Add proper validation and error handling to all endpoints
- [x] Add comprehensive docstrings to all endpoints

### Testing
- [x] Create unit tests for new Pydantic models
- [x] Create unit tests for new LLM functions
- [x] Create integration tests for new endpoints
- [x] Create end-to-end test for the complete workflow
- [x] Verify test coverage meets targets

### Code Cleanup & Removal
- [x] Remove `generate_full_prediction` function
- [x] Remove the `/predict` endpoint
- [x] Remove obsolete Pydantic models or fields
- [x] Remove unused imports across the codebase
- [x] Remove obsolete test files or test cases
- [x] Run linters and formatters on the refactored code

### Documentation
- [x] Update README.md with new API flow if applicable
- [x] Add comments explaining complex logic in implementation
- [x] Document any non-obvious design decisions

### Final Verification
- [x] Verify all tests pass
- [x] Verify the codebase size has been reduced
- [x] Conduct code review of this refactoring project by running `git diff main` - the main branch contains our production version. 
- [x] Verify API behaves as expected in test environment
- [x] Check performance compared to previous implementation
- [x] Test locally using uvicorn and curl

### Deployment Preparation
- [x] Create deployment plan
- [x] Document breaking changes for client communication
- [x] Consider backward compatibility requirements if needed