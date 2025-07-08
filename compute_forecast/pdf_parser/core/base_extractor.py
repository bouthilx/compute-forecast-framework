"""Base extractor interface for PDF text extraction."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List


class BaseExtractor(ABC):
    """Abstract base class for PDF text extractors."""

    @abstractmethod
    def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
        """Extract text from specific pages of a PDF.

        Args:
            pdf_path: Path to the PDF file
            pages: List of page indices to extract (0-based)

        Returns:
            Dictionary containing:
                - text: Extracted text content
                - method: Name of extraction method used
                - confidence: Confidence score (0.0-1.0)
        """
        pass

    @abstractmethod
    def extract_full_text(self, pdf_path: Path) -> str:
        """Extract text from entire PDF document.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Full text content of the document
        """
        pass

    @abstractmethod
    def can_extract_affiliations(self) -> bool:
        """Check if this extractor can be used for affiliation extraction.

        Returns:
            True if this extractor is suitable for affiliation extraction
        """
        pass
