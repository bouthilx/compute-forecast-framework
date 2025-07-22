"""Integration tests for AAAI collector."""

import pytest
from datetime import datetime

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.aaai_collector import (
    AAICollector,
)
from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)


@pytest.mark.integration
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


class TestAAIIntegration:
    """Integration tests for AAAI collector with real data."""

    @pytest.fixture
    def collector(self):
        """Create collector instance."""
        return AAICollector()

    @pytest.mark.skip(reason="Requires network access to AAAI site")
    def test_discover_real_paper(self, collector):
        """Test discovering a real AAAI paper.

        This test is skipped by default as it requires network access.
        Run with: pytest -m integration --no-skip
        """
        # Create a paper that should exist in AAAI proceedings
        paper = create_test_paper(
            paper_id="paper_78",
            title="Attention Is All You Need",  # Famous transformer paper
            authors=[Author(name="Ashish Vaswani"), Author(name="Noam Shazeer")],
            venue="AAAI",
            year=2023,  # Adjust year if needed
            citation_count=1000,
        )

        try:
            pdf_record = collector._discover_single(paper)

            # Verify we got a valid PDF record
            assert pdf_record is not None
            assert pdf_record.paper_id == "test_transformer_paper"
            assert pdf_record.source == "aaai"
            assert pdf_record.pdf_url.startswith("https://ojs.aaai.org")
            assert "download" in pdf_record.pdf_url
            assert pdf_record.confidence_score == 0.95
            assert pdf_record.validation_status == "verified"

            print(f"Successfully discovered PDF: {pdf_record.pdf_url}")

        except ValueError as e:
            # Paper might not be in AAAI proceedings
            print(f"Paper not found: {e}")
            pytest.skip(f"Test paper not found in AAAI: {e}")

    @pytest.mark.skip(reason="Requires network access to AAAI site")
    def test_search_functionality(self, collector):
        """Test search functionality with various queries."""
        test_queries = [
            ("reinforcement learning", 2024),
            ("neural networks", 2023),
            ("natural language processing", 2022),
        ]

        for query, year in test_queries:
            result = collector._search_by_title(query, year)
            if result:
                article_id, pdf_id = result
                print(
                    f"Found result for '{query}' ({year}): article={article_id}, pdf={pdf_id}"
                )
            else:
                print(f"No results found for '{query}' ({year})")

    @pytest.mark.skip(reason="Manual test for verifying collector setup")
    def test_collector_configuration(self, collector):
        """Verify collector is properly configured."""
        assert collector.source_name == "aaai"
        assert collector.base_url == "https://ojs.aaai.org"
        assert collector.proceedings_path == "/index.php/AAAI"
        assert collector.search_path == "/index.php/AAAI/search/search"

        # Check year mappings
        assert collector.year_to_edition[2024] == 38
        assert collector.year_to_edition[2025] == 39

        print("Collector configuration verified")

    @pytest.mark.skip(reason="Performance test - requires network")
    def test_rate_limiting(self, collector):
        """Test rate limiting behavior."""
        import time

        papers = [
            create_test_paper(
                paper_id=f"test_{i}",
                title=f"Test Paper {i}",
                authors=[Author(name=f"Author {i}")],
                venue="AAAI",
                year=2024,
                citation_count=10,
            )
            for i in range(3)
        ]

        start_time = time.time()
        results = []

        for paper in papers:
            try:
                result = collector._search_by_title(paper.title, paper.year)
                results.append(result)
            except Exception as e:
                print(f"Error searching for {paper.title}: {e}")

        elapsed = time.time() - start_time

        # Should take at least (n-1) * delay seconds due to rate limiting
        expected_min_time = (len(papers) - 1) * collector.request_delay
        assert elapsed >= expected_min_time, (
            f"Rate limiting not working: {elapsed}s < {expected_min_time}s"
        )

        print(f"Rate limiting test passed: {elapsed:.2f}s for {len(papers)} requests")
