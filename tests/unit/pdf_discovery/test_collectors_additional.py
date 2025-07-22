"""Additional unit tests for collectors to improve coverage."""

from unittest.mock import Mock, patch
from compute_forecast.pipeline.pdf_acquisition.discovery.core.collectors import (
    BasePDFCollector,
)
from compute_forecast.pipeline.metadata_collection.models import Paper
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


class SimpleCollector(BasePDFCollector):
    """Simple collector for testing."""

    def _discover_single(self, paper: Paper):
        return Mock(paper_id=paper.paper_id)


class TestAdditionalCollectorCoverage:
    """Additional tests to achieve 90%+ coverage."""

    def test_reset_statistics(self):
        """Test resetting collector statistics."""
        collector = SimpleCollector("test")

        # Modify stats
        collector._stats["attempted"] = 10
        collector._stats["successful"] = 8
        collector._stats["failed"] = 2

        # Reset
        collector.reset_statistics()

        # Should be back to zeros
        stats = collector.get_statistics()
        assert stats["attempted"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0

    def test_collector_with_batch_but_no_method(self):
        """Test collector that claims batch support but has no method."""
        collector = SimpleCollector("test")
        collector.supports_batch = True  # Claims support
        # But doesn't implement discover_pdfs_batch

        papers = [
            create_test_paper(
                paper_id="p1",
                title="Test",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
        ]

        # Should fall back to single discovery
        with patch.object(
            collector, "_discover_single", return_value=Mock(paper_id="p1")
        ) as mock_discover:
            collector.discover_pdfs(papers)
            assert mock_discover.called
