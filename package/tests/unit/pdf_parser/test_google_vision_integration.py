"""Integration tests for Google Cloud Vision extractor with PDF processor."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.extractors.google_vision_extractor import GoogleCloudVisionExtractor


class TestGoogleVisionIntegration:
    """Test Google Cloud Vision integration with PDF processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor_config = {
            'extraction': {
                'max_pages': 2,
                'min_confidence': 0.5
            }
        }
        self.credentials_path = "/fake/path/to/credentials.json"
        
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_register_with_processor(self, mock_client_class):
        """Test that Google Vision extractor can be registered with processor."""
        processor = OptimizedPDFProcessor(self.processor_config)
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Register extractor at priority level 3 (fallback)
        processor.register_extractor('google_vision', extractor, level=3)
        
        assert 'google_vision' in processor.extractors
        assert processor.extractors['google_vision']['level'] == 3
        assert processor.extractors['google_vision']['extractor'] == extractor
        
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_processor_uses_google_vision_for_affiliations(self, mock_client_class):
        """Test processor can use Google Vision for affiliation extraction."""
        # Setup mocked client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        processor = OptimizedPDFProcessor(self.processor_config)
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Register as only extractor to ensure it gets used
        processor.register_extractor('google_vision', extractor, level=0)
        
        # Mock the extractor methods
        with patch.object(extractor, 'extract_first_pages') as mock_extract:
            with patch.object(extractor, 'extract_full_text') as mock_full_text:
                with patch.object(processor.validator, 'validate_affiliations') as mock_validate:
                    # Configure mocks
                    mock_extract.return_value = {
                        'affiliations': [
                            {'name': 'University of Montreal', 'type': 'academic'},
                            {'name': 'Mila - Quebec AI Institute', 'type': 'research'}
                        ],
                        'method': 'google_cloud_vision',
                        'confidence': 0.95,
                        'cost': 0.003
                    }
                    mock_full_text.return_value = "Sample paper text with computational content"
                    mock_validate.return_value = True
                    
                    # Process a fake PDF
                    result = processor.process_pdf(
                        Path("/fake/paper.pdf"),
                        {'title': 'Test Paper', 'authors': ['John Doe']}
                    )
                    
                    # Verify results
                    assert 'affiliations' in result
                    assert len(result['affiliations']) == 2
                    assert result['method'] == 'google_cloud_vision'
                    assert result['confidence'] == 0.95
                    assert 'extraction_timestamp' in result
                    
                    # Verify cost tracking
                    cost_summary = processor.get_cost_summary()
                    assert cost_summary['total_cost'] > 0
                    assert 'google_vision' in cost_summary['by_extractor']
                    
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_processor_fallback_when_google_vision_fails(self, mock_client_class):
        """Test processor falls back from Google Vision when it fails."""
        # Setup mocked client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        processor = OptimizedPDFProcessor(self.processor_config)
        
        # Create a mock fallback extractor
        fallback_extractor = Mock()
        fallback_extractor.can_extract_affiliations.return_value = True
        fallback_extractor.extract_first_pages.return_value = {
            'affiliations': [{'name': 'Fallback University', 'type': 'academic'}],
            'method': 'fallback',
            'confidence': 0.8
        }
        fallback_extractor.extract_full_text.return_value = "Fallback text"
        
        # Register extractors with Google Vision as higher priority
        google_extractor = GoogleCloudVisionExtractor(self.credentials_path)
        processor.register_extractor('google_vision', google_extractor, level=0)
        processor.register_extractor('fallback', fallback_extractor, level=1)
        
        # Mock Google Vision to fail
        with patch.object(google_extractor, 'extract_first_pages') as mock_google_extract:
            with patch.object(processor.validator, 'validate_affiliations') as mock_validate:
                # Google Vision fails validation
                mock_google_extract.return_value = {
                    'affiliations': [],
                    'method': 'google_cloud_vision',
                    'confidence': 0.2
                }
                
                # Validation fails for Google Vision but succeeds for fallback
                mock_validate.side_effect = [False, True]
                
                # Process PDF
                result = processor.process_pdf(
                    Path("/fake/paper.pdf"),
                    {'title': 'Test Paper', 'authors': ['John Doe']}
                )
                
                # Should use fallback extractor
                assert result['method'] == 'fallback'
                assert result['affiliations'][0]['name'] == 'Fallback University'
                
                # Verify both extractors were tried
                assert mock_google_extract.called
                assert fallback_extractor.extract_first_pages.called
                
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_cost_tracking_integration(self, mock_client_class):
        """Test that cost tracking works properly in processor integration."""
        # Setup mocked client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        processor = OptimizedPDFProcessor(self.processor_config)
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        processor.register_extractor('google_vision', extractor, level=0)
        
        # Mock extraction with cost
        with patch.object(extractor, 'extract_first_pages') as mock_extract:
            with patch.object(extractor, 'extract_full_text') as mock_full_text:
                with patch.object(processor.validator, 'validate_affiliations') as mock_validate:
                    mock_extract.return_value = {
                        'affiliations': [{'name': 'Test University', 'type': 'academic'}],
                        'method': 'google_cloud_vision',
                        'confidence': 0.9,
                        'cost': 0.003
                    }
                    mock_full_text.return_value = "Test content"
                    mock_validate.return_value = True
                    
                    # Process multiple PDFs to accumulate costs
                    for i in range(3):
                        processor.process_pdf(
                            Path(f"/fake/paper{i}.pdf"),
                            {'title': f'Test Paper {i}', 'authors': ['Test Author']}
                        )
                    
                    # Check cost summary
                    cost_summary = processor.get_cost_summary()
                    
                    # Should have affiliation extraction costs (3 papers) + full text costs (3 papers)
                    # Based on processor's cost mapping: google_vision affiliation=0.05, full_text=0.08
                    expected_total_cost = 0.05 * 3 + 0.08 * 3  # affiliation + full text costs
                    assert cost_summary['total_cost'] == expected_total_cost
                    assert cost_summary['by_extractor']['google_vision'] == expected_total_cost
                    assert cost_summary['total_operations'] == 6  # 3 affiliation + 3 full text
                    
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_page_limit_enforcement_in_processor(self, mock_client_class):
        """Test that page limit is enforced when used with processor."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        processor = OptimizedPDFProcessor(self.processor_config)
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        processor.register_extractor('google_vision', extractor, level=0)
        
        # Mock PDF to images and extraction
        with patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image') as mock_pdf2image:
            with patch.object(processor.validator, 'validate_affiliations') as mock_validate:
                mock_pdf2image.convert_from_path.return_value = [Mock()]  # 1 image per call
                mock_validate.return_value = True
                
                # Mock the Vision API response
                with patch('google.cloud.vision.Image'):
                    with patch('src.pdf_parser.extractors.google_vision_extractor.cv2') as mock_cv2:
                        mock_buffer = Mock()
                        mock_buffer.tobytes.return_value = b'fake_bytes'
                        mock_cv2.imencode.return_value = (True, mock_buffer)
                        
                        mock_annotation = Mock()
                        mock_annotation.description = "Test content"
                        mock_response = Mock()
                        mock_response.text_annotations = [mock_annotation]
                        mock_client.text_detection.return_value = mock_response
                        
                        # Process PDF - processor requests first 2 pages (indices 0, 1)
                        result = processor.process_pdf(
                            Path("/fake/paper.pdf"),
                            {'title': 'Test Paper', 'authors': ['Test Author']}
                        )
                        
                        # Verify only 2 pages were processed despite potentially more being available
                        assert mock_pdf2image.convert_from_path.call_count == 2
                        assert 'affiliations' in result