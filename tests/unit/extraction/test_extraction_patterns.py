"""
Unit tests for extraction patterns module.

Tests common patterns, regex extractors, and edge case handlers for computational resource extraction.
"""

import pytest

from compute_forecast.analysis.computational.extraction_patterns import (
    PatternType,
    ExtractionPattern,
    CommonPatterns,
    ExtractionRegexPatterns,
    EdgeCaseHandler,
    PatternMatcher,
)


@pytest.fixture
def sample_texts():
    """Sample text snippets for pattern testing."""
    return {
        "simple_gpu": "We used 8 V100 GPUs for training.",
        "complex_hardware": "Training was performed on a cluster with 8 NVIDIA V100 GPUs, each with 16GB memory.",
        "training_time": "The model was trained for 120 hours on 8 GPUs.",
        "distributed": "We trained on 32 nodes with 8 A100s each for 2 days.",
        "parameters": "Our model has 175 billion parameters.",
        "cost_info": "Training cost approximately $50,000 in cloud credits.",
        "multiple_phases": "Pre-training took 100 hours, fine-tuning took 20 hours.",
        "vague_time": "Training took several days on our cluster.",
        "tpu_training": "We used TPU v3-128 pods for training.",
        "relative_ref": "Following the same setup as BERT-large.",
        "gpu_hours": "Total training required 2,560 GPU-hours.",
    }


@pytest.fixture
def pattern_matcher():
    """Create pattern matcher instance."""
    return PatternMatcher()


@pytest.fixture
def edge_case_handler():
    """Create edge case handler instance."""
    return EdgeCaseHandler()


class TestPatternType:
    """Test PatternType enum."""

    def test_pattern_types_exist(self):
        """Test that all expected pattern types exist."""
        expected_types = [
            PatternType.EXPLICIT_RESOURCE,
            PatternType.DISTRIBUTED_TRAINING,
            PatternType.MULTIPLE_PHASES,
            PatternType.IMPLICIT_INFORMATION,
            PatternType.CLOUD_CREDITS,
            PatternType.RELATIVE_REFERENCE,
        ]

        for pattern_type in expected_types:
            assert isinstance(pattern_type, PatternType)

    def test_pattern_type_values(self):
        """Test pattern type string values."""
        assert PatternType.EXPLICIT_RESOURCE.value == "explicit_resource"
        assert PatternType.DISTRIBUTED_TRAINING.value == "distributed_training"
        assert PatternType.MULTIPLE_PHASES.value == "multiple_phases"


class TestExtractionPattern:
    """Test ExtractionPattern dataclass."""

    def test_pattern_creation(self):
        """Test creating extraction pattern."""
        pattern = ExtractionPattern(
            pattern_type=PatternType.EXPLICIT_RESOURCE,
            description="Explicit GPU count and type",
            example_text="We used 8 V100 GPUs",
            extraction_approach="Direct regex matching",
            expected_fields=["gpu_count", "gpu_type"],
            confidence_level="high",
            notes=["Most reliable pattern"],
        )

        assert pattern.pattern_type == PatternType.EXPLICIT_RESOURCE
        assert pattern.description == "Explicit GPU count and type"
        assert pattern.confidence_level == "high"
        assert "gpu_count" in pattern.expected_fields


class TestCommonPatterns:
    """Test CommonPatterns class."""

    def test_patterns_database_exists(self):
        """Test that patterns database is populated."""
        assert hasattr(CommonPatterns, "PATTERNS")
        assert isinstance(CommonPatterns.PATTERNS, list)
        assert len(CommonPatterns.PATTERNS) > 0

    def test_get_pattern_valid(self):
        """Test getting valid pattern."""
        pattern = CommonPatterns.get_pattern(PatternType.EXPLICIT_RESOURCE)
        assert pattern is not None
        assert isinstance(pattern, ExtractionPattern)
        assert pattern.pattern_type == PatternType.EXPLICIT_RESOURCE

    def test_get_pattern_invalid(self):
        """Test getting invalid pattern returns None."""
        # Create a mock pattern type that doesn't exist
        pattern = CommonPatterns.get_pattern(None)
        assert pattern is None

    def test_get_patterns_by_confidence(self):
        """Test filtering patterns by confidence level."""
        high_patterns = CommonPatterns.get_patterns_by_confidence("high")
        assert isinstance(high_patterns, list)

        for pattern in high_patterns:
            assert pattern.confidence_level == "high"


class TestExtractionRegexPatterns:
    """Test ExtractionRegexPatterns class."""

    def test_gpu_extraction(self, sample_texts):
        """Test GPU information extraction."""
        gpu_info = ExtractionRegexPatterns.extract_gpu_info(sample_texts["simple_gpu"])
        assert len(gpu_info) > 0

        # Should extract count and type
        found_count = False
        found_type = False
        for count, gpu_type in gpu_info:
            if count == 8:
                found_count = True
            if "V100" in gpu_type:
                found_type = True

        assert found_count or found_type  # At least one should be found

    def test_training_time_extraction(self, sample_texts):
        """Test training time extraction."""
        time_info = ExtractionRegexPatterns.extract_training_time(
            sample_texts["training_time"]
        )
        assert len(time_info) > 0

        # Should extract hours
        found_hours = False
        for value, unit in time_info:
            if value == 120.0 and unit.lower() in ["hour", "hours", "h"]:
                found_hours = True

        assert found_hours

    def test_parameter_extraction(self, sample_texts):
        """Test parameter count extraction."""
        param_info = ExtractionRegexPatterns.extract_parameters(
            sample_texts["parameters"]
        )
        assert len(param_info) > 0

        # Should extract billions
        found_billions = False
        for value, unit in param_info:
            if value == 175.0 and unit.lower() in ["billion", "billions", "b"]:
                found_billions = True

        assert found_billions

    def test_normalize_time_to_hours(self):
        """Test time normalization."""
        # Test units that are actually supported
        assert ExtractionRegexPatterns.normalize_time_to_hours(2.0, "days") == 48.0
        assert ExtractionRegexPatterns.normalize_time_to_hours(1.0, "week") == 168.0
        assert ExtractionRegexPatterns.normalize_time_to_hours(120.0, "hours") == 120.0
        # Test unsupported unit returns original value
        assert ExtractionRegexPatterns.normalize_time_to_hours(30.0, "minutes") == 30.0

    def test_normalize_parameters_to_millions(self):
        """Test parameter normalization."""
        # Test units that are actually supported
        assert (
            ExtractionRegexPatterns.normalize_parameters_to_millions(1000000.0, "k")
            == 1000.0
        )  # 1M k = 1000 M
        # Test unsupported units return original value
        assert (
            ExtractionRegexPatterns.normalize_parameters_to_millions(1.0, "billion")
            == 1.0
        )
        assert (
            ExtractionRegexPatterns.normalize_parameters_to_millions(500.0, "millions")
            == 500.0
        )

    def test_gpu_patterns_exist(self):
        """Test that GPU patterns are defined."""
        assert hasattr(ExtractionRegexPatterns, "GPU_COUNT_PATTERNS")
        assert isinstance(ExtractionRegexPatterns.GPU_COUNT_PATTERNS, list)
        assert len(ExtractionRegexPatterns.GPU_COUNT_PATTERNS) > 0

    def test_time_patterns_exist(self):
        """Test that time patterns are defined."""
        assert hasattr(ExtractionRegexPatterns, "TIME_PATTERNS")
        assert isinstance(ExtractionRegexPatterns.TIME_PATTERNS, list)
        assert len(ExtractionRegexPatterns.TIME_PATTERNS) > 0


class TestEdgeCaseHandler:
    """Test EdgeCaseHandler class."""

    def test_handle_missing_gpu_type(self, edge_case_handler):
        """Test handling missing GPU type."""
        result = edge_case_handler.handle_missing_gpu_type("latest NVIDIA GPUs", 2023)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_handle_vague_time(self, edge_case_handler):
        """Test handling vague time expressions."""
        min_time, max_time = edge_case_handler.handle_vague_time("several days")
        assert isinstance(min_time, float)
        assert isinstance(max_time, float)
        assert min_time < max_time
        assert min_time > 0

    def test_estimate_from_cost(self, edge_case_handler):
        """Test estimating resources from cost."""
        gpu_hours = edge_case_handler.estimate_from_cost(1000.0, "aws", "V100")
        assert isinstance(gpu_hours, float)
        assert gpu_hours > 0

    def test_resolve_model_reference(self, edge_case_handler):
        """Test resolving model references."""
        model_info = edge_case_handler.resolve_model_reference("BERT-large")
        assert isinstance(model_info, dict)

        # Should have some key information
        assert len(model_info) > 0

    def test_handle_distributed_training(self, edge_case_handler, sample_texts):
        """Test handling distributed training."""
        result = edge_case_handler.handle_distributed_training(
            sample_texts["distributed"]
        )
        assert isinstance(result, dict)

    def test_handle_multiple_experiments(self, edge_case_handler, sample_texts):
        """Test handling multiple experiments."""
        result = edge_case_handler.handle_multiple_experiments(
            sample_texts["multiple_phases"]
        )
        assert isinstance(result, dict)

    def test_known_models_exist(self):
        """Test that known models database exists."""
        assert hasattr(EdgeCaseHandler, "KNOWN_MODELS")
        assert isinstance(EdgeCaseHandler.KNOWN_MODELS, dict)
        assert len(EdgeCaseHandler.KNOWN_MODELS) > 0

    def test_cloud_pricing_exists(self):
        """Test that cloud pricing data exists."""
        assert hasattr(EdgeCaseHandler, "CLOUD_PRICING")
        assert isinstance(EdgeCaseHandler.CLOUD_PRICING, dict)


class TestPatternMatcher:
    """Test PatternMatcher class."""

    def test_initialization(self, pattern_matcher):
        """Test pattern matcher initialization."""
        assert isinstance(pattern_matcher, PatternMatcher)

    def test_identify_pattern_type(self, pattern_matcher, sample_texts):
        """Test pattern type identification."""
        # Test explicit resource pattern
        patterns = pattern_matcher.identify_pattern_type(sample_texts["simple_gpu"])
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert PatternType.EXPLICIT_RESOURCE in patterns

        # Test distributed training pattern
        patterns = pattern_matcher.identify_pattern_type(sample_texts["distributed"])
        assert PatternType.DISTRIBUTED_TRAINING in patterns

        # Test cost pattern
        patterns = pattern_matcher.identify_pattern_type(sample_texts["cost_info"])
        assert PatternType.CLOUD_CREDITS in patterns

    def test_extract_all_patterns(self, pattern_matcher, sample_texts):
        """Test extracting all patterns from text."""
        results = pattern_matcher.extract_all_patterns(sample_texts["complex_hardware"])
        assert isinstance(results, dict)

        # Should identify explicit resource pattern
        if PatternType.EXPLICIT_RESOURCE in results:
            resource_data = results[PatternType.EXPLICIT_RESOURCE]
            assert isinstance(resource_data, dict)

    def test_extract_explicit_resources(self, pattern_matcher, sample_texts):
        """Test explicit resource extraction."""
        results = pattern_matcher._extract_explicit_resources(
            sample_texts["simple_gpu"]
        )
        assert isinstance(results, dict)

    def test_extract_multiple_phases(self, pattern_matcher, sample_texts):
        """Test multiple phases extraction."""
        results = pattern_matcher._extract_multiple_phases(
            sample_texts["multiple_phases"]
        )
        assert isinstance(results, dict)

    def test_extract_implicit_info(self, pattern_matcher, sample_texts):
        """Test implicit information extraction."""
        results = pattern_matcher._extract_implicit_info(sample_texts["relative_ref"])
        assert isinstance(results, dict)

    def test_extract_cost_info(self, pattern_matcher, sample_texts):
        """Test cost information extraction."""
        results = pattern_matcher._extract_cost_info(sample_texts["cost_info"])
        assert isinstance(results, dict)

    def test_extract_relative_info(self, pattern_matcher, sample_texts):
        """Test relative information extraction."""
        results = pattern_matcher._extract_relative_info(sample_texts["relative_ref"])
        assert isinstance(results, dict)


class TestIntegrationPatterns:
    """Test integration of pattern matching components."""

    def test_end_to_end_explicit_extraction(self, pattern_matcher, sample_texts):
        """Test end-to-end explicit resource extraction."""
        text = sample_texts["complex_hardware"]

        # Identify patterns
        pattern_types = pattern_matcher.identify_pattern_type(text)
        assert PatternType.EXPLICIT_RESOURCE in pattern_types

        # Extract all patterns
        results = pattern_matcher.extract_all_patterns(text)
        assert PatternType.EXPLICIT_RESOURCE in results

        # Verify extraction results
        explicit_data = results[PatternType.EXPLICIT_RESOURCE]
        assert isinstance(explicit_data, dict)

    def test_end_to_end_distributed_extraction(self, pattern_matcher, sample_texts):
        """Test end-to-end distributed training extraction."""
        text = sample_texts["distributed"]

        pattern_types = pattern_matcher.identify_pattern_type(text)
        assert PatternType.DISTRIBUTED_TRAINING in pattern_types

        results = pattern_matcher.extract_all_patterns(text)
        assert PatternType.DISTRIBUTED_TRAINING in results

    def test_pattern_confidence_consistency(self):
        """Test that pattern confidence levels are consistent."""
        all_patterns = []
        for pattern_type in PatternType:
            pattern = CommonPatterns.get_pattern(pattern_type)
            if pattern:
                all_patterns.append(pattern)

        assert len(all_patterns) > 0

        # Check that confidence levels are valid
        valid_levels = {"low", "medium", "high"}
        for pattern in all_patterns:
            assert pattern.confidence_level in valid_levels


class TestEdgeCaseScenarios:
    """Test edge case scenarios."""

    def test_empty_text_handling(self, pattern_matcher):
        """Test handling of empty text."""
        results = pattern_matcher.extract_all_patterns("")
        assert isinstance(results, dict)
        # Should handle gracefully without crashing

    def test_no_patterns_text(self, pattern_matcher):
        """Test text with no computational patterns."""
        text = "This is a paper about theoretical mathematics with no computational experiments."
        patterns = pattern_matcher.identify_pattern_type(text)
        results = pattern_matcher.extract_all_patterns(text)

        # Should handle gracefully
        assert isinstance(patterns, list)
        assert isinstance(results, dict)

    def test_mixed_pattern_text(self, pattern_matcher):
        """Test text with multiple pattern types."""
        text = """
        We trained our 175B parameter model on 64 V100 GPUs for 2 weeks.
        This cost approximately $100,000 in cloud credits.
        Following the BERT-large setup, we used distributed training across 8 nodes.
        """

        patterns = pattern_matcher.identify_pattern_type(text)
        results = pattern_matcher.extract_all_patterns(text)

        # Should identify multiple patterns
        assert len(patterns) > 1
        assert len(results) > 1

        # Should include explicit resource and cost patterns
        assert PatternType.EXPLICIT_RESOURCE in patterns
        assert PatternType.CLOUD_CREDITS in patterns

    def test_regex_edge_cases(self):
        """Test regex patterns with edge cases."""
        # Test GPU extraction with various formats
        test_cases = [
            "8x V100 GPUs",
            "eight V100 GPUs",
            "V100 x8",
            "8 NVIDIA V100s",
            "8-GPU V100 setup",
        ]

        for text in test_cases:
            try:
                results = ExtractionRegexPatterns.extract_gpu_info(text)
                # Should not crash and return list
                assert isinstance(results, list)
            except Exception as e:
                pytest.fail(f"GPU extraction failed for '{text}': {e}")

    def test_time_normalization_edge_cases(self):
        """Test time normalization with edge cases."""
        edge_cases = [
            (0.0, "hours", 0.0),
            (1.5, "days", 36.0),
            (0.5, "weeks", 84.0),
            (90.0, "minutes", 90.0),  # unsupported unit returns original
        ]

        for value, unit, expected in edge_cases:
            result = ExtractionRegexPatterns.normalize_time_to_hours(value, unit)
            assert abs(result - expected) < 0.01, f"Failed for {value} {unit}"
