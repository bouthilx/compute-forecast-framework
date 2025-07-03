"""Google Cloud Vision OCR extractor for PDF documents."""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
import pdf2image
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ServiceUnavailable, DeadlineExceeded

from src.pdf_parser.core.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class GoogleCloudVisionExtractor(BaseExtractor):
    """Google Cloud Vision API extractor for OCR on difficult scanned PDFs."""
    
    def __init__(self, credentials_path: str):
        """Initialize Google Cloud Vision client.
        
        Args:
            credentials_path: Path to Google Cloud service account credentials JSON
        """
        from google.cloud import vision
        
        # Set credentials environment variable
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        # Initialize Vision client
        self.client = vision.ImageAnnotatorClient()
        self.page_limit = 2  # Cost control - only process first 2 pages
        
        logger.info(f"Initialized Google Cloud Vision extractor with page limit {self.page_limit}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, DeadlineExceeded))
    )
    def _call_vision_api(self, vision_image):
        """Call Vision API with retry logic for transient errors.
        
        Args:
            vision_image: Google Cloud Vision Image object
            
        Returns:
            Text detection response
        """
        return self.client.text_detection(image=vision_image)
    
    def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
        """Use Google Cloud Vision for OCR on first pages.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page indices to extract (0-based)
            
        Returns:
            Dictionary containing:
                - text: Extracted text from pages
                - method: 'google_cloud_vision'
                - confidence: 0.9 (GCV is very reliable)
                - cost: Total cost for extraction
                - pages_processed: Number of pages processed
        """
        from google.cloud import vision
        
        # Track extraction time
        start_time = time.time()
        
        # Limit to first pages for cost control
        pages_to_process = [p for p in pages if p < self.page_limit]
        
        if not pages_to_process:
            logger.warning(f"No pages to process within limit {self.page_limit}")
            return {
                'text': '',
                'method': 'google_cloud_vision',
                'confidence': 0.0,
                'cost': 0.0,
                'pages_processed': 0,
                'extraction_time': time.time() - start_time
            }
        
        logger.info(f"Processing {len(pages_to_process)} pages with Google Cloud Vision")
        
        all_text = []
        total_cost = 0.0
        successfully_processed = 0
        
        # Process pages one at a time for memory efficiency
        for page_num in pages_to_process:
            try:
                # Convert single page to image for memory efficiency
                images = pdf2image.convert_from_path(
                    pdf_path,
                    first_page=page_num + 1,
                    last_page=page_num + 1
                )
                
                if not images:
                    logger.warning(f"Failed to convert page {page_num + 1} to image")
                    continue
                    
                image = images[0]
                
                # Convert PIL image to numpy array for OpenCV
                image_array = np.array(image)
                
                # Convert image to bytes for Vision API
                _, buffer = cv2.imencode('.png', image_array)
                image_bytes = buffer.tobytes()
                
                # Create Vision API image
                vision_image = vision.Image(content=image_bytes)
                
                # Perform text detection with retry logic
                response = self._call_vision_api(vision_image)
                
                if response.text_annotations:
                    # First annotation contains all text
                    page_text = response.text_annotations[0].description
                    all_text.append(f'[Page {page_num + 1}]\n{page_text}')
                    logger.debug(f"Extracted {len(page_text)} characters from page {page_num + 1}")
                else:
                    logger.warning(f"No text found on page {page_num + 1}")
                
                # Track cost ($0.0015 per page)
                total_cost += 0.0015
                successfully_processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process page {page_num + 1}: {str(e)}")
                continue
        
        result_text = '\n'.join(all_text)
        
        logger.info(f"Completed Google Cloud Vision extraction: {len(result_text)} chars, ${total_cost:.4f}")
        
        return {
            'text': result_text,
            'method': 'google_cloud_vision',
            'confidence': 0.9,  # GCV is very reliable
            'cost': total_cost,
            'pages_processed': successfully_processed,
            'extraction_time': time.time() - start_time
        }
    
    def can_extract_affiliations(self) -> bool:
        """Check if this extractor can be used for affiliation extraction.
        
        Returns:
            True - Google Cloud Vision can extract affiliations from OCR
        """
        return True
        
    def extract_full_text(self, pdf_path: Path) -> str:
        """Not implemented - too expensive for full documents.
        
        Args:
            pdf_path: Path to PDF file
            
        Raises:
            NotImplementedError: Full text extraction is not cost-effective
        """
        raise NotImplementedError('Use PyMuPDF for full document extraction')
    
    def _pdf_to_images(self, pdf_path: Path, pages: List[int]) -> List[Image.Image]:
        """Convert PDF pages to images for OCR processing.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of 0-based page indices to convert
            
        Returns:
            List of PIL Image objects
        """
        # pdf2image uses 1-based page indexing
        first_page = min(pages) + 1
        last_page = max(pages) + 1
        
        logger.debug(f"Converting PDF pages {first_page}-{last_page} to images")
        
        images = pdf2image.convert_from_path(
            pdf_path,
            first_page=first_page,
            last_page=last_page
        )
        
        return images