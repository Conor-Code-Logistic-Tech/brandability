from trademark_core import models


def make_valid_prediction_request() -> dict:
    """Helper to construct a valid PredictionRequest as dict for the /predict endpoint."""
    return models.PredictionRequest(
        applicant=models.Mark(wordmark="EXAMPLIA", is_registered=True, registration_number="1234567"),
        opponent=models.Mark(wordmark="EXEMPLAR", is_registered=False),
        applicant_goods=[
            models.GoodService(term="Software for legal research", nice_class=42)
        ],
        opponent_goods=[
            models.GoodService(term="Computer software for legal case management", nice_class=42)
        ]
    ).model_dump()

def test_predict_success(test_client):
    """Test /predict endpoint with valid input returns HTTP 200 and CasePrediction structure."""
    payload = make_valid_prediction_request()
    response = test_client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Check top-level keys from CasePrediction
    assert set(data.keys()) == {"mark_comparison", "goods_services_comparisons", "likelihood_of_confusion", "opposition_outcome"}
    # Check mark_comparison structure
    mark_comp = data["mark_comparison"]
    assert set(mark_comp.keys()) == {"visual", "aural", "conceptual", "overall"}
    # Check goods_services_comparisons is a list and has expected keys
    assert isinstance(data["goods_services_comparisons"], list)
    if data["goods_services_comparisons"]:
        gsc = data["goods_services_comparisons"][0]
        assert set(gsc.keys()) >= {"applicant_good", "opponent_good", "overall_similarity", "are_competitive", "are_complementary"}
    # Check opposition_outcome structure
    outcome = data["opposition_outcome"]
    assert set(outcome.keys()) == {"result", "confidence", "reasoning"}
    # Check likelihood_of_confusion is a bool
    assert isinstance(data["likelihood_of_confusion"], bool)

def test_predict_invalid_input(test_client):
    """Test /predict endpoint with invalid input returns HTTP 422."""
    # Remove required field 'applicant' from payload
    payload = make_valid_prediction_request()
    del payload["applicant"]
    response = test_client.post("/predict", json=payload)
    assert response.status_code == 422
