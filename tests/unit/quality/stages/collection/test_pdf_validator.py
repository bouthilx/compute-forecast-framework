"""Tests for PDF URL validator."""

import pytest
from compute_forecast.quality.stages.collection.pdf_validator import PDFURLValidator


class TestPDFURLValidator:
    """Test PDF URL validation functionality."""

    def test_init_default_strict_mode(self):
        """Test validator initializes with strict mode by default."""
        validator = PDFURLValidator()
        assert validator.strict_mode is True

    def test_init_lenient_mode(self):
        """Test validator can be initialized in lenient mode."""
        validator = PDFURLValidator(strict_mode=False)
        assert validator.strict_mode is False

    @pytest.mark.parametrize(
        "url,expected",
        [
            # Valid strict PDF URLs
            ("https://example.com/paper.pdf", True),
            ("http://arxiv.org/pdf/2301.12345.pdf", True),
            ("https://proceedings.mlr.press/v139/smith21a/smith21a.pdf", True),
            ("https://example.com/path/to/document.PDF", True),
            ("https://example.com/paper.pdf?download=true", True),
            # Invalid strict PDF URLs
            ("https://example.com/pdf/viewer", False),
            ("https://example.com/paper.html", False),
            ("https://example.com/getpdf.php?id=123", False),
            ("https://example.com/paper", False),
            ("https://example.com/pdf-guide.html", False),
            ("https://example.com/paper.pdf.html", False),
            # Invalid URL formats
            ("not a url", False),
            ("ftp://example.com/paper.pdf", False),
            ("//example.com/paper.pdf", False),
            ("https://", False),
            ("", False),
            (None, False),
        ],
    )
    def test_is_valid_pdf_url_strict_mode(self, url, expected):
        """Test URL validation in strict mode."""
        validator = PDFURLValidator(strict_mode=True)
        if url is None:
            # Test type checking
            assert validator.is_valid_pdf_url(None) is False  # type: ignore
        else:
            assert validator.is_valid_pdf_url(url) == expected

    @pytest.mark.parametrize(
        "url,expected",
        [
            # All strict mode valid URLs should also be valid
            ("https://example.com/paper.pdf", True),
            ("http://arxiv.org/pdf/2301.12345.pdf", True),
            # Additional lenient mode valid URLs
            ("https://example.com/pdf/viewer", True),
            ("https://example.com/download?format=pdf", True),
            ("https://example.com/getpdf.aspx?id=123", True),
            ("https://dl.acm.org/doi/pdf/10.1145/1234567", True),
            ("https://example.com/download/pdf", True),
            ("https://example.com/pdfviewer?doc=paper", True),
            ("https://example.com/paper?type=pdf", True),
            # Still invalid in lenient mode
            ("https://example.com/paper.html", False),
            ("https://example.com/image.jpg", False),
            ("https://example.com/about", False),
            ("invalid url", False),
        ],
    )
    def test_is_valid_pdf_url_lenient_mode(self, url, expected):
        """Test URL validation in lenient mode."""
        validator = PDFURLValidator(strict_mode=False)
        assert validator.is_valid_pdf_url(url) == expected

    def test_validate_paper_pdfs_legacy_field(self):
        """Test validation with legacy pdf_url field."""
        validator = PDFURLValidator()

        # Valid PDF URL
        paper = {"pdf_url": "https://example.com/paper.pdf"}
        assert validator.validate_paper_pdfs(paper) is True

        # Invalid PDF URL
        paper = {"pdf_url": "https://example.com/paper.html"}
        assert validator.validate_paper_pdfs(paper) is False

        # Empty/None values
        paper = {"pdf_url": ""}
        assert validator.validate_paper_pdfs(paper) is False

        paper = {"pdf_url": None}
        assert validator.validate_paper_pdfs(paper) is False

    def test_validate_paper_pdfs_list_field(self):
        """Test validation with pdf_urls list field."""
        validator = PDFURLValidator()

        # Valid PDF URLs
        paper = {
            "pdf_urls": [
                "https://example.com/paper.pdf",
                "https://mirror.com/paper.pdf",
            ]
        }
        assert validator.validate_paper_pdfs(paper) is True

        # Mixed valid/invalid URLs (should pass if at least one valid)
        paper = {
            "pdf_urls": ["https://example.com/paper.html", "https://arxiv.org/1234.pdf"]
        }
        assert validator.validate_paper_pdfs(paper) is True

        # All invalid URLs
        paper = {"pdf_urls": ["https://example.com/about", "not-a-url"]}
        assert validator.validate_paper_pdfs(paper) is False

        # Empty list
        paper = {"pdf_urls": []}
        assert validator.validate_paper_pdfs(paper) is False

    def test_validate_paper_pdfs_url_records(self):
        """Test validation with URLRecord structure."""
        validator = PDFURLValidator()

        # Valid URL record
        paper = {
            "urls": [
                {
                    "source": "scraper",
                    "timestamp": "2025-01-01",
                    "data": {"url": "https://example.com/paper.pdf"},
                }
            ]
        }
        assert validator.validate_paper_pdfs(paper) is True

        # Invalid URL in record
        paper = {
            "urls": [
                {
                    "source": "scraper",
                    "timestamp": "2025-01-01",
                    "data": {"url": "https://example.com/about.html"},
                }
            ]
        }
        assert validator.validate_paper_pdfs(paper) is False

        # Missing data field
        paper = {"urls": [{"source": "scraper"}]}
        assert validator.validate_paper_pdfs(paper) is False

        # Non-dict in urls list
        paper = {"urls": ["https://example.com/paper.pdf"]}
        assert validator.validate_paper_pdfs(paper) is False

    def test_validate_paper_pdfs_multiple_fields(self):
        """Test validation when paper has multiple PDF fields."""
        validator = PDFURLValidator()

        # Valid PDF in one field, invalid in others
        paper = {
            "pdf_url": "not-a-url",
            "pdf_urls": ["https://example.com/paper.pdf"],
            "urls": [{"data": {"url": "https://example.com/about"}}],
        }
        assert validator.validate_paper_pdfs(paper) is True

        # All fields have invalid URLs
        paper = {
            "pdf_url": "https://example.com/index.html",
            "pdf_urls": ["not-a-url"],
            "urls": [{"data": {"url": "ftp://example.com/paper.pdf"}}],
        }
        assert validator.validate_paper_pdfs(paper) is False

    def test_validate_paper_pdfs_lenient_mode(self):
        """Test paper validation in lenient mode."""
        validator = PDFURLValidator(strict_mode=False)

        # URLs that are only valid in lenient mode
        paper = {"pdf_url": "https://dl.acm.org/doi/pdf/10.1145/1234567"}
        assert validator.validate_paper_pdfs(paper) is True

        paper = {"urls": [{"data": {"url": "https://example.com/download?format=pdf"}}]}
        assert validator.validate_paper_pdfs(paper) is True

    def test_get_invalid_urls(self):
        """Test extraction of invalid URLs from paper."""
        validator = PDFURLValidator(strict_mode=True)

        paper = {
            "pdf_url": "https://example.com/viewer",  # Invalid in strict mode
            "pdf_urls": [
                "https://example.com/paper.pdf",  # Valid
                "not-a-url",  # Invalid
                "https://example.com/pdf-guide.html",  # Invalid
            ],
            "urls": [
                {
                    "data": {"url": "https://example.com/pdf/viewer"}
                },  # Invalid but PDF-like
                {
                    "data": {"url": "https://example.com/index.html"}
                },  # Invalid, not PDF-like
            ],
        }

        invalid_urls = validator.get_invalid_urls(paper)

        # Should include invalid URLs that look like they might be PDFs
        assert "https://example.com/viewer" in invalid_urls
        assert "not-a-url" in invalid_urls
        assert "https://example.com/pdf-guide.html" in invalid_urls
        assert "https://example.com/pdf/viewer" in invalid_urls
        # Should not include URLs that don't look PDF-related
        assert "https://example.com/index.html" not in invalid_urls

    def test_get_invalid_urls_empty_paper(self):
        """Test get_invalid_urls with paper having no PDF fields."""
        validator = PDFURLValidator()
        paper = {"title": "Test Paper", "year": 2025}
        assert validator.get_invalid_urls(paper) == []

    def test_string_conversion_handling(self):
        """Test that non-string values are converted to strings."""
        validator = PDFURLValidator()

        # Integer as pdf_url (should convert to string)
        paper = {"pdf_url": 12345}
        assert validator.validate_paper_pdfs(paper) is False

        # Non-string in list
        paper = {"pdf_urls": [12345, "https://example.com/paper.pdf"]}
        assert validator.validate_paper_pdfs(paper) is True
