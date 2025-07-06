"""Additional unit tests for collectors to improve coverage."""

from unittest.mock import Mock, patch
from compute_forecast.pdf_discovery.core.collectors import BasePDFCollector
from compute_forecast.data.models import Paper


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
            Paper(
                paper_id="p1",
                title="Test",
                authors=[],
                year=2024,
                citations=0,
                venue="Test",
            )
        ]

        # Should fall back to single discovery
        with patch.object(
            collector, "_discover_single", return_value=Mock(paper_id="p1")
        ) as mock_discover:
            collector.discover_pdfs(papers)
            assert mock_discover.called
