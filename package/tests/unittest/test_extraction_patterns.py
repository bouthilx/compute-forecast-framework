"""
Unit tests for extraction patterns module.

Tests common patterns, regex extractors, and edge case handlers for computational resource extraction.
"""

import pytest

from src.analysis.computational.extraction_patterns import (
    PatternMatcher,
    RegexExtractor,
    HardwarePatterns,
    TrainingPatterns,
    ModelPatterns,
    DatasetPatterns,
    ComputationPatterns,
    EdgeCaseHandler,
    ExtractionContext,
    PatternResult,
    PatternLibrary
)


@pytest.fixture
def sample_texts():
    """Sample text snippets for pattern testing."""
    return {
        "simple_gpu": "We used 8 V100 GPUs for training.",
        "complex_hardware": "Training was performed on a cluster with 8 NVIDIA V100 GPUs, each with 16GB memory.",
        "training_time": "The model was trained for 120 hours on 8 GPUs.",
        "training_days": "Training took 5 days using 8 V100 GPUs.",
        "model_params": "Our model has 340 million parameters.",
        "model_params_b": "The model contains 1.5B parameters.",
        "transformer": "We use a BERT-like transformer architecture with 24 layers.",
        "dataset": "We trained on ImageNet containing 1.2 million images.",
        "gpu_hours": "Total training required 960 GPU-hours.",
        "cost": "Training cost was approximately $2,880.",
        "complex_sentence": "The 175B parameter model was trained on 1024 V100 GPUs for 14 days, consuming 336,000 GPU-hours.",
        "ambiguous": "We used GPUs for training.",
        "mixed_units": "Training time: 2.5 days or 60 hours total.",
        "multiple_numbers": "We used 8, 16, or 32 GPUs depending on model size."
    }


@pytest.fixture
def pattern_matcher():
    """Create pattern matcher instance."""
    return PatternMatcher()


@pytest.fixture
def regex_extractor():
    """Create regex extractor instance."""
    return RegexExtractor()


@pytest.fixture
def edge_case_handler():
    """Create edge case handler instance."""
    return EdgeCaseHandler()


class TestPatternResult:
    """Test PatternResult dataclass."""
    
    def test_pattern_result_creation(self):
        """Test creating pattern result."""
        result = PatternResult(
            value="V100",
            confidence=0.9,
            pattern_name="gpu_type",
            source_text="We used V100 GPUs",
            start_pos=8,
            end_pos=12
        )
        
        assert result.value == "V100"
        assert result.confidence == 0.9
        assert result.pattern_name == "gpu_type"
        assert result.source_text == "We used V100 GPUs"
        assert result.start_pos == 8
        assert result.end_pos == 12
        assert result.metadata == {}


class TestExtractionContext:
    """Test ExtractionContext class."""
    
    def test_context_creation(self):
        """Test creating extraction context."""
        context = ExtractionContext(
            text="Sample paper text",
            section="abstract",
            paper_id="test_001"
        )
        
        assert context.text == "Sample paper text"
        assert context.section == "abstract"
        assert context.paper_id == "test_001"
        assert context.metadata == {}


class TestHardwarePatterns:
    """Test HardwarePatterns class."""
    
    def test_extract_gpu_type(self, sample_texts):
        """Test GPU type extraction."""
        patterns = HardwarePatterns()
        
        result = patterns.extract_gpu_type(sample_texts["simple_gpu"])
        assert result.value == "V100"
        assert result.confidence > 0.8
        
        result = patterns.extract_gpu_type(sample_texts["complex_hardware"])
        assert result.value == "V100"
        assert "NVIDIA" in result.metadata.get("brand", "")
    
    def test_extract_gpu_count(self, sample_texts):
        """Test GPU count extraction."""
        patterns = HardwarePatterns()
        
        result = patterns.extract_gpu_count(sample_texts["simple_gpu"])
        assert result.value == 8
        assert result.confidence > 0.8
        
        result = patterns.extract_gpu_count(sample_texts["complex_sentence"])
        assert result.value == 1024
    
    def test_extract_gpu_memory(self, sample_texts):
        """Test GPU memory extraction."""
        patterns = HardwarePatterns()
        
        result = patterns.extract_gpu_memory(sample_texts["complex_hardware"])
        assert result.value == 16.0
        assert result.metadata.get("unit") == "GB"
    
    def test_extract_node_count(self):
        """Test node count extraction."""
        patterns = HardwarePatterns()
        text = "Training was performed on 4 nodes with 8 GPUs each."
        
        result = patterns.extract_node_count(text)
        assert result.value == 4
        assert result.confidence > 0.7
    
    def test_extract_special_hardware(self):
        """Test special hardware extraction."""
        patterns = HardwarePatterns()
        
        # TPU text
        tpu_text = "We used 8 TPU v3 cores for training."
        result = patterns.extract_special_hardware(tpu_text)
        assert "TPU" in result.value
        assert "v3" in result.value
        
        # Custom hardware
        custom_text = "Training on custom ASIC chips designed for ML."
        result = patterns.extract_special_hardware(custom_text)
        assert "ASIC" in result.value
    
    def test_gpu_type_normalization(self):
        """Test GPU type normalization."""
        patterns = HardwarePatterns()
        
        # Test various GPU naming formats
        assert patterns._normalize_gpu_type("Tesla V100") == "V100"
        assert patterns._normalize_gpu_type("NVIDIA V100") == "V100"
        assert patterns._normalize_gpu_type("GeForce RTX 3090") == "RTX3090"
        assert patterns._normalize_gpu_type("A100-80GB") == "A100"


class TestTrainingPatterns:
    """Test TrainingPatterns class."""
    
    def test_extract_training_time_hours(self, sample_texts):
        """Test training time extraction in hours."""
        patterns = TrainingPatterns()
        
        result = patterns.extract_training_time(sample_texts["training_time"])
        assert result.value == 120.0
        assert result.metadata.get("unit") == "hours"
        assert result.confidence > 0.9
    
    def test_extract_training_time_days(self, sample_texts):
        """Test training time extraction in days."""
        patterns = TrainingPatterns()
        
        result = patterns.extract_training_time(sample_texts["training_days"])
        assert result.value == 120.0  # 5 days * 24 hours
        assert result.metadata.get("original_unit") == "days"
        assert result.metadata.get("unit") == "hours"
    
    def test_extract_training_epochs(self):
        """Test training epochs extraction."""
        patterns = TrainingPatterns()
        text = "The model was trained for 100 epochs."
        
        result = patterns.extract_training_epochs(text)
        assert result.value == 100
        assert result.confidence > 0.8
    
    def test_extract_batch_size(self):
        """Test batch size extraction."""
        patterns = TrainingPatterns()
        text = "We used a batch size of 64 for training."
        
        result = patterns.extract_batch_size(text)
        assert result.value == 64
        assert result.confidence > 0.8
    
    def test_extract_learning_rate(self):
        """Test learning rate extraction."""
        patterns = TrainingPatterns()
        text = "The learning rate was set to 1e-4."
        
        result = patterns.extract_learning_rate(text)
        assert result.value == 0.0001
        assert result.confidence > 0.8
        
        # Scientific notation
        text2 = "Learning rate: 2.5e-05"
        result2 = patterns.extract_learning_rate(text2)
        assert result2.value == 0.000025
    
    def test_time_unit_conversion(self):
        """Test time unit conversion."""
        patterns = TrainingPatterns()
        
        # Days to hours
        assert patterns._convert_to_hours(5, "days") == 120.0
        assert patterns._convert_to_hours(1, "day") == 24.0
        
        # Weeks to hours
        assert patterns._convert_to_hours(1, "week") == 168.0
        assert patterns._convert_to_hours(2, "weeks") == 336.0
        
        # Hours (no conversion)
        assert patterns._convert_to_hours(10, "hours") == 10.0
        assert patterns._convert_to_hours(1, "hour") == 1.0
        
        # Minutes to hours
        assert patterns._convert_to_hours(120, "minutes") == 2.0


class TestModelPatterns:
    """Test ModelPatterns class."""
    
    def test_extract_parameter_count_millions(self, sample_texts):
        """Test parameter count extraction in millions."""
        patterns = ModelPatterns()
        
        result = patterns.extract_parameter_count(sample_texts["model_params"])
        assert result.value == 340.0
        assert result.metadata.get("unit") == "millions"
        assert result.confidence > 0.9
    
    def test_extract_parameter_count_billions(self, sample_texts):
        """Test parameter count extraction in billions."""
        patterns = ModelPatterns()
        
        result = patterns.extract_parameter_count(sample_texts["model_params_b"])
        assert result.value == 1500.0  # Converted to millions
        assert result.metadata.get("original_unit") == "billions"
        assert result.metadata.get("unit") == "millions"
    
    def test_extract_architecture(self, sample_texts):
        """Test architecture extraction."""
        patterns = ModelPatterns()
        
        result = patterns.extract_architecture(sample_texts["transformer"])
        assert "Transformer" in result.value or "BERT" in result.value
        assert result.confidence > 0.7
    
    def test_extract_layer_count(self, sample_texts):
        """Test layer count extraction."""
        patterns = ModelPatterns()
        
        result = patterns.extract_layer_count(sample_texts["transformer"])
        assert result.value == 24
        assert result.confidence > 0.8
    
    def test_extract_hidden_size(self):
        """Test hidden size extraction."""
        patterns = ModelPatterns()
        text = "The model has a hidden size of 768."
        
        result = patterns.extract_hidden_size(text)
        assert result.value == 768
        assert result.confidence > 0.8
    
    def test_parameter_unit_conversion(self):
        """Test parameter unit conversion."""
        patterns = ModelPatterns()
        
        # Billions to millions
        assert patterns._convert_to_millions(1.5, "billions") == 1500.0
        assert patterns._convert_to_millions(1.5, "B") == 1500.0
        
        # Thousands to millions
        assert patterns._convert_to_millions(500, "thousands") == 0.5
        assert patterns._convert_to_millions(500, "K") == 0.5
        
        # Millions (no conversion)
        assert patterns._convert_to_millions(340, "millions") == 340.0
        assert patterns._convert_to_millions(340, "M") == 340.0


class TestDatasetPatterns:
    """Test DatasetPatterns class."""
    
    def test_extract_dataset_name(self, sample_texts):
        """Test dataset name extraction."""
        patterns = DatasetPatterns()
        
        result = patterns.extract_dataset_name(sample_texts["dataset"])
        assert result.value == "ImageNet"
        assert result.confidence > 0.9
    
    def test_extract_dataset_size(self, sample_texts):
        """Test dataset size extraction."""
        patterns = DatasetPatterns()
        
        result = patterns.extract_dataset_size(sample_texts["dataset"])
        assert result.value == 1.2
        assert result.metadata.get("unit") == "millions"
        assert result.metadata.get("type") == "images"
    
    def test_extract_common_datasets(self):
        """Test common dataset extraction."""
        patterns = DatasetPatterns()
        
        datasets = ["CIFAR-10", "MNIST", "COCO", "WikiText", "Common Crawl"]
        for dataset in datasets:
            text = f"We trained on {dataset} dataset."
            result = patterns.extract_dataset_name(text)
            assert dataset.upper() in result.value.upper()
    
    def test_dataset_size_units(self):
        """Test dataset size unit handling."""
        patterns = DatasetPatterns()
        
        # Test different units
        text1 = "Dataset contains 50K samples."
        result1 = patterns.extract_dataset_size(text1)
        assert result1.value == 0.05  # Converted to millions
        
        text2 = "Dataset has 2B tokens."
        result2 = patterns.extract_dataset_size(text2)
        assert result2.value == 2000.0  # Converted to millions


class TestComputationPatterns:
    """Test ComputationPatterns class."""
    
    def test_extract_gpu_hours(self, sample_texts):
        """Test GPU-hours extraction."""
        patterns = ComputationPatterns()
        
        result = patterns.extract_gpu_hours(sample_texts["gpu_hours"])
        assert result.value == 960.0
        assert result.confidence > 0.9
    
    def test_extract_cost(self, sample_texts):
        """Test cost extraction."""
        patterns = ComputationPatterns()
        
        result = patterns.extract_cost(sample_texts["cost"])
        assert result.value == 2880.0
        assert result.metadata.get("currency") == "USD"
        assert result.confidence > 0.8
    
    def test_extract_flops(self):
        """Test FLOPS extraction."""
        patterns = ComputationPatterns()
        text = "The model requires 300 TFLOPs for inference."
        
        result = patterns.extract_flops(text)
        assert result.value == 300.0
        assert result.metadata.get("unit") == "TFLOPS"
    
    def test_calculate_gpu_hours_from_context(self):
        """Test GPU-hours calculation from context."""
        patterns = ComputationPatterns()
        
        context = {
            "gpu_count": 8,
            "training_hours": 120,
            "nodes": 1
        }
        
        calculated_hours = patterns._calculate_gpu_hours(context)
        assert calculated_hours == 960.0  # 8 * 120


class TestRegexExtractor:
    """Test RegexExtractor utility class."""
    
    def test_extract_numbers(self, regex_extractor):
        """Test number extraction."""
        text = "We used 8 GPUs and trained for 120 hours."
        numbers = regex_extractor.extract_numbers(text)
        
        assert 8 in numbers
        assert 120 in numbers
    
    def test_extract_with_pattern(self, regex_extractor):
        """Test extraction with custom pattern."""
        text = "Model: BERT-large, Parameters: 340M"
        pattern = r"Parameters:\s*(\d+(?:\.\d+)?)([MBK]?)"
        
        matches = regex_extractor.extract_with_pattern(text, pattern)
        assert len(matches) == 1
        assert matches[0][0] == "340"
        assert matches[0][1] == "M"
    
    def test_extract_scientific_notation(self, regex_extractor):
        """Test scientific notation extraction."""
        text = "Learning rate: 1e-4, batch size: 2.5e2"
        scientific_numbers = regex_extractor.extract_scientific_notation(text)
        
        assert 0.0001 in scientific_numbers
        assert 250.0 in scientific_numbers
    
    def test_find_nearest_context(self, regex_extractor):
        """Test finding context around matches."""
        text = "The model has 340 million parameters and uses transformer architecture."
        match_pos = text.find("340")
        
        context = regex_extractor.find_nearest_context(text, match_pos, window=10)
        assert "model has 340 million" in context


class TestEdgeCaseHandler:
    """Test EdgeCaseHandler class."""
    
    def test_handle_ambiguous_numbers(self, edge_case_handler, sample_texts):
        """Test handling ambiguous numbers."""
        result = edge_case_handler.handle_ambiguous_numbers(sample_texts["multiple_numbers"])
        
        # Should identify multiple possible GPU counts
        assert len(result) >= 3
        assert 8 in [r.value for r in result]
        assert 16 in [r.value for r in result]
        assert 32 in [r.value for r in result]
    
    def test_handle_missing_units(self, edge_case_handler):
        """Test handling missing units."""
        text = "Training took 120 on 8 GPUs."  # Missing time unit
        
        results = edge_case_handler.handle_missing_units(text, "time")
        # Should suggest possible units
        assert len(results) > 0
        assert any("hours" in r.metadata.get("suggested_unit", "") for r in results)
    
    def test_handle_conflicting_information(self, edge_case_handler, sample_texts):
        """Test handling conflicting information."""
        conflicts = edge_case_handler.handle_conflicting_information(sample_texts["mixed_units"])
        
        # Should identify the conflict between days and hours
        assert len(conflicts) > 0
        assert any("conflict" in c.lower() for c in conflicts)
    
    def test_resolve_approximate_values(self, edge_case_handler):
        """Test resolving approximate values."""
        text = "Training took approximately 5 days or about 120 hours."
        
        results = edge_case_handler.resolve_approximate_values(text)
        # Should handle approximate language
        assert len(results) > 0
        assert any(r.confidence < 1.0 for r in results)  # Lower confidence for approximate
    
    def test_handle_ranges(self, edge_case_handler):
        """Test handling value ranges."""
        text = "Training time ranged from 100 to 150 hours."
        
        results = edge_case_handler.handle_ranges(text)
        assert len(results) >= 2
        
        values = [r.value for r in results]
        assert 100 in values
        assert 150 in values
    
    def test_context_disambiguation(self, edge_case_handler):
        """Test context-based disambiguation."""
        text = "We used 8 for training and 16 for inference."
        context = ExtractionContext(text=text, section="experimental_setup")
        
        results = edge_case_handler.disambiguate_by_context(context, "gpu_count")
        # Should prefer the training context value
        assert any(r.value == 8 and r.confidence > 0.8 for r in results)


class TestPatternMatcher:
    """Test PatternMatcher main class."""
    
    def test_match_all_patterns(self, pattern_matcher, sample_texts):
        """Test matching all patterns against text."""
        results = pattern_matcher.match_all_patterns(sample_texts["complex_sentence"])
        
        # Should find multiple types of information
        assert len(results) > 0
        
        # Check for different pattern types
        pattern_types = [r.pattern_name for r in results]
        assert any("parameter" in p for p in pattern_types)
        assert any("gpu" in p for p in pattern_types)
    
    def test_get_best_matches(self, pattern_matcher):
        """Test getting best matches."""
        text = "We used 8 V100 GPUs and 16 A100 GPUs for different experiments."
        results = pattern_matcher.match_all_patterns(text)
        
        best_gpu_type = pattern_matcher.get_best_match(results, "gpu_type")
        assert best_gpu_type is not None
        assert best_gpu_type.confidence > 0.0
    
    def test_filter_by_confidence(self, pattern_matcher):
        """Test filtering results by confidence."""
        # Mock some results with different confidence scores
        results = [
            PatternResult("V100", 0.9, "gpu_type", "text", 0, 4),
            PatternResult("8", 0.7, "gpu_count", "text", 5, 6),
            PatternResult("maybe", 0.3, "uncertain", "text", 7, 12)
        ]
        
        high_confidence = pattern_matcher.filter_by_confidence(results, min_confidence=0.8)
        assert len(high_confidence) == 1
        assert high_confidence[0].value == "V100"
    
    def test_merge_overlapping_results(self, pattern_matcher):
        """Test merging overlapping results."""
        # Results that overlap in the same text region
        results = [
            PatternResult("NVIDIA V100", 0.8, "full_gpu", "text", 0, 11),
            PatternResult("V100", 0.9, "gpu_type", "text", 7, 11)
        ]
        
        merged = pattern_matcher.merge_overlapping_results(results)
        # Should prefer higher confidence result
        assert len(merged) == 1
        assert merged[0].confidence == 0.9


class TestPatternLibrary:
    """Test PatternLibrary class."""
    
    def test_get_all_patterns(self):
        """Test getting all available patterns."""
        library = PatternLibrary()
        patterns = library.get_all_patterns()
        
        assert "hardware" in patterns
        assert "training" in patterns
        assert "model" in patterns
        assert "dataset" in patterns
        assert "computation" in patterns
    
    def test_get_pattern_by_name(self):
        """Test getting specific pattern."""
        library = PatternLibrary()
        
        gpu_patterns = library.get_pattern("hardware")
        assert isinstance(gpu_patterns, HardwarePatterns)
        
        training_patterns = library.get_pattern("training")
        assert isinstance(training_patterns, TrainingPatterns)
    
    def test_register_custom_pattern(self):
        """Test registering custom pattern."""
        library = PatternLibrary()
        
        class CustomPattern:
            def extract_custom_field(self, text):
                return PatternResult("custom", 1.0, "custom", text, 0, len(text))
        
        custom_pattern = CustomPattern()
        library.register_pattern("custom", custom_pattern)
        
        retrieved = library.get_pattern("custom")
        assert retrieved == custom_pattern


class TestPatternEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_text_patterns(self):
        """Test patterns with empty text."""
        patterns = HardwarePatterns()
        result = patterns.extract_gpu_type("")
        
        assert result.value is None
        assert result.confidence == 0.0
    
    def test_no_matches_found(self):
        """Test when no patterns match."""
        patterns = HardwarePatterns()
        text = "This text contains no GPU information."
        
        result = patterns.extract_gpu_count(text)
        assert result.value is None
        assert result.confidence == 0.0
    
    def test_malformed_numbers(self, regex_extractor):
        """Test handling malformed numbers."""
        text = "We used 8..5 GPUs and 12..0.3 hours."
        numbers = regex_extractor.extract_numbers(text)
        
        # Should handle malformed numbers gracefully
        assert isinstance(numbers, list)
    
    def test_unicode_text_handling(self):
        """Test handling unicode characters."""
        patterns = ModelPatterns()
        text = "The model has 340M paramètres with spéciàl characters."
        
        # Should not crash on unicode
        result = patterns.extract_parameter_count(text)
        assert result.value == 340.0