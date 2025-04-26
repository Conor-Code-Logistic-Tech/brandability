"""
FastAPI application for trademark similarity prediction.

This module provides HTTP endpoints for comparing trademarks and predicting
opposition outcomes using LLM-powered similarity analysis and reasoning.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware
from pydantic import BaseModel
import firebase_admin

from trademark_core import models
from trademark_core.llm import generate_full_prediction
from api.auth import initialize_firebase_admin, get_current_user

# Initialize FastAPI app
app = FastAPI(
    title="Trademark Similarity API",
    description="API for predicting trademark opposition outcomes",
    version="1.0.0"
)

# --- CORS Configuration ---
# Define allowed origins. Adjust as necessary for production.
# For development, allow localhost. You might want to add your deployed frontend URL later.
origins = [
    "http://localhost:8080",
    "https://trademark-prediction-system.web.app"
    # Allow localhost for frontend development
    # Add your production frontend URL here when deployed, e.g.:
    # "https://your-frontend-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True, # Allow cookies/auth headers
    allow_methods=["*"], # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"]  # Allow all headers
)
# --- End CORS Configuration ---

# Initialize Firebase Admin SDK
# This ensures it's ready before the first request that needs it
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
        # Use the LLM-centric approach to generate the full prediction
        prediction = await generate_full_prediction(request)
        return prediction
    except Exception as e:
        # Handle any errors from the LLM process
        raise HTTPException(
            status_code=500,
            detail=f"Error generating prediction: {str(e)}"
        ) 