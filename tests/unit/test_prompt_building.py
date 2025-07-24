"""
Unit tests for prompt building functionality in trademark_core.llm.

These tests validate that prompts are correctly built with template variables
filled in and few-shot examples properly appended before being sent to the LLM.
"""

import pytest
import re
from pathlib import Path
from unittest.mock import patch, mock_open

from trademark_core import llm, models
from tests.utils.fixtures import (
    IDENTICAL_MARKS,
    SIMILAR_MARKS,
    MODERATE_SIMILARITY_ASSESSMENT,
)


class TestPromptLoading:
    """Test cases for prompt and examples loading functions."""

    def test_load_prompt_from_file_success(self):
        """Test successful loading of prompt template from file."""
        mock_content = "# Test Prompt\n\nThis is a test prompt with {variable}."
        
        with patch("builtins.open", mock_open(read_data=mock_content)):
            result = llm._load_prompt_from_file("test_prompt")
            
        assert result == mock_content

    def test_load_prompt_from_file_not_found(self):
        """Test handling of missing prompt file."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                llm._load_prompt_from_file("nonexistent_prompt")

    def test_load_examples_from_file_success(self):
        """Test successful loading of examples from file."""
        mock_content = "<few_shot_examples>\nExample 1\nExample 2\n</few_shot_examples>"
        
        with patch("builtins.open", mock_open(read_data=mock_content)):
            result = llm._load_examples_from_file("test_examples")
            
        assert result == mock_content

    def test_load_examples_from_file_not_found(self):
        """Test handling of missing examples file."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                llm._load_examples_from_file("nonexistent_examples")


class TestPromptCombination:
    """Test cases for combining prompts with examples."""

    def test_combine_prompt_with_examples_success(self):
        """Test successful combination of prompt template with examples."""
        prompt_template = "This is a prompt template.\n\nInstructions here."
        examples_content = """
Some content before examples.

<few_shot_examples>
Example 1: Input -> Output
Example 2: Input -> Output
</few_shot_examples>

Some content after examples.
"""
        
        result = llm._combine_prompt_with_examples(prompt_template, examples_content)
        
        # Should contain the original prompt
        assert "This is a prompt template." in result
        assert "Instructions here." in result
        
        # Should contain the examples section
        assert "<few_shot_examples>" in result
        assert "Example 1: Input -> Output" in result
        assert "Example 2: Input -> Output" in result
        
        # Should not contain content outside the examples tags
        assert "Some content before examples." not in result
        assert "Some content after examples." not in result

    def test_combine_prompt_with_examples_no_tags(self):
        """Test combination when examples file has no few_shot_examples tags."""
        prompt_template = "This is a prompt template."
        examples_content = "Just some content without proper tags."
        
        result = llm._combine_prompt_with_examples(prompt_template, examples_content)
        
        # Should return just the original prompt when no examples tags found
        assert result == prompt_template

    def test_combine_prompt_with_examples_multiline(self):
        """Test combination with multiline examples content."""
        prompt_template = "Prompt template"
        examples_content = """
<few_shot_examples>
Example 1:
  Input: Test input
  Output: Test output

Example 2:
  Input: Another input
  Output: Another output
</few_shot_examples>
"""
        
        result = llm._combine_prompt_with_examples(prompt_template, examples_content)
        
        # Should preserve multiline structure within examples
        assert "Example 1:" in result
        assert "  Input: Test input" in result
        assert "  Output: Test output" in result


class TestMarkSimilarityPromptBuilding:
    """Test cases for mark similarity prompt building."""

    @patch('trademark_core.llm.generate_structured_content')
    @patch('trademark_core.llm._combine_prompt_with_examples')
    async def test_mark_similarity_prompt_variable_substitution(self, mock_combine, mock_generate):
        """Test that mark similarity prompt has all variables properly substituted."""
        # Setup mocks
        mock_template = "Applicant: {applicant_wordmark}, Opponent: {opponent_wordmark}, Visual: {visual_score}, Aural: {aural_score}"
        mock_combine.return_value = mock_template
        mock_generate.return_value = models.MarkSimilarityOutput(
            visual="moderate", aural="moderate", conceptual="moderate", overall="moderate"
        )
        
        # Test data
        applicant_mark = models.Mark(wordmark="TESTMARK")
        opponent_mark = models.Mark(wordmark="TESTMARK2")
        visual_score = 0.75
        aural_score = 0.65
        
        # Call the function
        await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=visual_score,
            aural_score=aural_score
        )
        
        # Verify that generate_structured_content was called with properly substituted prompt
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        actual_prompt = call_args[1]['prompt']  # Get the prompt from kwargs
        
        # Verify all variables were substituted
        assert "TESTMARK" in actual_prompt
        assert "TESTMARK2" in actual_prompt
        assert "0.75" in actual_prompt
        assert "0.65" in actual_prompt
        
        # Verify no template variables remain
        assert "{applicant_wordmark}" not in actual_prompt
        assert "{opponent_wordmark}" not in actual_prompt
        assert "{visual_score}" not in actual_prompt
        assert "{aural_score}" not in actual_prompt

    @patch('trademark_core.llm.generate_structured_content')
    async def test_mark_similarity_prompt_includes_examples(self, mock_generate):
        """Test that mark similarity prompt includes examples from the examples file."""
        mock_generate.return_value = models.MarkSimilarityOutput(
            visual="moderate", aural="moderate", conceptual="moderate", overall="moderate"
        )
        
        # Call the function
        await llm.generate_mark_similarity_assessment(
            applicant_mark=models.Mark(wordmark="TEST"),
            opponent_mark=models.Mark(wordmark="TEST2"),
            visual_score=0.5,
            aural_score=0.5
        )
        
        # Get the actual prompt that was sent
        call_args = mock_generate.call_args
        actual_prompt = call_args[1]['prompt']
        
        # Verify examples are included (should contain few_shot_examples tags)
        assert "<few_shot_examples>" in actual_prompt
        assert "</few_shot_examples>" in actual_prompt


class TestGsLikelihoodPromptBuilding:
    """Test cases for goods/services likelihood prompt building."""

    @patch('trademark_core.llm.generate_structured_content')
    @patch('trademark_core.llm._combine_prompt_with_examples')
    async def test_gs_likelihood_prompt_variable_substitution(self, mock_combine, mock_generate):
        """Test that G/S likelihood prompt has all variables properly substituted."""
        # Setup mocks
        mock_template = """
        Applicant: {applicant_term} (Class {applicant_nice_class})
        Opponent: {opponent_term} (Class {opponent_nice_class})
        Mark similarity - Visual: {mark_visual}, Aural: {mark_aural}, 
        Conceptual: {mark_conceptual}, Overall: {mark_overall}
        """
        mock_combine.return_value = mock_template
        mock_generate.return_value = models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.8,
            likelihood_of_confusion=True,
            confusion_type="direct"
        )
        
        # Test data
        applicant_good = models.GoodService(term="Software applications", nice_class=9)
        opponent_good = models.GoodService(term="Computer programs", nice_class=9)
        mark_similarity = models.MarkSimilarityOutput(
            visual="high", aural="moderate", conceptual="low", overall="moderate"
        )
        
        # Call the function
        await llm.generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        
        # Verify that generate_structured_content was called with properly substituted prompt
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        actual_prompt = call_args[1]['prompt']
        
        # Verify all variables were substituted
        assert "Software applications" in actual_prompt
        assert "Computer programs" in actual_prompt
        assert "9" in actual_prompt  # Nice class
        assert "high" in actual_prompt  # Visual similarity
        assert "moderate" in actual_prompt  # Aural and overall similarity
        assert "low" in actual_prompt  # Conceptual similarity
        
        # Verify no template variables remain
        assert "{applicant_term}" not in actual_prompt
        assert "{opponent_term}" not in actual_prompt
        assert "{applicant_nice_class}" not in actual_prompt
        assert "{opponent_nice_class}" not in actual_prompt
        assert "{mark_visual}" not in actual_prompt
        assert "{mark_aural}" not in actual_prompt
        assert "{mark_conceptual}" not in actual_prompt
        assert "{mark_overall}" not in actual_prompt


class TestCasePredictionPromptBuilding:
    """Test cases for case prediction prompt building."""

    @patch('trademark_core.llm.generate_structured_content')
    async def test_case_prediction_prompt_includes_statistics(self, mock_generate):
        """Test that case prediction prompt includes calculated statistics."""
        mock_generate.return_value = models.OppositionOutcome(
            result="Opposition likely to succeed",
            confidence=0.85,
            reasoning="Test reasoning"
        )
        
        # Test data with multiple G/S likelihoods
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        gs_likelihoods = [
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.9,
                likelihood_of_confusion=True,
                confusion_type="direct"
            ),
            models.GoodServiceLikelihoodOutput(
                are_competitive=False,
                are_complementary=True,
                similarity_score=0.3,
                likelihood_of_confusion=False,
                confusion_type=None
            ),
            models.GoodServiceLikelihoodOutput(
                are_competitive=True,
                are_complementary=False,
                similarity_score=0.7,
                likelihood_of_confusion=True,
                confusion_type="indirect"
            )
        ]
        
        # Call the function
        await llm.generate_case_prediction(
            mark_similarity=mark_similarity,
            goods_services_likelihoods=gs_likelihoods
        )
        
        # Get the actual prompt that was sent
        call_args = mock_generate.call_args
        actual_prompt = call_args[1]['prompt']
        
        # Verify statistics are calculated and included
        assert "Total G/S pairs analyzed: 3" in actual_prompt
        assert "Pairs with likelihood of confusion: 2 (66.7%)" in actual_prompt
        assert "Direct confusion instances: 1" in actual_prompt
        assert "Indirect confusion instances: 1" in actual_prompt
        assert "Average G/S similarity score: 0.63" in actual_prompt
        
        # Verify mark similarity context is included
        assert mark_similarity.visual in actual_prompt
        assert mark_similarity.aural in actual_prompt
        assert mark_similarity.conceptual in actual_prompt
        assert mark_similarity.overall in actual_prompt


class TestConceptualSimilarityPromptBuilding:
    """Test cases for conceptual similarity prompt building."""

    @patch('trademark_core.llm.generate_structured_content')
    async def test_conceptual_similarity_prompt_variable_substitution(self, mock_generate):
        """Test that conceptual similarity prompt has variables properly substituted."""
        mock_generate.return_value = models.ConceptualSimilarityScore(score=0.7)
        
        # Call the function
        await llm._get_conceptual_similarity_score_from_llm("MOUNTAIN", "HILL")
        
        # Get the actual prompt that was sent
        call_args = mock_generate.call_args
        actual_prompt = call_args[1]['prompt']
        
        # Verify variables were substituted
        assert "MOUNTAIN" in actual_prompt
        assert "HILL" in actual_prompt
        
        # Verify no template variables remain
        assert "{mark1}" not in actual_prompt
        assert "{mark2}" not in actual_prompt


class TestPromptStructureValidation:
    """Test cases for validating prompt structure and content."""

    @patch('trademark_core.llm.generate_structured_content')
    async def test_prompt_contains_required_sections(self, mock_generate):
        """Test that generated prompts contain required sections for proper LLM guidance."""
        mock_generate.return_value = models.MarkSimilarityOutput(
            visual="moderate", aural="moderate", conceptual="moderate", overall="moderate"
        )
        
        # Call the function
        await llm.generate_mark_similarity_assessment(
            applicant_mark=models.Mark(wordmark="TEST"),
            opponent_mark=models.Mark(wordmark="TEST2"),
            visual_score=0.5,
            aural_score=0.5
        )
        
        # Get the actual prompt
        call_args = mock_generate.call_args
        actual_prompt = call_args[1]['prompt']
        
        # Verify prompt contains key structural elements
        assert "Role Definition" in actual_prompt or "## Role" in actual_prompt
        assert "Task Overview" in actual_prompt or "## Task" in actual_prompt
        assert "Input Data" in actual_prompt or "## Input" in actual_prompt
        assert "Output Requirements" in actual_prompt or "## Output" in actual_prompt
        
        # Verify JSON schema guidance is present
        assert "JSON" in actual_prompt
        assert "schema" in actual_prompt.lower()

    @patch('trademark_core.llm.generate_structured_content')
    async def test_prompt_json_structure_not_broken(self, mock_generate):
        """Test that variable substitution doesn't break JSON structure in prompts."""
        mock_generate.return_value = models.GoodServiceLikelihoodOutput(
            are_competitive=True,
            are_complementary=False,
            similarity_score=0.8,
            likelihood_of_confusion=True,
            confusion_type="direct"
        )
        
        # Test with goods that might contain special characters
        applicant_good = models.GoodService(term="Software & applications", nice_class=9)
        opponent_good = models.GoodService(term="Computer programs (downloadable)", nice_class=9)
        mark_similarity = MODERATE_SIMILARITY_ASSESSMENT
        
        # Call the function
        await llm.generate_gs_likelihood_assessment(
            applicant_good=applicant_good,
            opponent_good=opponent_good,
            mark_similarity=mark_similarity
        )
        
        # Get the actual prompt
        call_args = mock_generate.call_args
        actual_prompt = call_args[1]['prompt']
        
        # Verify that special characters are properly handled
        assert "Software & applications" in actual_prompt
        assert "Computer programs (downloadable)" in actual_prompt
        
        # Verify JSON structure indicators are still present
        assert "{" in actual_prompt
        assert "}" in actual_prompt


class TestPromptConsistency:
    """Test cases for ensuring prompt consistency across different calls."""

    @patch('trademark_core.llm.generate_structured_content')
    async def test_identical_inputs_produce_identical_prompts(self, mock_generate):
        """Test that identical inputs always produce identical prompts."""
        mock_generate.return_value = models.MarkSimilarityOutput(
            visual="moderate", aural="moderate", conceptual="moderate", overall="moderate"
        )
        
        # Test data
        applicant_mark = models.Mark(wordmark="CONSISTENT")
        opponent_mark = models.Mark(wordmark="CONSISTENT2")
        visual_score = 0.8
        aural_score = 0.7
        
        # Call the function twice with identical inputs
        await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=visual_score,
            aural_score=aural_score
        )
        first_prompt = mock_generate.call_args[1]['prompt']
        
        mock_generate.reset_mock()
        
        await llm.generate_mark_similarity_assessment(
            applicant_mark=applicant_mark,
            opponent_mark=opponent_mark,
            visual_score=visual_score,
            aural_score=aural_score
        )
        second_prompt = mock_generate.call_args[1]['prompt']
        
        # Verify prompts are identical
        assert first_prompt == second_prompt

    @patch('trademark_core.llm.generate_structured_content')
    async def test_different_inputs_produce_different_prompts(self, mock_generate):
        """Test that different inputs produce different prompts."""
        mock_generate.return_value = models.MarkSimilarityOutput(
            visual="moderate", aural="moderate", conceptual="moderate", overall="moderate"
        )
        
        # First call
        await llm.generate_mark_similarity_assessment(
            applicant_mark=models.Mark(wordmark="FIRST"),
            opponent_mark=models.Mark(wordmark="SECOND"),
            visual_score=0.8,
            aural_score=0.7
        )
        first_prompt = mock_generate.call_args[1]['prompt']
        
        mock_generate.reset_mock()
        
        # Second call with different inputs
        await llm.generate_mark_similarity_assessment(
            applicant_mark=models.Mark(wordmark="THIRD"),
            opponent_mark=models.Mark(wordmark="FOURTH"),
            visual_score=0.6,
            aural_score=0.5
        )
        second_prompt = mock_generate.call_args[1]['prompt']
        
        # Verify prompts are different
        assert first_prompt != second_prompt
        assert "FIRST" in first_prompt and "FIRST" not in second_prompt
        assert "THIRD" in second_prompt and "THIRD" not in first_prompt 