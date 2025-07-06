"""Tests for normalization engine."""

from compute_forecast.extraction.normalization_engine import NormalizationEngine
from compute_forecast.extraction.template_engine import ExtractionField


class TestNormalizationEngine:
    """Test NormalizationEngine functionality."""

    def test_engine_initialization(self):
        """Test that normalization engine initializes properly."""
        engine = NormalizationEngine()
        assert hasattr(engine, "time_conversions")
        assert hasattr(engine, "memory_conversions")
        assert hasattr(engine, "parameter_conversions")

    def test_normalize_time_to_hours(self):
        """Test time normalization to hours."""
        engine = NormalizationEngine()

        # Test various units
        assert engine.normalize_time_to_hours(60, "minutes") == 1.0
        assert engine.normalize_time_to_hours(2, "hours") == 2.0
        assert engine.normalize_time_to_hours(1, "days") == 24.0
        assert engine.normalize_time_to_hours(1, "weeks") == 168.0

        # Test edge cases
        assert engine.normalize_time_to_hours(30, "minutes") == 0.5
        assert engine.normalize_time_to_hours(0.5, "days") == 12.0

        # Test unknown unit defaults to no conversion
        assert engine.normalize_time_to_hours(100, "unknown") == 100.0

    def test_normalize_memory_to_gb(self):
        """Test memory normalization to GB."""
        engine = NormalizationEngine()

        # Test various units
        assert engine.normalize_memory_to_gb(1024, "MB") == 1.0
        assert engine.normalize_memory_to_gb(2, "GB") == 2.0
        assert engine.normalize_memory_to_gb(1, "TB") == 1024.0

        # Test edge cases
        assert engine.normalize_memory_to_gb(512, "MB") == 0.5
        assert engine.normalize_memory_to_gb(0.5, "TB") == 512.0

        # Test unknown unit defaults to no conversion
        assert engine.normalize_memory_to_gb(100, "unknown") == 100.0

    def test_normalize_parameters_to_millions(self):
        """Test parameter count normalization to millions."""
        engine = NormalizationEngine()

        # Test various units
        assert engine.normalize_parameters_to_millions(1000, "K") == 1.0
        assert engine.normalize_parameters_to_millions(2, "M") == 2.0
        assert engine.normalize_parameters_to_millions(1, "B") == 1000.0
        assert engine.normalize_parameters_to_millions(0.001, "T") == 1000.0

        # Test edge cases
        assert engine.normalize_parameters_to_millions(500, "K") == 0.5
        assert engine.normalize_parameters_to_millions(0.175, "B") == 175.0

        # Test unknown unit defaults to no conversion
        assert engine.normalize_parameters_to_millions(100, "unknown") == 100.0

    def test_normalize_gpu_names(self):
        """Test GPU name normalization."""
        engine = NormalizationEngine()

        # Test V100 variations
        assert engine.normalize_gpu_names("V100") == "V100"
        assert engine.normalize_gpu_names("Tesla V100") == "V100"
        assert engine.normalize_gpu_names("V100-SXM2") == "V100"
        assert engine.normalize_gpu_names("V100-PCIE") == "V100"
        assert engine.normalize_gpu_names("NVIDIA V100") == "V100"

        # Test A100 variations
        assert engine.normalize_gpu_names("A100") == "A100"
        assert engine.normalize_gpu_names("A100-SXM4") == "A100"
        assert engine.normalize_gpu_names("A100 40GB") == "A100"
        assert engine.normalize_gpu_names("A100 80GB") == "A100"
        assert engine.normalize_gpu_names("NVIDIA A100") == "A100"

        # Test H100 variations
        assert engine.normalize_gpu_names("H100") == "H100"
        assert engine.normalize_gpu_names("H100-SXM5") == "H100"
        assert engine.normalize_gpu_names("NVIDIA H100") == "H100"

        # Test consumer GPU variations
        assert engine.normalize_gpu_names("RTX 3090") == "RTX 3090"
        assert engine.normalize_gpu_names("GeForce RTX 3090") == "RTX 3090"
        assert engine.normalize_gpu_names("3090") == "RTX 3090"
        assert engine.normalize_gpu_names("RTX 4090") == "RTX 4090"
        assert engine.normalize_gpu_names("4090") == "RTX 4090"

        # Test unknown GPU (returns as-is)
        assert engine.normalize_gpu_names("Unknown GPU") == "Unknown GPU"

    def test_extract_value_and_unit(self):
        """Test extracting numeric value and unit from strings."""
        engine = NormalizationEngine()

        # Test time strings
        assert engine.extract_value_and_unit("7 days") == (7.0, "days")
        assert engine.extract_value_and_unit("168 hours") == (168.0, "hours")
        assert engine.extract_value_and_unit("2.5 weeks") == (2.5, "weeks")

        # Test memory strings
        assert engine.extract_value_and_unit("32GB") == (32.0, "GB")
        assert engine.extract_value_and_unit("512 MB") == (512.0, "MB")
        assert engine.extract_value_and_unit("1.5TB") == (1.5, "TB")

        # Test parameter strings
        assert engine.extract_value_and_unit("340M") == (340.0, "M")
        assert engine.extract_value_and_unit("1.5B parameters") == (1.5, "B")
        assert engine.extract_value_and_unit("175 billion") == (175.0, "B")

        # Test edge cases
        assert engine.extract_value_and_unit("100") == (100.0, None)
        assert engine.extract_value_and_unit("no number") == (None, None)

    def test_normalize_field_value(self):
        """Test normalizing specific field values."""
        engine = NormalizationEngine()

        # Test training time normalization
        result = engine.normalize_field_value(
            ExtractionField.TRAINING_TIME_HOURS, "7 days"
        )
        assert result == 168.0

        # Test parameter normalization (to millions)
        result = engine.normalize_field_value(ExtractionField.PARAMETERS_COUNT, "1.5B")
        assert result == 1500.0  # 1.5B = 1500M

        # Test dataset size normalization
        result = engine.normalize_field_value(ExtractionField.DATASET_SIZE_GB, "2.5TB")
        assert result == 2560.0  # 2.5TB = 2560GB

        # Test GPU type normalization
        result = engine.normalize_field_value(ExtractionField.GPU_TYPE, "Tesla V100")
        assert result == "V100"

        # Test numeric value without unit
        result = engine.normalize_field_value(ExtractionField.GPU_COUNT, 8)
        assert result == 8

    def test_normalize_extraction(self):
        """Test normalizing complete extraction results."""
        engine = NormalizationEngine()

        extraction = {
            ExtractionField.GPU_TYPE: "Tesla V100-SXM2",
            ExtractionField.GPU_COUNT: 64,
            ExtractionField.TRAINING_TIME_HOURS: "7 days",
            ExtractionField.PARAMETERS_COUNT: "340M",
            ExtractionField.DATASET_SIZE_GB: "750GB",
            ExtractionField.BATCH_SIZE: 2048,
            ExtractionField.GPU_MEMORY_GB: "32 GB",
        }

        normalized = engine.normalize_extraction(extraction)

        # Check normalizations
        assert normalized[ExtractionField.GPU_TYPE] == "V100"
        assert normalized[ExtractionField.GPU_COUNT] == 64
        assert normalized[ExtractionField.TRAINING_TIME_HOURS] == 168.0
        assert normalized[ExtractionField.PARAMETERS_COUNT] == 340.0  # In millions
        assert normalized[ExtractionField.DATASET_SIZE_GB] == 750.0
        assert normalized[ExtractionField.BATCH_SIZE] == 2048
        assert normalized[ExtractionField.GPU_MEMORY_GB] == 32.0
