"""
LLM integration for trademark similarity prediction reasoning.

This module provides integration with Google's Vertex AI Gemini 2.5 Pro model
for generating detailed legal reasoning based on trademark similarity analyses.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from google import genai
from google.api_core.exceptions import GoogleAPIError
from google.genai import types
from pydantic import ValidationError
from google.cloud import storage

from trademark_core import models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default model configuration
DEFAULT_MODEL = "gemini-2.5-pro"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_TEMPERATURE_INCREMENT = 0.1
DEFAULT_TOP_P = 0.95
DEFAULT_TOP_K = 40
DEFAULT_MAX_OUTPUT_TOKENS = 16000

# Environment variable to control exception raising in tests
# When set to "1", LLM and batch processing functions will raise exceptions

# immediately for easier debugging in test environments.
# Otherwise, they will log errors and attempt to continue or return partial results.
TEST_RAISE_EXCEPTIONS_ENV_VAR = "TEST_RAISE_EXCEPTIONS"

# Initialize Generative AI client with Vertex AI
try:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    # Using Vertex AI with Application Default Credentials (ADC)
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required for Vertex AI")

    logger.info("Configuring Google Generative AI with Vertex AI")
    # Initialize the client once at the module level
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        http_options=types.HttpOptions(api_version="v1"), # Retained HttpOptions as per original
    )
    logger.info(f"Successfully configured Vertex AI SDK in {location} for project {project_id}")

    # Initialize GCS client
    gcs_client = storage.Client(project=project_id)
    BRANDABILITY_BUCKET_NAME = "brandability-bucket"

except Exception as e:
    logger.error(f"Failed to initialize Google Generative AI client or GCS client: {str(e)}")
    raise


def _should_raise_exceptions_for_tests() -> bool:
    """
    Determines if exceptions should be raised for testing purposes.
    Checks the TEST_RAISE_EXCEPTIONS environment variable.
    """
    env_value = os.environ.get(TEST_RAISE_EXCEPTIONS_ENV_VAR)
    should_raise = env_value == "1"
    logger.info(
        f"Checking {TEST_RAISE_EXCEPTIONS_ENV_VAR}: got '{env_value}', so should_raise is {should_raise}"
    )
    return should_raise


# --- Prompt Loading Functions ---
def _load_content_from_gcs(gcs_path: str) -> str:
    """
    Load content from a GCS bucket.

    Args:
        gcs_path: The path to the object within the bucket (e.g., "prompts/file.md")

    Returns:
        The content as a string

    Raises:
        google.cloud.exceptions.NotFound: If the blob doesn't exist.
        Exception: For other GCS errors.
    """
    try:
        bucket = gcs_client.bucket(BRANDABILITY_BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        content = blob.download_as_text(encoding="utf-8")
        logger.debug(f"Loaded content from gs://{BRANDABILITY_BUCKET_NAME}/{gcs_path}")
        return content
    except storage.exceptions.NotFound:
        logger.error(f"GCS object not found: gs://{BRANDABILITY_BUCKET_NAME}/{gcs_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading content from gs://{BRANDABILITY_BUCKET_NAME}/{gcs_path}: {str(e)}")
        raise


def _combine_prompt_with_examples(prompt_template: str, examples_content: str) -> str:
    """
    Combine a prompt template with few-shot examples.
    
    Args:
        prompt_template: The main prompt template
        examples_content: The few-shot examples content
        
    Returns:
        Combined prompt with examples appended
    """
    # Extract just the examples section from the markdown file
    # Look for content between <few_shot_examples> tags
    import re
    examples_match = re.search(r'<few_shot_examples>.*?</few_shot_examples>', 
                              examples_content, re.DOTALL)
    if examples_match:
        examples_section = examples_match.group(0)
        # Append examples to the prompt
        combined = f"{prompt_template}\n\n{examples_section}"
        return combined
    else:
        logger.warning("No <few_shot_examples> section found in examples file")
        return prompt_template


# Load prompt templates and examples at module initialization
try:
    # Load prompts from GCS
    MARK_SIMILARITY_PROMPT_TEMPLATE = _load_content_from_gcs("prompts/mark_similarity_prompt.md")
    GS_LIKELIHOOD_PROMPT_TEMPLATE = _load_content_from_gcs("prompts/gs_likelihood_prompt.md")
    CONCEPTUAL_SIMILARITY_PROMPT_TEMPLATE = _load_content_from_gcs("prompts/conceptual_similarity_prompt.md")
    CASE_PREDICTION_PROMPT_TEMPLATE = _load_content_from_gcs("prompts/case_prediction_prompt.md")

    # Load examples from GCS
    MARK_SIMILARITY_EXAMPLES = _load_content_from_gcs("examples/mark_similarity_examples.md")
    GS_LIKELIHOOD_EXAMPLES = _load_content_from_gcs("examples/gs_likelihood_examples.md")
    CONCEPTUAL_SIMILARITY_EXAMPLES = _load_content_from_gcs("examples/conceptual_similarity_examples.md")
    CASE_PREDICTION_EXAMPLES = _load_content_from_gcs("examples/case_prediction_examples.md")

    logger.info("Successfully loaded all prompts and examples from GCS")
except Exception as e:
    logger.error(f"Failed to load prompts or examples from GCS: {str(e)}")
    raise


# --- Mark Similarity Assessment Function ---
async def generate_mark_similarity_assessment(
    applicant_mark: models.Mark,
    opponent_mark: models.Mark,
    visual_score: float,
    aural_score: float,
    model: str = None,
) -> models.MarkSimilarityOutput:
    """
    Generate a comprehensive mark similarity assessment using the Gemini LLM.

    This function takes two marks, along with pre-calculated visual and aural
    similarity scores, and uses the LLM to generate a holistic assessment of
    similarity across all dimensions (visual, aural, conceptual, and overall).

    Args:
        applicant_mark: The applicant's mark details
        opponent_mark: The opponent's mark details
        visual_score: Pre-calculated visual similarity score (0.0-1.0)
        aural_score: Pre-calculated aural similarity score (0.0-1.0)
        model: Optional model override to use for the assessment

    Returns:
        MarkSimilarityOutput: Structured assessment of mark similarity

    Raises:
        GoogleAPIError: If there's an issue with the Gemini API
        ValueError: If the LLM returns empty or invalid parsed data
    """
    # Generate a unique ID for this request to track it through logs
    request_id = str(uuid.uuid4())[:8]
    log_prefix = f"[Mark Assessment {request_id}]"

    try:
        logger.info(
            f"{log_prefix} Starting mark similarity assessment: '{applicant_mark.wordmark}' vs '{opponent_mark.wordmark}'"
        )
        if model:
            logger.info(f"{log_prefix} Using custom model: {model}")

        # Combine prompt template with examples
        prompt_with_examples = _combine_prompt_with_examples(
            MARK_SIMILARITY_PROMPT_TEMPLATE, 
            MARK_SIMILARITY_EXAMPLES
        )
        
        # Build the prompt using manual replacement to avoid JSON brace conflicts
        prompt = prompt_with_examples.replace("{applicant_wordmark}", applicant_mark.wordmark)
        prompt = prompt.replace("{opponent_wordmark}", opponent_mark.wordmark)
        prompt = prompt.replace("{visual_score}", f"{visual_score:.2f}")
        prompt = prompt.replace("{aural_score}", f"{aural_score:.2f}")

        # Call the LLM with the structured output schema
        result = await generate_structured_content(
            prompt=prompt,
            schema=models.MarkSimilarityOutput,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            top_k=DEFAULT_TOP_K,
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            request_context=log_prefix,
            model=model,
        )

        # Validate the result and ensure reasoning is not None if provided
        result_dict = result.model_dump()
        
        # Ensure reasoning field has a fallback if None (even though it's optional in this model)
        if result_dict.get('reasoning') is None:
            result_dict['reasoning'] = "Reasoning could not be generated for this mark similarity assessment."
            logger.warning(f"{log_prefix} LLM returned None for reasoning field, using fallback")
        
        validated_assessment = models.MarkSimilarityOutput.model_validate(result_dict)
        logger.info(
            f"{log_prefix} Successfully generated with overall similarity: {validated_assessment.overall}"
        )

        return validated_assessment

    except GoogleAPIError as e:
        logger.error(f"{log_prefix} Google API error: {str(e)}")
        raise
    except ValidationError as e:
        logger.error(f"{log_prefix} Validation failed: {e}")
        raise ValueError(f"LLM output failed validation: {e}")
    except Exception as e:
        logger.error(f"{log_prefix} Unexpected error: {str(e)}")
        raise


# --- Goods/Services Likelihood Assessment Function ---
async def generate_gs_likelihood_assessment(
    applicant_good: models.GoodService,
    opponent_good: models.GoodService,
    mark_similarity: models.MarkSimilarityOutput,
    model: str = None,
) -> models.GoodServiceLikelihoodOutput:
    """
    Generate a goods/services likelihood of confusion assessment using the Gemini LLM.

    This function assesses the relationship between a specific pair of goods/services
    and determines the likelihood of confusion considering the interdependence with
    the provided mark similarity context.

    Args:
        applicant_good: The applicant's good/service details
        opponent_good: The opponent's good/service details
        mark_similarity: The mark similarity context from previous assessment
        model: Optional model override to use for the assessment

    Returns:
        GoodServiceLikelihoodOutput: Structured assessment of G/S relationship and likelihood

    Raises:
        GoogleAPIError: If there's an issue with the Gemini API
        ValueError: If the LLM returns empty or invalid parsed data
    """
    # Generate a unique ID for this request to track it through logs
    request_id = str(uuid.uuid4())[:8]
    log_prefix = f"[G/S Assessment {request_id}]"

    try:
        logger.info(
            f"{log_prefix} Starting G/S likelihood assessment: '{applicant_good.term}' vs '{opponent_good.term}'"
        )
        if model:
            logger.info(f"{log_prefix} Using custom model: {model}")

        # Combine prompt template with examples
        prompt_with_examples = _combine_prompt_with_examples(
            GS_LIKELIHOOD_PROMPT_TEMPLATE,
            GS_LIKELIHOOD_EXAMPLES
        )
        
        # Build the prompt using manual replacement to avoid JSON brace conflicts
        prompt = prompt_with_examples.replace("{applicant_term}", applicant_good.term)
        prompt = prompt.replace("{applicant_nice_class}", str(applicant_good.nice_class))
        prompt = prompt.replace("{opponent_term}", opponent_good.term)
        prompt = prompt.replace("{opponent_nice_class}", str(opponent_good.nice_class))
        prompt = prompt.replace("{mark_visual}", mark_similarity.visual)
        prompt = prompt.replace("{mark_aural}", mark_similarity.aural)
        prompt = prompt.replace("{mark_conceptual}", mark_similarity.conceptual)
        prompt = prompt.replace("{mark_overall}", mark_similarity.overall)

        # Call the LLM with the structured output schema
        result = await generate_structured_content(
            prompt=prompt,
            schema=models.GoodServiceLikelihoodOutput,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            top_k=DEFAULT_TOP_K,
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            request_context=log_prefix,
            model=model,
        )

        # Validate the result
        validated_assessment = models.GoodServiceLikelihoodOutput.model_validate(
            result.model_dump()
        )
        logger.info(
            f"{log_prefix} Successfully generated with confusion: {validated_assessment.likelihood_of_confusion}"
        )

        return validated_assessment

    except GoogleAPIError as e:
        logger.error(f"{log_prefix} Google API error: {str(e)}")
        raise
    except ValidationError as e:
        logger.error(f"{log_prefix} Validation failed: {e}")
        raise ValueError(f"LLM output failed validation: {e}")
    except Exception as e:
        logger.error(f"{log_prefix} Unexpected error: {str(e)}")
        raise


# --- Conceptual similarity function ---
async def _get_conceptual_similarity_score_from_llm(mark1: str, mark2: str) -> float:
    """
    Calculate conceptual similarity score between two wordmarks using Gemini with structured output.
    In test mode (TEST_RAISE_EXCEPTIONS=1), exceptions are propagated for strict error handling tests.
    """
    # Combine prompt template with examples
    prompt_with_examples = _combine_prompt_with_examples(
        CONCEPTUAL_SIMILARITY_PROMPT_TEMPLATE,
        CONCEPTUAL_SIMILARITY_EXAMPLES
    )
    
    # Replace placeholders manually to avoid JSON brace conflicts
    prompt = prompt_with_examples.replace("{mark1}", mark1).replace("{mark2}", mark2)

    try:
        logger.debug(f"Calculating conceptual similarity score: '{mark1}' vs '{mark2}'")

        result = await generate_structured_content(
            prompt=prompt,
            schema=models.ConceptualSimilarityScore,
            temperature=0.1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=4000,
        )

        # Extract and return the score directly
        score = result.score
        logger.info(f"Parsed Conceptual Similarity Score ({mark1} vs {mark2}): {score}")
        return score

    except Exception as e:
        logger.error(
            f"Error calculating conceptual similarity score ({mark1} vs {mark2}): {str(e)}",
            exc_info=True,
        )
        if _should_raise_exceptions_for_tests():
            raise
        # Return a neutral score on error in production
        return 0.5


# Helper function for standardized LLM calls
async def generate_structured_content(
    prompt: str,
    schema: Any,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    top_k: int = DEFAULT_TOP_K,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    request_context: str = "",
    model: str = None,
) -> Any:
    """
    Make a standardized LLM call with structured output and reasoning capabilities.

    Args:
        prompt: The prompt to send to the LLM
        schema: The Pydantic model to use for response validation
        temperature: Controls randomness (lower = more deterministic)
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        max_output_tokens: Maximum number of tokens to generate
        request_context: Optional context identifier for logging
        model: Optional model override to use for the call

    Returns:
        The parsed response object

    Raises:
        GoogleAPIError: If there's an API issue
        ValueError: If response parsing fails
    """
    # If no request context provided, generate a unique ID
    if not request_context:
        request_context = f"[LLM Request {str(uuid.uuid4())[:8]}]"

    try:
        # For Pydantic models, directly use the class instead of converting to schema dictionary
        # The Gemini Python SDK will properly translate Pydantic models to the appropriate schema
        config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema,  # Pass the Pydantic class directly as recommended in the docs
        )

        # Log the schema being used for debugging
        schema_name = schema.__name__ if hasattr(schema, "__name__") else str(schema)
        logger.info(
            f"{request_context} REQUEST: Using schema: {schema_name} (temp={temperature}, top_p={top_p}, top_k={top_k})"
        )

        # Log prompt (truncated if too long)
        prompt_excerpt = prompt[:500] + "..." if len(prompt) > 500 else prompt
        logger.info(f"{request_context} PROMPT: {prompt_excerpt}")

        # Make up to 3 attempts to get a valid response
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                # Use the client to generate content with the correct syntax
                response = client.models.generate_content(
                    model=model or DEFAULT_MODEL,
                    contents=prompt, 
                    config=config
                )

                # Log the raw response for debugging - use INFO level to ensure it appears in logs
                if hasattr(response, "text"):
                    raw_response = response.text
                    # Truncate very long responses in logs
                    log_response = (
                        raw_response[:5000] + "..." if len(raw_response) > 5000 else raw_response
                    )
                    logger.info(
                        f"{request_context} RAW RESPONSE (attempt {attempt}): {log_response}"
                    )
                else:
                    logger.info(
                        f"{request_context} RAW RESPONSE (attempt {attempt}) - No text attribute: {response}"
                    )

                # Check if we have a valid response
                if response.parsed:
                    # Additional safety check: ensure reasoning fields are not None if the schema expects them
                    parsed_result = response.parsed
                    if hasattr(parsed_result, 'model_dump'):
                        result_dict = parsed_result.model_dump()
                        
                        # Check if this model has a reasoning field that should not be None
                        if 'reasoning' in result_dict:
                            # For OppositionOutcome, reasoning is required (not optional)
                            if schema.__name__ == 'OppositionOutcome' and not result_dict.get('reasoning'):
                                logger.warning(f"{request_context} OppositionOutcome reasoning was None/empty, applying fallback")
                                result_dict['reasoning'] = "Reasoning could not be generated."
                                # Recreate the parsed result with the fixed reasoning
                                parsed_result = schema.model_validate(result_dict)
                    
                    parsed_str = json.dumps(
                        parsed_result.model_dump()
                        if hasattr(parsed_result, "model_dump")
                        else parsed_result,
                        indent=2,
                    )
                    # Truncate very long responses in logs
                    parsed_log = parsed_str[:5000] + "..." if len(parsed_str) > 5000 else parsed_str
                    logger.info(f"{request_context} PARSED RESPONSE: {parsed_log}")
                    return parsed_result

                # If we reach here, no valid data was returned
                logger.warning(
                    f"{request_context} Empty parsed data (attempt {attempt}/{max_attempts})"
                )

                # For subsequent attempts, increase temperature slightly to encourage variation
                if attempt < max_attempts:
                    # Increase temperature by 0.1 for each retry (up to a max of 0.6)
                    config.temperature = min(
                        0.6, temperature + (DEFAULT_TEMPERATURE_INCREMENT * attempt)
                    )
                    logger.info(f"{request_context} Retrying with temperature={config.temperature}")
                else:
                    # Last attempt failed, raise error
                    logger.error(f"{request_context} All attempts failed")
                    raise ValueError("LLM returned empty parsed data after multiple attempts")

            except GoogleAPIError as api_error:
                error_str = str(api_error)
                logger.error(f"{request_context} API ERROR (attempt {attempt}): {error_str}")
                # Only retry on specific types of API errors that might be transient
                if "rate limit" in error_str.lower() or "timeout" in error_str.lower():
                    if attempt < max_attempts:
                        logger.warning(f"{request_context} Transient API error, will retry")
                        continue
                # For other API errors or last attempt, re-raise
                raise

        # If we exit the loop without returning or raising, raise a value error
        raise ValueError("LLM returned empty parsed data")

    except GoogleAPIError as e:
        logger.error(f"{request_context} Google API error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"{request_context} Unexpected error: {str(e)}", exc_info=True)
        raise


# New function for batch processing goods/services
async def batch_process_goods_services(
    applicant_goods: list[models.GoodService],
    opponent_goods: list[models.GoodService],
    mark_similarity: models.MarkSimilarityOutput,
    model: str = None,
) -> list[models.GoodServiceLikelihoodOutput]:
    """
    Process multiple goods/services comparisons with rate limiting.
    In test mode (TEST_RAISE_EXCEPTIONS=1), exceptions in batch items are propagated for strict error handling tests.

    This function processes combinations of goods/services in smaller batches
    to avoid overwhelming the LLM API with too many concurrent requests.

    Args:
        applicant_goods: List of applicant's goods/services
        opponent_goods: List of opponent's goods/services
        mark_similarity: Mark similarity assessment to use for all comparisons
        model: Optional model override to use for all assessments

    Returns:
        List of GoodServiceLikelihoodOutput objects for each pair
    """
    import asyncio

    # Generate a unique batch ID for this entire batch process
    batch_id = str(uuid.uuid4())[:8]
    log_prefix = f"[Batch Process {batch_id}]"

    # Log the start of batch processing with details
    logger.info(
        f"{log_prefix} Starting batch processing: {len(applicant_goods)} applicant goods × {len(opponent_goods)} opponent goods = {len(applicant_goods) * len(opponent_goods)} total combinations"
    )
    if model:
        logger.info(f"{log_prefix} Using custom model: {model}")

    # Create a list of all combinations to process
    combinations = []
    for applicant_good in applicant_goods:
        for opponent_good in opponent_goods:
            combinations.append((applicant_good, opponent_good))

    # Process batches of combinations with rate limiting
    batch_size = 3  # Process only a small number of combinations at once
    delay_seconds = 1  # Add delay between batches

    processed_results = []
    successful_count = 0
    error_count = 0

    for i in range(0, len(combinations), batch_size):
        batch = combinations[i : i + batch_size]
        current_batch_num = i // batch_size + 1
        total_batches = (len(combinations) + batch_size - 1) // batch_size
        batch_log_prefix = f"{log_prefix} Batch {current_batch_num}/{total_batches}"

        # Log batch start with combination details
        logger.info(f"{batch_log_prefix} Processing combinations:")
        for idx, (app_good, opp_good) in enumerate(batch):
            logger.info(
                f"{batch_log_prefix} Item {idx + 1}: '{app_good.term}' vs '{opp_good.term}'"
            )

        # Create tasks for this batch
        tasks = []
        for applicant_good, opponent_good in batch:
            task = generate_gs_likelihood_assessment(
                applicant_good=applicant_good,
                opponent_good=opponent_good,
                mark_similarity=mark_similarity,
                model=model,
            )
            tasks.append(task)

        # Process this batch
        logger.info(f"{batch_log_prefix} Starting processing")
        start_time = asyncio.get_event_loop().time()
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        batch_duration = end_time - start_time

        # Handle any exceptions
        batch_success = 0
        batch_errors = 0
        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                error_count += 1
                batch_errors += 1
                error_type = type(result).__name__
                error_msg = str(result)
                logger.error(f"{batch_log_prefix} Item {j + 1} ERROR ({error_type}): {error_msg}")
                if _should_raise_exceptions_for_tests():
                    raise result
            else:
                successful_count += 1
                batch_success += 1
                processed_results.append(result)

        # Log batch completion stats
        logger.info(
            f"{batch_log_prefix} Completed in {batch_duration:.2f}s: {batch_success} successful, {batch_errors} failed"
        )

        # Add delay between batches to avoid rate limits
        if i + batch_size < len(combinations):
            logger.info(f"{batch_log_prefix} Waiting {delay_seconds}s before next batch")
            await asyncio.sleep(delay_seconds)

    # Log overall batch processing stats
    total_processed = successful_count + error_count
    success_rate = (successful_count / total_processed * 100) if total_processed > 0 else 0
    logger.info(
        f"{log_prefix} Batch processing complete: {successful_count}/{total_processed} successful ({success_rate:.1f}%)"
    )

    return processed_results


# New function for comprehensive case prediction
async def generate_case_prediction(
    mark_similarity: models.MarkSimilarityOutput,
    goods_services_likelihoods: list[models.GoodServiceLikelihoodOutput],
    model: str = None,
) -> models.OppositionOutcome:
    """
    Generate a comprehensive case prediction using all assessment data.
    
    This function uses an LLM to analyse the complete case data and provide
    a nuanced prediction with appropriate confidence levels based on legal
    principles and precedent.
    
    Args:
        mark_similarity: The mark similarity assessment
        goods_services_likelihoods: List of all G/S likelihood assessments
        model: Optional model override to use for the assessment
        
    Returns:
        OppositionOutcome: Structured prediction with result, confidence, and reasoning
        
    Raises:
        GoogleAPIError: If there's an issue with the Gemini API
        ValueError: If the LLM returns invalid data
    """
    # Generate a unique ID for this request
    request_id = str(uuid.uuid4())[:8]
    log_prefix = f"[Case Prediction {request_id}]"
    
    try:
        logger.info(f"{log_prefix} Starting comprehensive case prediction")
        if model:
            logger.info(f"{log_prefix} Using custom model: {model}")
        
        # Calculate statistics
        total_pairs = len(goods_services_likelihoods)
        confused_pairs = sum(1 for gs in goods_services_likelihoods if gs.likelihood_of_confusion)
        confused_percentage = (confused_pairs / total_pairs * 100) if total_pairs > 0 else 0
        
        direct_confusion_count = sum(
            1 for gs in goods_services_likelihoods 
            if gs.likelihood_of_confusion and gs.confusion_type == "direct"
        )
        indirect_confusion_count = sum(
            1 for gs in goods_services_likelihoods 
            if gs.likelihood_of_confusion and gs.confusion_type == "indirect"
        )
        
        avg_similarity = (
            sum(gs.similarity_score for gs in goods_services_likelihoods) / total_pairs
            if total_pairs > 0 else 0
        )
        
        # Format goods/services summary
        gs_summary_lines = []
        for i, gs in enumerate(goods_services_likelihoods, 1):
            confusion_str = "No confusion"
            if gs.likelihood_of_confusion:
                confusion_str = f"{gs.confusion_type.capitalize()} confusion likely"
            
            gs_summary_lines.append(
                f"    {i}. G/S Similarity: {gs.similarity_score:.2f} | "
                f"Competitive: {gs.are_competitive} | Complementary: {gs.are_complementary} | "
                f"{confusion_str}"
            )
        
        goods_services_summary = "\n".join(gs_summary_lines)
        
        # Combine prompt template with examples
        prompt_with_examples = _combine_prompt_with_examples(
            CASE_PREDICTION_PROMPT_TEMPLATE,
            CASE_PREDICTION_EXAMPLES
        )
        
        # Build the prompt using manual replacement to avoid JSON brace conflicts
        prompt = prompt_with_examples.replace("{mark_visual}", mark_similarity.visual)
        prompt = prompt.replace("{mark_aural}", mark_similarity.aural)
        prompt = prompt.replace("{mark_conceptual}", mark_similarity.conceptual)
        prompt = prompt.replace("{mark_overall}", mark_similarity.overall)
        prompt = prompt.replace("{mark_reasoning}", mark_similarity.reasoning or "No specific reasoning provided")
        prompt = prompt.replace("{goods_services_summary}", goods_services_summary)
        prompt = prompt.replace("{total_pairs}", str(total_pairs))
        prompt = prompt.replace("{confused_pairs}", str(confused_pairs))
        prompt = prompt.replace("{confused_percentage}", f"{confused_percentage:.1f}")
        prompt = prompt.replace("{direct_confusion_count}", str(direct_confusion_count))
        prompt = prompt.replace("{indirect_confusion_count}", str(indirect_confusion_count))
        prompt = prompt.replace("{avg_similarity}", f"{avg_similarity:.2f}")
        
        # Call the LLM
        result = await generate_structured_content(
            prompt=prompt,
            schema=models.OppositionOutcome,
            temperature=0.3,  # Lower temperature for more consistent legal reasoning
            top_p=DEFAULT_TOP_P,
            top_k=DEFAULT_TOP_K,
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            request_context=log_prefix,
            model=model,
        )
        
        # Validate the result and ensure reasoning is never None
        result_dict = result.model_dump()
        
        # Critical: OppositionOutcome.reasoning is required, never allow None
        if not result_dict.get('reasoning'):
            result_dict['reasoning'] = "Reasoning could not be generated for this case prediction."
            logger.warning(f"{log_prefix} LLM returned None/empty for reasoning field, using fallback")
        
        validated_outcome = models.OppositionOutcome.model_validate(result_dict)
        logger.info(
            f"{log_prefix} Generated prediction: {validated_outcome.result} "
            f"(confidence: {validated_outcome.confidence:.2f})"
        )
        
        return validated_outcome
        
    except GoogleAPIError as e:
        logger.error(f"{log_prefix} Google API error: {str(e)}")
        raise
    except ValidationError as e:
        logger.error(f"{log_prefix} Validation failed: {e}")
        raise ValueError(f"LLM output failed validation: {e}")
    except Exception as e:
        logger.error(f"{log_prefix} Unexpected error: {str(e)}")
        raise
