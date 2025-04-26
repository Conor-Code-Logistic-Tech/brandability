"""
Main entry point for the FastAPI application.

This module imports and exposes the FastAPI application instance for ASGI servers like Uvicorn.
"""

from api.main import app as fastapi_app

app = fastapi_app
