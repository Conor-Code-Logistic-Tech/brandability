"""
Main entry point for the FastAPI application.

This module imports and exposes the FastAPI application instance for ASGI servers like Uvicorn.
"""

from api.main import app as fastapi_app

# The ASGI server (e.g., Uvicorn specified in Procfile) will look for an 'app' instance.
# We rename the imported app for clarity if needed elsewhere, but ensure 'app' is available.
app = fastapi_app

# Removed the functions_framework wrapper function 'api' 