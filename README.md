# Trademark Similarity Prediction API

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)

## Overview

This project provides a backend API designed to assist trademark lawyers by comparing two trademarks (wordmarks) and their associated goods/services. It predicts the likelihood and potential outcome of a trademark opposition case using a modular, multi-faceted similarity analysis powered by Google's Gemini 2.5 Pro large language model via Vertex AI.

The API follows a sequential, modular approach that better aligns with UK/EU legal reasoning for trademark oppositions:
1. First, assess mark similarity in isolation
2. Then evaluate goods/services similarity with knowledge of the mark similarity
3. Finally determine likelihood of confusion and overall opposition outcome

This sequential flow allows for more nuanced legal reasoning and gives clients flexibility to process multiple goods/services comparisons concurrently.

The API requires authentication using Firebase Authentication.

## Core Features

-   **Modular Mark Similarity Assessment (`/mark_similarity`):**
    -   **Visual:** Levenshtein distance between wordmarks.
    -   **Aural:** Double Metaphone phonetic encoding compared using Levenshtein distance.
    -   **Conceptual:** Semantic similarity assessed by the Gemini LLM.
    -   **Global Assessment:** LLM performs a global assessment following UK/EU trademark principles.
-   **Goods & Services Analysis with Mark Context (`/gs_similarity`):**
    -   Compares a single pair of applicant and opponent goods/services
    -   Assesses similarity, competitiveness, and complementarity based on UK/EU factors
    -   Determines likelihood of confusion for that specific pair considering the interdependence with mark similarity
    -   Identifies the type of confusion (direct/indirect) if relevant
-   **Case Outcome Aggregation (`/case_prediction`):**
    -   Aggregates mark similarity and all goods/services comparisons
    -   Determines overall opposition outcome based on UK/EU legal principles
    -   Provides a confidence score and detailed reasoning

## Tech Stack

-   **API Framework:** FastAPI
-   **Cloud Platform:** Google Cloud (Deployed via Cloud Functions/Run)
-   **Authentication:** Firebase Authentication
-   **Language Model:** Google Vertex AI (Gemini 2.5 Pro)
-   **Language:** Python 3.11
-   **Linting/Formatting:** Ruff
-   **Testing:** Pytest

## API Reference

### Base URL

The API is hosted on Google Cloud Functions. Obtain the specific function URL after deployment.
Example format:
`https://<region>-<your-gcp-project-id>.cloudfunctions.net/<function-name>`

*Replace placeholders with your actual deployment details.* 

### Authentication

All endpoints that interact with the Gemini LLM **must** include a valid Firebase ID Token in the `Authorization` header.

-   **Header:** `Authorization: Bearer <FIREBASE_ID_TOKEN>`

Clients must authenticate using Firebase Authentication (e.g., via the Firebase Web SDK) to obtain this token before calling the API.

### Endpoints

#### 1. Health Check

-   **Endpoint:** `/health`
-   **Method:** `GET`
-   **Authentication:** None required.
-   **Description:** Verifies API availability.
-   **Example Request:**
    ```bash
    curl https://<your-function-url>/health
    ```
-   **Success Response (200 OK):**
    ```json
    {"status": "ok"}
    ```

#### 2. Mark Similarity Assessment

-   **Endpoint:** `/mark_similarity`
-   **Method:** `POST`
-   **Authentication:** Firebase ID Token required (Bearer Token).
-   **Description:** Assesses similarity between two wordmarks across visual, aural, and conceptual dimensions.
-   **Request Body:** A JSON object conforming to the `MarkSimilarityRequest` schema.
    ```typescript
    interface MarkSimilarityRequest {
      applicant: Mark;
      opponent: Mark;
    }

    interface Mark {
      wordmark: string;
      is_registered?: boolean; // default: false
      registration_number?: string | null;
    }
    ```
-   **Example Request:**
    ```bash
    # Replace <FIREBASE_ID_TOKEN> with a valid token
    curl -X POST https://<your-function-url>/mark_similarity \
      -H "Authorization: Bearer <FIREBASE_ID_TOKEN>" \
      -H "Content-Type: application/json" \
      -d '{
        "applicant": {
          "wordmark": "CloudCanvas"
        },
        "opponent": {
          "wordmark": "Kloud Kanvas",
          "is_registered": true,
          "registration_number": "UK7654321"
        }
      }'
    ```
-   **Response Body:** A JSON object conforming to the `MarkSimilarityOutput` schema.
    ```typescript
    type EnumStr = "dissimilar" | "low" | "moderate" | "high" | "identical";

    interface MarkSimilarityOutput {
      visual: EnumStr;
      aural: EnumStr;
      conceptual: EnumStr;
      overall: EnumStr;
      reasoning?: string; // Optional LLM reasoning
    }
    ```
-   **Example Response:**
    ```json
    {
      "visual": "high",
      "aural": "high",
      "conceptual": "moderate",
      "overall": "high",
      "reasoning": "Both marks contain the same concepts of 'cloud' and 'canvas' with similar phonetic sounds..."
    }
    ```

#### 3. Goods/Services Similarity with Likelihood of Confusion

-   **Endpoint:** `/gs_similarity`
-   **Method:** `POST`
-   **Authentication:** Firebase ID Token required (Bearer Token).
-   **Description:** Assesses similarity between a single pair of goods/services and determines likelihood of confusion, considering the mark similarity context.
-   **Request Body:** A JSON object conforming to the `GsSimilarityRequest` schema.
    ```typescript
    interface GsSimilarityRequest {
      applicant_good: GoodService;
      opponent_good: GoodService;
      mark_similarity: MarkSimilarityOutput; // The output from /mark_similarity
    }

    interface GoodService {
      term: string;
      nice_class: number; // 1-45
    }
    ```
-   **Example Request:**
    ```bash
    # Replace <FIREBASE_ID_TOKEN> with a valid token
    curl -X POST https://<your-function-url>/gs_similarity \
      -H "Authorization: Bearer <FIREBASE_ID_TOKEN>" \
      -H "Content-Type: application/json" \
      -d '{
        "applicant_good": {
          "term": "Platform as a service (PAAS)",
          "nice_class": 42
        },
        "opponent_good": {
          "term": "Cloud computing services",
          "nice_class": 42
        },
        "mark_similarity": {
          "visual": "high",
          "aural": "high",
          "conceptual": "moderate",
          "overall": "high"
        }
      }'
    ```
-   **Response Body:** A JSON object conforming to the `GoodServiceLikelihoodOutput` schema.
    ```typescript
    interface GoodServiceLikelihoodOutput {
      applicant_good: GoodService;
      opponent_good: GoodService;
      are_competitive: boolean;
      are_complementary: boolean;
      similarity_score: number; // 0.0 to 1.0
      likelihood_of_confusion: boolean;
      confusion_type?: "direct" | "indirect"; // Only if likelihood_of_confusion is true
    }
    ```
-   **Example Response:**
    ```json
    {
      "applicant_good": {
        "term": "Platform as a service (PAAS)",
        "nice_class": 42
      },
      "opponent_good": {
        "term": "Cloud computing services",
        "nice_class": 42
      },
      "are_competitive": true,
      "are_complementary": false,
      "similarity_score": 0.85,
      "likelihood_of_confusion": true,
      "confusion_type": "direct"
    }
    ```

#### 4. Case Prediction (Final Outcome)

-   **Endpoint:** `/case_prediction`
-   **Method:** `POST`
-   **Authentication:** Firebase ID Token required (Bearer Token).
-   **Description:** Aggregates mark similarity and goods/services assessments to determine the overall opposition outcome.
-   **Request Body:** A JSON object conforming to the `CasePredictionRequest` schema.
    ```typescript
    interface CasePredictionRequest {
      mark_similarity: MarkSimilarityOutput; // From /mark_similarity
      goods_services_likelihoods: GoodServiceLikelihoodOutput[]; // Array of /gs_similarity results
    }
    ```
-   **Example Request:**
    ```bash
    # Replace <FIREBASE_ID_TOKEN> with a valid token
    curl -X POST https://<your-function-url>/case_prediction \
      -H "Authorization: Bearer <FIREBASE_ID_TOKEN>" \
      -H "Content-Type: application/json" \
      -d '{
        "mark_similarity": {
          "visual": "high",
          "aural": "high",
          "conceptual": "moderate",
          "overall": "high"
        },
        "goods_services_likelihoods": [
          {
            "applicant_good": {"term": "Platform as a service (PAAS)", "nice_class": 42},
            "opponent_good": {"term": "Cloud computing services", "nice_class": 42},
            "are_competitive": true,
            "are_complementary": false,
            "similarity_score": 0.85,
            "likelihood_of_confusion": true,
            "confusion_type": "direct"
          },
          {
            "applicant_good": {"term": "Software as a service (SAAS)", "nice_class": 42},
            "opponent_good": {"term": "Computer software development tools", "nice_class": 9},
            "are_competitive": false,
            "are_complementary": true,
            "similarity_score": 0.4,
            "likelihood_of_confusion": false
          }
        ]
      }'
    ```
-   **Response Body:** A JSON object conforming to the `CasePredictionResult` schema.
    ```typescript
    type OppositionResultEnum = "Opposition likely to succeed" | "Opposition may partially succeed" | "Opposition likely to fail";

    interface CasePredictionResult {
      mark_similarity: MarkSimilarityOutput;
      goods_services_likelihoods: GoodServiceLikelihoodOutput[];
      opposition_outcome: OppositionOutcome;
    }

    interface OppositionOutcome {
      result: OppositionResultEnum;
      confidence: number; // 0.0 to 1.0
      reasoning: string;
    }
    ```
-   **Example Response:**
    ```json
    {
      "mark_similarity": {
        "visual": "high",
        "aural": "high",
        "conceptual": "moderate",
        "overall": "high"
      },
      "goods_services_likelihoods": [
        {
          "applicant_good": {"term": "Platform as a service (PAAS)", "nice_class": 42},
          "opponent_good": {"term": "Cloud computing services", "nice_class": 42},
          "are_competitive": true,
          "are_complementary": false,
          "similarity_score": 0.85,
          "likelihood_of_confusion": true,
          "confusion_type": "direct"
        },
        {
          "applicant_good": {"term": "Software as a service (SAAS)", "nice_class": 42},
          "opponent_good": {"term": "Computer software development tools", "nice_class": 9},
          "are_competitive": false,
          "are_complementary": true,
          "similarity_score": 0.4,
          "likelihood_of_confusion": false
        }
      ],
      "opposition_outcome": {
        "result": "Opposition may partially succeed",
        "confidence": 0.75,
        "reasoning": "The opposition is likely to succeed for services in class 42 where there is a high similarity of marks and goods/services leading to a direct likelihood of confusion. However, it may fail for the comparison between SAAS in class 42 and software development tools in class 9 where no likelihood of confusion was found despite the high mark similarity."
      }
    }
    ```
-   **Error Responses:**
    -   `401 Unauthorized`: Missing, invalid, or expired Firebase token.
    -   `422 Unprocessable Entity`: Request body validation failed (e.g., missing fields, incorrect types).
    -   `500 Internal Server Error`: Unexpected error during processing (e.g., LLM API issue).

## Client Integration Guide

To use the modular API effectively, clients should follow this sequential workflow:

1. **Step 1:** Call `/mark_similarity` with the applicant and opponent marks.
2. **Step 2:** For each pair of goods/services, make concurrent calls to `/gs_similarity`, passing:
   - One applicant good/service
   - One opponent good/service
   - The mark similarity result from Step 1
3. **Step 3:** Once all `/gs_similarity` calls have completed, call `/case_prediction` with:
   - The mark similarity result from Step 1
   - An array of all goods/services likelihood results from Step 2

This approach provides several benefits:
- More focused LLM prompts that better follow UK/EU legal reasoning
- Ability to process multiple goods/services pairs concurrently
- More detailed reasoning about likelihood of confusion for each specific goods/services pair

## Project Structure

```
trademark_prod/
├── .gcloudignore           # Files ignored by gcloud CLI deployments
├── .gitignore              # Files ignored by Git
├── .pytest_cache/          # pytest cache
├── .ruff_cache/            # Ruff linter cache
├── .env.yaml               # Environment variables for cloud deployment (sensitive)
├── env.example             # Template for environment variables
├── api/
│   ├── __init__.py
│   ├── auth.py             # Firebase Authentication dependency logic
│   ├── main.py             # FastAPI app definition, CORS, health endpoint
│   └── routes/             # API routes organized in modules
│       ├── __init__.py
│       ├── mark_similarity.py  # /mark_similarity endpoint 
│       ├── gs_similarity.py    # /gs_similarity endpoint
│       └── case_prediction.py  # /case_prediction endpoint
├── trademark_core/
│   ├── __init__.py
│   ├── llm.py              # Gemini LLM interaction logic, structured output generation
│   ├── models.py           # Pydantic models (SSoT for API schemas & internal data)
│   ├── prompts.py          # Central store for LLM prompt templates
│   └── similarity.py       # Visual, Aural similarity calculation logic
├── tests/                  # Automated tests
│   ├── __init__.py
│   └── # ... test files ...
├── main.py                 # Cloud Functions entry point (imports app from api.main)
├── pyproject.toml          # Project metadata & dependencies (Poetry or similar)
├── requirements.txt        # Project dependencies (pip format)
└── README.md               # This file
```

### Key File Descriptions

*   **`README.md`**: Project overview, API usage, setup instructions.
*   **`main.py` (root)**: Entry point for Google Cloud Functions.
*   **`api/main.py`**: Defines the FastAPI application, middleware (CORS), authentication dependency (`api/auth.py`), and the `/health` endpoint.
*   **`api/routes/`**: Contains modular endpoint implementations for each API route.
*   **`api/auth.py`**: Handles Firebase ID token verification logic for securing endpoints.
*   **`trademark_core/models.py`**: **Single Source of Truth (SSoT)** for all data structures using Pydantic. Defines the exact request and response schemas for all API endpoints.
*   **`trademark_core/similarity.py`**: Contains functions to calculate visual and aural similarity scores.
*   **`trademark_core/llm.py`**: Manages interaction with the Google Vertex AI Gemini model. Uses prompts from `prompts.py`, sends requests, parses structured JSON responses, and handles LLM API errors. Contains modular LLM generation functions for mark similarity and goods/services assessments.
*   **`trademark_core/prompts.py`**: Stores all prompt templates used to interact with the Gemini LLM, organized by endpoint.
*   **`tests/`**: Contains unit and integration tests.
*   **`pyproject.toml` / `requirements.txt`**: Define project dependencies.
*   **`.env.example` / `.env.yaml`**: Template and actual configuration for environment variables (GCP Project ID, API keys, etc.). **Sensitive files should not be committed to Git.**

## Local Development (For Contributors)

1.  **Prerequisites:**
    *   Python 3.11
    *   Git
    *   Access to a Google Cloud Project with Vertex AI enabled.
    *   Firebase Project set up for authentication.
    *   `gcloud` CLI installed and authenticated (`gcloud auth application-default login`).
2.  **Clone:**
    ```bash
    git clone <repository-url>
    cd trademark_prod
    ```
3.  **Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate # Linux/macOS
    # venv\Scripts\activate # Windows
    ```
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Environment Variables:**
    *   Copy `env.example` to a new file named `.env` (this file is gitignored).
    *   Fill in the required values in `.env`, especially:
        *   `GOOGLE_CLOUD_PROJECT`: Your GCP Project ID.
        *   `GOOGLE_CLOUD_LOCATION`: The region for Vertex AI (e.g., `us-central1`).
    *   Ensure your environment is configured for Application Default Credentials (ADC) by running `gcloud auth application-default login`.
6.  **Run Tests:**
    ```bash
    pytest
    ```
7.  **Linting/Formatting:**
    ```bash
    ruff check .
    ruff format .
    ```
8.  **Run Server Locally:**
    *   Ensure environment variables from `.env` are loaded (e.g., using `python-dotenv` implicitly via FastAPI/Uvicorn or exporting them manually).
    ```bash
    # Requires uvicorn installed (pip install uvicorn)
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
    ```
    *   The server will be available at `http://localhost:8000`. You'll need a valid Firebase ID token to test the `/predict` endpoint locally (e.g., obtained from a test frontend).

## Deployment

This application is designed for deployment to Google Cloud Functions (or potentially Cloud Run).

-   Ensure `requirements.txt` is up-to-date.
-   Use the `gcloud functions deploy` command, specifying the entry point (`app` from `main.py`), runtime, region, and necessary environment variables (can be set via `.env.yaml` or command-line flags).
-   Configure appropriate IAM permissions for the function's service account to access Vertex AI.

Refer to Google Cloud Functions documentation for detailed deployment steps.

## Development and Testing

### Setup

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and set appropriate values

### Running Tests

The project includes a comprehensive test suite. Tests can be run in two modes:

#### With Mocks (Default)

For quick development feedback, tests use mocks by default instead of making real LLM API calls:

```bash
# Run all tests with mocks
pytest

# Run specific tests
pytest tests/test_batch_gs_processing.py

# Run with coverage information
pytest --cov=trademark_core --cov=api 
```

#### With Real LLM Calls

Following the testing strategy, the project supports tests with real LLM calls to Vertex AI for higher fidelity validation:

```bash
# First, ensure you have the necessary environment variables set:
# - GOOGLE_CLOUD_PROJECT
# - GOOGLE_CLOUD_LOCATION (default: us-central1)
# - GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)

# Run all real LLM tests
python tests/run_real_llm_tests.py

# Run specific test file with real LLM calls
python tests/run_real_llm_tests.py tests/test_real_llm_integration.py

# Run all tests with real LLM calls (may be slow)
python tests/run_real_llm_tests.py tests/
```

Or you can set the environment variable manually:

```bash
# Disable mocks and run tests directly
USE_LLM_MOCKS=0 pytest tests/test_real_llm_integration.py

# With additional options
USE_LLM_MOCKS=0 pytest -v tests/test_real_llm_integration.py::test_real_mark_similarity_identical
```

> **Note**: Running tests with real LLM calls requires valid Vertex AI credentials and will consume API quota. Tests may also run slower due to network latency and rate limiting.

### Model Parameter Testing

Tests for the model parameter functionality are available, allowing you to verify that different models can be specified:

```bash
# Run model parameter tests with mocks
pytest tests/test_model_parameter.py

# Run model parameter tests with real LLM calls
python tests/run_real_llm_tests.py tests/test_model_parameter.py
```

