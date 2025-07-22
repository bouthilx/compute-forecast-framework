"""Tests for Unpaywall client functionality."""

import pytest
from unittest.mock import Mock, patch
import requests

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.unpaywall_client import (
    UnpaywallClient,
)


class TestUnpaywallClient:
    """Test Unpaywall client functionality."""

    @pytest.fixture
    def client(self):
        """Create an Unpaywall client instance."""
        return UnpaywallClient(email="test@example.com")

    @pytest.fixture
    def mock_oa_response(self):
        """Mock successful open access response."""
        return {
            "doi": "10.1038/nature12373",
            "is_oa": True,
            "oa_locations": [
                {
                    "url": "https://www.nature.com/articles/nature12373.pdf",
                    "host_type": "publisher",
                    "license": "cc-by",
                    "oa_date": "2021-05-15",
                    "version": "publishedVersion",
                },
                {
                    "url": "https://arxiv.org/pdf/2105.12345.pdf",
                    "host_type": "repository",
                    "license": None,
                    "oa_date": "2021-05-10",
                    "version": "submittedVersion",
                },
            ],
            "title": "Example Paper Title",
            "journal_name": "Nature",
            "year": 2021,
            "authors": ["John Doe", "Jane Smith"],
            "published_date": "2021-05-15",
        }

    @pytest.fixture
    def mock_no_oa_response(self):
        """Mock response for paper with no open access."""
        return {
            "doi": "10.1038/nature12374",
            "is_oa": False,
            "oa_locations": [],
            "title": "Closed Access Paper",
            "journal_name": "Nature",
            "year": 2021,
            "authors": ["John Doe"],
            "published_date": "2021-05-15",
        }

    def test_init_requires_email(self):
        """Test that UnpaywallClient requires an email."""
        with pytest.raises(ValueError, match="Email is required"):
            UnpaywallClient(email=None)

    def test_find_open_access_success(self, client, mock_oa_response):
        """Test successful open access lookup."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_oa_response
            mock_get.return_value = mock_response

            result = client.find_open_access("10.1038/nature12373")

            assert result.success is True
            assert len(result.papers) == 1
            paper = result.papers[0]
            assert getattr(paper, "doi", "") == "10.1038/nature12373"
            assert paper.title == "Example Paper Title"
            assert paper.venue == "Nature"
            assert paper.year == 2021
            assert len(paper.urls) == 2
            # URLs are now URLRecord objects
            url_strings = [url.data.url for url in paper.urls]
            assert "https://www.nature.com/articles/nature12373.pdf" in url_strings
            assert "https://arxiv.org/pdf/2105.12345.pdf" in url_strings

    def test_find_open_access_no_oa(self, client, mock_no_oa_response):
        """Test lookup for paper with no open access."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_no_oa_response
            mock_get.return_value = mock_response

            result = client.find_open_access("10.1038/nature12374")

            assert result.success is True
            assert len(result.papers) == 1
            paper = result.papers[0]
            assert len(paper.urls) == 0  # No open access URLs

    def test_find_open_access_not_found(self, client):
        """Test DOI lookup when DOI is not found."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = client.find_open_access("10.1234/nonexistent")

            assert result.success is False
            assert len(result.papers) == 0
            assert len(result.errors) == 1
            assert result.errors[0].error_type == "not_found"

    def test_find_open_access_rate_limit(self, client):
        """Test rate limiting response."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response

            result = client.find_open_access("10.1038/nature12373")

            assert result.success is False
            assert len(result.errors) == 1
            assert result.errors[0].error_type == "rate_limit_exceeded"

    def test_find_open_access_timeout(self, client):
        """Test timeout handling."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

            result = client.find_open_access("10.1038/nature12373")

            assert result.success is False
            assert len(result.errors) == 1
            assert result.errors[0].error_type == "request_timeout"

    def test_normalize_doi(self, client):
        """Test DOI normalization."""
        assert client.normalize_doi("10.1038/nature12373") == "10.1038/nature12373"
        assert client.normalize_doi("doi:10.1038/nature12373") == "10.1038/nature12373"
        assert (
            client.normalize_doi("https://doi.org/10.1038/nature12373")
            == "10.1038/nature12373"
        )
        assert client.normalize_doi("DOI: 10.1038/nature12373") == "10.1038/nature12373"

    def test_extract_oa_urls(self, client):
        """Test open access URL extraction."""
        oa_locations = [
            {
                "url": "https://www.nature.com/articles/nature12373.pdf",
                "host_type": "publisher",
                "license": "cc-by",
                "version": "publishedVersion",
            },
            {
                "url": "https://arxiv.org/pdf/2105.12345.pdf",
                "host_type": "repository",
                "license": None,
                "version": "submittedVersion",
            },
            {
                "url": None,  # Invalid URL
                "host_type": "repository",
            },
        ]

        urls = client._extract_oa_urls(oa_locations)

        assert len(urls) == 2
        assert "https://www.nature.com/articles/nature12373.pdf" in urls
        assert "https://arxiv.org/pdf/2105.12345.pdf" in urls

    def test_prioritize_oa_urls(self, client):
        """Test open access URL prioritization."""
        oa_locations = [
            {
                "url": "https://repo.example.com/paper.pdf",
                "host_type": "repository",
                "license": None,
                "version": "submittedVersion",
            },
            {
                "url": "https://publisher.com/paper.pdf",
                "host_type": "publisher",
                "license": "cc-by",
                "version": "publishedVersion",
            },
        ]

        urls = client._extract_oa_urls(oa_locations)

        # Publisher version should come first
        assert urls[0] == "https://publisher.com/paper.pdf"
        assert urls[1] == "https://repo.example.com/paper.pdf"

    def test_create_paper_from_unpaywall_data(self, client, mock_oa_response):
        """Test paper creation from Unpaywall data."""
        paper = client._create_paper_from_unpaywall_data(mock_oa_response)

        assert getattr(paper, "doi", "") == "10.1038/nature12373"
        assert paper.title == "Example Paper Title"
        assert paper.venue == "Nature"
        assert paper.year == 2021
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "John Doe"
        assert paper.authors[1].name == "Jane Smith"
        assert len(paper.urls) == 2
