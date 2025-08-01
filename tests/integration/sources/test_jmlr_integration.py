"""Integration tests for JMLR/TMLR PDF collector."""

import pytest
from datetime import datetime

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.sources.jmlr_collector import (
    JMLRCollector,
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


class TestJMLRIntegration:
    """Integration tests for JMLR/TMLR collector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.collector = JMLRCollector()

    @pytest.mark.skip(reason="Requires network access to jmlr.org")
    def test_discover_real_jmlr_paper(self):
        """Test discovering a real JMLR paper."""
        # This is a real JMLR paper that should exist
        paper = create_test_paper(
            paper_id="test_jmlr_1",
            title="A Dual Coordinate Descent Method for Large-scale Linear SVM",
            venue="Journal of Machine Learning Research",
            authors=[],
            year=2008,
            citation_count=0,
        )

        record = self.collector._discover_single(paper)

        assert record is not None
        assert record.paper_id == "test_jmlr_1"
        assert record.pdf_url == "https://jmlr.org/papers/v9/hsieh08a.pdf"
        assert record.source == "jmlr_tmlr"
        assert record.confidence_score > 0.9
        assert record.validation_status == "verified"

    @pytest.mark.skip(reason="Requires network access to jmlr.org")
    def test_discover_real_tmlr_paper(self):
        """Test discovering a real TMLR paper."""
        # This would need a real TMLR paper title
        paper = create_test_paper(
            paper_id="test_tmlr_1",
            title="Example TMLR Paper Title",  # Replace with real paper
            venue="Transactions on Machine Learning Research",
            authors=[],
            year=2023,
            citation_count=0,
        )

        try:
            record = self.collector._discover_single(paper)

            assert record is not None
            assert record.paper_id == "test_tmlr_1"
            assert record.source == "jmlr_tmlr"
            assert record.pdf_url.startswith("https://jmlr.org/tmlr/papers/")
            assert record.pdf_url.endswith(".pdf")
        except ValueError as e:
            # Expected if the paper doesn't exist
            assert "Could not find TMLR paper" in str(e)

    def test_collector_statistics(self):
        """Test that collector tracks statistics correctly."""
        papers = [
            create_test_paper(
                paper_id="test1",
                title="Test Paper 1",
                venue="JMLR",
                authors=[],
                year=2023,
                citation_count=0,
            ),
            create_test_paper(
                paper_id="test2",
                title="Test Paper 2",
                venue="NeurIPS",  # Not JMLR/TMLR
                authors=[],
                year=2023,
                citation_count=0,
            ),
        ]

        # Run discovery (will fail for both in test environment)
        self.collector.discover_pdfs(papers)

        stats = self.collector.get_statistics()
        assert stats["attempted"] == 2
        assert stats["failed"] == 2  # Both should fail without network
        assert stats["successful"] == 0
