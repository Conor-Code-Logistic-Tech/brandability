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
from trademark_core.llm import generate_full_prediction

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

@app.post("/predict", response_model=models.CasePrediction)
async def predict_opposition(
    request: models.PredictionRequest,
    user: firebase_admin.auth.UserRecord = Depends(get_current_user)  # Add auth dependency
) -> models.CasePrediction:
    """
    Predict the outcome of a trademark opposition based on mark and goods/services comparison.
    
    Requires Firebase Authentication.
    
    Args:
        request: The prediction request containing applicant and opponent details
        user: The authenticated Firebase user (injected by dependency)
        
    Returns:
        CasePrediction: Detailed prediction results with mark comparison and outcome
    """
    try:
        # 1. Calculate individual similarities first
        visual_score = calculate_visual_similarity(
            request.applicant.wordmark,
            request.opponent.wordmark
        )
        aural_score = calculate_aural_similarity(
            request.applicant.wordmark,
            request.opponent.wordmark
        )
        # Conceptual similarity is async
        conceptual_score = await calculate_conceptual_similarity(
            request.applicant.wordmark,
            request.opponent.wordmark
        )

        # 2. Call the LLM with pre-calculated scores
        prediction = await generate_full_prediction(
            request=request,
            visual_score=visual_score,
            aural_score=aural_score,
            conceptual_score=conceptual_score
        )
        return prediction
    except Exception as e:
        # Handle any errors from the LLM process
        raise HTTPException(
            status_code=500,
            detail=f"Error generating prediction: {str(e)}"
        )
