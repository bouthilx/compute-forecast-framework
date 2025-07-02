"""Tests for PDF discovery exceptions."""

import pytest

from src.pdf_discovery.utils.exceptions import (
    PDFDiscoveryError,
    APIError,
    NoResultsError,
    NoPDFFoundError,
    RateLimitError
)


class TestPDFDiscoveryExceptions:
    """Tests for custom PDF discovery exceptions."""
    
    def test_pdf_discovery_error_base(self):
        """Test base PDFDiscoveryError exception."""
        error = PDFDiscoveryError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)
    
    def test_api_error_inheritance(self):
        """Test APIError inherits from PDFDiscoveryError."""
        error = APIError("API failed", status_code=500, response_text="Server error")
        assert isinstance(error, PDFDiscoveryError)
        assert str(error) == "API failed"
        assert error.status_code == 500
        assert error.response_text == "Server error"
    
    def test_api_error_without_details(self):
        """Test APIError with minimal information."""
        error = APIError("Simple API error")
        assert str(error) == "Simple API error"
        assert error.status_code is None
        assert error.response_text is None
    
    def test_no_results_error(self):
        """Test NoResultsError exception."""
        error = NoResultsError("No search results", query="test query")
        assert isinstance(error, PDFDiscoveryError)
        assert str(error) == "No search results"
        assert error.query == "test query"
    
    def test_no_pdf_found_error(self):
        """Test NoPDFFoundError exception."""
        error = NoPDFFoundError("PDF not available", results_count=5)
        assert isinstance(error, PDFDiscoveryError)
        assert str(error) == "PDF not available"
        assert error.results_count == 5
    
    def test_rate_limit_error(self):
        """Test RateLimitError exception."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        assert isinstance(error, PDFDiscoveryError)
        assert str(error) == "Rate limit exceeded"
        assert error.retry_after == 60
    
    def test_exception_with_cause(self):
        """Test exception with underlying cause."""
        original = ValueError("Original error")
        try:
            raise APIError("Wrapped error") from original
        except APIError as error:
            assert str(error) == "Wrapped error"
            assert error.__cause__ is original