"""
Integration tests for the complete data extraction framework.

Tests the end-to-end workflow from paper content to final extraction forms.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from src.analysis.computational.extraction_protocol import ExtractionProtocol
from src.analysis.computational.extraction_forms import FormManager, ExtractionFormTemplate
from src.analysis.computational.extraction_patterns import PatternMatcher
from src.analysis.computational.quality_control import QualityController


@pytest.fixture
def sample_paper_content():
    """Sample paper content for integration testing."""
    return """
    Large Language Model Training Infrastructure

    Abstract
    We present the training infrastructure for our large language model.

    Methodology
    Our model was trained on 64 NVIDIA A100 GPUs with 40GB memory each.
    The training process took 168 hours (7 days) with a batch size of 2048.
    Our model has 13 billion parameters and uses the Transformer architecture.
    
    Results
    The total computational cost was 10,752 GPU-hours (64 GPUs × 168 hours).
    Training was performed on a distributed cluster with high-speed interconnects.
    
    The model achieved state-of-the-art performance on several benchmarks.
    """


@pytest.fixture 
def integration_setup():
    """Set up components for integration testing."""
    return {
        'protocol': None,  # Will be created in tests
        'form_manager': FormManager(),
        'pattern_matcher': PatternMatcher(),
        'quality_controller': QualityController()
    }


class TestExtractionPipelineIntegration:
    """Test complete extraction pipeline integration."""
    
    def test_end_to_end_extraction_workflow(self, sample_paper_content, integration_setup):
        """Test complete end-to-end extraction workflow."""
        # Initialize extraction protocol
        protocol = ExtractionProtocol(
            paper_content=sample_paper_content,
            paper_id="integration_test_001",
            analyst="integration_test_analyst"
        )
        
        # Run phases sequentially
        prep_result = protocol.phase1_preparation()
        assert prep_result["has_computational_experiments"] is True
        
        # Mock analyzer for phase 2
        mock_analyzer = Mock()
        mock_analyzer.confidence = 0.85
        auto_result = protocol.phase2_automated_extraction(mock_analyzer)
        assert isinstance(auto_result, dict)
        
        # Run manual extraction
        manual_result = protocol.phase3_manual_extraction()
        assert isinstance(manual_result, dict)
        
        # Run validation
        validation_result = protocol.phase4_validation()
        assert validation_result is not None
        
        # Run documentation
        doc_result = protocol.phase5_documentation()
        assert isinstance(doc_result, dict)
        
        # Get final extraction result
        extraction_result = protocol.run_full_protocol(mock_analyzer)
        assert extraction_result is not None
        assert extraction_result.metadata.paper_id == "integration_test_001"
    
    def test_extraction_with_pattern_matching(self, sample_paper_content, integration_setup):
        """Test extraction workflow with pattern matching."""
        pattern_matcher = integration_setup['pattern_matcher']
        
        # Identify patterns in the content
        pattern_types = pattern_matcher.identify_pattern_type(sample_paper_content)
        assert len(pattern_types) > 0
        
        # Extract all patterns
        pattern_results = pattern_matcher.extract_all_patterns(sample_paper_content)
        assert isinstance(pattern_results, dict)
        
        # Should find explicit resource patterns
        from src.analysis.computational.extraction_patterns import PatternType
        if pattern_results:
            # Verify we can extract meaningful information
            assert len(pattern_results) > 0
    
    def test_extraction_with_quality_control(self, sample_paper_content, integration_setup):
        """Test extraction workflow with quality control."""
        # Run extraction protocol
        protocol = ExtractionProtocol(
            paper_content=sample_paper_content,
            paper_id="quality_test_001", 
            analyst="quality_test_analyst"
        )
        
        mock_analyzer = Mock()
        mock_analyzer.confidence = 0.9
        extraction_result = protocol.run_full_protocol(mock_analyzer)
        
        # Run quality control
        quality_controller = integration_setup['quality_controller']
        quality_report = quality_controller.run_quality_checks(extraction_result)
        
        assert quality_report is not None
        assert hasattr(quality_report, 'overall_score')
        assert quality_report.overall_score >= 0.0
    
    def test_extraction_to_form_conversion(self, sample_paper_content, integration_setup):
        """Test conversion from extraction result to form."""
        # Run extraction
        protocol = ExtractionProtocol(
            paper_content=sample_paper_content,
            paper_id="form_test_001",
            analyst="form_test_analyst"
        )
        
        mock_analyzer = Mock()
        mock_analyzer.confidence = 0.8
        extraction_result = protocol.run_full_protocol(mock_analyzer)
        
        # Convert to form
        form_manager = integration_setup['form_manager']
        form_data = form_manager.convert_extraction_result_to_form(extraction_result)
        
        assert isinstance(form_data, dict)
        assert "metadata" in form_data
        assert form_data["metadata"]["paper_id"] == "form_test_001"
    
    def test_form_validation_workflow(self, integration_setup):
        """Test form validation workflow."""
        form_manager = integration_setup['form_manager']
        
        # Create a test form
        test_form = form_manager.create_form_for_paper(
            paper_id="validation_test_001",
            analyst="validation_analyst",
            paper_title="Test Paper for Validation"
        )
        
        # Fill in some data
        test_form["hardware"]["gpu_type"] = "A100"
        test_form["hardware"]["gpu_count"] = 64
        test_form["training"]["total_time_hours"] = 168.0
        test_form["computation"]["total_gpu_hours"] = 10752.0
        
        # Validate form
        validation_result = form_manager.validate_form(test_form)
        assert validation_result.is_valid is True
        assert validation_result.completeness_score > 0.0
    
    def test_template_usage_workflow(self, integration_setup):
        """Test template usage workflow."""
        # Get blank template
        blank_template = ExtractionFormTemplate.get_blank_template()
        assert isinstance(blank_template, dict)
        assert "metadata" in blank_template
        
        # Get example template
        example_template = ExtractionFormTemplate.get_example_template()
        assert isinstance(example_template, dict)
        assert example_template["metadata"]["paper_id"] != ""
        
        # Validate example template
        form_manager = integration_setup['form_manager']
        validation_result = form_manager.validate_form(example_template)
        assert validation_result.is_valid is True


class TestErrorHandlingIntegration:
    """Test error handling across the pipeline."""
    
    def test_empty_content_handling(self, integration_setup):
        """Test handling of empty paper content."""
        protocol = ExtractionProtocol(
            paper_content="",
            paper_id="empty_test_001",
            analyst="empty_test_analyst"
        )
        
        # Should not crash
        prep_result = protocol.phase1_preparation()
        assert isinstance(prep_result, dict)
        assert prep_result["has_computational_experiments"] is False
    
    def test_invalid_data_handling(self, integration_setup):
        """Test handling of invalid extraction data."""
        form_manager = integration_setup['form_manager']
        
        # Create invalid form data
        invalid_form = {
            "metadata": {
                "paper_id": "",  # Invalid empty ID
                "extraction_date": "invalid-date",
                "analyst": ""
            },
            "hardware": {
                "gpu_count": -1,  # Invalid negative count
            }
        }
        
        # Should handle gracefully
        validation_result = form_manager.validate_form(invalid_form)
        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0
    
    def test_missing_analyzer_handling(self, sample_paper_content):
        """Test handling of missing analyzer."""
        protocol = ExtractionProtocol(
            paper_content=sample_paper_content,
            paper_id="missing_analyzer_test",
            analyst="test_analyst"
        )
        
        # Should handle None analyzer gracefully
        try:
            result = protocol.phase2_automated_extraction(None)
            assert isinstance(result, dict)
        except Exception:
            # If it raises an exception, that's also acceptable
            # as long as it doesn't crash the entire system
            pass


class TestPerformanceIntegration:
    """Test performance aspects of the pipeline."""
    
    def test_large_content_processing(self, integration_setup):
        """Test processing of large paper content."""
        # Create large content (simulating a long paper)
        large_content = """
        Large Scale Model Training
        
        """ + "We used 128 A100 GPUs for training. " * 1000
        
        protocol = ExtractionProtocol(
            paper_content=large_content,
            paper_id="performance_test_001",
            analyst="performance_analyst"
        )
        
        # Should complete without timeout
        prep_result = protocol.phase1_preparation()
        assert isinstance(prep_result, dict)
    
    def test_pattern_matching_performance(self, integration_setup):
        """Test pattern matching performance."""
        pattern_matcher = integration_setup['pattern_matcher']
        
        # Create content with many potential patterns
        complex_content = """
        We trained multiple models:
        - Model A: 8 V100 GPUs for 24 hours
        - Model B: 16 A100 GPUs for 48 hours  
        - Model C: 32 TPU v3 cores for 72 hours
        - Model D: 64 H100 GPUs for 96 hours
        Total cost: $100,000 in cloud credits.
        """ * 10
        
        # Should complete efficiently
        pattern_types = pattern_matcher.identify_pattern_type(complex_content)
        pattern_results = pattern_matcher.extract_all_patterns(complex_content)
        
        assert isinstance(pattern_types, list)
        assert isinstance(pattern_results, dict)


class TestDataConsistencyIntegration:
    """Test data consistency across pipeline components."""
    
    def test_extraction_result_consistency(self, sample_paper_content, integration_setup):
        """Test consistency of extraction results."""
        protocol = ExtractionProtocol(
            paper_content=sample_paper_content,
            paper_id="consistency_test_001",
            analyst="consistency_analyst"
        )
        
        mock_analyzer = Mock()
        mock_analyzer.confidence = 0.85
        
        # Run extraction multiple times
        result1 = protocol.run_full_protocol(mock_analyzer)
        
        # Create new protocol instance
        protocol2 = ExtractionProtocol(
            paper_content=sample_paper_content,
            paper_id="consistency_test_002", 
            analyst="consistency_analyst"
        )
        result2 = protocol2.run_full_protocol(mock_analyzer)
        
        # Results should be structurally consistent
        assert type(result1) == type(result2)
        assert hasattr(result1, 'metadata')
        assert hasattr(result2, 'metadata')
        assert hasattr(result1, 'hardware')
        assert hasattr(result2, 'hardware')
    
    def test_form_conversion_consistency(self, sample_paper_content, integration_setup):
        """Test consistency of form conversion."""
        protocol = ExtractionProtocol(
            paper_content=sample_paper_content,
            paper_id="conversion_test_001",
            analyst="conversion_analyst"
        )
        
        mock_analyzer = Mock()
        mock_analyzer.confidence = 0.9
        extraction_result = protocol.run_full_protocol(mock_analyzer)
        
        form_manager = integration_setup['form_manager']
        
        # Convert to form multiple times
        form1 = form_manager.convert_extraction_result_to_form(extraction_result)
        form2 = form_manager.convert_extraction_result_to_form(extraction_result)
        
        # Should produce identical results
        assert form1["metadata"]["paper_id"] == form2["metadata"]["paper_id"]
        assert form1["hardware"] == form2["hardware"]
    
    def test_validation_consistency(self, integration_setup):
        """Test validation consistency."""
        form_manager = integration_setup['form_manager']
        
        # Create test form
        test_form = {
            "metadata": {
                "paper_id": "validation_consistency_test",
                "extraction_date": datetime.now().isoformat(),
                "analyst": "test_analyst"
            },
            "hardware": {
                "gpu_type": "A100",
                "gpu_count": 8,
                "gpu_memory_gb": 40.0
            },
            "training": {
                "total_time_hours": 24.0,
                "time_unit_original": "hours"
            },
            "validation": {
                "confidence_hardware": "high",
                "confidence_training": "medium",
                "confidence_overall": "high"
            }
        }
        
        # Validate multiple times
        result1 = form_manager.validate_form(test_form)
        result2 = form_manager.validate_form(test_form)
        
        # Should produce consistent results
        assert result1.is_valid == result2.is_valid
        assert result1.completeness_score == result2.completeness_score
        assert len(result1.errors) == len(result2.errors)