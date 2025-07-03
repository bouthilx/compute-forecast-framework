"""Integration tests for Claude Vision extractor with PDF processor."""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.extractors.claude_vision_extractor import ClaudeVisionExtractor


class TestClaudeVisionIntegration:
    """Test Claude Vision extractor integration with PDF processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"
        self.extractor = ClaudeVisionExtractor(self.api_key)
        self.processor = OptimizedPDFProcessor({})
        self.sample_pdf_path = Path("/tmp/test_paper.pdf")
        
    def test_processor_registration(self):
        """Test registering Claude Vision extractor with processor."""
        self.processor.register_extractor("claude_vision", self.extractor, level=1)
        
        assert "claude_vision" in self.processor.extractors
        assert self.processor.extractors["claude_vision"]["level"] == 1
        assert self.processor.extractors["claude_vision"]["extractor"] == self.extractor
        
    @patch('src.pdf_parser.extractors.claude_vision_extractor.fitz')
    def test_affiliation_extraction_priority(self, mock_fitz):
        """Test that Claude Vision is used for affiliation extraction when registered."""
        # Mock PDF to images
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b'fake_image_data'
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__len__.return_value = 2
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None
        mock_fitz.open.return_value = mock_doc
        
        # Mock Claude API response
        mock_response = MagicMock()
        mock_response_content = MagicMock()
        mock_response_content.text = '''
        {
            "authors_with_affiliations": [
                {"name": "John Doe", "affiliation": "MIT", "email": "john@mit.edu"}
            ],
            "all_affiliations": ["MIT"],
            "confidence": 0.9
        }
        '''
        mock_response.content = [mock_response_content]
        self.extractor.client.messages.create = MagicMock(return_value=mock_response)
        
        # Register extractor
        self.processor.register_extractor("claude_vision", self.extractor, level=1)
        
        # Mock validation to pass
        with patch.object(self.processor.validator, 'validate_affiliations', return_value=True):
            # Test affiliation extraction
            paper_metadata = {"title": "Test Paper", "authors": ["John Doe"]}
            result = self.processor._extract_affiliations(self.sample_pdf_path, paper_metadata)
            
            assert result["method"] == "claude_vision"
            assert result["confidence"] == 0.9
            assert len(result["affiliations"]) == 1
            assert result["affiliations"][0] == "MIT"
        
    def test_cost_tracking_integration(self):
        """Test that cost tracking works with processor."""
        # Register extractor
        self.processor.register_extractor("claude_vision", self.extractor, level=1)
        
        # Mock a successful extraction with cost
        with patch.object(self.extractor, 'extract_first_pages') as mock_extract:
            mock_extract.return_value = {
                'affiliations': ['MIT'],
                'authors_with_affiliations': [{'name': 'John Doe', 'affiliation': 'MIT'}],
                'method': 'claude_vision',
                'confidence': 0.9,
                'cost': 0.10
            }
            
            # Mock validation to pass
            with patch.object(self.processor.validator, 'validate_affiliations', return_value=True):
                paper_metadata = {"title": "Test Paper"}
                result = self.processor._extract_affiliations(self.sample_pdf_path, paper_metadata)
                
                # Check that cost was recorded
                cost_summary = self.processor.get_cost_summary()
                assert cost_summary['total_cost'] > 0
                assert 'claude_vision' in cost_summary['by_extractor']
                
    def test_fallback_behavior(self):
        """Test that processor falls back when Claude Vision fails."""
        # Create a mock fallback extractor
        fallback_extractor = Mock()
        fallback_extractor.can_extract_affiliations.return_value = True
        fallback_extractor.extract_first_pages.return_value = {
            'affiliations': ['Fallback University'],
            'method': 'fallback',
            'confidence': 0.7
        }
        
        # Register both extractors (Claude Vision at level 1, fallback at level 2)
        self.processor.register_extractor("claude_vision", self.extractor, level=1)
        self.processor.register_extractor("fallback", fallback_extractor, level=2)
        
        # Mock Claude Vision to fail
        with patch.object(self.extractor, 'extract_first_pages', side_effect=Exception("API Error")):
            # Mock validation to pass for fallback
            with patch.object(self.processor.validator, 'validate_affiliations', return_value=True):
                paper_metadata = {"title": "Test Paper"}
                result = self.processor._extract_affiliations(self.sample_pdf_path, paper_metadata)
                
                # Should use fallback extractor
                assert result["method"] == "fallback"
                assert result["affiliations"] == ["Fallback University"]
                
    def test_validation_failure_triggers_fallback(self):
        """Test that validation failure causes fallback to next extractor."""
        # Mock Claude Vision to return low-confidence result
        with patch.object(self.extractor, 'extract_first_pages') as mock_extract:
            mock_extract.return_value = {
                'affiliations': ['Uncertain University'],
                'method': 'claude_vision',
                'confidence': 0.3  # Low confidence
            }
            
            # Create fallback extractor
            fallback_extractor = Mock()
            fallback_extractor.can_extract_affiliations.return_value = True
            fallback_extractor.extract_first_pages.return_value = {
                'affiliations': ['Better University'],
                'method': 'fallback',
                'confidence': 0.8
            }
            
            # Register both extractors
            self.processor.register_extractor("claude_vision", self.extractor, level=1)
            self.processor.register_extractor("fallback", fallback_extractor, level=2)
            
            # Mock validation to fail for Claude, pass for fallback
            def validation_side_effect(result, metadata):
                return result.get('confidence', 0) > 0.5
                
            with patch.object(self.processor.validator, 'validate_affiliations', side_effect=validation_side_effect):
                paper_metadata = {"title": "Test Paper"}
                result = self.processor._extract_affiliations(self.sample_pdf_path, paper_metadata)
                
                # Should use fallback due to validation failure
                assert result["method"] == "fallback"
                assert result["affiliations"] == ["Better University"]