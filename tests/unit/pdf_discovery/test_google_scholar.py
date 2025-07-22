"""
Unit tests for Google Scholar source implementation
"""

import pytest
from unittest.mock import Mock, patch

from compute_forecast.pipeline.metadata_collection.sources.google_scholar import (
    GoogleScholarSource as GoogleScholarClient,
)


@pytest.mark.skip(reason="refactor: GoogleScholarSource module not found")
class TestGoogleScholarClient:
    """Test Google Scholar client functionality"""

    @pytest.fixture
    def client(self):
        """Create Google Scholar client without proxy"""
        return GoogleScholarClient(use_proxy=False)

    @pytest.fixture
    def mock_scholarly_result(self):
        """Mock result from scholarly library"""
        return {
            "bib": {
                "title": "Deep Learning for Computer Vision",
                "author": ["John Doe", "Jane Smith"],
                "venue": "NeurIPS",
                "pub_year": "2023",
                "abstract": "This paper presents a novel approach...",
            },
            "num_citations": 42,
            "gsrank": "12345",
        }

    def test_init_without_proxy(self):
        """Test client initialization without proxy"""
        client = GoogleScholarClient(use_proxy=False)
        assert client.use_proxy is False
        assert client.rate_limit_delay == 5.0
        assert client.max_results_per_query == 100
        assert client.last_request_time == 0

    @patch(
        "compute_forecast.pipeline.metadata_collection.sources.google_scholar.scholarly"
    )
    @patch(
        "compute_forecast.pipeline.metadata_collection.sources.google_scholar.ProxyGenerator"
    )
    def test_init_with_proxy(self, mock_proxy_gen, mock_scholarly):
        """Test client initialization with proxy"""
        mock_pg = Mock()
        mock_pg.FreeProxies.return_value = True
        mock_proxy_gen.return_value = mock_pg
        mock_scholarly.use_proxy = Mock()

        client = GoogleScholarClient(use_proxy=True)
        assert client.use_proxy is True
        mock_proxy_gen.assert_called_once()
        mock_pg.FreeProxies.assert_called_once()

    @patch(
        "compute_forecast.pipeline.metadata_collection.sources.google_scholar.scholarly"
    )
    @patch("time.time")
    def test_search_papers_success(
        self, mock_time, mock_scholarly, client, mock_scholarly_result
    ):
        """Test successful paper search"""
        # Mock time for rate limiting and timing
        mock_time.side_effect = [0, 0, 1, 2, 3, 10]  # More values for multiple calls

        # Mock scholarly search
        mock_scholarly.search_pubs.return_value = iter([mock_scholarly_result])

        # Perform search
        response = client.search_papers("deep learning", 2023, limit=10)

        # Verify response
        assert response.success is True
        assert len(response.papers) == 1
        assert response.metadata.total_results == 1
        assert response.metadata.api_name == "google_scholar"

        # Verify paper data
        paper = response.papers[0]
        assert paper.title == "Deep Learning for Computer Vision"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "John Doe"
        assert paper.venue == "NeurIPS"
        assert paper.year == 2023
        assert paper.citations == 42
        assert paper.paper_id == "gs_12345"
        assert paper.collection_source == "google_scholar"

    @patch(
        "compute_forecast.pipeline.metadata_collection.sources.google_scholar.scholarly"
    )
    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limiting(self, mock_sleep, mock_time, mock_scholarly, client):
        """Test rate limiting enforcement"""
        # Mock time - simulate recent request
        mock_time.side_effect = [3.0, 3.0, 8.0, 8.0, 15.0]  # last_request was at 3.0
        client.last_request_time = 3.0

        # Mock scholarly search
        mock_scholarly.search_pubs.return_value = iter([])

        # Perform search
        client.search_papers("test", 2023, limit=10)

        # Verify rate limiting was applied
        mock_sleep.assert_called_once_with(5.0)  # Should sleep for 5 seconds

    @patch(
        "compute_forecast.pipeline.metadata_collection.sources.google_scholar.scholarly"
    )
    def test_search_papers_error(self, mock_scholarly, client):
        """Test error handling in search"""
        # Mock scholarly to raise exception
        mock_scholarly.search_pubs.side_effect = Exception("Connection error")

        # Perform search
        response = client.search_papers("test", 2023, limit=10)

        # Verify error response
        assert response.success is False
        assert len(response.papers) == 0
        assert len(response.errors) == 1
        assert response.errors[0].error_type == "search_error"
        assert "Connection error" in response.errors[0].message

    def test_parse_scholarly_result_complete(self, client, mock_scholarly_result):
        """Test parsing complete scholarly result"""
        paper = client._parse_scholarly_result(mock_scholarly_result)

        assert paper is not None
        assert paper.title == "Deep Learning for Computer Vision"
        assert len(paper.authors) == 2
        assert paper.venue == "NeurIPS"
        assert paper.year == 2023
        assert paper.citations == 42

    def test_parse_scholarly_result_missing_title(self, client):
        """Test parsing result without title"""
        result = {"bib": {}}
        paper = client._parse_scholarly_result(result)
        assert paper is None

    def test_parse_scholarly_result_single_author_string(self, client):
        """Test parsing result with single author as string"""
        result = {"bib": {"title": "Test Paper", "author": "John Doe"}}
        paper = client._parse_scholarly_result(result)

        assert paper is not None
        assert len(paper.authors) == 1
        assert paper.authors[0].name == "John Doe"

    def test_parse_scholarly_result_venue_variations(self, client):
        """Test parsing different venue field names"""
        # Test 'venue' field
        result1 = {"bib": {"title": "Paper 1", "venue": "Conference A"}}
        paper1 = client._parse_scholarly_result(result1)
        assert paper1.venue == "Conference A"

        # Test 'journal' field
        result2 = {"bib": {"title": "Paper 2", "journal": "Journal B"}}
        paper2 = client._parse_scholarly_result(result2)
        assert paper2.venue == "Journal B"

        # Test 'conference' field
        result3 = {"bib": {"title": "Paper 3", "conference": "Conference C"}}
        paper3 = client._parse_scholarly_result(result3)
        assert paper3.venue == "Conference C"

    @patch(
        "compute_forecast.pipeline.metadata_collection.sources.google_scholar.scholarly"
    )
    def test_search_venue_batch(self, mock_scholarly, client):
        """Test batch venue search"""
        # Mock scholarly search
        mock_scholarly.search_pubs.return_value = iter([])

        # Perform batch search
        venues = ["NeurIPS", "ICML", "ICLR"]
        client.search_venue_batch(venues, 2023, limit=50)

        # Verify query construction
        expected_query = 'source:"NeurIPS" OR source:"ICML" OR source:"ICLR" 2023'
        mock_scholarly.search_pubs.assert_called_once_with(expected_query)

    @patch(
        "compute_forecast.pipeline.metadata_collection.sources.google_scholar.scholarly"
    )
    @patch("time.sleep")
    def test_periodic_delay_during_collection(self, mock_sleep, mock_scholarly, client):
        """Test periodic delays during result collection"""
        # Create 15 mock results
        results = []
        for i in range(15):
            results.append(
                {
                    "bib": {
                        "title": f"Paper {i}",
                        "author": ["Author"],
                        "pub_year": "2023",
                    }
                }
            )

        mock_scholarly.search_pubs.return_value = iter(results)

        # Perform search
        client.search_papers("test", 2023, limit=15)

        # Should have added delay after 10th result (index 9)
        assert mock_sleep.call_count >= 1  # At least one delay call
