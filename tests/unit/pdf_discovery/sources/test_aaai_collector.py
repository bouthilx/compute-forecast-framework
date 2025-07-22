"""Unit tests for AAAI collector."""

import pytest
from unittest.mock import Mock, patch
import requests

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.aaai_collector import (
    AAICollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from datetime import datetime
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)


def create_test_paper(
    paper_id: str,
    title: str,
    venue: str,
    year: int,
    citation_count: int,
    authors: list,
    abstract_text: str = "",
) -> Paper:
    """Helper to create Paper objects with new model format."""
    citations = []
    if citation_count > 0:
        citations.append(
            CitationRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=CitationData(count=citation_count),
            )
        )

    abstracts = []
    if abstract_text:
        abstracts.append(
            AbstractRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=AbstractData(text=abstract_text),
            )
        )

    return Paper(
        paper_id=paper_id,
        title=title,
        venue=venue,
        normalized_venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
    )


class TestAAICollector:
    """Test AAAI collector functionality."""

    @pytest.fixture
    def collector(self):
        """Create collector instance."""
        return AAICollector()

    @pytest.fixture
    def sample_paper(self):
        """Create sample paper for testing."""
        return create_test_paper(
            paper_id="paper_76",
            title="Deep Learning for Natural Language Processing",
            authors=[Author(name="John Smith"), Author(name="Jane Doe")],
            venue="AAAI",
            year=2024,
            citation_count=10,
        )

    @pytest.fixture
    def search_response_html(self):
        """Sample search response HTML."""
        return """
        <html>
        <body>
            <article class="obj_article_summary">
                <h3 class="title">
                    <a href="/index.php/AAAI/article/view/12345">
                        Deep Learning for Natural Language Processing
                    </a>
                </h3>
                <div class="published">
                    Published in AAAI 2024
                </div>
            </article>
            <article class="obj_article_summary">
                <h3 class="title">
                    <a href="/index.php/AAAI/article/view/67890">
                        Another Paper Title
                    </a>
                </h3>
                <div class="published">
                    Published in AAAI 2023
                </div>
            </article>
        </body>
        </html>
        """

    @pytest.fixture
    def article_response_html(self):
        """Sample article page HTML."""
        return """
        <html>
        <body>
            <a class="obj_galley_link pdf" href="/index.php/AAAI/article/download/12345/98765">
                PDF
            </a>
        </body>
        </html>
        """

    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector.source_name == "aaai"
        assert collector.base_url == "https://ojs.aaai.org"
        assert collector.request_delay == 0.5
        assert collector.max_retries == 3

    def test_make_request_success(self, collector):
        """Test successful request with rate limiting."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        # Set last request time to simulate that we already made a request before
        collector.last_request_time = 100

        with patch("requests.get", return_value=mock_response) as mock_get:
            with patch(
                "time.time", side_effect=[101, 102]
            ):  # Time has passed since last request
                with patch("time.sleep") as mock_sleep:
                    response = collector._make_request("http://test.com")

                    assert response == mock_response
                    mock_get.assert_called_once()
                    mock_sleep.assert_not_called()  # No sleep needed, enough time passed

    def test_make_request_with_rate_limiting(self, collector):
        """Test request with rate limiting when requests are too close."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        # Set last request time to very recent
        collector.last_request_time = 100

        with patch("requests.get", return_value=mock_response) as mock_get:
            with patch(
                "time.time", side_effect=[100.1, 100.6]
            ):  # Only 0.1s passed, need to wait
                with patch("time.sleep") as mock_sleep:
                    response = collector._make_request("http://test.com")

                    assert response == mock_response
                    mock_get.assert_called_once()
                    # Should sleep for remaining time (0.5 - 0.1 = 0.4s)
                    mock_sleep.assert_called_once_with(pytest.approx(0.4, rel=0.01))

    def test_make_request_with_retry(self, collector):
        """Test request retry on failure."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        # First two calls fail, third succeeds
        with patch(
            "requests.get",
            side_effect=[
                requests.RequestException("Connection error"),
                requests.RequestException("Timeout"),
                mock_response,
            ],
        ) as mock_get:
            with patch("time.sleep") as mock_sleep:
                response = collector._make_request("http://test.com")

                assert response == mock_response
                assert mock_get.call_count == 3
                assert mock_sleep.call_count == 2  # Sleep between retries

    def test_make_request_max_retries_exceeded(self, collector):
        """Test request fails after max retries."""
        with patch(
            "requests.get", side_effect=requests.RequestException("Persistent error")
        ):
            with patch("time.sleep"):
                with pytest.raises(requests.RequestException):
                    collector._make_request("http://test.com")

    def test_search_by_title_success(
        self, collector, search_response_html, article_response_html
    ):
        """Test successful paper search by title."""
        with patch.object(collector, "_make_request") as mock_request:
            # Setup mock responses
            search_response = Mock()
            search_response.text = search_response_html

            article_response = Mock()
            article_response.text = article_response_html

            mock_request.side_effect = [search_response, article_response]

            result = collector._search_by_title(
                "Deep Learning for Natural Language Processing", 2024
            )

            assert result is not None
            assert result == ("12345", "98765")
            assert mock_request.call_count == 2

    def test_search_by_title_no_results(self, collector):
        """Test search with no results."""
        with patch.object(collector, "_make_request") as mock_request:
            response = Mock()
            response.text = "<html><body>No results found</body></html>"
            mock_request.return_value = response

            result = collector._search_by_title("Nonexistent Paper", 2024)

            assert result is None

    def test_search_by_title_fuzzy_matching(self, collector, article_response_html):
        """Test fuzzy title matching."""
        search_html = """
        <article class="obj_article_summary">
            <h3 class="title">
                <a href="/index.php/AAAI/article/view/12345">
                    Deep Learning for Natural Language Processing: A Survey
                </a>
            </h3>
            <div class="published">2024</div>
        </article>
        """

        with patch.object(collector, "_make_request") as mock_request:
            search_response = Mock()
            search_response.text = search_html

            article_response = Mock()
            article_response.text = article_response_html

            mock_request.side_effect = [search_response, article_response]

            # Search with slightly different title
            result = collector._search_by_title(
                "Deep Learning for Natural Language Processing", 2024
            )

            assert result is not None
            assert result[0] == "12345"

    def test_get_pdf_id_from_article(self, collector, article_response_html):
        """Test PDF ID extraction from article page."""
        with patch.object(collector, "_make_request") as mock_request:
            response = Mock()
            response.text = article_response_html
            mock_request.return_value = response

            pdf_id = collector._get_pdf_id_from_article("12345")

            assert pdf_id == "98765"

    def test_search_by_authors_success(
        self, collector, search_response_html, article_response_html
    ):
        """Test successful search by authors."""
        with patch.object(collector, "_make_request") as mock_request:
            search_response = Mock()
            search_response.text = search_response_html

            article_response = Mock()
            article_response.text = article_response_html

            mock_request.side_effect = [search_response, article_response]

            result = collector._search_by_authors(
                ["John Smith", "Jane Doe"],
                "Deep Learning for Natural Language Processing",
                2024,
            )

            assert result is not None
            assert result == ("12345", "98765")

    def test_construct_pdf_url(self, collector):
        """Test PDF URL construction."""
        url = collector._construct_pdf_url("12345", "98765")
        expected = "https://ojs.aaai.org/index.php/AAAI/article/download/12345/98765"
        assert url == expected

    def test_discover_single_success(
        self, collector, sample_paper, search_response_html, article_response_html
    ):
        """Test successful PDF discovery."""
        with patch.object(collector, "_make_request") as mock_request:
            search_response = Mock()
            search_response.text = search_response_html

            article_response = Mock()
            article_response.text = article_response_html

            mock_request.side_effect = [search_response, article_response]

            pdf_record = collector._discover_single(sample_paper)

            assert isinstance(pdf_record, PDFRecord)
            assert pdf_record.paper_id == "paper_76"
            assert (
                pdf_record.pdf_url
                == "https://ojs.aaai.org/index.php/AAAI/article/download/12345/98765"
            )
            assert pdf_record.source == "aaai"
            assert pdf_record.confidence_score == 0.95
            assert pdf_record.validation_status == "verified"
            assert pdf_record.version_info["article_id"] == "12345"
            assert pdf_record.version_info["pdf_id"] == "98765"

    def test_discover_single_not_found(self, collector, sample_paper):
        """Test PDF discovery when paper not found."""
        with patch.object(collector, "_search_by_title", return_value=None):
            with patch.object(collector, "_search_by_authors", return_value=None):
                with pytest.raises(ValueError, match="Paper not found"):
                    collector._discover_single(sample_paper)

    def test_year_to_edition_mapping(self, collector):
        """Test year to conference edition mapping."""
        assert collector.year_to_edition[2025] == 39
        assert collector.year_to_edition[2024] == 38
        assert collector.year_to_edition[2019] == 33

    def test_caching(self, collector, search_response_html, article_response_html):
        """Test search result caching."""
        with patch.object(collector, "_make_request") as mock_request:
            search_response = Mock()
            search_response.text = search_response_html

            article_response = Mock()
            article_response.text = article_response_html

            mock_request.side_effect = [search_response, article_response]

            # First search
            result1 = collector._search_by_title(
                "Deep Learning for Natural Language Processing", 2024
            )

            # Second search should use cache
            result2 = collector._search_by_title(
                "Deep Learning for Natural Language Processing", 2024
            )

            assert result1 == result2
            assert mock_request.call_count == 2  # Only called for first search
