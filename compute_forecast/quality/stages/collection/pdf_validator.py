"""PDF URL validation for quality checks."""

import re
from urllib.parse import urlparse
from typing import Dict, Any, List
import logging


class PDFURLValidator:
    """Validates PDF URLs with configurable strictness levels."""

    PDF_EXTENSIONS = {".pdf", ".PDF"}
    PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}

    # Strict URL pattern that ensures .pdf is at the end of the path (before query/fragment)
    PDF_URL_PATTERN = re.compile(r"^https?://[^/]+.*\.pdf(\?.*)?$", re.IGNORECASE)

    def __init__(self, strict_mode: bool = True):
        """Initialize validator.

        Args:
            strict_mode: If True, only accept URLs ending with .pdf extension.
                        If False, accept various PDF URL patterns.
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)

    def is_valid_pdf_url(self, url: str) -> bool:
        """Validate if a URL points to a PDF.

        Args:
            url: URL string to validate

        Returns:
            True if URL appears to point to a PDF, False otherwise
        """
        if not isinstance(url, str) or not url.strip():
            return False

        # Parse URL
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.netloc:
                return False
        except Exception:
            return False

        # Check URL pattern
        if self.strict_mode:
            # Strict mode: URL must end with .pdf
            return bool(self.PDF_URL_PATTERN.match(url))
        else:
            # Lenient mode: check various PDF indicators
            url_lower = url.lower()
            path = parsed.path.lower()

            # Check file extension
            if path.endswith(".pdf"):
                return True

            # Check common PDF URL patterns
            pdf_patterns = [
                "/pdf/",
                "format=pdf",
                "type=pdf",
                "/download/pdf",
                "pdf.aspx",
                "pdfviewer",
            ]

            return any(pattern in url_lower for pattern in pdf_patterns)

    def validate_paper_pdfs(self, paper: Dict[str, Any]) -> bool:
        """Check if a paper has at least one valid PDF URL.

        Args:
            paper: Paper dictionary with potential PDF URL fields

        Returns:
            True if paper has at least one valid PDF URL, False otherwise
        """
        # Check legacy pdf_url field
        if paper.get("pdf_url"):
            if self.is_valid_pdf_url(str(paper["pdf_url"])):
                return True

        # Check pdf_urls field
        pdf_urls = paper.get("pdf_urls", [])
        if isinstance(pdf_urls, list):
            for url in pdf_urls:
                if self.is_valid_pdf_url(str(url)):
                    return True

        # Check urls field with URLRecord structure
        urls = paper.get("urls", [])
        if isinstance(urls, list):
            for url_record in urls:
                if isinstance(url_record, dict) and "data" in url_record:
                    url = url_record["data"].get("url", "")
                    if self.is_valid_pdf_url(url):
                        return True

        return False

    def get_invalid_urls(self, paper: Dict[str, Any]) -> List[str]:
        """Get list of invalid PDF URLs from a paper.

        Args:
            paper: Paper dictionary with potential PDF URL fields

        Returns:
            List of invalid URL strings found in the paper
        """
        invalid_urls = []

        # Check legacy pdf_url field
        if paper.get("pdf_url"):
            url = str(paper["pdf_url"])
            if url.strip() and not self.is_valid_pdf_url(url):
                invalid_urls.append(url)

        # Check pdf_urls field
        pdf_urls = paper.get("pdf_urls", [])
        if isinstance(pdf_urls, list):
            for url in pdf_urls:
                url_str = str(url)
                if url_str.strip() and not self.is_valid_pdf_url(url_str):
                    invalid_urls.append(url_str)

        # Check urls field
        urls = paper.get("urls", [])
        if isinstance(urls, list):
            for url_record in urls:
                if isinstance(url_record, dict) and "data" in url_record:
                    url = url_record["data"].get("url", "")
                    if url and not self.is_valid_pdf_url(url):
                        # Only add URLs that look like they might be PDFs
                        url_lower = url.lower()
                        if any(
                            indicator in url_lower
                            for indicator in [".pdf", "/pdf", "pdf"]
                        ):
                            invalid_urls.append(url)

        return invalid_urls
