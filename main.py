"""
Main entry point for Cloud Functions with FastAPI integration.

This module creates a functions_framework compatible HTTP function that serves
the FastAPI app, allowing it to run in Cloud Functions (Gen2).
"""

import asyncio

import functions_framework
from flask import Response, jsonify

# Import the FastAPI app
from api.main import app


@functions_framework.http
def api(request):
    """HTTP Cloud Function that proxies requests to a FastAPI app.

    This function handles the request by manually routing it to the FastAPI application
    and converting between Flask and FastAPI.

    Args:
        request: The Flask request object from Functions Framework

    Returns:
        A Flask response object with the FastAPI response data and proper CORS headers
    """
    # Extract request components
    path = request.path
    method = request.method

    # For CORS preflight requests
    if method == "OPTIONS":
        # Create a response with CORS headers
        response = Response("", status=204)
        origin = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    # Create event loop for async execution
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Get query parameters
    query_params = request.args.to_dict()

    # Get headers
    headers = {k: v for k, v in request.headers.items()}

    # Get body
    body = request.get_data()

    # Call FastAPI app
    try:
        # Start ASGI cycle with scope
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "query_string": request.query_string,
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        }

        # Prepare response data containers
        response_status = None
        response_headers = []
        response_body = b""

        # Define ASGI receive function
        async def receive():
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }

        # Define ASGI send function
        async def send(message):
            nonlocal response_status, response_headers, response_body

            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")

        # Run the ASGI application
        async def run_app():
            await app(scope, receive, send)

        loop.run_until_complete(run_app())

        # Create Flask response
        flask_response = Response(
            response_body,
            status=response_status,
            headers=[(k.decode(), v.decode()) for k, v in response_headers],
        )

        # Add CORS headers to all responses
        origin = request.headers.get("Origin", "*")
        flask_response.headers["Access-Control-Allow-Origin"] = origin
        flask_response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        flask_response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"

        return flask_response

    except Exception as e:
        # Return error response
        error_response = {"error": str(e), "type": type(e).__name__}

        # Add CORS headers to error response
        response = jsonify(error_response)
        origin = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"

        return response, 500
