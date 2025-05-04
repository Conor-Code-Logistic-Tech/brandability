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

# --- Mark Similarity Assessment Function ---
async def generate_mark_similarity_assessment(
    applicant_mark: models.Mark, 
    opponent_mark: models.Mark,
    visual_score: float,
    aural_score: float
) -> models.MarkSimilarityOutput:
    """
    Generate a comprehensive mark similarity assessment using the Gemini LLM.
    
    This function takes pre-calculated visual and aural similarity scores and uses
    the LLM to perform a global assessment of similarity between two wordmarks,
    following UK/EU trademark law principles.
    
    Args:
        applicant_mark: The applicant's mark details
        opponent_mark: The opponent's mark details
        visual_score: Pre-calculated visual similarity score (0.0-1.0)
        aural_score: Pre-calculated aural similarity score (0.0-1.0)
        
    Returns:
        MarkSimilarityOutput: Structured similarity assessment across all dimensions
        
    Raises:
        GoogleAPIError: If there's an issue with the Gemini API
        ValueError: If the LLM returns empty or invalid parsed data
    """
    try:
        logger.info(f"Generating mark similarity assessment: '{applicant_mark.wordmark}' vs '{opponent_mark.wordmark}'")
        
        # Build the prompt using the template
        prompt = prompts.MARK_SIMILARITY_PROMPT_TEMPLATE.format(
            applicant_wordmark=applicant_mark.wordmark,
            opponent_wordmark=opponent_mark.wordmark,
            visual_score=visual_score,
            aural_score=aural_score
        )
        
        # Call the LLM with the structured output schema
        result = await generate_structured_content(
            prompt=prompt,
            schema=models.MarkSimilarityOutput,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            top_k=DEFAULT_TOP_K,
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS
        )
        
        # Validate the result
        validated_assessment = models.MarkSimilarityOutput.model_validate(result.model_dump())
        logger.info(f"Successfully generated mark similarity assessment with overall similarity: {validated_assessment.overall}")
        
        return validated_assessment
        
    except GoogleAPIError as e:
        logger.error(f"Google API error during mark similarity assessment: {str(e)}")
        raise
    except ValidationError as e:
        logger.error(f"Validation failed for LLM MarkSimilarityOutput: {e}")
        raise ValueError(f"LLM output failed validation: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in mark similarity assessment: {str(e)}")
        raise

# --- Goods/Services Likelihood Assessment Function ---
async def generate_gs_likelihood_assessment(
    applicant_good: models.GoodService,
    opponent_good: models.GoodService,
    mark_similarity: models.MarkSimilarityOutput
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
        
    Returns:
        GoodServiceLikelihoodOutput: Structured assessment of G/S relationship and likelihood
        
    Raises:
        GoogleAPIError: If there's an issue with the Gemini API
        ValueError: If the LLM returns empty or invalid parsed data
    """
    try:
        logger.info(f"Generating G/S likelihood assessment: '{applicant_good.term}' vs '{opponent_good.term}'")
        
        # Build the prompt using the template
        prompt = prompts.GS_LIKELIHOOD_PROMPT_TEMPLATE.format(
            applicant_term=applicant_good.term,
            applicant_nice_class=applicant_good.nice_class,
            opponent_term=opponent_good.term,
            opponent_nice_class=opponent_good.nice_class,
            mark_visual=mark_similarity.visual,
            mark_aural=mark_similarity.aural,
            mark_conceptual=mark_similarity.conceptual,
            mark_overall=mark_similarity.overall
        )
        
        # Call the LLM with the structured output schema
        result = await generate_structured_content(
            prompt=prompt,
            schema=models.GoodServiceLikelihoodOutput,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            top_k=DEFAULT_TOP_K,
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS
        )
        
        # Validate the result
        validated_assessment = models.GoodServiceLikelihoodOutput.model_validate(result.model_dump())
        logger.info(f"Successfully generated G/S likelihood assessment with confusion: {validated_assessment.likelihood_of_confusion}")
        
        return validated_assessment
        
    except GoogleAPIError as e:
        logger.error(f"Google API error during G/S likelihood assessment: {str(e)}")
        raise
    except ValidationError as e:
        logger.error(f"Validation failed for LLM GoodServiceLikelihoodOutput: {e}")
        raise ValueError(f"LLM output failed validation: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in G/S likelihood assessment: {str(e)}")
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
            max_output_tokens=4000
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
