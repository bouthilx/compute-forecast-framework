"""TDD tests for Semantic Scholar PDF Collector improvements based on code review."""

from unittest.mock import Mock, patch

from compute_forecast.pdf_discovery.sources.semantic_scholar_collector import (
    SemanticScholarPDFCollector,
    SEMANTIC_SCHOLAR_MAX_BATCH_SIZE,
    DEFAULT_MAX_RETRIES,
    CONFIDENCE_SCORE_WITH_IDENTIFIER,
    CONFIDENCE_SCORE_TITLE_SEARCH,
)
from compute_forecast.data.models import Paper


class TestSemanticScholarImprovements:
    """Test improvements suggested in code review."""

    def test_constants_are_defined(self):
        """Test that module-level constants are defined."""
        # These should be imported from the module
        assert SEMANTIC_SCHOLAR_MAX_BATCH_SIZE == 500
        assert DEFAULT_MAX_RETRIES == 3
        assert CONFIDENCE_SCORE_WITH_IDENTIFIER == 0.9
        assert CONFIDENCE_SCORE_TITLE_SEARCH == 0.8

    def test_collector_uses_constants(self):
        """Test that collector uses module-level constants."""
        collector = SemanticScholarPDFCollector()
        assert collector.batch_size == SEMANTIC_SCHOLAR_MAX_BATCH_SIZE
        assert collector.max_retries == DEFAULT_MAX_RETRIES

    @patch(
        "src.pdf_discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_simplified_paper_matching(self, mock_ss_class):
        """Test simplified paper matching logic in batch processing."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Create test papers
        papers = []

        # Paper with DOI
        p1 = Paper(
            paper_id="doi_paper",
            title="DOI Paper",
            authors=[],
            year=2024,
            citations=0,
            venue="Test",
        )
        p1.doi = "10.1234/test"
        papers.append(p1)

        # Paper with arXiv ID
        p2 = Paper(
            paper_id="arxiv_paper",
            title="ArXiv Paper",
            authors=[],
            year=2024,
            citations=0,
            venue="Test",
        )
        p2.arxiv_id = "2301.00001"
        papers.append(p2)

        # Mock batch response
        mock_api.get_papers.return_value = [
            {
                "paperId": "ss_1",
                "doi": "10.1234/test",
                "openAccessPdf": {"url": "doi.pdf", "status": "GREEN"},
            },
            {
                "paperId": "ss_2",
                "arxivId": "2301.00001",
                "openAccessPdf": {"url": "arxiv.pdf", "status": "GREEN"},
            },
        ]

        collector = SemanticScholarPDFCollector()

        # The new implementation should use _match_paper_to_response helper
        results = collector.discover_pdfs_batch(papers)

        assert len(results) == 2
        assert results["doi_paper"].pdf_url == "doi.pdf"
        assert results["arxiv_paper"].pdf_url == "arxiv.pdf"

    def test_docstring_with_examples(self):
        """Test that key methods have proper docstring examples."""
        # Check discover_pdfs_batch docstring
        docstring = SemanticScholarPDFCollector.discover_pdfs_batch.__doc__
        assert "Example:" in docstring
        assert "collector = SemanticScholarPDFCollector()" in docstring
        assert "records = collector.discover_pdfs_batch([paper1, paper2])" in docstring

    @patch("time.sleep", return_value=None)
    @patch(
        "src.pdf_discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_error_handling_with_severity(self, mock_ss_class, mock_sleep):
        """Test that errors are handled with appropriate severity levels."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock API to fail
        mock_api.get_papers.side_effect = Exception("API Error")

        # Paper with identifier (should attempt batch)
        p1 = Paper(
            paper_id="test_paper",
            title="Test Paper",
            authors=[],
            year=2024,
            citations=0,
            venue="Test",
        )
        p1.doi = "10.1234/test"

        # Mock _discover_single to also fail
        mock_api.get_paper.side_effect = Exception("API Error")
        mock_api.search_paper.side_effect = Exception("API Error")

        collector = SemanticScholarPDFCollector()

        # Should handle errors gracefully and log appropriately
        results = collector.discover_pdfs_batch([p1])

        # Should return empty results but not crash
        assert len(results) == 0
