"""Integration tests for PyMuPDFExtractor with OptimizedPDFProcessor."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.extractors.pymupdf_extractor import PyMuPDFExtractor


class TestPyMuPDFIntegration:
    """Test PyMuPDFExtractor integration with the PDF processor framework."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"test": True}
        self.processor = OptimizedPDFProcessor(self.config)
        self.test_pdf_path = Path('/fake/test.pdf')
        self.paper_metadata = {
            'title': 'Test Paper',
            'authors': ['John Doe', 'Jane Smith']
        }
    
    @patch.object(PyMuPDFExtractor, '_create_fitz_doc')
    def test_register_and_use_pymupdf_extractor(self, mock_create_doc):
        """Test registering PyMuPDFExtractor with processor and using it."""
        # Create and register extractor
        extractor = PyMuPDFExtractor()
        self.processor.register_extractor('pymupdf', extractor, level=1)
        
        # Mock document for affiliation extraction
        mock_doc = Mock()
        mock_page1 = Mock()
        mock_page2 = Mock()
        mock_page1.get_text.return_value = "Page 1: John Doe, University of Test"
        mock_page2.get_text.return_value = "Page 2: Jane Smith, Research Institute"
        
        mock_doc.__len__ = Mock(return_value=5)
        mock_doc.__getitem__ = Mock(side_effect=lambda x: [mock_page1, mock_page2][x])
        mock_doc.__iter__ = Mock(return_value=iter([mock_page1, mock_page2]))  # For full text
        mock_doc.close = Mock()
        
        mock_create_doc.return_value = mock_doc
        
        # Mock the affiliation validation to pass
        with patch.object(self.processor.validator, 'validate_affiliations', return_value=True):
            # Process PDF
            result = self.processor.process_pdf(self.test_pdf_path, self.paper_metadata)
        
        # Verify results
        assert 'affiliations' in result
        assert 'full_text' in result
        assert 'computational_specs' in result
        assert 'extraction_timestamp' in result
        
        # Verify PyMuPDF was used
        assert result.get('method') == 'pymupdf'
        assert result.get('confidence', 0) > 0
        
        # Verify document cleanup
        assert mock_doc.close.call_count >= 2  # Called for both affiliation and full text
    
    @patch.object(PyMuPDFExtractor, '_create_fitz_doc')
    def test_pymupdf_fallback_behavior(self, mock_create_doc):
        """Test PyMuPDF as fallback when other extractors fail."""
        # Create a mock extractor that fails
        failing_extractor = Mock()
        failing_extractor.can_extract_affiliations.return_value = True
        failing_extractor.extract_first_pages.side_effect = Exception("Extractor failed")
        
        # Register failing extractor at higher priority
        self.processor.register_extractor('failing_extractor', failing_extractor, level=0)
        
        # Register PyMuPDF as fallback
        extractor = PyMuPDFExtractor()
        self.processor.register_extractor('pymupdf', extractor, level=1)
        
        # Mock successful PyMuPDF extraction
        mock_doc = Mock()
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Successful extraction from PyMuPDF"
        
        mock_doc.__len__ = Mock(return_value=2)
        mock_doc.__getitem__ = Mock(return_value=mock_page1)
        mock_doc.__iter__ = Mock(return_value=iter([mock_page1]))
        mock_doc.close = Mock()
        
        mock_create_doc.return_value = mock_doc
        
        # Mock validation to pass for PyMuPDF
        with patch.object(self.processor.validator, 'validate_affiliations', return_value=True):
            # Also need to mock full text extraction to return a string
            with patch.object(self.processor, '_extract_full_text', return_value="Successful extraction from PyMuPDF"):
                result = self.processor.process_pdf(self.test_pdf_path, self.paper_metadata)
        
        # Verify PyMuPDF was used as fallback
        assert result.get('method') == 'pymupdf'
        assert 'Successful extraction from PyMuPDF' in result.get('full_text', '')
    
    def test_pymupdf_cost_tracking(self):
        """Test that PyMuPDF operations are correctly tracked as free."""
        extractor = PyMuPDFExtractor()
        self.processor.register_extractor('pymupdf', extractor, level=1)
        
        # Check initial cost
        cost_summary = self.processor.get_cost_summary()
        assert cost_summary['total_cost'] == 0.0
        
        # Test cost calculation for PyMuPDF operations
        cost = self.processor._calculate_extraction_cost('pymupdf', 'affiliation_extraction', {})
        assert cost == 0.0
        
        cost = self.processor._calculate_extraction_cost('pymupdf', 'full_text', {})
        assert cost == 0.0
    
    def test_pymupdf_can_extract_affiliations(self):
        """Test that PyMuPDF correctly reports affiliation extraction capability."""
        extractor = PyMuPDFExtractor()
        self.processor.register_extractor('pymupdf', extractor, level=1)
        
        # Verify PyMuPDF is included in affiliation-capable extractors
        affiliation_extractors = [
            (info['level'], name, info['extractor'])
            for name, info in self.processor.extractors.items()
            if info['extractor'].can_extract_affiliations()
        ]
        
        assert len(affiliation_extractors) == 1
        assert affiliation_extractors[0][1] == 'pymupdf'
        assert affiliation_extractors[0][2] == extractor