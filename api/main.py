"""
FastAPI application for trademark similarity prediction.

This module provides HTTP endpoints for comparing trademarks and predicting
opposition outcomes using LLM-powered similarity analysis and reasoning.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import firebase_admin
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware

from api.auth import get_current_user, initialize_firebase_admin
from trademark_core import models
from trademark_core.llm import (
    batch_process_goods_services,
    generate_gs_likelihood_assessment,
    generate_mark_similarity_assessment,
    generate_case_prediction,
)

# Import similarity calculation functions
from trademark_core.similarity import (
    calculate_aural_similarity,
    calculate_visual_similarity,
)

# Initialize FastAPI app
app = FastAPI(
    title="Trademark Similarity API",
    description="API for predicting trademark opposition outcomes",
    version="1.0.0",
)

# --- CORS Configuration ---
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,  # Allow cookies/auth headers
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Initialize Firebase Admin SDK
initialize_firebase_admin()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/mark_similarity", response_model=models.MarkSimilarityOutput)
async def mark_similarity(
    request: models.MarkSimilarityRequest,
    user: firebase_admin.auth.UserRecord = Depends(get_current_user),  # Add auth dependency
) -> models.MarkSimilarityOutput:
    """
    Assess similarity between two wordmarks across multiple dimensions.

    This endpoint calculates visual and aural similarity scores using algorithms,
    then uses an LLM to perform a global assessment following UK/EU trademark
    law principles.

    Requires Firebase Authentication.

    Args:
        request: The mark similarity request containing applicant and opponent mark details
        user: The authenticated Firebase user (injected by dependency)

    Returns:
        MarkSimilarityOutput: Detailed similarity assessment across visual, aural, conceptual,
        and overall dimensions with optional reasoning
    """
    try:
        # 1. Calculate algorithmic similarities
        visual_score = calculate_visual_similarity(
            request.applicant.wordmark, request.opponent.wordmark
        )
        aural_score = calculate_aural_similarity(
            request.applicant.wordmark, request.opponent.wordmark
        )

        # 2. Call the LLM for global assessment
        mark_similarity_output = await generate_mark_similarity_assessment(
            applicant_mark=request.applicant,
            opponent_mark=request.opponent,
            visual_score=visual_score,
            aural_score=aural_score,
        )

        return mark_similarity_output

    except Exception as e:
        # Handle any errors from the LLM process
        raise HTTPException(
            status_code=500, detail=f"Error generating mark similarity assessment: {str(e)}"
        )


@app.post("/gs_similarity", response_model=models.GoodServiceLikelihoodOutput)
async def gs_similarity(
    request: models.GsSimilarityRequest,
    user: firebase_admin.auth.UserRecord = Depends(get_current_user),  # Add auth dependency
) -> models.GoodServiceLikelihoodOutput:
    """
    Assess relationship and likelihood of confusion between a pair of goods/services.

    This endpoint takes a specific pair of goods/services and the mark similarity context,
    then uses an LLM to assess their relationship and the likelihood of confusion
    following the interdependence principle from UK/EU trademark law.

    Requires Firebase Authentication.

    Args:
        request: The G/S similarity request containing goods details and mark similarity context
        user: The authenticated Firebase user (injected by dependency)

    Returns:
        GoodServiceLikelihoodOutput: Assessment of G/S relationship and likelihood of confusion
    """
    try:
        # Generate the goods/services likelihood assessment
        gs_likelihood_output = await generate_gs_likelihood_assessment(
            applicant_good=request.applicant_good,
            opponent_good=request.opponent_good,
            mark_similarity=request.mark_similarity,
        )

        return gs_likelihood_output

    except Exception as e:
        # Handle any errors from the LLM process
        raise HTTPException(
            status_code=500, detail=f"Error generating goods/services assessment: {str(e)}"
        )


@app.post("/batch_gs_similarity", response_model=list[models.GoodServiceLikelihoodOutput])
async def batch_gs_similarity(
    request: models.BatchGsSimilarityRequest,
    user: firebase_admin.auth.UserRecord = Depends(get_current_user),
) -> list[models.GoodServiceLikelihoodOutput]:
    """
    Process multiple goods/services comparisons concurrently.

    This endpoint takes lists of applicant and opponent goods/services along with
    the mark similarity context, and returns a list of likelihood assessments for
    all combinations. All comparisons are processed concurrently using proper async
    event loop handling.

    Requires Firebase Authentication.

    Args:
        request: The batch G/S request containing lists of goods/services and mark similarity
        user: The authenticated Firebase user (injected by dependency)

    Returns:
        List of GoodServiceLikelihoodOutput objects for all G/S combinations
    """
    try:
        # Limit the number of items to process to avoid timeouts
        max_items_per_list = 5
        if (
            len(request.applicant_goods) > max_items_per_list
            or len(request.opponent_goods) > max_items_per_list
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Too many items to process. Please limit to {max_items_per_list} items per list.",
            )

        # Process all goods/services combinations concurrently
        results = await batch_process_goods_services(
            applicant_goods=request.applicant_goods,
            opponent_goods=request.opponent_goods,
            mark_similarity=request.mark_similarity,
        )

        return results

    except Exception as e:
        # Handle any errors from the batch processing
        raise HTTPException(
            status_code=500, detail=f"Error processing batch goods/services assessment: {str(e)}"
        )


@app.post("/case_prediction", response_model=models.CasePredictionResult)
async def case_prediction(
    request: models.CasePredictionRequest,
    user: firebase_admin.auth.UserRecord = Depends(get_current_user),  # Add auth dependency
) -> models.CasePredictionResult:
    """
    Generate the final case prediction based on mark similarity and goods/services assessments.

    This endpoint aggregates the results from mark_similarity and multiple gs_similarity calls,
    then uses an LLM to determine the final opposition outcome with nuanced confidence scoring
    based on UK/EU trademark opposition principles.

    Requires Firebase Authentication.

    Args:
        request: The case prediction request containing mark similarity and G/S likelihood assessments
        user: The authenticated Firebase user (injected by dependency)

    Returns:
        CasePredictionResult: Complete prediction including the final opposition outcome
    """
    try:
        # Use the new LLM-based prediction function
        opposition_outcome = await generate_case_prediction(
            mark_similarity=request.mark_similarity,
            goods_services_likelihoods=request.goods_services_likelihoods,
        )

        # Construct and return the complete prediction
        case_prediction = models.CasePredictionResult(
            mark_comparison=request.mark_similarity,
            goods_services_likelihoods=request.goods_services_likelihoods,
            opposition_outcome=opposition_outcome,
        )

        return case_prediction

    except Exception as e:
        # Handle any errors
        raise HTTPException(status_code=500, detail=f"Error generating case prediction: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
