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
    """
    try:
        if firebase_admin._apps:
            return firebase_admin.get_app()

        project_id = "trademark-prediction-system"
        
        # The GOOGLE_CLOUD_PROJECT environment variable can interfere with the Admin SDK's
        # project auto-detection, leading to incorrect audience claims. By temporarily
        # unsetting it, we force the SDK to use the projectId we provide explicitly.
        original_project = os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {'projectId': project_id})
            logger.info(f"Firebase Admin SDK initialized for project: {project_id}")
        finally:
            # Restore the environment variable to avoid side effects in other parts of the app.
            if original_project is not None:
                os.environ["GOOGLE_CLOUD_PROJECT"] = original_project
        
        return firebase_admin.get_app()

    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
        raise RuntimeError("Could not initialize Firebase Admin SDK.") from e


def is_test_mode() -> bool:
    """Return True if TEST_MODE environment variable is set to a truthy value."""
    value = os.environ.get("TEST_MODE", "").lower()
    return value in ("1", "true", "yes")


def get_current_user(token: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """
    Dependency to get the current Firebase user.
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
        initialize_firebase_admin()
        id_token = token.credentials
        
        # The Admin SDK will now correctly expect the audience to be the project ID.
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        user = auth.get_user(decoded_token["uid"])
        logger.info(f"Successfully verified token for user: {user.uid}")
        return user

    except auth.InvalidIdTokenError as e:
        logger.error(f"Token verification failed: {e}")
        # The detailed error from `e` will be sent to the client.
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")
    except auth.UserNotFoundError:
        logger.warning("User from token not found in Firebase.")
        raise HTTPException(status_code=401, detail="User not found.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during authentication: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not process authentication token.")
