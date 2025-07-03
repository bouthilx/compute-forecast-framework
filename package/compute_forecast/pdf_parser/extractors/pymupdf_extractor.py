"""PyMuPDF extractor for basic PDF text extraction."""

import logging
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING
import re

if TYPE_CHECKING:
    import fitz

from compute_forecast.pdf_parser.core.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logger.error("PyMuPDF (fitz) not available. Install with: pip install pymupdf")


class PyMuPDFExtractor(BaseExtractor):
    """PyMuPDF-based PDF text extractor for fast, basic text extraction."""
    
    # Confidence calculation constants
    BASE_CONFIDENCE_SCORE = 0.2
    MIN_TEXT_LENGTH_THRESHOLD = 50
    MEDIUM_TEXT_LENGTH_THRESHOLD = 200
    LARGE_TEXT_LENGTH_THRESHOLD = 1000
    LENGTH_BONUS_SMALL = 0.2
    LENGTH_BONUS_MEDIUM = 0.1
    LENGTH_BONUS_LARGE = 0.1
    ACADEMIC_MARKER_BONUS = 0.05
    MAX_ACADEMIC_BONUS = 0.2
    GARBAGE_PENALTY_FACTOR = 0.5
    MAX_GARBAGE_PENALTY = 0.3
    SHORT_WORD_PENALTY_FACTOR = 0.3
    MAX_SHORT_WORD_PENALTY = 0.2
    MAX_PENALTY_RATIO = 0.5  # Penalties capped at 50% of positive score
    
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
        doc = None
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
            
            full_text = '\n'.join(text_parts)
            confidence = self._calculate_confidence(full_text)
            
            return {
                'text': full_text,
                'method': 'pymupdf',
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed for {pdf_path} (pages: {pages}): {type(e).__name__}: {str(e)}")
            raise
        finally:
            if doc:
                doc.close()
    
    def extract_full_text(self, pdf_path: Path) -> str:
        """Extract text from entire PDF document.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Full text content of the document with page markers
        """
        doc = None
        try:
            doc = self._create_fitz_doc(pdf_path)
            full_text = ''
            
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                full_text += f'\n[Page {page_num + 1}]\n{page_text}'
            
            return full_text
            
        except Exception as e:
            logger.error(f"PyMuPDF full text extraction failed for {pdf_path}: {type(e).__name__}: {str(e)}")
            raise
        finally:
            if doc:
                doc.close()
    
    def can_extract_affiliations(self) -> bool:
        """Check if this extractor can be used for affiliation extraction.
        
        Returns:
            True - PyMuPDF can attempt affiliation extraction from standard PDFs
        """
        return True
    
    def _create_fitz_doc(self, pdf_path: Path) -> 'fitz.Document':
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
        
        text_lower = text.lower()
        
        # Calculate positive contributions
        base_score = self.BASE_CONFIDENCE_SCORE  # Base score for having text
        
        # Length-based scoring
        text_length = len(text.strip())
        length_bonus = 0.0
        if text_length > self.MIN_TEXT_LENGTH_THRESHOLD:
            length_bonus += self.LENGTH_BONUS_SMALL
        if text_length > self.MEDIUM_TEXT_LENGTH_THRESHOLD:
            length_bonus += self.LENGTH_BONUS_MEDIUM
        if text_length > self.LARGE_TEXT_LENGTH_THRESHOLD:
            length_bonus += self.LENGTH_BONUS_LARGE
        
        # Academic paper markers (higher confidence for academic content)
        academic_markers = [
            'abstract', 'introduction', 'methodology', 'results', 
            'conclusion', 'references', 'bibliography', 'acknowledgments',
            'keywords', 'doi:', 'arxiv:', 'university', 'department'
        ]
        
        marker_count = sum(1 for marker in academic_markers if marker in text_lower)
        marker_bonus = min(marker_count * self.ACADEMIC_MARKER_BONUS, self.MAX_ACADEMIC_BONUS)
        
        # Total positive score
        positive_score = base_score + length_bonus + marker_bonus
        
        # Calculate penalties
        penalty = 0.0
        
        # Penalize for garbage characters (low ASCII, excessive special chars)
        garbage_chars = len(re.findall(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\\]', text))
        garbage_ratio = garbage_chars / len(text) if text else 0
        garbage_penalty = min(garbage_ratio * self.GARBAGE_PENALTY_FACTOR, self.MAX_GARBAGE_PENALTY)
        
        # Penalize for too many short words (OCR artifacts)
        words = text.split()
        if words:
            short_word_ratio = sum(1 for word in words if len(word) <= 2) / len(words)
            short_word_penalty = min(short_word_ratio * self.SHORT_WORD_PENALTY_FACTOR, self.MAX_SHORT_WORD_PENALTY)
        else:
            short_word_penalty = 0.0
        
        # Total penalty capped at 50% of positive score
        penalty = min(garbage_penalty + short_word_penalty, positive_score * self.MAX_PENALTY_RATIO)
        
        # Final confidence score
        confidence = positive_score - penalty
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))