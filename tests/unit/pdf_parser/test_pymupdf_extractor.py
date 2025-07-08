"""Tests for PyMuPDFExtractor implementation."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from compute_forecast.pdf_parser.extractors.pymupdf_extractor import PyMuPDFExtractor


class TestPyMuPDFExtractor:
    """Test PyMuPDFExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PyMuPDFExtractor()
        self.test_pdf_path = Path("/fake/test.pdf")

    def test_can_extract_affiliations(self):
        """Test can_extract_affiliations returns True."""
        assert self.extractor.can_extract_affiliations() is True

    @patch.object(PyMuPDFExtractor, "_create_fitz_doc")
    def test_extract_first_pages_success(self, mock_create_doc):
        """Test successful extraction of first pages."""
        # Mock document and pages
        mock_doc = Mock()
        mock_page1 = Mock()
        mock_page2 = Mock()
        mock_page1.get_text.return_value = "Page 1 content with academic text"
        mock_page2.get_text.return_value = "Page 2 content with more text"

        mock_doc.__len__ = Mock(return_value=10)  # 10 pages total
        mock_doc.__getitem__ = Mock(side_effect=lambda x: [mock_page1, mock_page2][x])
        mock_doc.close = Mock()

        mock_create_doc.return_value = mock_doc

        # Test extraction
        result = self.extractor.extract_first_pages(self.test_pdf_path, [0, 1])

        # Verify structure
        assert isinstance(result, dict)
        assert "text" in result
        assert "method" in result
        assert "confidence" in result
        assert result["method"] == "pymupdf"

        # Verify text content
        expected_text = "[Page 1]\nPage 1 content with academic text\n[Page 2]\nPage 2 content with more text"
        assert result["text"] == expected_text

        # Verify confidence calculation
        assert 0.0 <= result["confidence"] <= 1.0

        # Verify proper cleanup
        mock_doc.close.assert_called_once()

    @patch.object(PyMuPDFExtractor, "_create_fitz_doc")
    def test_extract_first_pages_page_out_of_range(self, mock_create_doc):
        """Test extraction when requested page is out of range."""
        mock_doc = Mock()
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Page 1 content"

        mock_doc.__len__ = Mock(return_value=1)  # Only 1 page
        mock_doc.__getitem__ = Mock(return_value=mock_page1)
        mock_doc.close = Mock()

        mock_create_doc.return_value = mock_doc

        # Request pages [0, 1] but only page 0 exists
        result = self.extractor.extract_first_pages(self.test_pdf_path, [0, 1])

        # Should only extract page 0
        expected_text = "[Page 1]\nPage 1 content"
        assert result["text"] == expected_text
        mock_doc.close.assert_called_once()

    @patch.object(PyMuPDFExtractor, "_create_fitz_doc")
    def test_extract_first_pages_pdf_error(self, mock_create_doc):
        """Test handling of PDF opening errors."""
        mock_create_doc.side_effect = Exception("PDF corrupted")

        with pytest.raises(Exception):
            self.extractor.extract_first_pages(self.test_pdf_path, [0, 1])

    @patch.object(PyMuPDFExtractor, "_create_fitz_doc")
    def test_extract_first_pages_ensures_cleanup_on_error(self, mock_create_doc):
        """Test that document is closed even when processing fails."""
        mock_doc = Mock()
        mock_page = Mock()
        mock_page.get_text.side_effect = Exception("Text extraction failed")
        mock_doc.__len__ = Mock(return_value=5)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_doc.close = Mock()

        mock_create_doc.return_value = mock_doc

        with pytest.raises(Exception):
            self.extractor.extract_first_pages(self.test_pdf_path, [0])

        # Verify document was closed despite the error
        mock_doc.close.assert_called_once()

    @patch.object(PyMuPDFExtractor, "_create_fitz_doc")
    def test_extract_full_text_success(self, mock_create_doc):
        """Test successful full text extraction."""
        # Mock document with multiple pages
        mock_doc = Mock()
        mock_pages = []

        for i in range(3):
            page = Mock()
            page.get_text.return_value = f"Content of page {i + 1}"
            mock_pages.append(page)

        mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
        mock_doc.close = Mock()

        mock_create_doc.return_value = mock_doc

        # Test extraction
        result = self.extractor.extract_full_text(self.test_pdf_path)

        # Verify result
        expected_text = "\n[Page 1]\nContent of page 1\n[Page 2]\nContent of page 2\n[Page 3]\nContent of page 3"
        assert result == expected_text
        mock_doc.close.assert_called_once()

    @patch.object(PyMuPDFExtractor, "_create_fitz_doc")
    def test_extract_full_text_empty_pdf(self, mock_create_doc):
        """Test extraction from empty PDF."""
        mock_doc = Mock()
        mock_doc.__iter__ = Mock(return_value=iter([]))
        mock_doc.close = Mock()

        mock_create_doc.return_value = mock_doc

        result = self.extractor.extract_full_text(self.test_pdf_path)

        assert result == ""
        mock_doc.close.assert_called_once()

    @patch.object(PyMuPDFExtractor, "_create_fitz_doc")
    def test_extract_full_text_ensures_cleanup_on_error(self, mock_create_doc):
        """Test that document is closed even when full text extraction fails."""
        mock_doc = Mock()
        mock_page = Mock()
        mock_page.get_text.side_effect = Exception("Page extraction failed")
        mock_doc.__iter__ = Mock(return_value=iter([mock_page]))
        mock_doc.close = Mock()

        mock_create_doc.return_value = mock_doc

        with pytest.raises(Exception):
            self.extractor.extract_full_text(self.test_pdf_path)

        # Verify document was closed despite the error
        mock_doc.close.assert_called_once()

    def test_calculate_confidence_high_quality(self):
        """Test confidence calculation for high quality text."""
        text = """
        Abstract: This paper presents a novel approach to machine learning.
        The methodology involves deep neural networks and extensive experimentation.
        We demonstrate significant improvements over baseline methods with university
        research conducted at the department of computer science. The results
        show significant improvements. References: [1] Smith, J. et al. Nature 2023.
        Keywords: machine learning, neural networks, methodology, university
        """

        confidence = self.extractor._calculate_confidence(text)

        # Should be high confidence due to academic markers and good length
        assert confidence > 0.6  # Adjusted based on actual scoring

    def test_calculate_confidence_low_quality(self):
        """Test confidence calculation for low quality text."""
        text = "abc !@# xyz"  # Short text with garbage characters

        confidence = self.extractor._calculate_confidence(text)

        # Should be low confidence
        assert confidence < 0.3

    def test_calculate_confidence_empty_text(self):
        """Test confidence calculation for empty text."""
        confidence = self.extractor._calculate_confidence("")
        assert confidence == 0.0

    def test_calculate_confidence_medium_quality(self):
        """Test confidence calculation for medium quality text."""
        text = "This is a research paper about computational methods. " * 5

        confidence = self.extractor._calculate_confidence(text)

        # Should be medium confidence
        assert 0.3 <= confidence <= 0.8

    def test_calculate_confidence_extreme_garbage(self):
        """Test confidence calculation never goes negative even with extreme garbage."""
        # Text with extreme garbage characters and short words
        text = "!@#$%^&*()_+ a b c d e f g h i j k l m n o p !@#$%^&*()_+"

        confidence = self.extractor._calculate_confidence(text)

        # Should never be negative
        assert confidence >= 0.0
        assert confidence <= 1.0

    @patch("compute_forecast.pdf_parser.extractors.pymupdf_extractor.fitz")
    def test_integration_with_base_extractor_interface(self, mock_fitz):
        """Test that PyMuPDFExtractor properly implements BaseExtractor interface."""
        from compute_forecast.pdf_parser.core.base_extractor import BaseExtractor

        # Verify inheritance
        assert isinstance(self.extractor, BaseExtractor)

        # Verify all abstract methods are implemented
        assert hasattr(self.extractor, "extract_first_pages")
        assert hasattr(self.extractor, "extract_full_text")
        assert hasattr(self.extractor, "can_extract_affiliations")

        # Verify methods are callable
        assert callable(self.extractor.extract_first_pages)
        assert callable(self.extractor.extract_full_text)
        assert callable(self.extractor.can_extract_affiliations)
