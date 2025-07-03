"""Tests for Google Cloud Vision extractor."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from google.api_core.exceptions import ServiceUnavailable, DeadlineExceeded
from src.pdf_parser.extractors.google_vision_extractor import GoogleCloudVisionExtractor


class TestGoogleCloudVisionExtractor:
    """Test Google Cloud Vision extractor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.credentials_path = "/fake/path/to/credentials.json"
        
    @patch('google.cloud.vision.ImageAnnotatorClient')
    @patch.dict('os.environ', {}, clear=False)
    def test_init_sets_credentials(self, mock_client_class):
        """Test that initializer sets up credentials correctly."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Check that the environment variable was set
        import os
        assert os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') == self.credentials_path
        mock_client_class.assert_called_once()
        assert extractor.client == mock_client
        assert extractor.page_limit == 2
        
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_can_extract_affiliations_returns_true(self, mock_client_class):
        """Test that Google Cloud Vision can extract affiliations."""
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        assert extractor.can_extract_affiliations() is True
            
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_extract_full_text_raises_not_implemented(self, mock_client_class):
        """Test that full text extraction is not implemented due to cost."""
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        with pytest.raises(NotImplementedError, match="Use PyMuPDF for full document extraction"):
            extractor.extract_full_text(Path("/fake/path.pdf"))
            
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('src.pdf_parser.extractors.google_vision_extractor.cv2')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_extract_first_pages_limits_to_page_limit(self, mock_client_class, mock_cv2, mock_pdf2image):
        """Test that extraction is limited to first 2 pages."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Mock pdf2image to return images
        mock_pdf2image.convert_from_path.return_value = [Mock()]
        
        # Mock cv2.imencode
        mock_buffer = Mock()
        mock_buffer.tobytes.return_value = b'fake_image_bytes'
        mock_cv2.imencode.return_value = (True, mock_buffer)
        
        # Mock Vision API response
        mock_annotation = Mock()
        mock_annotation.description = "Page text content"
        mock_response = Mock()
        mock_response.text_annotations = [mock_annotation]
        mock_client.text_detection.return_value = mock_response
        
        # Mock vision.Image
        with patch('google.cloud.vision.Image') as mock_image_class:
            mock_image_class.return_value = Mock()
            result = extractor.extract_first_pages(Path("/fake/path.pdf"), [0, 1, 2, 3, 4])
        
        # Should only process first 2 pages (indices 0, 1)
        assert mock_pdf2image.convert_from_path.call_count == 2
        assert result['pages_processed'] == 2
            
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('src.pdf_parser.extractors.google_vision_extractor.cv2')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_extract_first_pages_successful_extraction(self, mock_client_class, mock_cv2, mock_pdf2image):
        """Test successful text extraction from pages."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Mock pdf2image to return images for each page
        mock_pdf2image.convert_from_path.side_effect = [[Mock()], [Mock()]]
        
        # Mock cv2.imencode
        mock_buffer = Mock()
        mock_buffer.tobytes.return_value = b'fake_image_bytes'
        mock_cv2.imencode.return_value = (True, mock_buffer)
        
        # Mock Vision API responses
        mock_annotation1 = Mock()
        mock_annotation1.description = "Page 1 text content"
        mock_response1 = Mock()
        mock_response1.text_annotations = [mock_annotation1]
        
        mock_annotation2 = Mock()
        mock_annotation2.description = "Page 2 text content"
        mock_response2 = Mock()
        mock_response2.text_annotations = [mock_annotation2]
        
        mock_client.text_detection.side_effect = [mock_response1, mock_response2]
        
        # Mock vision.Image
        with patch('google.cloud.vision.Image') as mock_image_class:
            mock_image_class.return_value = Mock()
            result = extractor.extract_first_pages(Path("/fake/path.pdf"), [0, 1])
        
        expected_text = "[Page 1]\nPage 1 text content\n[Page 2]\nPage 2 text content"
        assert result['text'] == expected_text
        assert result['method'] == 'google_cloud_vision'
        assert result['confidence'] == 0.9
        assert result['cost'] == 0.003  # 2 pages * 0.0015
        assert result['pages_processed'] == 2
        assert 'extraction_time' in result
            
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('src.pdf_parser.extractors.google_vision_extractor.cv2')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_extract_first_pages_no_text_found(self, mock_client_class, mock_cv2, mock_pdf2image):
        """Test extraction when no text is found."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Mock pdf2image to return an image
        mock_pdf2image.convert_from_path.return_value = [Mock()]
        
        # Mock cv2.imencode
        mock_buffer = Mock()
        mock_buffer.tobytes.return_value = b'fake_image_bytes'
        mock_cv2.imencode.return_value = (True, mock_buffer)
        
        # Mock Vision API response with no text
        mock_response = Mock()
        mock_response.text_annotations = []
        mock_client.text_detection.return_value = mock_response
        
        # Mock vision.Image
        with patch('google.cloud.vision.Image') as mock_image_class:
            mock_image_class.return_value = Mock()
            result = extractor.extract_first_pages(Path("/fake/path.pdf"), [0])
        
        assert result['text'] == ""
        assert result['pages_processed'] == 1
        assert result['cost'] == 0.0015
        assert 'extraction_time' in result
            
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_pdf_to_images_conversion(self, mock_client_class, mock_pdf2image):
        """Test PDF to images conversion."""
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        mock_images = [Mock(), Mock()]
        mock_pdf2image.convert_from_path.return_value = mock_images
        
        result = extractor._pdf_to_images(Path("/fake/path.pdf"), [0, 1])
        
        mock_pdf2image.convert_from_path.assert_called_once_with(
            Path("/fake/path.pdf"),
            first_page=1,  # pdf2image uses 1-based indexing
            last_page=2
        )
        assert result == mock_images
        
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_pdf_to_images_single_page(self, mock_client_class, mock_pdf2image):
        """Test PDF to images conversion for single page."""
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        mock_images = [Mock()]
        mock_pdf2image.convert_from_path.return_value = mock_images
        
        result = extractor._pdf_to_images(Path("/fake/path.pdf"), [1])
        
        mock_pdf2image.convert_from_path.assert_called_once_with(
            Path("/fake/path.pdf"),
            first_page=2,  # pdf2image uses 1-based indexing
            last_page=2
        )
        assert result == mock_images
        
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('src.pdf_parser.extractors.google_vision_extractor.cv2')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_extract_with_retry_on_service_unavailable(self, mock_client_class, mock_cv2, mock_pdf2image):
        """Test that API calls are retried on ServiceUnavailable errors."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Mock pdf2image to return an image
        mock_pdf2image.convert_from_path.return_value = [Mock()]
        
        # Mock cv2.imencode
        mock_buffer = Mock()
        mock_buffer.tobytes.return_value = b'fake_image_bytes'
        mock_cv2.imencode.return_value = (True, mock_buffer)
        
        # Mock Vision API to fail twice then succeed
        mock_annotation = Mock()
        mock_annotation.description = "Page text after retry"
        mock_response = Mock()
        mock_response.text_annotations = [mock_annotation]
        
        mock_client.text_detection.side_effect = [
            ServiceUnavailable("Service temporarily unavailable"),
            ServiceUnavailable("Service temporarily unavailable"),
            mock_response
        ]
        
        # Mock vision.Image
        with patch('google.cloud.vision.Image') as mock_image_class:
            mock_image_class.return_value = Mock()
            result = extractor.extract_first_pages(Path("/fake/path.pdf"), [0])
        
        assert result['text'] == "[Page 1]\nPage text after retry"
        assert mock_client.text_detection.call_count == 3
            
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('src.pdf_parser.extractors.google_vision_extractor.cv2')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_extract_fails_after_max_retries(self, mock_client_class, mock_cv2, mock_pdf2image):
        """Test that extraction fails gracefully after max retries."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Mock pdf2image to return an image
        mock_pdf2image.convert_from_path.return_value = [Mock()]
        
        # Mock cv2.imencode
        mock_buffer = Mock()
        mock_buffer.tobytes.return_value = b'fake_image_bytes'
        mock_cv2.imencode.return_value = (True, mock_buffer)
            
        # Mock Vision API to always fail
        mock_client.text_detection.side_effect = ServiceUnavailable("Service unavailable")
        
        # Mock vision.Image
        with patch('google.cloud.vision.Image') as mock_image_class:
            mock_image_class.return_value = Mock()
            result = extractor.extract_first_pages(Path("/fake/path.pdf"), [0])
        
        # Should have empty result after retries exhausted
        assert result['text'] == ""
        assert result['pages_processed'] == 0
        # Should have tried 3 times (initial + 2 retries)
        assert mock_client.text_detection.call_count == 3
            
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('src.pdf_parser.extractors.google_vision_extractor.cv2')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_extract_tracks_processing_time(self, mock_client_class, mock_cv2, mock_pdf2image):
        """Test that extraction tracks processing time."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Mock pdf2image to return an image
        mock_pdf2image.convert_from_path.return_value = [Mock()]
        
        # Mock cv2.imencode
        mock_buffer = Mock()
        mock_buffer.tobytes.return_value = b'fake_image_bytes'
        mock_cv2.imencode.return_value = (True, mock_buffer)
            
        # Mock Vision API response
        mock_annotation = Mock()
        mock_annotation.description = "Page text content"
        mock_response = Mock()
        mock_response.text_annotations = [mock_annotation]
        mock_client.text_detection.return_value = mock_response
        
        # Mock vision.Image
        with patch('google.cloud.vision.Image') as mock_image_class:
            mock_image_class.return_value = Mock()
            result = extractor.extract_first_pages(Path("/fake/path.pdf"), [0])
        
        assert 'extraction_time' in result
        assert result['extraction_time'] >= 0
            
    @patch('src.pdf_parser.extractors.google_vision_extractor.pdf2image')
    @patch('src.pdf_parser.extractors.google_vision_extractor.cv2')
    @patch('google.cloud.vision.ImageAnnotatorClient')
    def test_memory_efficient_page_processing(self, mock_client_class, mock_cv2, mock_pdf2image):
        """Test that pages are processed one at a time for memory efficiency."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        extractor = GoogleCloudVisionExtractor(self.credentials_path)
        
        # Mock pdf2image to return one image at a time
        mock_image1 = Mock()
        mock_image2 = Mock()
        mock_pdf2image.convert_from_path.side_effect = [[mock_image1], [mock_image2]]
        
        # Mock cv2.imencode
        mock_buffer = Mock()
        mock_buffer.tobytes.return_value = b'fake_image_bytes'
        mock_cv2.imencode.return_value = (True, mock_buffer)
        
        # Mock Vision API responses
        mock_annotation = Mock()
        mock_annotation.description = "Page text content"
        mock_response = Mock()
        mock_response.text_annotations = [mock_annotation]
        mock_client.text_detection.return_value = mock_response
        
        # Mock vision.Image
        with patch('google.cloud.vision.Image') as mock_image_class:
            mock_image_class.return_value = Mock()
            result = extractor.extract_first_pages(Path("/fake/path.pdf"), [0, 1])
        
        # Verify pdf2image was called separately for each page
        assert mock_pdf2image.convert_from_path.call_count == 2
        mock_pdf2image.convert_from_path.assert_any_call(
            Path("/fake/path.pdf"),
            first_page=1,
            last_page=1
        )
        mock_pdf2image.convert_from_path.assert_any_call(
            Path("/fake/path.pdf"),
            first_page=2,
            last_page=2
        )
        
        assert result['pages_processed'] == 2