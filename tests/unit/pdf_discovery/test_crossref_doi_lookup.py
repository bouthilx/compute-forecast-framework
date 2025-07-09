"""Tests for CrossRef DOI lookup functionality."""

import pytest
from unittest.mock import Mock, patch
import requests

from compute_forecast.pipeline.metadata_collection.sources.enhanced_crossref import (
    EnhancedCrossrefClient,
)


class TestCrossrefDOILookup:
    """Test CrossRef DOI lookup functionality."""

    @pytest.fixture
    def client(self):
        """Create a CrossRef client instance."""
        return EnhancedCrossrefClient(email="test@example.com")

    @pytest.fixture
    def mock_doi_response(self):
        """Mock successful DOI lookup response."""
        return {
            "status": "ok",
            "message": {
                "DOI": "10.1038/nature12373",
                "title": ["Example Paper Title"],
                "author": [
                    {"given": "John", "family": "Doe", "affiliation": []},
                    {"given": "Jane", "family": "Smith", "affiliation": []},
                ],
                "container-title": ["Nature"],
                "published-print": {"date-parts": [[2021, 5, 15]]},
                "is-referenced-by-count": 42,
                "abstract": "This is an example abstract.",
                "link": [
                    {
                        "URL": "https://www.nature.com/articles/nature12373.pdf",
                        "content-type": "application/pdf",
                        "content-version": "vor",
                        "intended-application": "text-mining",
                    },
                    {
                        "URL": "https://www.nature.com/articles/nature12373",
                        "content-type": "text/html",
                        "content-version": "vor",
                        "intended-application": "text-mining",
                    },
                ],
            },
        }

    def test_lookup_doi_success(self, client, mock_doi_response):
        """Test successful DOI lookup."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_doi_response
            mock_get.return_value = mock_response

            result = client.lookup_doi("10.1038/nature12373")

            assert result.success is True
            assert len(result.papers) == 1
            paper = result.papers[0]
            assert paper.doi == "10.1038/nature12373"
            assert paper.title == "Example Paper Title"
            assert len(paper.authors) == 2
            assert paper.venue == "Nature"
            assert paper.year == 2021
            assert paper.citations == 42

            # Check that PDF URLs are extracted
            assert len(paper.urls) >= 1
            assert "https://www.nature.com/articles/nature12373.pdf" in paper.urls

    def test_lookup_doi_not_found(self, client):
        """Test DOI lookup when DOI is not found."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = client.lookup_doi("10.1234/nonexistent")

            assert result.success is False
            assert len(result.papers) == 0
            assert len(result.errors) == 1
            assert result.errors[0].error_type == "not_found"

    def test_lookup_doi_rate_limit(self, client):
        """Test DOI lookup rate limiting."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response

            result = client.lookup_doi("10.1038/nature12373")

            assert result.success is False
            assert len(result.errors) == 1
            assert result.errors[0].error_type == "rate_limit_exceeded"

    def test_lookup_doi_server_error_with_retry(self, client):
        """Test DOI lookup with server error and retry."""
        with patch("requests.get") as mock_get:
            # First call fails with 503, second succeeds
            mock_response_fail = Mock()
            mock_response_fail.status_code = 503

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {
                "status": "ok",
                "message": {
                    "DOI": "10.1038/nature12373",
                    "title": ["Example Paper Title"],
                    "author": [],
                    "container-title": ["Nature"],
                    "published-print": {"date-parts": [[2021, 5, 15]]},
                    "is-referenced-by-count": 0,
                },
            }

            mock_get.side_effect = [mock_response_fail, mock_response_success]

            result = client.lookup_doi("10.1038/nature12373")

            assert result.success is True
            assert len(result.papers) == 1
            assert mock_get.call_count == 2

    def test_lookup_doi_timeout(self, client):
        """Test DOI lookup timeout handling."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

            result = client.lookup_doi("10.1038/nature12373")

            assert result.success is False
            assert len(result.errors) == 1
            assert result.errors[0].error_type == "request_timeout"

    def test_normalize_doi(self, client):
        """Test DOI normalization."""
        # Test various DOI formats
        assert client.normalize_doi("10.1038/nature12373") == "10.1038/nature12373"
        assert client.normalize_doi("doi:10.1038/nature12373") == "10.1038/nature12373"
        assert (
            client.normalize_doi("https://doi.org/10.1038/nature12373")
            == "10.1038/nature12373"
        )
        assert (
            client.normalize_doi("http://dx.doi.org/10.1038/nature12373")
            == "10.1038/nature12373"
        )
        assert client.normalize_doi("DOI: 10.1038/nature12373") == "10.1038/nature12373"

    def test_extract_pdf_urls_from_links(self, client):
        """Test PDF URL extraction from CrossRef links."""
        links = [
            {
                "URL": "https://example.com/paper.pdf",
                "content-type": "application/pdf",
                "content-version": "vor",
            },
            {"URL": "https://example.com/paper", "content-type": "text/html"},
            {
                "URL": "https://example.com/paper-preprint.pdf",
                "content-type": "application/pdf",
                "content-version": "am",
            },
        ]

        pdf_urls = client._extract_pdf_urls_from_links(links)

        assert len(pdf_urls) == 2
        assert "https://example.com/paper.pdf" in pdf_urls
        assert "https://example.com/paper-preprint.pdf" in pdf_urls
        assert "https://example.com/paper" not in pdf_urls
