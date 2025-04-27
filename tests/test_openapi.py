def test_openapi_schema_contains_endpoints(test_client):
    """Smoke test: OpenAPI schema loads and contains /predict and /health endpoints."""
    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    paths = data.get("paths", {})
    assert "/predict" in paths
    assert "/health" in paths
