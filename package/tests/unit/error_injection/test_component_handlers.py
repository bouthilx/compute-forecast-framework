"""Tests for component-specific error handlers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from src.testing.error_injection.component_handlers.collector_errors import CollectorErrorHandler
from src.testing.error_injection.component_handlers.analyzer_errors import AnalyzerErrorHandler
from src.testing.error_injection.component_handlers.reporter_errors import ReporterErrorHandler
from src.testing.error_injection.injection_framework import ErrorType


class TestCollectorErrorHandler:
    """Test suite for CollectorErrorHandler."""
    
    def test_simulate_api_timeout(self):
        """Test API timeout simulation."""
        handler = CollectorErrorHandler()
        mock_api = Mock()
        
        # Configure API to raise timeout
        handler.register_api("semantic_scholar", mock_api)
        handler.simulate_api_timeout("semantic_scholar")
        
        # Verify API was configured to timeout
        assert handler._active_errors["semantic_scholar"] == ErrorType.API_TIMEOUT
    
    def test_simulate_rate_limit(self):
        """Test rate limit simulation."""
        handler = CollectorErrorHandler()
        mock_api = Mock()
        
        # Configure API to hit rate limit
        handler.register_api("openalex", mock_api)
        handler.simulate_rate_limit("openalex")
        
        # Verify rate limit was set
        assert handler._active_errors["openalex"] == ErrorType.API_RATE_LIMIT
    
    def test_verify_fallback_behavior(self):
        """Test fallback behavior verification."""
        handler = CollectorErrorHandler()
        
        # Setup APIs with one failed
        handler.register_api("semantic_scholar", Mock())
        handler.register_api("openalex", Mock())
        handler.register_api("crossref", Mock())
        
        # Simulate failure in one API
        handler.simulate_api_timeout("semantic_scholar")
        
        # Configure fallback behavior
        handler.set_fallback_order(["semantic_scholar", "openalex", "crossref"])
        
        # Verify fallback works
        result = handler.verify_fallback_behavior()
        assert result is True
        assert handler.get_active_api() == "openalex"
    
    def test_simulate_auth_failure(self):
        """Test authentication failure simulation."""
        handler = CollectorErrorHandler()
        mock_api = Mock()
        
        handler.register_api("crossref", mock_api)
        handler.simulate_auth_failure("crossref")
        
        assert handler._active_errors["crossref"] == ErrorType.API_AUTH_FAILURE
    
    def test_clear_error(self):
        """Test error clearing."""
        handler = CollectorErrorHandler()
        mock_api = Mock()
        
        handler.register_api("semantic_scholar", mock_api)
        handler.simulate_api_timeout("semantic_scholar")
        
        # Clear the error
        handler.clear_error("semantic_scholar")
        
        assert "semantic_scholar" not in handler._active_errors


class TestAnalyzerErrorHandler:
    """Test suite for AnalyzerErrorHandler."""
    
    def test_simulate_corrupted_input(self):
        """Test corrupted input simulation."""
        handler = AnalyzerErrorHandler()
        
        # Simulate various corruption types
        handler.simulate_corrupted_input("missing_fields")
        assert handler._active_corruption_type == "missing_fields"
        
        handler.simulate_corrupted_input("invalid_format")
        assert handler._active_corruption_type == "invalid_format"
        
        handler.simulate_corrupted_input("encoding_error")
        assert handler._active_corruption_type == "encoding_error"
    
    def test_simulate_memory_pressure(self):
        """Test memory pressure simulation."""
        handler = AnalyzerErrorHandler()
        
        # Configure memory limits
        handler.set_memory_limit_mb(100)
        handler.simulate_memory_pressure()
        
        assert handler._memory_pressure_active is True
        assert handler.get_available_memory_mb() < 100
    
    def test_verify_partial_analysis(self):
        """Test partial analysis verification."""
        handler = AnalyzerErrorHandler()
        
        # Setup test data
        total_papers = 100
        handler.set_total_papers(total_papers)
        
        # Simulate processing with memory pressure
        handler.simulate_memory_pressure()
        handler.process_papers_batch(50)  # Process only half
        
        result = handler.verify_partial_analysis()
        
        assert result["partial_results_available"] is True
        assert result["papers_processed"] == 50
        assert result["papers_skipped"] == 50
        assert result["completion_percentage"] == 50.0
    
    def test_simulate_processing_error(self):
        """Test processing error simulation."""
        handler = AnalyzerErrorHandler()
        
        # Configure error injection with high rate to ensure errors
        handler.set_error_rate(0.5)  # 50% error rate
        handler.simulate_processing_errors()
        
        # Process multiple batches to ensure we get errors
        total_errors = 0
        for _ in range(5):  # Try 5 batches
            results = handler.process_papers_batch(10)
            total_errors += len(results["errors"])
        
        assert handler._processing_errors_active is True
        assert total_errors > 0  # Should have some errors across batches


class TestReporterErrorHandler:
    """Test suite for ReporterErrorHandler."""
    
    def test_simulate_output_failure(self):
        """Test output failure simulation."""
        handler = ReporterErrorHandler()
        
        # Configure output path
        handler.set_output_path("/test/output")
        handler.simulate_output_failure("permission_denied")
        
        assert handler._output_error_type == "permission_denied"
        assert handler.can_write_output() is False
    
    def test_simulate_disk_full(self):
        """Test disk full simulation."""
        handler = ReporterErrorHandler()
        
        handler.set_output_path("/test/output")
        handler.simulate_disk_full()
        
        assert handler._output_error_type == "disk_full"
        assert handler.get_available_space_mb() == 0
    
    def test_verify_alternative_output(self):
        """Test alternative output verification."""
        handler = ReporterErrorHandler()
        
        # Setup primary and alternative outputs
        handler.set_output_path("/primary/output")
        handler.add_alternative_output("/backup/output", "backup")
        handler.add_alternative_output("memory://", "memory")
        
        # Simulate primary failure
        handler.simulate_output_failure("permission_denied")
        
        # Verify alternative output works
        result = handler.verify_alternative_output()
        
        assert result["alternative_available"] is True
        assert result["active_output"] == "backup"
        assert result["output_type"] == "file"
    
    def test_simulate_format_error(self):
        """Test format error simulation."""
        handler = ReporterErrorHandler()
        
        handler.simulate_format_error("json")
        
        # Try to format data
        test_data = {"key": "value"}
        result = handler.format_output(test_data, "json")
        
        assert result is None  # Format should fail
        assert handler.get_last_error() is not None
    
    def test_recovery_from_output_error(self):
        """Test recovery from output errors."""
        handler = ReporterErrorHandler()
        
        # Setup outputs
        handler.set_output_path("/primary/output")
        # For disk_full recovery, need non-file alternative
        handler.add_alternative_output("memory://", "memory", "memory")
        
        # Simulate failure and recovery
        handler.simulate_disk_full()
        
        # Attempt recovery
        recovery_result = handler.attempt_recovery()
        
        assert recovery_result["recovered"] is True
        assert recovery_result["recovery_method"] == "alternative_output"
        assert handler.can_write_output() is True  # Can write to alternative
        assert handler.get_available_space_mb() == 0  # But disk still full