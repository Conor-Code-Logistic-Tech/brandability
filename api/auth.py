"""
Firebase Authentication dependency for FastAPI.

This module provides a FastAPI dependency to verify Firebase ID tokens
and ensure that API requests are authenticated.
"""

import logging
from functools import lru_cache

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use HTTPBearer security scheme for extracting the token
bearer_scheme = HTTPBearer()

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

        # Attempt initialization using Application Default Credentials (ADC)
        # This is the standard way in Cloud Functions/Run environments
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully using ADC.")
        return firebase_admin.get_app()

    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
        # Depending on the deployment, you might want to handle this differently.
        # For a critical API, you might want the app to fail startup.
        raise RuntimeError("Could not initialize Firebase Admin SDK.") from e


async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> auth.UserRecord:
    """
    FastAPI dependency to verify Firebase ID Token and return user info.

    Args:
        token: The HTTPAuthorizationCredentials containing the bearer token.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing, invalid, or expired.
        HTTPException: 500 Internal Server Error if Firebase Admin is not initialized.

    Returns:
        auth.UserRecord: The verified Firebase user object.
    """
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
        user = auth.get_user(decoded_token['uid'])
        if not user:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user # Or return decoded_token if you only need claims

    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid ID token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
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
