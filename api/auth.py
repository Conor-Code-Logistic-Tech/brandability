"""
Firebase Authentication dependency for FastAPI.

This module provides a FastAPI dependency to verify Firebase ID tokens
and ensure that API requests are authenticated.
"""

import logging
import os
from functools import lru_cache

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use HTTPBearer security scheme for extracting the token
bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def initialize_firebase_admin():
    """
    Initializes the Firebase Admin SDK.

    Uses application default credentials if GOOGLE_APPLICATION_CREDENTIALS
    environment variable is set (typical for Cloud Functions/Run).
    Falls back to trying to find a service account key file if specified.
    """
    try:
        # Check if already initialized (useful for hot-reloads or testing)
        if firebase_admin._apps:
            logger.info("Firebase Admin SDK already initialized.")
            return firebase_admin.get_app()

        # Get the project ID from environment variable
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "trademark-prediction-system")
        
        # Debug: Log all relevant environment variables
        logger.info(f"Raw GOOGLE_CLOUD_PROJECT: '{project_id}'")
        logger.info(f"GOOGLE_CLOUD_LOCATION: '{os.environ.get('GOOGLE_CLOUD_LOCATION', 'not set')}'")
        logger.info(f"GOOGLE_GENAI_USE_VERTEXAI: '{os.environ.get('GOOGLE_GENAI_USE_VERTEXAI', 'not set')}'")
        logger.info(f"TEST_MODE: '{os.environ.get('TEST_MODE', 'not set')}'")
        
        # Ensure project ID is clean (no extra environment variables)
        project_id = project_id.strip()
        
        # Additional check for any unexpected characters or concatenation
        if ' ' in project_id or '\n' in project_id or '\t' in project_id:
            logger.error(f"Project ID contains whitespace or special characters: '{project_id}'")
            # Clean the project ID by taking only the first part before any space
            project_id = project_id.split()[0]
            logger.info(f"Cleaned project ID: '{project_id}'")
        
        logger.info(f"Initializing Firebase Admin SDK with project ID: '{project_id}'")

        # Attempt initialization using Application Default Credentials (ADC)
        # This is the standard way in Cloud Functions/Run environments
        cred = credentials.ApplicationDefault()
        
        # Initialize with explicit project ID to avoid any concatenation issues
        firebase_admin.initialize_app(cred, {
            'projectId': project_id
        })
        
        logger.info("Firebase Admin SDK initialized successfully using ADC.")
        return firebase_admin.get_app()

    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
        # Depending on the deployment, you might want to handle this differently.
        # For a critical API, you might want the app to fail startup.
        raise RuntimeError("Could not initialize Firebase Admin SDK.") from e


def is_test_mode() -> bool:
    """Return True if TEST_MODE environment variable is set to a truthy value."""
    value = os.environ.get("TEST_MODE", "").lower()
    return value in ("1", "true", "yes")


def get_current_user(token: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """
    Dependency to get the current Firebase user.
    Returns a dummy user if TEST_MODE is set (for tests/dev), otherwise enforces Firebase authentication.

    Args:
        token: The HTTP Bearer token extracted from the Authorization header

    Returns:
        The Firebase UserRecord for the authenticated user
    """
    if is_test_mode():

        class DummyUser:
            uid = "test-user"
            email = "test@example.com"
            display_name = "Test User"

        return DummyUser()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Ensure Firebase Admin is initialized before verifying tokens
        initialize_firebase_admin()

        # Verify the ID token
        decoded_token = auth.verify_id_token(token.credentials)
        # Optionally, you could fetch the full UserRecord if needed:
        # user = auth.get_user(decoded_token['uid'])
        # return user
        # For now, just returning the decoded token payload might be sufficient
        # but returning UserRecord aligns better with common patterns.
        # Let's return the UID for now as a simpler example.
        # To get UserRecord, uncomment the get_user line above and below.
        # uid = decoded_token.get("uid")
        user = auth.get_user(decoded_token["uid"])
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user  # Or return decoded_token if you only need claims

    except auth.InvalidIdTokenError as e:
        error_msg = str(e)
        logger.warning(f"Invalid ID token: {error_msg}")
        
        # Check if this is specifically an audience claim issue
        if "aud" in error_msg:
            logger.error(f"Firebase audience claim mismatch detected: {error_msg}")
            logger.error("This suggests a Firebase project configuration issue.")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {error_msg}",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except auth.UserNotFoundError:
        logger.warning("User not found for token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Catch other potential errors during verification or Firebase init issues
        logger.error(f"Error verifying token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process authentication token.",
        )
