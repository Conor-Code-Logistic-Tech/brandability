"""
LLM integration for trademark similarity prediction reasoning.

This module provides integration with Google's Vertex AI Gemini 2.5 Pro model
for generating detailed legal reasoning based on trademark similarity analyses.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio # Added for concurrent G&S calls
import uuid

# Updated imports for Google Generative AI SDK
from google import genai
from google.api_core.exceptions import GoogleAPIError
from google.genai import types
# Add pydantic import for validation error
from pydantic import ValidationError

from trademark_core import models, prompts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import or define similarity calculation functions
def calculate_visual_similarity(mark1: str, mark2: str) -> float:
    """Calculate visual similarity between two wordmarks using Levenshtein distance."""
    from Levenshtein import ratio
    return ratio(mark1.lower(), mark2.lower())

def calculate_aural_similarity(mark1: str, mark2: str) -> float:
    """Calculate aural (phonetic) similarity between two wordmarks using Double Metaphone."""
    from metaphone import doublemetaphone
    import Levenshtein
    
    # Clean input
    mark1 = mark1.strip().lower()
    mark2 = mark2.strip().lower()
    
    # Handle empty cases
    if not mark1 and not mark2:
        return 1.0  # Both empty
    if not mark1 or not mark2:
        return 0.0  # One empty
    
    # Generate phonetic codes
    code1 = doublemetaphone(mark1)[0]
    code2 = doublemetaphone(mark2)[0]
    
    # Calculate similarity based on codes
    return Levenshtein.ratio(code1, code2)

async def calculate_conceptual_similarity(mark1: str, mark2: str) -> float:
    """Calculate conceptual similarity between two wordmarks using Gemini, parsing JSON from text."""
    prompt = f"""
    Analyze the conceptual similarity between Mark 1: '{mark1}' and Mark 2: '{mark2}'.
    Consider meaning, shared concepts, and overall commercial impression.
    Provide a single decimal score between 0.0 (dissimilar) and 1.0 (identical).

    Please provide the result as a JSON object in the following format (you can include brief explanatory text around it if needed):
    ```json
    {{
      "score": <similarity_score_float>
    }}
    ```
    Replace `<similarity_score_float>` with your calculated score.
    Example JSON block: {{"score": 0.8}}
    """
    
    # Configuration WITHOUT strict JSON output enforcement
    config = types.GenerateContentConfig(
        temperature=0.1,  # Low temperature for consistent scoring
        top_p=0.95,
        top_k=40, # Adjusted Top K
        max_output_tokens=1000
        # Removed response_mime_type and response_schema
    )

    raw_text = None # Initialize raw_text
    response = None # Initialize response
    try:
        logger.debug(f"Calculating conceptual similarity: '{mark1}' vs '{mark2}'")
        logger.info(f"Conceptual Similarity Request - Model: {DEFAULT_MODEL}")
        logger.info(f"Conceptual Similarity Request - Config (Text Output): {config}")
        logger.debug(f"Conceptual Similarity Request - Prompt: {prompt}")
        
        response = await client.aio.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=config
        )
        
        logger.info(f"Conceptual Similarity Response Object: {response}")
        if response.prompt_feedback:
            logger.info(f"Conceptual Similarity Response Prompt Feedback: {response.prompt_feedback}")
        if response.candidates:
             logger.info(f"Conceptual Similarity Response Candidates: {response.candidates}")

        # Attempt to get raw text
        raw_text = getattr(response, 'text', None)
        if not raw_text and response.candidates:
            try:
                 if response.candidates[0].content and response.candidates[0].content.parts:
                      raw_text = response.candidates[0].content.parts[0].text
            except (IndexError, AttributeError) as e: # Removed StopCandidateException
                 logger.warning(f"Could not extract raw text from candidate parts: {e}")
                 raw_text = None

        logger.info(f"Raw LLM Conceptual Score text ({mark1} vs {mark2}): {raw_text}")
        
        if raw_text is None:
            logger.error(f"LLM response text is None for conceptual similarity ({mark1} vs {mark2}). Falling back.")
            return 0.5

        # --- Manually Parse JSON from Text --- 
        try:
            # Find the JSON block within the text (simple search for now)
            json_start = raw_text.find('{')
            json_end = raw_text.rfind('}')
            if json_start != -1 and json_end != -1 and json_start < json_end:
                json_str = raw_text[json_start : json_end + 1]
                logger.info(f"Extracted JSON string: {json_str}")
                data = json.loads(json_str)
                score = data.get('score')
                if isinstance(score, (int, float)) and 0.0 <= score <= 1.0:
                    logger.info(f"Parsed Conceptual Similarity Score ({mark1} vs {mark2}): {score}")
                    return float(score)
                else:
                    logger.error(f"Invalid 'score' value in parsed JSON ({mark1} vs {mark2}): {score}. Falling back.")
                    return 0.5
            else:
                logger.error(f"Could not find valid JSON block in LLM response text ({mark1} vs {mark2}). Text: {raw_text}. Falling back.")
                return 0.5
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from LLM response text ({mark1} vs {mark2}): {e}. Text: {raw_text}. Falling back.")
            return 0.5
        except KeyError:
            logger.error(f"'score' key not found in parsed JSON ({mark1} vs {mark2}). Text: {raw_text}. Falling back.")
            return 0.5
        # --- End JSON Parsing --- 
        
    # Removed specific StopCandidateException handler
    except GoogleAPIError as e:
        logger.error(f"Google API error calculating conceptual similarity ({mark1} vs {mark2}): {str(e)}")
        logger.error(f"Response object on API error: {response}")
        logger.error(f"Raw LLM text on error: {raw_text}")
        return 0.5
    except Exception as e:
        logger.error(f"Unexpected error calculating conceptual similarity ({mark1} vs {mark2}): {str(e)}", exc_info=True)
        logger.error(f"Response object on unexpected error: {response}")
        logger.error(f"Raw LLM text on error: {raw_text}")
        return 0.5

# Initialize Generative AI client
use_vertexai = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

try:
    if use_vertexai:
        # Using Vertex AI with Application Default Credentials (ADC)
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required for Vertex AI")
            
        logger.info("Configuring Google Generative AI with Vertex AI")
        client = genai.Client(
            vertexai=True,  # Required for Vertex AI
            project=project_id,
            location=location,
            http_options=types.HttpOptions(api_version='v1')  # Use stable API version
        )
        logger.info(f"Successfully initialized Vertex AI client in {location}")
    else:
        # Using direct API access with API Key
        logger.info("Configuring Google Generative AI with API Key")
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found, falling back to Vertex AI")
            if not project_id:
                raise ValueError("Neither GOOGLE_API_KEY nor GOOGLE_CLOUD_PROJECT found. Cannot initialize client.")
                
            # Fallback to Vertex AI
            client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
                http_options=types.HttpOptions(api_version='v1')
            )
            logger.info(f"Successfully initialized Vertex AI client in {location} (fallback)")
        else:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(api_version='v1')
            )
            logger.info("Successfully initialized API Key client")
        
except Exception as e:
    logger.error(f"Failed to initialize Google Generative AI client: {str(e)}")
    raise

# Model configuration
DEFAULT_MODEL = "gemini-2.5-pro-preview-03-25"  # Model name is the same for both Vertex AI and direct API
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TEMPERATURE_INCREMENT = 0.1
DEFAULT_TOP_P = 0.95
DEFAULT_TOP_K = 40
DEFAULT_MAX_OUTPUT_TOKENS = 2048

# List of supported models
SUPPORTED_MODELS = ["gemini-2.5-pro-preview-03-25", "gemini-2.5-flash-preview-04-17"]

# Function declarations for the LLM
visual_similarity_func = types.FunctionDeclaration(
    name="calculate_visual_similarity",
    description="Calculate visual similarity between two wordmarks using Levenshtein distance",
    parameters={
        "type": "OBJECT",
        "properties": {
            "mark1": {"type": "STRING", "description": "First trademark text"},
            "mark2": {"type": "STRING", "description": "Second trademark text"}
        },
        "required": ["mark1", "mark2"]
    }
)

aural_similarity_func = types.FunctionDeclaration(
    name="calculate_aural_similarity", 
    description="Calculate aural (phonetic) similarity between two wordmarks using Double Metaphone",
    parameters={
        "type": "OBJECT",
        "properties": {
            "mark1": {"type": "STRING", "description": "First trademark text"},
            "mark2": {"type": "STRING", "description": "Second trademark text"}
        },
        "required": ["mark1", "mark2"]
    }
)

conceptual_similarity_func = types.FunctionDeclaration(
    name="calculate_conceptual_similarity",
    description="Calculate conceptual similarity between two wordmarks using semantic embeddings",
    parameters={
        "type": "OBJECT",
        "properties": {
            "mark1": {"type": "STRING", "description": "First trademark text"},
            "mark2": {"type": "STRING", "description": "Second trademark text"}
        },
        "required": ["mark1", "mark2"]
    }
)

# Function implementations for the LLM
async def _calculate_visual_similarity_impl(args: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation of calculate_visual_similarity for LLM function calling."""
    mark1 = args.get("mark1", "")
    mark2 = args.get("mark2", "")
    
    similarity = calculate_visual_similarity(mark1, mark2)
    return {"similarity": similarity}

async def _calculate_aural_similarity_impl(args: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation of calculate_aural_similarity for LLM function calling."""
    mark1 = args.get("mark1", "")
    mark2 = args.get("mark2", "")
    
    similarity = calculate_aural_similarity(mark1, mark2)
    return {"similarity": similarity}

async def _calculate_conceptual_similarity_impl(args: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation of calculate_conceptual_similarity for LLM function calling."""
    mark1 = args.get("mark1", "")
    mark2 = args.get("mark2", "")
    
    similarity = await calculate_conceptual_similarity(mark1, mark2)
    return {"similarity": similarity}

# Function dispatcher
FUNCTION_MAP = {
    "calculate_visual_similarity": _calculate_visual_similarity_impl,
    "calculate_aural_similarity": _calculate_aural_similarity_impl,
    "calculate_conceptual_similarity": _calculate_conceptual_similarity_impl
}

async def handle_function_call(model_response) -> List[Dict[str, Any]]:
    """Process function calls from the model and return the results."""
    function_responses = []
    
    # Check if there are any function calls in the response
    for candidate in model_response.candidates:
        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                function_call = part.function_call
                function_name = function_call.name
                function_args = function_call.args
                
                logger.info(f"Function call: {function_name} with args: {function_args}")
                
                # Call the appropriate function
                if function_name in FUNCTION_MAP:
                    try:
                        function_impl = FUNCTION_MAP[function_name]
                        result = await function_impl(function_args)
                        
                        function_responses.append({
                            "name": function_name,
                            "response": result
                        })
                    except Exception as e:
                        logger.error(f"Error executing function {function_name}: {str(e)}")
                        function_responses.append({
                            "name": function_name,
                            "error": str(e)
                        })
                else:
                    logger.warning(f"Unknown function: {function_name}")
                    function_responses.append({
                        "name": function_name,
                        "error": "Function not implemented"
                    })
    
    return function_responses

# --- New function for single G&S pair comparison --- 
async def calculate_single_goods_services_similarity(
    applicant_good: models.GoodService, 
    opponent_good: models.GoodService
) -> models.GoodServiceComparison:
    """
    Compares a single pair of applicant and opponent goods/services using the LLM.
    
    Args:
        applicant_good: The applicant's good/service item.
        opponent_good: The opponent's good/service item.
        
    Returns:
        GoodServiceComparison: Detailed comparison results including similarity, 
                               competitiveness, and complementarity.
                               
    Raises:
        GoogleAPIError: If there's an issue with the Gemini API.
        ValueError: If the LLM response cannot be parsed or validated.
    """
    prompt = f"""You are a trademark law expert specializing in goods and services comparisons.
    Analyze the relationship between the following two items:

    Applicant Good/Service: {applicant_good.term} (Class {applicant_good.nice_class})
    Opponent Good/Service: {opponent_good.term} (Class {opponent_good.nice_class})

    Your task is to determine:
    1.  **Overall Similarity:** Assess the similarity based on nature, purpose, use, trade channels, and consumers. Use ONLY one category: "dissimilar", "low", "moderate", "high", or "identical".
    2.  **Competitiveness:** Are these goods/services directly competitive in the marketplace? (true/false)
    3.  **Complementarity:** Are these goods/services complementary (used together or related in consumption)? (true/false)

    Consider the Nice class, but focus primarily on the commercial reality and potential for consumer confusion between the terms themselves.

    Generate a JSON object conforming to the provided schema, containing 'overall_similarity', 'are_competitive', and 'are_complementary'.
    The JSON response should ONLY contain these three fields, correctly populated based on your analysis. Do NOT include the input applicant_good or opponent_good fields in the response JSON.
    """

    response_text = None
    parsed_response = None
    try:
        logger.debug(f"Comparing G&S: '{applicant_good.term}' vs '{opponent_good.term}'")
        
        # Use the GoodServiceComparisonOutput schema for LLM output
        expected_llm_output_schema = models.GoodServiceComparisonOutput
        
        response = await client.aio.models.generate_content(
            model=DEFAULT_MODEL, 
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1, # Low temperature for consistent categorization
                top_p=0.95,
                top_k=20,
                max_output_tokens=500, # Reduced token count for focused response
                response_mime_type="application/json",
                response_schema=expected_llm_output_schema 
            )
        )
        
        # Log raw text output for debugging parsing issues
        raw_text = response.text
        if not raw_text and response.candidates and response.candidates[0].content.parts:
            raw_text = response.candidates[0].content.parts[0].text
        logger.info(f"Raw LLM G&S text ({applicant_good.term} vs {opponent_good.term}): {raw_text}")
        
        if not response.parsed:
             raise ValueError("LLM returned empty parsed data for G&S comparison")

        # --- DEBUGGING: Log parsed response ---
        logger.info(f"Parsed LLM G&S Response ({applicant_good.term} vs {opponent_good.term}): {response.parsed}")
        # --- END DEBUGGING ---

        comparison_data = response.parsed # GoodServiceComparisonOutput instance
        
        # Construct the full GoodServiceComparison object, adding the input goods
        full_comparison = models.GoodServiceComparison(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            overall_similarity=comparison_data.overall_similarity,
            are_competitive=comparison_data.are_competitive,
            are_complementary=comparison_data.are_complementary
        )
        # Validate the constructed object
        return models.GoodServiceComparison.model_validate(full_comparison.model_dump())

    except GoogleAPIError as e:
        logger.error(f"Google API error during G&S comparison ({applicant_good.term} vs {opponent_good.term}): {str(e)}")
        raise
    except (ValidationError, json.JSONDecodeError) as e:
        logger.error(f"Failed to validate/parse LLM G&S response ({applicant_good.term} vs {opponent_good.term}): {str(e)}")
        if response_text:
             logger.error(f"Raw LLM G&S response: {response_text}")
        raise ValueError(f"Invalid G&S response format from LLM: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in G&S comparison ({applicant_good.term} vs {opponent_good.term}): {str(e)}")
        if response_text:
             logger.error(f"Raw LLM G&S response: {response_text}")
        raise

# --- Refactored main prediction function --- 
async def generate_full_prediction(request: models.PredictionRequest) -> models.CasePrediction:
    """
    Generate a complete trademark opposition prediction using the Gemini LLM.

    This function embeds both trademark details and the raw goods/services arrays into a single LLM prompt,
    then calls Gemini once with a structured schema to produce the full CasePrediction JSON.

    Args:
        request: The prediction request containing applicant and opponent details.

    Returns:
        CasePrediction: Complete prediction object parsed by Pydantic.

    Raises:
        GoogleAPIError: If there's an issue with the Gemini API.
        ValueError: If the LLM returns empty or invalid parsed data.
    """
    # Programmatically compute mark similarities
    visual_score = calculate_visual_similarity(request.applicant.wordmark, request.opponent.wordmark)
    aural_score = calculate_aural_similarity(request.applicant.wordmark, request.opponent.wordmark)
    conceptual_score = await calculate_conceptual_similarity(request.applicant.wordmark, request.opponent.wordmark)

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

    # Build the unified prompt
    prompt = f"""
    You are TrademarkGPT, a specialized legal AI assistant for trademark lawyers.

    **Input Data:**

    *   **Applicant Mark:**
        *   Wordmark: `{request.applicant.wordmark}`
        *   Registration Status: {('Registered' if request.applicant.is_registered else 'Application only')}
        {f'*   Registration Number: `{request.applicant.registration_number}`' if request.applicant.registration_number else ''}
    *   **Opponent Mark:**
        *   Wordmark: `{request.opponent.wordmark}`
        *   Registration Status: {('Registered' if request.opponent.is_registered else 'Application only')}
        {f'*   Registration Number: `{request.opponent.registration_number}`' if request.opponent.registration_number else ''}
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

    raw_text = None # Initialize raw_text
    try:
        # Call the LLM with the full schema
        response = await client.aio.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=DEFAULT_TEMPERATURE,
                top_p=DEFAULT_TOP_P,
                top_k=DEFAULT_TOP_K,
                max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                response_mime_type="application/json",
                response_schema=models.CasePrediction
            )
        )
        
        # --- Log raw response text ---
        raw_text = getattr(response, 'text', None)
        if not raw_text and response.candidates and response.candidates[0].content.parts:
            raw_text = response.candidates[0].content.parts[0].text
        logger.info(f"Raw LLM Full Prediction text: {raw_text}")
        # --- End logging ---
        
        if not response.parsed:
            logger.error(f"LLM returned empty parsed data for full prediction. Raw text: {raw_text}")
            raise ValueError("LLM returned empty parsed data for full prediction")
        
        # Return the parsed CasePrediction directly
        # Add validation step
        try:
             validated_prediction = models.CasePrediction.model_validate(response.parsed.model_dump())
             logger.info("Successfully validated CasePrediction from LLM response.")
             return validated_prediction
        except ValidationError as e:
             logger.error(f"Validation failed for LLM CasePrediction output: {e}")
             logger.error(f"Invalid LLM raw output: {raw_text}")
             raise ValueError(f"LLM output failed validation: {e}")

    except GoogleAPIError as e:
         logger.error(f"Google API error during full prediction: {str(e)}")
         raise
    except Exception as e:
        logger.error(f"Unexpected error in full prediction: {str(e)}")
        logger.error(f"Raw LLM text on error: {raw_text}") # Log raw text on error
        raise 

# --- Mark Similarity Assessment Function ---
async def generate_mark_similarity_assessment(
    applicant_mark: models.Mark, 
    opponent_mark: models.Mark,
    visual_score: float,
    aural_score: float,
    model: str | None = None
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
        model: Optional model name to override DEFAULT_MODEL
        
    Returns:
        MarkSimilarityOutput: Structured similarity assessment across all dimensions
        
    Raises:
        GoogleAPIError: If there's an issue with the Gemini API
        ValueError: If the LLM returns empty or invalid parsed data
    """
    # Generate a unique ID for this request to track it through logs
    request_id = str(uuid.uuid4())[:8]
    log_prefix = f"[Mark Similarity {request_id}]"
    
    try:
        logger.info(f"{log_prefix} Starting mark similarity assessment: '{applicant_mark.wordmark}' vs '{opponent_mark.wordmark}'")
        
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
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            request_context=log_prefix,
            model=model
        )
        
        # Validate the result
        validated_assessment = models.MarkSimilarityOutput.model_validate(result.model_dump())
        logger.info(f"{log_prefix} Successfully generated with overall similarity: {validated_assessment.overall}")
        
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
    model: str | None = None
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
        model: Optional model name to override DEFAULT_MODEL
        
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
        logger.info(f"{log_prefix} Starting G/S likelihood assessment: '{applicant_good.term}' vs '{opponent_good.term}'")
        
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
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            request_context=log_prefix,
            model=model
        )
        
        # Validate the result
        validated_assessment = models.GoodServiceLikelihoodOutput.model_validate(result.model_dump())
        logger.info(f"{log_prefix} Successfully generated with confusion: {validated_assessment.likelihood_of_confusion}")
        
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
async def _get_conceptual_similarity_score_from_llm(mark1: str, mark2: str, model: str | None = None) -> float:
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
            max_output_tokens=4000,
            model=model
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
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    request_context: str = "",
    model: str | None = None
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
        request_context: Optional context identifier for logging
        model: Optional model name to override DEFAULT_MODEL
        
    Returns:
        The parsed response object
        
    Raises:
        GoogleAPIError: If there's an API issue
        ValueError: If response parsing fails or unsupported model specified
    """
    # If no request context provided, generate a unique ID
    if not request_context:
        request_context = f"[LLM Request {str(uuid.uuid4())[:8]}]"
    
    # Determine which model to use
    model_to_use = DEFAULT_MODEL
    if model is not None:
        if model in SUPPORTED_MODELS:
            model_to_use = model
        else:
            raise ValueError(f"Unsupported model: {model}. Supported models are: {', '.join(SUPPORTED_MODELS)}")
    
    try:
        # For Pydantic models, directly use the class instead of converting to schema dictionary
        # The Gemini Python SDK will properly translate Pydantic models to the appropriate schema
        config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema  # Pass the Pydantic class directly as recommended in the docs
        )

        # Create a new client instance every time to avoid event loop issues
        local_client = genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            http_options=types.HttpOptions(api_version='v1')
        )

        # Log the schema and model being used
        schema_name = schema.__name__ if hasattr(schema, '__name__') else str(schema)
        logger.info(f"{request_context} REQUEST: Using schema: {schema_name} with model: {model_to_use} (temp={temperature}, top_p={top_p}, top_k={top_k})")
        
        # Log prompt (truncated if too long)
        prompt_excerpt = prompt[:500] + "..." if len(prompt) > 500 else prompt
        logger.info(f"{request_context} PROMPT: {prompt_excerpt}")

        # Make up to 3 attempts to get a valid response
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = await local_client.aio.models.generate_content(
                    model=model_to_use,
                    contents=prompt,
                    config=config
                )
                
                # Log the raw response for debugging - use INFO level to ensure it appears in logs
                if hasattr(response, "text"):
                    raw_response = response.text
                    # Truncate very long responses in logs
                    log_response = raw_response[:5000] + "..." if len(raw_response) > 5000 else raw_response
                    logger.info(f"{request_context} RAW RESPONSE (attempt {attempt}): {log_response}")
                else:
                    logger.info(f"{request_context} RAW RESPONSE (attempt {attempt}) - No text attribute: {response}")
                
                # Check if we have a valid response
                if response.parsed:
                    parsed_str = json.dumps(response.parsed.model_dump() if hasattr(response.parsed, 'model_dump') else response.parsed, indent=2)
                    # Truncate very long responses in logs
                    parsed_log = parsed_str[:5000] + "..." if len(parsed_str) > 5000 else parsed_str
                    logger.info(f"{request_context} PARSED RESPONSE: {parsed_log}")
                    return response.parsed
                
                # If we reach here, no valid data was returned
                logger.warning(f"{request_context} Empty parsed data (attempt {attempt}/{max_attempts})")
                
                # For subsequent attempts, increase temperature slightly to encourage variation
                if attempt < max_attempts:
                    # Increase temperature by 0.1 for each retry (up to a max of 0.6)
                    config.temperature = min(0.6, temperature + (DEFAULT_TEMPERATURE_INCREMENT * attempt))
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
    model: str | None = None
) -> list[models.GoodServiceLikelihoodOutput]:
    """
    Process multiple goods/services comparisons with rate limiting.
    
    This function processes combinations of goods/services in smaller batches
    to avoid overwhelming the LLM API with too many concurrent requests.
    
    Args:
        applicant_goods: List of applicant's goods/services
        opponent_goods: List of opponent's goods/services
        mark_similarity: Mark similarity assessment to use for all comparisons
        model: Optional model name to override DEFAULT_MODEL
        
    Returns:
        List of GoodServiceLikelihoodOutput objects for each pair
    """
    import asyncio
    
    # Generate a unique batch ID for this entire batch process
    batch_id = str(uuid.uuid4())[:8]
    log_prefix = f"[Batch Process {batch_id}]"
    
    # Log the start of batch processing with details
    logger.info(f"{log_prefix} Starting batch processing: {len(applicant_goods)} applicant goods × {len(opponent_goods)} opponent goods = {len(applicant_goods) * len(opponent_goods)} total combinations")
    
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
        batch = combinations[i:i+batch_size]
        current_batch_num = i//batch_size + 1
        total_batches = (len(combinations)+batch_size-1)//batch_size
        batch_log_prefix = f"{log_prefix} Batch {current_batch_num}/{total_batches}"
        
        # Log batch start with combination details
        logger.info(f"{batch_log_prefix} Processing combinations:")
        for idx, (app_good, opp_good) in enumerate(batch):
            logger.info(f"{batch_log_prefix} Item {idx+1}: '{app_good.term}' vs '{opp_good.term}'")
        
        # Create tasks for this batch
        tasks = []
        for applicant_good, opponent_good in batch:
            task = generate_gs_likelihood_assessment(
                applicant_good=applicant_good,
                opponent_good=opponent_good,
                mark_similarity=mark_similarity,
                model=model
            )
            tasks.append(task)
        
        # Process this batch
        logger.info(f"{batch_log_prefix} Starting processing")
        start_time = asyncio.get_event_loop().time()
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        
        # Handle results and exceptions
        for idx, result in enumerate(batch_results):
            app_good, opp_good = batch[idx]
            if isinstance(result, Exception):
                logger.error(f"{batch_log_prefix} Error processing item {idx+1} ('{app_good.term}' vs '{opp_good.term}'): {str(result)}")
                error_count += 1
                # Re-raise the first exception after processing all items
                if error_count == 1:
                    first_error = result
            else:
                logger.info(f"{batch_log_prefix} Successfully processed item {idx+1}: '{app_good.term}' vs '{opp_good.term}'")
                processed_results.append(result)
                successful_count += 1
        
        # Log completion of this batch
        duration = end_time - start_time
        logger.info(f"{batch_log_prefix} Completed in {duration:.2f}s")
        
        # Add a small delay between batches to avoid rate limiting
        if i + batch_size < len(combinations):
            logger.info(f"{batch_log_prefix} Waiting {delay_seconds}s before next batch")
            await asyncio.sleep(delay_seconds)
    
    # Log overall completion
    logger.info(f"{log_prefix} Batch processing complete. Successful: {successful_count}, Errors: {error_count}")
    
    # If there were any errors, raise the first one
    if error_count > 0:
        logger.error(f"{log_prefix} Raising first error encountered during batch processing")
        raise first_error
    
    return processed_results 