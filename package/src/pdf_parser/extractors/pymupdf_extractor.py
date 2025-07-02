"""PyMuPDF extractor for basic PDF text extraction."""

import logging
from pathlib import Path
from typing import Dict, List
import re

from src.pdf_parser.core.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logger.error("PyMuPDF (fitz) not available. Install with: pip install pymupdf")


class PyMuPDFExtractor(BaseExtractor):
    """PyMuPDF-based PDF text extractor for fast, basic text extraction."""
    
    def __init__(self):
        """Initialize PyMuPDF extractor."""
        if fitz is None:
            raise ImportError("PyMuPDF library not available")
        
        self.fitz = fitz
        logger.info("PyMuPDF extractor initialized")
    
    def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
        """Extract text from specific pages of a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            pages: List of page indices to extract (0-based)
            
        Returns:
            Dictionary containing:
                - text: Extracted text content with page markers
                - method: 'pymupdf'
                - confidence: Confidence score (0.0-1.0)
        """
        try:
            doc = self._create_fitz_doc(pdf_path)
            text_parts = []
            
            for page_num in pages:
                if page_num < len(doc):
                    page = doc[page_num]
                    page_text = page.get_text()
                    text_parts.append(f'[Page {page_num + 1}]\n{page_text}')
                else:
                    logger.warning(f"Page {page_num} out of range for PDF with {len(doc)} pages")
            
            doc.close()
            
            full_text = '\n'.join(text_parts)
            confidence = self._calculate_confidence(full_text)
            
            return {
                'text': full_text,
                'method': 'pymupdf',
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed for {pdf_path}: {str(e)}")
            raise
    
    def extract_full_text(self, pdf_path: Path) -> str:
        """Extract text from entire PDF document.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Full text content of the document with page markers
        """
        try:
            doc = self._create_fitz_doc(pdf_path)
            full_text = ''
            
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                full_text += f'\n[Page {page_num + 1}]\n{page_text}'
            
            doc.close()
            return full_text
            
        except Exception as e:
            logger.error(f"PyMuPDF full text extraction failed for {pdf_path}: {str(e)}")
            raise
    
    def can_extract_affiliations(self) -> bool:
        """Check if this extractor can be used for affiliation extraction.
        
        Returns:
            True - PyMuPDF can attempt affiliation extraction from standard PDFs
        """
        return True
    
    def _create_fitz_doc(self, pdf_path: Path):
        """Create a fitz document object. Separated for easier testing.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Fitz document object
        """
        return self.fitz.open(str(pdf_path))
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score based on text quality.
        
        Args:
            text: Extracted text to evaluate
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not text or not text.strip():
            return 0.0
        
        confidence = 0.0
        text_lower = text.lower()
        
        # Base score for having text
        confidence += 0.2
        
        # Length-based scoring
        text_length = len(text.strip())
        if text_length > 50:
            confidence += 0.2
        if text_length > 200:
            confidence += 0.1
        if text_length > 1000:
            confidence += 0.1
        
        # Academic paper markers (higher confidence for academic content)
        academic_markers = [
            'abstract', 'introduction', 'methodology', 'results', 
            'conclusion', 'references', 'bibliography', 'acknowledgments',
            'keywords', 'doi:', 'arxiv:', 'university', 'department'
        ]
        
        marker_count = sum(1 for marker in academic_markers if marker in text_lower)
        confidence += min(marker_count * 0.05, 0.2)  # Up to 0.2 bonus
        
        # Penalize for garbage characters (low ASCII, excessive special chars)
        garbage_chars = len(re.findall(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\\]', text))
        garbage_ratio = garbage_chars / len(text) if text else 0
        confidence -= min(garbage_ratio * 0.5, 0.3)  # Up to 0.3 penalty
        
        # Penalize for too many short words (OCR artifacts)
        words = text.split()
        if words:
            short_word_ratio = sum(1 for word in words if len(word) <= 2) / len(words)
            confidence -= min(short_word_ratio * 0.3, 0.2)  # Up to 0.2 penalty
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))