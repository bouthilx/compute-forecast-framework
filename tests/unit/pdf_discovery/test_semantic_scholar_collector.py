"""Unit tests for Semantic Scholar PDF Collector."""

import pytest
from unittest.mock import Mock, patch
import time
from datetime import datetime

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector import (
    SemanticScholarPDFCollector,
)
from compute_forecast.pipeline.metadata_collection.models import Paper, Author
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
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
    )


class TestSemanticScholarPDFCollector:
    """Test SemanticScholarPDFCollector implementation."""

    def test_collector_initialization(self):
        """Test collector initialization with default settings."""
        collector = SemanticScholarPDFCollector()
        assert collector.source_name == "semantic_scholar"
        assert collector.supports_batch is True
        assert collector.batch_size == 500
        assert collector.rate_limit_delay == 3.0  # 100 requests per 5 minutes
        assert collector.timeout == 60

    def test_collector_with_api_key(self):
        """Test collector initialization with API key."""
        collector = SemanticScholarPDFCollector(api_key="test_key")
        assert collector.api_key == "test_key"
        assert collector.rate_limit_delay == 0.5  # Faster with API key

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_discover_single_paper_with_pdf(self, mock_ss_class, mock_sleep):
        """Test discovering a single paper with available PDF."""
        # Mock the API response
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        mock_paper_response = {
            "paperId": "ss_12345",
            "title": "Test Paper",
            "openAccessPdf": {
                "url": "https://arxiv.org/pdf/2301.00001.pdf",
                "status": "GREEN",
            },
        }
        # Mock direct lookup to return None (no DOI/arxiv_id on paper)
        mock_api.get_paper.return_value = None
        # Mock search to return our paper
        mock_api.search_paper.return_value = {"data": [mock_paper_response]}

        collector = SemanticScholarPDFCollector()
        paper = create_test_paper(
            paper_id="test_paper_1",
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
            citation_count=10,
            venue="Test Conference",
        )

        pdf_record = collector._discover_single(paper)

        assert pdf_record.paper_id == "test_paper_1"
        assert pdf_record.pdf_url == "https://arxiv.org/pdf/2301.00001.pdf"
        assert pdf_record.source == "semantic_scholar"
        assert (
            pdf_record.confidence_score == 0.8
        )  # Search by title has lower confidence
        assert pdf_record.validation_status == "GREEN"
        assert pdf_record.version_info["ss_paper_id"] == "ss_12345"

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_discover_single_paper_without_pdf(self, mock_ss_class, mock_sleep):
        """Test discovering a single paper without available PDF."""
        # Mock the API response
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        mock_paper_response = {
            "paperId": "ss_12345",
            "title": "Test Paper",
            "openAccessPdf": None,
        }
        # Mock direct lookup to return None (no DOI/arxiv_id on paper)
        mock_api.get_paper.return_value = None
        # Mock search to return our paper without PDF
        mock_api.search_paper.return_value = {"data": [mock_paper_response]}

        collector = SemanticScholarPDFCollector()
        paper = create_test_paper(
            paper_id="test_paper_1",
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
            citation_count=10,
            venue="Test Conference",
        )

        with pytest.raises(ValueError, match="No PDF available"):
            collector._discover_single(paper)

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_batch_discovery(self, mock_ss_class, mock_sleep):
        """Test batch discovery of multiple papers."""
        # Mock the API
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock API to handle both single and batch
        mock_api.get_paper.return_value = None  # No identifiers

        # Mock search results for each paper
        def search_side_effect(query, limit=5):
            if "Paper 1" in query:
                return {
                    "data": [
                        {
                            "paperId": "ss_1",
                            "title": "Paper 1",
                            "openAccessPdf": {
                                "url": "https://arxiv.org/pdf/2301.00001.pdf",
                                "status": "GREEN",
                            },
                        }
                    ]
                }
            elif "Paper 2" in query:
                return {
                    "data": [
                        {
                            "paperId": "ss_2",
                            "title": "Paper 2",
                            "openAccessPdf": {
                                "url": "https://arxiv.org/pdf/2301.00002.pdf",
                                "status": "GOLD",
                            },
                        }
                    ]
                }
            elif "Paper 3" in query:
                return {
                    "data": [
                        {
                            "paperId": "ss_3",
                            "title": "Paper 3",
                            "openAccessPdf": None,  # No PDF
                        }
                    ]
                }
            return {"data": []}

        mock_api.search_paper.side_effect = search_side_effect
        mock_api.get_papers.return_value = []  # No batch lookup

        collector = SemanticScholarPDFCollector()
        papers = [
            create_test_paper(
                paper_id=f"paper_{i}",
                title=f"Paper {i}",
                authors=[Author(name="Test Author")],
                year=2024,
                citation_count=i,
                venue="Test",
            )
            for i in range(1, 4)
        ]

        results = collector.discover_pdfs(papers)

        assert len(results) == 2  # Only papers with PDFs
        assert "paper_1" in results
        assert "paper_2" in results
        assert "paper_3" not in results

        assert results["paper_1"].pdf_url == "https://arxiv.org/pdf/2301.00001.pdf"
        assert results["paper_2"].pdf_url == "https://arxiv.org/pdf/2301.00002.pdf"

    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_rate_limiting(self, mock_ss_class):
        """Test rate limiting between requests."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock responses
        mock_api.get_paper.return_value = None
        mock_api.search_paper.return_value = {
            "data": [
                {
                    "paperId": "ss_1",
                    "title": "Test",
                    "openAccessPdf": {"url": "test.pdf", "status": "GREEN"},
                }
            ]
        }

        collector = SemanticScholarPDFCollector()
        collector.rate_limit_delay = 0.1  # Short delay for testing

        papers = [
            create_test_paper(
                paper_id=f"paper_{i}",
                title=f"Paper {i}",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
            for i in range(3)
        ]

        start_time = time.time()
        results = collector.discover_pdfs(papers)
        elapsed = time.time() - start_time

        # Should have delays between requests
        assert elapsed >= 0.2  # At least 2 delays of 0.1s
        assert len(results) == 3

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_retry_logic_on_failure(self, mock_ss_class, mock_sleep):
        """Test retry logic when API fails."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock get_paper to return None (no identifiers)
        mock_api.get_paper.return_value = None

        # First two search calls fail, third succeeds
        mock_api.search_paper.side_effect = [
            Exception("API Error"),
            Exception("API Error"),
            {
                "data": [
                    {
                        "paperId": "ss_1",
                        "title": "Test",
                        "openAccessPdf": {"url": "test.pdf", "status": "GREEN"},
                    }
                ]
            },
        ]

        collector = SemanticScholarPDFCollector()
        collector.max_retries = 3
        collector.retry_delay = 0.01  # Short for testing

        paper = create_test_paper(
            paper_id="test_paper",
            title="Test Paper",
            authors=[],
            year=2024,
            citation_count=0,
            venue="Test",
        )

        pdf_record = collector._discover_single(paper)

        assert pdf_record.pdf_url == "test.pdf"
        assert mock_api.search_paper.call_count == 3

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_handle_large_batch(self, mock_ss_class, mock_sleep):
        """Test handling batches larger than API limit."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock all papers to have semantic_scholar_id for batch processing
        papers = []
        for i in range(600):
            paper = create_test_paper(
                paper_id=f"paper_{i}",
                title=f"Paper {i}",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
            paper.semantic_scholar_id = f"ss_{i}"  # Add ID for batch lookup
            papers.append(paper)

        # Mock batch responses
        def mock_batch_response(paper_ids):
            # Convert IDs back to response format
            results = []
            for pid in paper_ids:
                if pid.startswith("ss_"):
                    idx = pid.replace("ss_", "")
                    results.append(
                        {
                            "paperId": pid,
                            "title": f"Paper {idx}",
                            "openAccessPdf": {
                                "url": f"https://test.com/{idx}.pdf",
                                "status": "GREEN",
                            },
                        }
                    )
            return results

        mock_api.get_papers.side_effect = mock_batch_response
        mock_api.get_paper.return_value = None
        mock_api.search_paper.return_value = {"data": []}

        collector = SemanticScholarPDFCollector()

        results = collector.discover_pdfs(papers)

        assert len(results) == 600
        assert mock_api.get_papers.call_count == 2  # Two batches

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_search_by_title_fallback(self, mock_ss_class, mock_sleep):
        """Test fallback to search by title when paper lookup fails."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Direct lookup fails
        mock_api.get_paper.return_value = None

        # Search succeeds
        mock_api.search_paper.return_value = {
            "data": [
                {
                    "paperId": "ss_found",
                    "title": "Test Paper",
                    "openAccessPdf": {"url": "https://found.pdf", "status": "GREEN"},
                }
            ]
        }

        collector = SemanticScholarPDFCollector()
        paper = create_test_paper(
            paper_id="test_paper",
            title="Test Paper",
            authors=[Author(name="John Doe")],
            year=2024,
            citation_count=0,
            venue="Test",
        )

        pdf_record = collector._discover_single(paper)

        assert pdf_record.pdf_url == "https://found.pdf"
        assert pdf_record.version_info["ss_paper_id"] == "ss_found"
        assert pdf_record.confidence_score == 0.8  # Lower confidence for search

    def test_statistics_tracking(self):
        """Test that statistics are properly tracked."""
        with patch("time.sleep", return_value=None):
            with patch(
                "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
            ) as mock_ss:
                mock_api = Mock()
                mock_ss.return_value = mock_api

                # Mix of successes and failures
                mock_api.get_paper.return_value = None

                def search_side_effect(query, limit=5):
                    if "Paper 0" in query:
                        return {
                            "data": [
                                {
                                    "paperId": "ss_1",
                                    "openAccessPdf": {
                                        "url": "test1.pdf",
                                        "status": "GREEN",
                                    },
                                }
                            ]
                        }
                    elif "Paper 1" in query:
                        return {
                            "data": [
                                {
                                    "paperId": "ss_2",
                                    "openAccessPdf": None,  # No PDF
                                }
                            ]
                        }
                    return {"data": []}

                mock_api.search_paper.side_effect = search_side_effect
                mock_api.get_papers.return_value = []

                collector = SemanticScholarPDFCollector()
                papers = [
                    create_test_paper(
                        paper_id=f"paper_{i}",
                        title=f"Paper {i}",
                        authors=[],
                        year=2024,
                        citation_count=0,
                        venue="Test",
                    )
                    for i in range(2)
                ]

                results = collector.discover_pdfs(papers)
                stats = collector.get_statistics()

                assert stats["attempted"] == 2
                # The base class handles statistics tracking automatically
                assert len(results) == 1  # Only one PDF found
                assert stats["successful"] == 1
                assert stats["failed"] == 1

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_discover_with_doi(self, mock_ss_class, mock_sleep):
        """Test discovering paper using DOI."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock DOI lookup
        mock_api.get_paper.return_value = {
            "paperId": "ss_doi",
            "title": "Paper with DOI",
            "openAccessPdf": {"url": "https://doi.pdf", "status": "GOLD"},
        }

        collector = SemanticScholarPDFCollector()
        paper = create_test_paper(
            paper_id="doi_paper",
            title="Paper with DOI",
            authors=[],
            year=2024,
            citation_count=0,
            venue="Test",
        )
        paper.doi = "10.1234/test"

        pdf_record = collector._discover_single(paper)

        assert pdf_record.pdf_url == "https://doi.pdf"
        assert pdf_record.confidence_score == 0.9  # Higher confidence for DOI
        mock_api.get_paper.assert_called_with("DOI:10.1234/test")

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_discover_with_arxiv_id(self, mock_ss_class, mock_sleep):
        """Test discovering paper using arXiv ID."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock arXiv lookup
        mock_api.get_paper.return_value = {
            "paperId": "ss_arxiv",
            "title": "ArXiv Paper",
            "openAccessPdf": {
                "url": "https://arxiv.org/pdf/2301.00001.pdf",
                "status": "GREEN",
            },
        }

        collector = SemanticScholarPDFCollector()
        paper = create_test_paper(
            paper_id="arxiv_paper",
            title="ArXiv Paper",
            authors=[],
            year=2024,
            citation_count=0,
            venue="Test",
        )
        paper.arxiv_id = "2301.00001"

        pdf_record = collector._discover_single(paper)

        assert pdf_record.pdf_url == "https://arxiv.org/pdf/2301.00001.pdf"
        assert pdf_record.confidence_score == 0.9  # Should be 0.9 for identifiers

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_discover_with_ss_id(self, mock_ss_class, mock_sleep):
        """Test discovering paper using Semantic Scholar ID."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock SS ID lookup
        mock_api.get_paper.return_value = {
            "paperId": "ss_direct",
            "title": "SS ID Paper",
            "openAccessPdf": {"url": "https://direct.pdf", "status": "BRONZE"},
        }

        collector = SemanticScholarPDFCollector()
        paper = create_test_paper(
            paper_id="ss_id_paper",
            title="SS ID Paper",
            authors=[],
            year=2024,
            citation_count=0,
            venue="Test",
        )
        paper.semantic_scholar_id = "ss_direct"

        pdf_record = collector._discover_single(paper)

        assert pdf_record.pdf_url == "https://direct.pdf"
        assert pdf_record.confidence_score == 0.9
        assert pdf_record.validation_status == "BRONZE"

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_search_fallback_no_exact_match(self, mock_ss_class, mock_sleep):
        """Test search fallback when no exact title match found."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # No identifiers
        mock_api.get_paper.return_value = None

        # Search returns similar but not exact match
        mock_api.search_paper.return_value = {
            "data": [
                {
                    "paperId": "ss_similar",
                    "title": "Similar Title Paper",  # Not exact match
                    "openAccessPdf": {"url": "https://similar.pdf", "status": "GREEN"},
                }
            ]
        }

        collector = SemanticScholarPDFCollector()
        paper = create_test_paper(
            paper_id="test_paper",
            title="Different Title",
            authors=[],
            year=2024,
            citation_count=0,
            venue="Test",
        )

        pdf_record = collector._discover_single(paper)

        # Should take first result even if not exact match
        assert pdf_record.pdf_url == "https://similar.pdf"
        assert pdf_record.confidence_score == 0.8

    @patch("time.sleep", return_value=None)
    @patch(
        "compute_forecast.pipeline.pdf_acquisition.discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_batch_error_handling(self, mock_ss_class, mock_sleep):
        """Test batch discovery error handling."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock batch call to fail
        mock_api.get_papers.side_effect = Exception("Batch API Error")
        mock_api.get_paper.return_value = None
        mock_api.search_paper.return_value = {
            "data": [
                {
                    "paperId": "ss_fallback",
                    "title": "Test",
                    "openAccessPdf": {"url": "fallback.pdf", "status": "GREEN"},
                }
            ]
        }

        collector = SemanticScholarPDFCollector()

        # Create papers with SS IDs to trigger batch path
        papers = []
        for i in range(2):
            p = create_test_paper(
                paper_id=f"paper_{i}",
                title=f"Paper {i}",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
            p.semantic_scholar_id = f"ss_{i}"
            papers.append(p)

        # Should fall back to individual discovery
        results = collector.discover_pdfs(papers)
        assert len(results) == 2  # Both found via fallback
