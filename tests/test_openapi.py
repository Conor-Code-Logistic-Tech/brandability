def test_openapi_schema_contains_endpoints(test_client):
    """Smoke test: OpenAPI schema loads and contains the required endpoints."""
    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    paths = data.get("paths", {})

    # Check for new endpoints after refactoring
    assert "/mark_similarity" in paths
    assert "/gs_similarity" in paths
    assert "/case_prediction" in paths
    assert "/health" in paths
