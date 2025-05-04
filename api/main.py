"""
FastAPI application for trademark similarity prediction.

This module provides HTTP endpoints for comparing trademarks and predicting
opposition outcomes using LLM-powered similarity analysis and reasoning.
"""

import firebase_admin
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware

from api.auth import get_current_user, initialize_firebase_admin
from trademark_core import models
from trademark_core.llm import (
    generate_gs_likelihood_assessment,
    generate_mark_similarity_assessment,
)

# Import similarity calculation functions
from trademark_core.similarity import (
    calculate_aural_similarity,
    calculate_conceptual_similarity,
    calculate_visual_similarity,
)

# Initialize FastAPI app
app = FastAPI(
    title="Trademark Similarity API",
    description="API for predicting trademark opposition outcomes",
    version="1.0.0"
)

# --- CORS Configuration ---
origins = [
    "localhost",
    "https://trademark-prediction-system.web.app",
    "https://europe-west2-trademark-prediction-system.cloudfunctions.net/trademark-api"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True, # Allow cookies/auth headers
    allow_methods=["*"], # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"]  # Allow all headers
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
    user: firebase_admin.auth.UserRecord = Depends(get_current_user)  # Add auth dependency
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
            request.applicant.wordmark,
            request.opponent.wordmark
        )
        aural_score = calculate_aural_similarity(
            request.applicant.wordmark,
            request.opponent.wordmark
        )
        
        # 2. Call the LLM for global assessment
        mark_similarity_output = await generate_mark_similarity_assessment(
            applicant_mark=request.applicant,
            opponent_mark=request.opponent,
            visual_score=visual_score,
            aural_score=aural_score
        )
        
        return mark_similarity_output
    
    except Exception as e:
        # Handle any errors from the LLM process
        raise HTTPException(
            status_code=500,
            detail=f"Error generating mark similarity assessment: {str(e)}"
        )

@app.post("/gs_similarity", response_model=models.GoodServiceLikelihoodOutput)
async def gs_similarity(
    request: models.GsSimilarityRequest,
    user: firebase_admin.auth.UserRecord = Depends(get_current_user)  # Add auth dependency
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
            mark_similarity=request.mark_similarity
        )
        
        return gs_likelihood_output
    
    except Exception as e:
        # Handle any errors from the LLM process
        raise HTTPException(
            status_code=500,
            detail=f"Error generating goods/services assessment: {str(e)}"
        )

@app.post("/case_prediction", response_model=models.CasePredictionResult)
async def case_prediction(
    request: models.CasePredictionRequest,
    user: firebase_admin.auth.UserRecord = Depends(get_current_user)  # Add auth dependency
) -> models.CasePredictionResult:
    """
    Generate the final case prediction based on mark similarity and goods/services assessments.
    
    This endpoint aggregates the results from mark_similarity and multiple gs_similarity calls,
    then determines the final opposition outcome using the UK/EU trademark opposition principles.
    
    Requires Firebase Authentication.
    
    Args:
        request: The case prediction request containing mark similarity and G/S likelihood assessments
        user: The authenticated Firebase user (injected by dependency)
        
    Returns:
        CasePredictionResult: Complete prediction including the final opposition outcome
    """
    try:
        # Determine opposition outcome based on aggregation of G/S likelihoods
        all_confusion = all(gs.likelihood_of_confusion for gs in request.goods_services_likelihoods)
        any_confusion = any(gs.likelihood_of_confusion for gs in request.goods_services_likelihoods)
        
        # Determine outcome category
        if all_confusion:
            result = "Opposition likely to succeed"
            confidence = 0.9
            reasoning = (
                "All goods/services pairings showed a likelihood of confusion when considering "
                f"the {request.mark_similarity.overall} mark similarity. Under UK/EU trademark law, "
                "this indicates the opposition is likely to succeed across all specifications."
            )
        elif not any_confusion:
            result = "Opposition likely to fail"
            confidence = 0.9
            reasoning = (
                "None of the goods/services pairings showed a likelihood of confusion, even when considering "
                f"the {request.mark_similarity.overall} mark similarity between the marks. Under UK/EU trademark law, "
                "this indicates the opposition is likely to fail entirely."
            )
        else:
            result = "Opposition may partially succeed"
            confused_count = sum(1 for gs in request.goods_services_likelihoods if gs.likelihood_of_confusion)
            total_count = len(request.goods_services_likelihoods)
            confidence = 0.7
            reasoning = (
                f"{confused_count} out of {total_count} goods/services pairings showed a likelihood of confusion "
                f"when considering the {request.mark_similarity.overall} mark similarity. Under UK/EU trademark law, "
                "this indicates the opposition may partially succeed, limited to those goods/services where "
                "confusion is likely."
            )
        
        # Construct the outcome
        opposition_outcome = models.OppositionOutcome(
            result=result,
            confidence=confidence,
            reasoning=reasoning
        )
        
        # Construct and return the complete prediction
        case_prediction = models.CasePredictionResult(
            mark_comparison=request.mark_similarity,
            goods_services_likelihoods=request.goods_services_likelihoods,
            opposition_outcome=opposition_outcome
        )
        
        return case_prediction
    
    except Exception as e:
        # Handle any errors
        raise HTTPException(
            status_code=500,
            detail=f"Error generating case prediction: {str(e)}"
        )
