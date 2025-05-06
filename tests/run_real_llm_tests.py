#!/usr/bin/env python
"""
Utility script to run tests with real LLM calls instead of mocks.

This script sets the USE_LLM_MOCKS environment variable to "0" before
running pytest, which will cause the tests to use real LLM calls to Vertex AI.

Usage:
    python tests/run_real_llm_tests.py [pytest_args]

Examples:
    # Run all tests with real LLM calls:
    python tests/run_real_llm_tests.py

    # Run a specific test file:
    python tests/run_real_llm_tests.py tests/test_real_llm_integration.py

    # Run with extra verbosity:
    python tests/run_real_llm_tests.py -v
"""

import os
import subprocess
import sys


def main():
    # Set environment variable to disable mocks
    os.environ["USE_LLM_MOCKS"] = "0"

    # Ensure we have Vertex AI credentials
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        print("ERROR: Missing GOOGLE_CLOUD_PROJECT environment variable")
        print("Please set the required Vertex AI credentials before running this script:")
        print("  - GOOGLE_CLOUD_PROJECT")
        print("  - GOOGLE_CLOUD_LOCATION (default: us-central1)")
        print("  - GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)")
        sys.exit(1)

    # Get command line arguments to pass to pytest
    pytest_args = sys.argv[1:] if len(sys.argv) > 1 else []

    # Default to test_real_llm_integration.py if no specific tests specified
    if not any(arg.startswith("tests/") for arg in pytest_args):
        pytest_args.append("tests/test_real_llm_integration.py")

    # Build the command with appropriate arguments
    cmd = ["pytest"] + pytest_args

    print(f"Running tests with real LLM calls: {' '.join(cmd)}")
    print("------------------------------------------------------------")

    # Run pytest with the specified arguments
    result = subprocess.run(cmd)

    # Return the exit code from pytest
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
