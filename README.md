# Trademark Similarity Prediction API

This project provides an API to compare two trademarks (wordmarks) along with their associated goods/services and predict the likelihood and outcome of a trademark opposition case, primarily aimed at assisting trademark lawyers. It leverages Google's Gemini 2.5 Pro via Vertex AI for detailed analysis and reasoning.

The API is deployed as a Google Cloud Function and is publicly accessible without authentication.

## Accessing the Deployed API

The API is hosted on Google Cloud Functions at the following base URL:

`https://europe-west2-trademark-prediction-system.cloudfunctions.net/trademark-api`

You can interact with the API using standard HTTP requests (e.g., using `curl` or any HTTP client).

### Endpoints

#### 1. Health Check

- **Endpoint:** `/health`
- **Method:** `GET`
- **Description:** A simple endpoint to verify if the API is running and accessible.
- **Example Request:**
  ```bash
  curl https://europe-west2-trademark-prediction-system.cloudfunctions.net/trademark-api/health
  ```
- **Example Response:**
  ```json
  {"status": "ok"}
  ```

#### 2. Predict Opposition Outcome

- **Endpoint:** `/predict`
- **Method:** `POST`
- **Description:** Analyzes the similarity between an applicant's and an opponent's trademark and goods/services to predict the outcome of a potential opposition. It requires details about both marks and their respective goods/services.
- **Request Body:** A JSON object conforming to the `PredictionRequest` schema (defined in `trademark_core/models.py`). See the example below.
- **Response Body:** A JSON object conforming to the `CasePrediction` schema (defined in `trademark_core/models.py`), containing detailed analysis and the predicted outcome.
- **Example Request:**
  ```bash
  curl -X POST https://europe-west2-trademark-prediction-system.cloudfunctions.net/trademark-api/predict \\
  -H "Content-Type: application/json" \\
  -d '{
    "applicant": {
      "wordmark": "COOLBRAND",
      "is_registered": false
    },
    "opponent": {
      "wordmark": "KOOL BRAND",
      "is_registered": true,
      "registration_number": "UK1234567"
    },
    "applicant_goods": [
      {
        "term": "T-shirts",
        "nice_class": 25
      },
      {
        "term": "Online retail services for clothing",
        "nice_class": 35
      }
    ],
    "opponent_goods": [
      {
        "term": "Clothing, namely shirts and jackets",
        "nice_class": 25
      }
    ]
  }'
  ```
- **Example Response Snippet (Structure):**
  ```json
  {
    "analysis": {
      "mark_comparison": {
        "visual_similarity": { "score": 0.8, "reasoning": "..." },
        "aural_similarity": { "score": 0.9, "reasoning": "..." },
        "conceptual_similarity": { "score": 0.6, "reasoning": "..." },
        "overall_mark_similarity": { "score": 0.75, "reasoning": "..." }
      },
      "goods_services_comparison": {
        "similarity_matrix": [...],
        "overall_similarity": { "score": 0.85, "reasoning": "..." }
      },
      "likelihood_of_confusion": { "score": 0.8, "reasoning": "..." }
    },
    "prediction": {
      "outcome": "Opposition likely to succeed",
      "confidence": "High",
      "summary": "..."
    }
    // ... other fields as defined in models.CasePrediction
  }
  ```
  *Note: Refer to `trademark_core/models.py` for the full response schema.*

## Core Features

The prediction process involves:

- **Multi-faceted Mark Similarity:** Analyzing visual (edit distance), aural (phonetic algorithms), and conceptual (LLM-based semantic understanding) similarities.
- **Goods & Services Analysis:** Assessing semantic similarity between terms and considering Nice classifications.
- **LLM-Powered Reasoning:** Utilizing Gemini 2.5 Pro for a comprehensive legal analysis, likelihood of confusion assessment, and outcome prediction based on established legal principles.

## Tech Stack

- **API Framework:** FastAPI
- **Deployment:** Google Cloud Functions
- **Language Model:** Google Vertex AI (Gemini 2.5 Pro)
- **Language:** Python 3.10+

## Project Structure and File Overview

```
trademark_prod/
├── .gcloudignore           # Specifies files to ignore when deploying to Google Cloud
├── .gitignore              # Specifies intentionally untracked files that Git should ignore
├── .env.yaml               # Environment variables (sensitive, typically not committed)
├── .env.example            # Example environment variables file
├── .pytest_cache/          # Cache directory for pytest runs
├── .ruff_cache/            # Cache directory for Ruff linter/formatter
├── api/                    # Contains the FastAPI application and routes
│   ├── __init__.py
│   ├── main.py             # FastAPI application instance and root/health endpoints
│   └── routes/             # Directory for API endpoint routers
│       ├── __init__.py
│       └── predict.py      # Router for the /predict endpoint
├── model_context/          # (Potentially) Contains context/prompts for the LLM
├── trademark_core/         # Core business logic and data models
│   ├── __init__.py
│   ├── llm_adapter.py      # Interface for interacting with the Vertex AI LLM
│   ├── models.py           # Pydantic models (SSoT for data structures)
│   └── services.py         # Business logic for trademark comparison
├── tests/                  # Contains all tests (unit, integration)
│   ├── __init__.py
│   └── test_predict.py     # Tests specifically for the prediction endpoint
├── venv/                   # Python virtual environment (dependencies)
├── main.py                 # GCP Cloud Function entry point
├── project-policy.yaml     # (Potentially) Policy or configuration file
├── pyproject.toml          # Project metadata and build configuration (uses Poetry)
├── README.md               # This file: Project overview, API usage, setup instructions
└── requirements.txt        # Project dependencies (alternative to pyproject.toml/Poetry)
```

### Key File/Directory Descriptions (for Frontend AI Agent)

*   **`README.md`**: You are reading it now! Provides the primary overview, explains how to interact with the *deployed* API, including endpoint details, request/response formats, and example `curl` commands. Also guides contributors on local setup.
*   **`main.py` (root level)**: This is the entry point specifically for Google Cloud Functions deployment. It imports and configures the FastAPI app from `api/main.py`. You generally don't interact with this directly.
*   **`api/`**: This directory holds the web server code built using the FastAPI framework.
    *   **`api/main.py`**: Creates the main FastAPI application object. It often includes basic endpoints like `/health` for status checks. The core application logic (like prediction) is typically delegated to routers.
    *   **`api/routes/predict.py`**: Defines the `/predict` API endpoint. It handles incoming POST requests, validates the data against the Pydantic models defined in `trademark_core/models.py`, calls the relevant backend services in `trademark_core/services.py` to perform the analysis, and formats the response according to the output Pydantic models. **This is the primary interaction point for a frontend.**
*   **`trademark_core/`**: Contains the essential backend logic, separate from the API layer.
    *   **`trademark_core/models.py`**: **Crucial for frontend interaction.** This file defines the *shape* of the data (schemas) used throughout the application, especially for API requests and responses, using Pydantic models. When you send data to `/predict`, it must match the `PredictionRequest` model defined here. The response you receive will match the `CasePrediction` model also defined here. Consider these models the **contract** for API communication.
    *   **`trademark_core/services.py`**: Implements the complex business logic for comparing trademarks and goods/services, involving similarity calculations and likelihood of confusion assessment. It likely uses `llm_adapter.py` to communicate with the AI model.
    *   **`trademark_core/llm_adapter.py`**: Handles communication with the external Large Language Model (Google's Gemini via Vertex AI) to get analysis and reasoning.
*   **`tests/`**: Contains automated tests to ensure the backend code works correctly. Not directly relevant for consuming the API but indicates project health.
*   **`pyproject.toml` / `requirements.txt`**: List the external Python libraries the project depends on. Useful if you need to understand the underlying technologies or set up a local copy for testing.
*   **`.env.example` / `.env`**: Define necessary environment variables, like API keys or cloud project IDs. `.env.example` shows *what* variables are needed, while the actual `.env` file (which is usually not committed to Git) holds the *values* for a specific deployment or local setup.

## Local Development (For Contributors)

While the primary way to use the API is via its deployed endpoint, contributors can set up a local environment:

1.  **Prerequisites:** Python 3.10+
2.  **Clone:** `git clone <repository-url>`
3.  **Dependencies:** `pip install -r requirements.txt`
4.  **Environment:** Copy `env.example` to `.env` and configure Google Cloud credentials (Project ID, potentially Application Credentials). See `.env.example` for details. *Note: Full local execution requires appropriate GCP authentication.*
5.  **Run Tests:** `pytest`
6.  **Linting/Formatting:** `ruff check .` / `ruff format .`

*Running the server locally (`uvicorn api.main:app --reload`) is possible but requires the environment variables to be correctly set up.*

