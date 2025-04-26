"""
LLM integration for trademark similarity prediction reasoning.

This module provides integration with Google's Vertex AI Gemini 2.5 Pro model
for generating detailed legal reasoning based on trademark similarity analyses.
"""

import json
import logging
import os
from typing import Any

from google import genai
from google.api_core.exceptions import GoogleAPIError
from google.genai import types
from pydantic import ValidationError

from trademark_core import models, prompts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default model configuration
DEFAULT_MODEL = "gemini-2.5-pro-preview-03-25"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.95
DEFAULT_TOP_K = 40
DEFAULT_MAX_OUTPUT_TOKENS = 2048

# Initialize Generative AI client with Vertex AI
try:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    # Using Vertex AI with Application Default Credentials (ADC)
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required for Vertex AI")

    logger.info("Configuring Google Generative AI with Vertex AI")
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        http_options=types.HttpOptions(api_version='v1')
    )
    logger.info(f"Successfully initialized Vertex AI client in {location}")
except Exception as e:
    logger.error(f"Failed to initialize Google Generative AI client: {str(e)}")
    raise

# --- Conceptual similarity function ---
async def _get_conceptual_similarity_score_from_llm(mark1: str, mark2: str) -> float:
    """Calculate conceptual similarity score between two wordmarks using Gemini with structured output."""
    prompt = prompts.CONCEPTUAL_SIMILARITY_PROMPT_TEMPLATE.format(mark1=mark1, mark2=mark2)

    try:
        logger.debug(f"Calculating conceptual similarity score: '{mark1}' vs '{mark2}'")

        result = await generate_structured_content(
            prompt=prompt,
            schema=models.ConceptualSimilarityScore,
            temperature=0.1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=1000
        )

        # Extract and return the score directly
        score = result.score
        logger.info(f"Parsed Conceptual Similarity Score ({mark1} vs {mark2}): {score}")
        return score

    except GoogleAPIError as e:
        logger.error(f"Google API error calculating conceptual similarity score ({mark1} vs {mark2}): {str(e)}")
        # Return a neutral score on API error to avoid breaking downstream calculations
        return 0.5
    except (ValueError, ValidationError) as e:
        logger.error(f"Validation/Parsing error for conceptual similarity score ({mark1} vs {mark2}): {str(e)}")
        # Return a neutral score on validation/parsing error
        return 0.5
    except Exception as e:
        logger.error(f"Unexpected error calculating conceptual similarity score ({mark1} vs {mark2}): {str(e)}", exc_info=True)
        # Return a neutral score on unexpected error
        return 0.5

# Helper function for standardized LLM calls
async def generate_structured_content(
    prompt: str,
    schema: Any,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    top_k: int = DEFAULT_TOP_K,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
) -> Any:
    """
    Make a standardized LLM call with structured output.
    
    Args:
        prompt: The prompt to send to the LLM
        schema: The Pydantic model to use for response validation
        temperature: Controls randomness (lower = more deterministic)
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        max_output_tokens: Maximum number of tokens to generate
        
    Returns:
        The parsed response object
        
    Raises:
        GoogleAPIError: If there's an API issue
        ValueError: If response parsing fails
    """
    try:
        config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema
        )

        response = await client.aio.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=config
        )

        if not response.parsed:
            logger.error("LLM returned empty parsed data")
            raise ValueError("LLM returned empty parsed data")

        return response.parsed

    except GoogleAPIError as e:
        logger.error(f"Google API error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise

# --- Refactored main prediction function ---
async def generate_full_prediction(
    request: models.PredictionRequest,
    visual_score: float, # Add pre-calculated scores as inputs
    aural_score: float,
    conceptual_score: float
) -> models.CasePrediction:
    """
    Generate a complete trademark opposition prediction using the Gemini LLM.
    
    This function takes pre-calculated similarity scores and generates the full prediction
    including mark comparison, G&S comparisons, likelihood, and outcome via a single LLM call.

    Args:
        request: The prediction request containing applicant and opponent details.
        visual_score: Pre-calculated visual similarity score (0.0-1.0).
        aural_score: Pre-calculated aural similarity score (0.0-1.0).
        conceptual_score: Pre-calculated conceptual similarity score (0.0-1.0).

    Returns:
        CasePrediction: Complete prediction object parsed by Pydantic.

    Raises:
        GoogleAPIError: If there's an issue with the Gemini API.
        ValueError: If the LLM returns empty or invalid parsed data.
    """
    # Convert conceptual score to EnumStr category
    if conceptual_score >= 0.9:
        conceptual_category = "identical"
    elif conceptual_score >= 0.7:
        conceptual_category = "high"
    elif conceptual_score >= 0.4:
        conceptual_category = "moderate"
    elif conceptual_score >= 0.1:
        conceptual_category = "low"
    else:
        conceptual_category = "dissimilar"

    # Serialize goods/services input as JSON
    applicant_goods_list = [gs.model_dump() for gs in request.applicant_goods]
    opponent_goods_list = [gs.model_dump() for gs in request.opponent_goods]
    goods_services_input_json = json.dumps({
        "applicant_goods": applicant_goods_list,
        "opponent_goods": opponent_goods_list
    }, indent=2)

    # Build the unified prompt using the template
    # Prepare dynamic parts for the prompt template
    applicant_status = 'Registered' if request.applicant.is_registered else 'Application only'
    applicant_reg_num_line = f'*   Registration Number: `{request.applicant.registration_number}`' if request.applicant.registration_number else ''
    opponent_status = 'Registered' if request.opponent.is_registered else 'Application only'
    opponent_reg_num_line = f'*   Registration Number: `{request.opponent.registration_number}`' if request.opponent.registration_number else ''

    prompt = prompts.FULL_PREDICTION_PROMPT_TEMPLATE.format(
        applicant_wordmark=request.applicant.wordmark,
        applicant_status=applicant_status,
        applicant_reg_num_line=applicant_reg_num_line,
        opponent_wordmark=request.opponent.wordmark,
        opponent_status=opponent_status,
        opponent_reg_num_line=opponent_reg_num_line,
        visual_score=visual_score,
        aural_score=aural_score,
        conceptual_score=conceptual_score,
        conceptual_category=conceptual_category,
        goods_services_input_json=goods_services_input_json
    )

    try:
        # Call the LLM with the full schema using our helper function
        result = await generate_structured_content(
            prompt=prompt,
            schema=models.CasePrediction,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            top_k=DEFAULT_TOP_K,
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS
        )

        # Validate the result
        validated_prediction = models.CasePrediction.model_validate(result.model_dump())
        logger.info("Successfully validated CasePrediction from LLM response.")
        return validated_prediction

    except GoogleAPIError as e:
        logger.error(f"Google API error during full prediction: {str(e)}")
        raise
    except ValidationError as e:
        logger.error(f"Validation failed for LLM CasePrediction output: {e}")
        raise ValueError(f"LLM output failed validation: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in full prediction: {str(e)}")
        raise
