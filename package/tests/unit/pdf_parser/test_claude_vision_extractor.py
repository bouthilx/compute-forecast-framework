"""Tests for Claude Vision extractor."""

import json
import base64
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.pdf_parser.extractors.claude_vision_extractor import ClaudeVisionExtractor


class TestClaudeVisionExtractor:
    """Test suite for Claude Vision extractor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"
        self.extractor = ClaudeVisionExtractor(self.api_key)
        self.sample_pdf_path = Path("/tmp/test_paper.pdf")
        
    def test_initialization(self):
        """Test extractor initialization."""
        assert self.extractor.api_key == self.api_key
        assert self.extractor.model == 'claude-3-haiku-20240307'
        assert self.extractor.client is not None
        
    def test_can_extract_affiliations(self):
        """Test that extractor can extract affiliations."""
        assert self.extractor.can_extract_affiliations() is True
        
    @patch('src.pdf_parser.extractors.claude_vision_extractor.fitz')
    def test_pdf_to_images_success(self, mock_fitz):
        """Test successful PDF to image conversion."""
        # Mock PyMuPDF
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b'fake_image_data'
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__len__.return_value = 2
        mock_doc.__enter__.return_value = mock_doc  # Context manager support
        mock_doc.__exit__.return_value = None
        mock_fitz.open.return_value = mock_doc
        
        images = self.extractor._pdf_to_images(self.sample_pdf_path, [0, 1])
        
        assert len(images) == 2
        mock_fitz.open.assert_called_once_with(self.sample_pdf_path)
        assert mock_page.get_pixmap.call_count == 2
        
    @patch('src.pdf_parser.extractors.claude_vision_extractor.fitz')
    def test_pdf_to_images_failure(self, mock_fitz):
        """Test PDF to image conversion failure."""
        mock_fitz.open.side_effect = Exception("PDF read error")
        
        with pytest.raises(Exception, match="PDF read error"):
            self.extractor._pdf_to_images(self.sample_pdf_path, [0])
            
    def test_build_affiliation_prompt(self):
        """Test affiliation prompt building."""
        prompt = self.extractor._build_affiliation_prompt()
        
        assert "extract author names" in prompt.lower()
        assert "institutional affiliations" in prompt.lower()
        assert "json" in prompt.lower()
        assert "confidence" in prompt.lower()
        
    def test_parse_claude_response_valid_json(self):
        """Test parsing valid JSON response."""
        response_text = """Here's the extraction:
        {
            "authors_with_affiliations": [
                {"name": "John Doe", "affiliation": "MIT", "email": "john@mit.edu"}
            ],
            "all_affiliations": ["MIT"],
            "confidence": 0.9
        }
        """
        
        result = self.extractor._parse_claude_response(response_text)
        
        assert len(result['authors_with_affiliations']) == 1
        assert result['authors_with_affiliations'][0]['name'] == "John Doe"
        assert result['all_affiliations'] == ["MIT"]
        assert result['confidence'] == 0.9
        
    def test_parse_claude_response_invalid_json(self):
        """Test parsing invalid JSON response."""
        response_text = "This is not valid JSON response"
        
        result = self.extractor._parse_claude_response(response_text)
        
        assert result['affiliations'] == []
        assert result['confidence'] == 0.0
        
    def test_parse_claude_response_no_json(self):
        """Test parsing response with no JSON."""
        response_text = "I couldn't extract affiliations from this document."
        
        result = self.extractor._parse_claude_response(response_text)
        
        assert result['affiliations'] == []
        assert result['confidence'] == 0.0
        
    @patch('src.pdf_parser.extractors.claude_vision_extractor.fitz')
    @patch.object(ClaudeVisionExtractor, '_parse_claude_response')
    def test_extract_first_pages_success(self, mock_parse, mock_fitz):
        """Test successful first pages extraction."""
        # Mock PDF to images
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b'fake_image_data'
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__len__.return_value = 2
        mock_doc.__enter__.return_value = mock_doc  # Context manager support
        mock_doc.__exit__.return_value = None
        mock_fitz.open.return_value = mock_doc
        
        # Mock Claude API response
        mock_response = MagicMock()
        mock_response_content = MagicMock()
        mock_response_content.text = '{"affiliations": ["MIT"], "confidence": 0.9}'
        mock_response.content = [mock_response_content]
        
        self.extractor.client.messages.create = MagicMock(return_value=mock_response)
        
        # Mock response parsing
        mock_parse.return_value = {
            'authors_with_affiliations': [{'name': 'John Doe', 'affiliation': 'MIT'}],
            'all_affiliations': ['MIT'],
            'confidence': 0.9
        }
        
        result = self.extractor.extract_first_pages(self.sample_pdf_path, [0, 1])
        
        assert result['method'] == 'claude_vision'
        assert result['confidence'] == 0.9
        assert 'cost' in result
        assert 'affiliations' in result
        
    @patch('src.pdf_parser.extractors.claude_vision_extractor.fitz')
    def test_extract_first_pages_api_failure(self, mock_fitz):
        """Test first pages extraction with API failure."""
        # Mock PDF to images
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b'fake_image_data'
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__len__.return_value = 2
        mock_doc.__enter__.return_value = mock_doc  # Context manager support
        mock_doc.__exit__.return_value = None
        mock_fitz.open.return_value = mock_doc
        
        # Mock API failure
        self.extractor.client.messages.create = MagicMock(side_effect=Exception("API Error"))
        
        with pytest.raises(Exception, match="API Error"):
            self.extractor.extract_first_pages(self.sample_pdf_path, [0, 1])
            
    def test_extract_full_text_not_implemented(self):
        """Test that full text extraction raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Use PyMuPDF for full document extraction"):
            self.extractor.extract_full_text(self.sample_pdf_path)
            
    def test_calculate_cost(self):
        """Test cost calculation."""
        cost = self.extractor._calculate_cost(2)  # 2 images
        
        assert cost == 0.10  # Cost per 2-page extraction
        
    def test_calculate_cost_single_page(self):
        """Test cost calculation for single page."""
        cost = self.extractor._calculate_cost(1)  # 1 image
        
        assert cost == 0.10  # Still charges for 2-page extraction
        
    @patch('src.pdf_parser.extractors.claude_vision_extractor.fitz')
    def test_integration_with_base_extractor_interface(self, mock_fitz):
        """Test that extractor properly implements BaseExtractor interface."""
        from src.pdf_parser.core.base_extractor import BaseExtractor
        
        assert isinstance(self.extractor, BaseExtractor)
        
        # Test required methods exist
        assert hasattr(self.extractor, 'extract_first_pages')
        assert hasattr(self.extractor, 'extract_full_text')
        assert hasattr(self.extractor, 'can_extract_affiliations')
        
        # Test method signatures
        assert callable(self.extractor.extract_first_pages)
        assert callable(self.extractor.extract_full_text) 
        assert callable(self.extractor.can_extract_affiliations)
        
    def test_fallback_parsing_no_affiliations(self):
        """Test fallback parsing when response indicates no affiliations."""
        response = "I cannot find any clear affiliations in this document."
        
        result = self.extractor._fallback_parsing(response)
        
        assert result['affiliations'] == []
        assert result['confidence'] == 0.0
        
    def test_fallback_parsing_generic_text(self):
        """Test fallback parsing with generic text."""
        response = "This is some generic text without clear indicators."
        
        result = self.extractor._fallback_parsing(response)
        
        assert result['affiliations'] == []
        assert result['confidence'] == 0.0
        
    def test_parse_claude_response_partial_json(self):
        """Test parsing response with partial/incomplete JSON."""
        response_text = '{"authors_with_affiliations": [{"name": "John"}]}'  # Missing required fields
        
        result = self.extractor._parse_claude_response(response_text)
        
        assert result['affiliations'] == []
        assert result['confidence'] == 0.0
        
    @patch('src.pdf_parser.extractors.claude_vision_extractor.fitz')
    def test_pdf_to_images_page_out_of_range(self, mock_fitz):
        """Test PDF to images when requested page is out of range."""
        # Mock PyMuPDF
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b'fake_image_data'
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__len__.return_value = 1  # Only 1 page
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None
        mock_fitz.open.return_value = mock_doc
        
        images = self.extractor._pdf_to_images(self.sample_pdf_path, [0, 1, 2])  # Request 3 pages
        
        assert len(images) == 1  # Only first page should be processed