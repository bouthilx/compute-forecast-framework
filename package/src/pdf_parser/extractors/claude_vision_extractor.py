"""Claude Vision extractor for targeted affiliation extraction."""

import json
import re
import base64
import logging
from pathlib import Path
from typing import Dict, List, Any

try:
    import anthropic
except ImportError:
    raise ImportError("anthropic package is required. Install with: uv add anthropic")

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF package is required. Install with: uv add pymupdf")

from src.pdf_parser.core.base_extractor import BaseExtractor
from src.pdf_parser.prompts.affiliation_prompts import build_affiliation_prompt

logger = logging.getLogger(__name__)


class ClaudeVisionExtractor(BaseExtractor):
    """Claude Vision API extractor for affiliation extraction from PDFs."""
    
    def __init__(self, api_key: str):
        """Initialize Claude Vision extractor.
        
        Args:
            api_key: Anthropic API key for Claude access
        """
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = 'claude-3-haiku-20240307'  # Cheaper, sufficient for this task
        
    def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
        """Use Claude to extract affiliations from first pages.
        
        Args:
            pdf_path: Path to the PDF file
            pages: List of page indices to extract (0-based)
            
        Returns:
            Dictionary containing:
                - affiliations: List of extracted affiliations
                - authors_with_affiliations: List of author-affiliation mappings
                - method: Extraction method used
                - confidence: Confidence score
                - cost: Extraction cost in dollars
        """
        try:
            # Convert PDF pages to images (max 2 pages)
            images = self._pdf_to_images(pdf_path, pages[:2])
            
            # Prepare targeted prompt
            prompt = self._build_affiliation_prompt()
            
            # Convert images to base64 for Claude
            image_contents = []
            for img_bytes in images:
                img_base64 = base64.b64encode(img_bytes).decode()
                image_contents.append({
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': 'image/png',
                        'data': img_base64
                    }
                })
            
            # Send to Claude
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        *image_contents
                    ]
                }]
            )
            
            # Parse response
            result = self._parse_claude_response(message.content[0].text)
            
            # Calculate cost
            cost = self._calculate_cost(len(images))
            
            return {
                'affiliations': result.get('all_affiliations', []),
                'authors_with_affiliations': result.get('authors_with_affiliations', []),
                'method': 'claude_vision',
                'confidence': result.get('confidence', 0.8),
                'cost': cost
            }
            
        except Exception as e:
            logger.error(f"Claude Vision extraction failed: {str(e)}")
            raise
    
    def extract_full_text(self, pdf_path: Path) -> str:
        """Extract full text from PDF.
        
        Note: This is not implemented for Claude Vision due to cost considerations.
        Use PyMuPDF or other extractors for full document text extraction.
        
        Args:
            pdf_path: Path to PDF file
            
        Raises:
            NotImplementedError: Always raised - use PyMuPDF for full text
        """
        raise NotImplementedError('Use PyMuPDF for full document extraction')
    
    def can_extract_affiliations(self) -> bool:
        """Check if this extractor can be used for affiliation extraction.
        
        Returns:
            True - Claude Vision is specifically designed for affiliation extraction
        """
        return True
    
    def _pdf_to_images(self, pdf_path: Path, pages: List[int]) -> List[bytes]:
        """Convert PDF pages to images.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page indices (0-based)
            
        Returns:
            List of image data as bytes (PNG format)
        """
        images = []
        
        with fitz.open(pdf_path) as doc:
            for page_num in pages:
                if page_num >= len(doc):
                    logger.warning(f"Page {page_num} not found in PDF (has {len(doc)} pages)")
                    continue
                    
                page = doc[page_num]
                # Convert to image at 150 DPI for good quality
                pixmap = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))
                img_data = pixmap.tobytes("png")
                images.append(img_data)
                
        logger.info(f"Converted {len(images)} pages to images")
        return images
    
    def _build_affiliation_prompt(self) -> str:
        """Build specific prompt for affiliation extraction.
        
        Returns:
            Prompt string optimized for affiliation extraction
        """
        return build_affiliation_prompt()
    
    def _parse_claude_response(self, response: str) -> Dict:
        """Parse JSON response from Claude.
        
        Args:
            response: Raw text response from Claude
            
        Returns:
            Dictionary with parsed affiliations or empty result if parsing fails
        """
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group())
                
                # Validate required fields
                if 'authors_with_affiliations' in json_data and 'all_affiliations' in json_data:
                    return json_data
                else:
                    logger.warning("Response missing required fields")
                    
            # If no valid JSON found, try to extract from structured text
            return self._fallback_parsing(response)
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            return self._fallback_parsing(response)
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return {'affiliations': [], 'confidence': 0.0}
    
    def _fallback_parsing(self, response: str) -> Dict:
        """Fallback parsing when JSON extraction fails.
        
        Args:
            response: Raw text response from Claude
            
        Returns:
            Dictionary with minimal extraction or empty result
        """
        # Simple fallback - look for common patterns
        if "no affiliations" in response.lower() or "cannot find" in response.lower():
            return {'affiliations': [], 'confidence': 0.0}
        
        # Return low confidence if we can't parse properly
        return {'affiliations': [], 'confidence': 0.0}
    
    def _calculate_cost(self, num_images: int) -> float:
        """Calculate cost for extraction operation.
        
        Args:
            num_images: Number of images processed
            
        Returns:
            Cost in dollars for this operation
        """
        # Claude Haiku pricing for vision tasks
        # Simplified cost model: $0.10 per 2-page extraction
        return 0.10