"""
Mock implementations for external services used in tests.

This module provides mock versions of external service functions to avoid
making actual API calls during testing.
"""

from typing import Any
from unittest.mock import patch

from pydantic import ValidationError

from trademark_core import models


# Utility: If a mock is called with side_effect, raise it
async def maybe_raise_side_effect(mock_self, *args, **kwargs):
    side_effect = getattr(mock_self, "side_effect", None)
    if side_effect is not None:
        if isinstance(side_effect, Exception):
            raise side_effect
        elif callable(side_effect):
            result = side_effect(*args, **kwargs)
            if isinstance(result, Exception):
                raise result
            return result
    return None


class MockLLM:
    """
    Mock implementation of LLM services for testing.
    This class provides predefined responses for LLM calls to avoid
    actual API calls during testing.

    All mock responses are validated against the Pydantic models from models.py
    to ensure strict adherence to the data models.
    """

    @staticmethod
    async def mock_mark_similarity_assessment(
        applicant_mark: models.Mark,
        opponent_mark: models.Mark,
        visual_score: float,
        aural_score: float,
        model: str = None,
    ) -> models.MarkSimilarityOutput:
        """
        Mock implementation of generate_mark_similarity_assessment.
        Returns a validated MarkSimilarityOutput based on input marks.
        """
        print(
            f"Mock LLM called for marks: '{applicant_mark.wordmark}' vs '{opponent_mark.wordmark}', model: {model or 'default'}"
        )

        # Validate input models
        if not isinstance(applicant_mark, models.Mark):
            raise TypeError(
                f"applicant_mark must be a models.Mark instance, got {type(applicant_mark)}"
            )
        if not isinstance(opponent_mark, models.Mark):
            raise TypeError(
                f"opponent_mark must be a models.Mark instance, got {type(opponent_mark)}"
            )

        # Validate score ranges
        if not (0 <= visual_score <= 1):
            raise ValueError(f"visual_score must be between 0 and 1, got {visual_score}")
        if not (0 <= aural_score <= 1):
            raise ValueError(f"aural_score must be between 0 and 1, got {aural_score}")

        # Check for side_effect on the mock
        import inspect

        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame)
        for f in outer:
            local_self = f.frame.f_locals.get("self")
            if hasattr(local_self, "side_effect"):
                maybe = await maybe_raise_side_effect(
                    local_self, applicant_mark, opponent_mark, visual_score, aural_score, model
                )
                if maybe is not None:
                    return maybe

        # Define response based on inputs
        response = None

        # If identical marks, return "identical" for all categories
        if applicant_mark.wordmark.lower() == opponent_mark.wordmark.lower():
            response = models.MarkSimilarityOutput(
                visual="identical",
                aural="identical",
                conceptual="identical",
                overall="identical",
                reasoning="The marks are identical in all aspects.",
            )

        # If very different marks
        elif (
            "ZOOPLANKTON" in applicant_mark.wordmark
            and "BUTTERFLY" in opponent_mark.wordmark
            or "BUTTERFLY" in applicant_mark.wordmark
            and "ZOOPLANKTON" in opponent_mark.wordmark
        ):
            response = models.MarkSimilarityOutput(
                visual="dissimilar",
                aural="dissimilar",
                conceptual="low",
                overall="dissimilar",
                reasoning="The marks are very different in appearance and sound.",
            )

        # Default: moderate similarity for most cases
        else:
            response = models.MarkSimilarityOutput(
                visual="moderate",
                aural="moderate",
                conceptual="moderate",
                overall="moderate",
                reasoning="The marks share some similarities but have distinguishing features.",
            )

        # Validate response against the expected model
        try:
            return models.MarkSimilarityOutput.model_validate(response.model_dump())
        except ValidationError as e:
            print(f"Mock validation error: {e}")
            raise

    @staticmethod
    async def mock_gs_likelihood_assessment(
        applicant_good: models.GoodService,
        opponent_good: models.GoodService,
        mark_similarity: models.MarkSimilarityOutput,
        model: str = None,
    ) -> models.GoodServiceLikelihoodOutput:
        """
        Mock implementation of generate_gs_likelihood_assessment.
        Returns a validated GoodServiceLikelihoodOutput based on input goods/services.
        """
        print(
            f"Mock G/S assessment called: '{applicant_good.term}' vs '{opponent_good.term}', model: {model or 'default'}"
        )

        # Validate input models
        if not isinstance(applicant_good, models.GoodService):
            raise TypeError(
                f"applicant_good must be a models.GoodService instance, got {type(applicant_good)}"
            )
        if not isinstance(opponent_good, models.GoodService):
            raise TypeError(
                f"opponent_good must be a models.GoodService instance, got {type(opponent_good)}"
            )
        if not isinstance(mark_similarity, models.MarkSimilarityOutput):
            raise TypeError(
                f"mark_similarity must be a models.MarkSimilarityOutput instance, got {type(mark_similarity)}"
            )

        # Check for side_effect on the mock
        import inspect

        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame)
        for f in outer:
            local_self = f.frame.f_locals.get("self")
            if hasattr(local_self, "side_effect"):
                maybe = await maybe_raise_side_effect(
                    local_self, applicant_good, opponent_good, mark_similarity, model
                )
                if maybe is not None:
                    return maybe

        # Define response based on inputs
        response = None

        # Identical legal software case for full workflow test
        if (
            "Identical legal software" in applicant_good.term
            and "Identical legal software" in opponent_good.term
        ):
            response = models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.95,
                likelihood_of_confusion=True,
                confusion_type="direct",
            )

        # Identical goods case
        elif (
            applicant_good.term.lower() == opponent_good.term.lower()
            and applicant_good.nice_class == opponent_good.nice_class
        ):
            # Identical goods with high/identical mark similarity -> confusion
            if mark_similarity.overall in ["high", "identical"]:
                response = models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.95,
                    likelihood_of_confusion=True,
                    confusion_type="direct",
                )
            else:
                # Identical goods but without high mark similarity
                response = models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.8,
                    likelihood_of_confusion=mark_similarity.overall
                    in ["moderate", "high", "identical"],
                    confusion_type="indirect"
                    if mark_similarity.overall == "moderate"
                    else "direct",
                )

        # Dissimilar goods case - specifically for Live plants vs Vehicles
        elif ("Live plants" in applicant_good.term and "Vehicles" in opponent_good.term) or (
            "Vehicles" in applicant_good.term and "Live plants" in opponent_good.term
        ):
            response = models.GoodServiceLikelihoodOutput(
                are_competitive=False,
                are_complementary=False,
                similarity_score=0.1,
                likelihood_of_confusion=False,
                confusion_type=None,
            )

        # Same nice class but different terms -> competitive
        elif applicant_good.nice_class == opponent_good.nice_class:
            response = models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=mark_similarity.overall
                in ["moderate", "high", "identical"],
                confusion_type="indirect" if mark_similarity.overall == "moderate" else "direct",
            )

        # Default: different nice classes -> non-competitive, no confusion
        else:
            response = models.GoodServiceLikelihoodOutput(
                are_competitive=False,
                are_complementary=True,
                similarity_score=0.3,
                likelihood_of_confusion=False,
                confusion_type=None,
            )

        # Make sure confusion_type is None when likelihood_of_confusion is False
        if not response.likelihood_of_confusion and response.confusion_type is not None:
            response.confusion_type = None

        # Validate response against the expected model
        try:
            return models.GoodServiceLikelihoodOutput.model_validate(response.model_dump())
        except ValidationError as e:
            print(f"Mock validation error: {e}")
            raise

    @staticmethod
    async def mock_structured_content(
        prompt: str,
        schema: type[Any],
        temperature: float = 0.2,
        top_p: float = 0.95,
        top_k: int = 40,
        max_output_tokens: int = 8192,
        request_context: str = "",
        model: str = None,
        **kwargs,
    ) -> Any:
        """
        Mock implementation of generate_structured_content.
        Returns a validated instance of the requested schema based on the prompt content.
        """
        # Validate required inputs
        if not isinstance(prompt, str):
            raise TypeError(f"prompt must be a string, got {type(prompt)}")

        response = None

        # Check for side_effect on the mock
        import inspect

        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame)
        for f in outer:
            local_self = f.frame.f_locals.get("self")
            if hasattr(local_self, "side_effect"):
                maybe = await maybe_raise_side_effect(
                    local_self,
                    prompt,
                    schema,
                    temperature,
                    top_p,
                    top_k,
                    max_output_tokens,
                    request_context,
                    model,
                    **kwargs,
                )
                if maybe is not None:
                    return maybe

        # Extract marks from the prompt for MarkSimilarityOutput
        if schema == models.MarkSimilarityOutput:
            # Special handling based on prompt content
            if "IDENTICAL" in prompt and "IDENTICAL" in prompt:
                # Identical marks case specifically for the full workflow test
                response = models.MarkSimilarityOutput(
                    visual="identical",
                    aural="identical",
                    conceptual="identical",
                    overall="identical",
                    reasoning="The marks are identical in all aspects.",
                )
            elif "EXAMPLIA" in prompt and "EXAMPLIA" in prompt:
                # Identical marks case
                response = models.MarkSimilarityOutput(
                    visual="identical",
                    aural="identical",
                    conceptual="identical",
                    overall="identical",
                    reasoning="The marks are identical in all aspects.",
                )
            elif "ZOOPLANKTON" in prompt and "BUTTERFLY" in prompt:
                # Dissimilar marks case
                response = models.MarkSimilarityOutput(
                    visual="dissimilar",
                    aural="dissimilar",
                    conceptual="low",
                    overall="dissimilar",
                    reasoning="The marks are very different in appearance and sound.",
                )
            else:
                # Default case - moderate similarity
                response = models.MarkSimilarityOutput(
                    visual="moderate",
                    aural="moderate",
                    conceptual="moderate",
                    overall="moderate",
                    reasoning="This is a mock response for testing.",
                )

            # Validate against schema
            try:
                return models.MarkSimilarityOutput.model_validate(response.model_dump())
            except ValidationError as e:
                print(f"Mock validation error for MarkSimilarityOutput: {e}")
                raise

        elif schema == models.GoodServiceLikelihoodOutput:
            # Special handling based on prompt content
            if "Identical legal software" in prompt:
                # Identical legal software case for full workflow test
                response = models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.95,
                    likelihood_of_confusion=True,
                    confusion_type="direct",
                )
            elif "Legal software" in prompt and "Legal software" in prompt:
                # Identical goods case
                response = models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.95,
                    likelihood_of_confusion=True,
                    confusion_type="direct",
                )
            elif "Cloud computing" in prompt and "Cloud computing" in prompt:
                # Identical goods case for full workflow test
                response = models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.95,
                    likelihood_of_confusion=True,
                    confusion_type="direct",
                )
            elif "Live plants" in prompt and "Vehicles" in prompt:
                # Dissimilar goods case
                response = models.GoodServiceLikelihoodOutput(
                    are_competitive=False,
                    are_complementary=False,
                    similarity_score=0.1,
                    likelihood_of_confusion=False,
                    confusion_type=None,
                )
            else:
                # Default case
                response = models.GoodServiceLikelihoodOutput(
                    are_competitive=True,
                    are_complementary=False,
                    similarity_score=0.7,
                    likelihood_of_confusion=True,
                    confusion_type="direct",
                )

            # Validate against schema
            try:
                return models.GoodServiceLikelihoodOutput.model_validate(response.model_dump())
            except ValidationError as e:
                print(f"Mock validation error for GoodServiceLikelihoodOutput: {e}")
                raise

        elif schema == models.ConceptualSimilarityScore:
            response = models.ConceptualSimilarityScore(score=0.5)

            # Validate against schema
            try:
                return models.ConceptualSimilarityScore.model_validate(response.model_dump())
            except ValidationError as e:
                print(f"Mock validation error for ConceptualSimilarityScore: {e}")
                raise

        elif schema == models.OppositionOutcome:
            # Create a mock opposition outcome
            response = models.OppositionOutcome(
                result="Opposition may partially succeed",
                confidence=0.75,
                reasoning="This is a mock opposition outcome for testing purposes.",
            )

            # Validate against schema
            try:
                return models.OppositionOutcome.model_validate(response.model_dump())
            except ValidationError as e:
                print(f"Mock validation error for OppositionOutcome: {e}")
                raise

        elif schema == models.CasePredictionResult:
            # Create a basic mock case prediction result
            # This would need more complex logic to be realistic
            mark_sim = models.MarkSimilarityOutput(
                visual="moderate",
                aural="moderate",
                conceptual="moderate",
                overall="moderate",
                reasoning="Mock similarity assessment.",
            )

            gs_likelihood = models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=True,
                confusion_type="direct",
            )

            opposition = models.OppositionOutcome(
                result="Opposition may partially succeed",
                confidence=0.75,
                reasoning="Mock opposition reasoning.",
            )

            response = models.CasePredictionResult(
                mark_comparison=mark_sim,
                goods_services_likelihoods=[gs_likelihood],
                opposition_outcome=opposition,
            )

            # Validate against schema
            try:
                return models.CasePredictionResult.model_validate(response.model_dump())
            except ValidationError as e:
                print(f"Mock validation error for CasePredictionResult: {e}")
                raise
        else:
            # If we don't know how to handle this schema, try to create an empty instance
            try:
                # Try to create an instance of the schema with default values
                response = schema()
                # Try to validate it if it's a Pydantic model
                if hasattr(schema, "model_validate") and callable(schema.model_validate):
                    return schema.model_validate(response.model_dump())
                return response
            except Exception as e:
                print(f"Failed to create mock for unknown schema {schema}: {e}")
                raise ValueError(f"Cannot create mock for unknown schema: {schema}")

    @staticmethod
    async def mock_conceptual_similarity_score(
        applicant_mark: str, opponent_mark: str, model: str = None
    ) -> float:
        """
        Mock implementation of _get_conceptual_similarity_score_from_llm.
        Returns a float score between 0.0 and 1.0.
        """
        print(
            f"Mock conceptual similarity called: '{applicant_mark}' vs '{opponent_mark}', model: {model or 'default'}"
        )

        # Validate input
        if not isinstance(applicant_mark, str):
            raise TypeError(f"applicant_mark must be a string, got {type(applicant_mark)}")
        if not isinstance(opponent_mark, str):
            raise TypeError(f"opponent_mark must be a string, got {type(opponent_mark)}")

        # Check for side_effect on the mock
        import inspect

        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame)
        for f in outer:
            local_self = f.frame.f_locals.get("self")
            if hasattr(local_self, "side_effect"):
                maybe = await maybe_raise_side_effect(
                    local_self, applicant_mark, opponent_mark, model
                )
                if maybe is not None:
                    return maybe

        # Logic for different score scenarios
        if applicant_mark.lower() == opponent_mark.lower():
            # Identical marks
            return 1.0
        elif (
            "ZOOPLANKTON" in applicant_mark
            and "BUTTERFLY" in opponent_mark
            or "BUTTERFLY" in applicant_mark
            and "ZOOPLANKTON" in opponent_mark
        ):
            # Very different concepts (but still some connection - both living organisms)
            return 0.2
        else:
            # Default moderate similarity
            return 0.5


def apply_llm_mocks():
    """
    Patch all LLM-related functions for testing.

    This function applies patches to all the LLM functions that would normally
    call external APIs to instead use mock implementations that respect side_effect.
    """
    # Path to the llm module to be patched
    llm_module_path = "trademark_core.llm"

    # Apply patches directly to the module functions
    patch(
        f"{llm_module_path}.generate_mark_similarity_assessment",
        MockLLM.mock_mark_similarity_assessment,
    ).start()

    patch(
        f"{llm_module_path}.generate_gs_likelihood_assessment",
        MockLLM.mock_gs_likelihood_assessment,
    ).start()

    patch(f"{llm_module_path}.generate_structured_content", MockLLM.mock_structured_content).start()

    patch(
        f"{llm_module_path}._get_conceptual_similarity_score_from_llm",
        MockLLM.mock_conceptual_similarity_score,
    ).start()

    print("Applied LLM mocks for testing")


# The tear down for mocks should be handled by pytest fixtures (see conftest.py)


# Example of how a test might use these mocks with side_effect:
#
# @pytest.mark.asyncio
# async def test_something_with_api_error():
#     # Assume mocks are applied by a fixture
#     # Get the patched mock object
#     from trademark_core.llm import generate_mark_similarity_assessment as real_func
#     patched_func = real_func # In a patched context, this will be the mock
#
#     # Set the side_effect on the patched mock object
#     patched_func.side_effect = GoogleAPIError("Simulated API error")
#
#     with pytest.raises(GoogleAPIError):
#          await real_func(...)
#
#     patched_func.assert_awaited_once()
