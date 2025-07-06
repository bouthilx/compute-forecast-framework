"""Unit tests for PDF discovery collectors."""

import pytest
from unittest.mock import patch
from datetime import datetime
from typing import Dict, List

from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.pdf_discovery.core.collectors import BasePDFCollector
from compute_forecast.data.models import Paper


class MockPDFCollector(BasePDFCollector):
    """Mock implementation for testing."""

    def __init__(self, source_name: str = "mock", delay: float = 0):
        super().__init__(source_name)
        self.delay = delay
        self.called_with = []

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Mock discovery implementation."""
        self.called_with.append(paper.paper_id)

        if self.delay:
            import time

            time.sleep(self.delay)

        if paper.paper_id == "fail_paper":
            raise ValueError("Failed to discover PDF")

        return PDFRecord(
            paper_id=paper.paper_id,
            pdf_url=f"https://mock.com/{paper.paper_id}.pdf",
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=0.9,
            version_info={},
            validation_status="mock",
        )


class TestBasePDFCollector:
    """Test BasePDFCollector abstract class."""

    def test_base_collector_initialization(self):
        """Test collector initialization."""
        collector = MockPDFCollector("test_source")
        assert collector.source_name == "test_source"
        assert collector.timeout == 60  # Default timeout

    def test_base_collector_custom_timeout(self):
        """Test collector with custom timeout."""
        collector = MockPDFCollector("test_source")
        collector.timeout = 30
        assert collector.timeout == 30

    def test_discover_pdfs_single_paper(self):
        """Test discovering PDF for a single paper."""
        collector = MockPDFCollector()
        paper = Paper(
            paper_id="paper_123",
            title="Test Paper",
            authors=[],
            year=2024,
            citations=10,
            venue="Test Venue",
        )

        results = collector.discover_pdfs([paper])

        assert len(results) == 1
        assert "paper_123" in results
        assert results["paper_123"].pdf_url == "https://mock.com/paper_123.pdf"
        assert results["paper_123"].source == "mock"

    def test_discover_pdfs_multiple_papers(self):
        """Test discovering PDFs for multiple papers."""
        collector = MockPDFCollector()
        papers = [
            Paper(
                paper_id=f"paper_{i}",
                title=f"Test Paper {i}",
                authors=[],
                year=2024,
                citations=i,
                venue="Test Venue",
            )
            for i in range(5)
        ]

        results = collector.discover_pdfs(papers)

        assert len(results) == 5
        for i in range(5):
            assert f"paper_{i}" in results
            assert results[f"paper_{i}"].pdf_url == f"https://mock.com/paper_{i}.pdf"

    def test_discover_pdfs_with_failures(self):
        """Test discovery with some failures."""
        collector = MockPDFCollector()
        papers = [
            Paper(
                paper_id="paper_1",
                title="Success 1",
                authors=[],
                year=2024,
                citations=0,
                venue="Test",
            ),
            Paper(
                paper_id="fail_paper",
                title="Fail",
                authors=[],
                year=2024,
                citations=0,
                venue="Test",
            ),
            Paper(
                paper_id="paper_2",
                title="Success 2",
                authors=[],
                year=2024,
                citations=0,
                venue="Test",
            ),
        ]

        results = collector.discover_pdfs(papers)

        assert len(results) == 2
        assert "paper_1" in results
        assert "paper_2" in results
        assert "fail_paper" not in results

    def test_discover_pdfs_empty_list(self):
        """Test discovery with empty paper list."""
        collector = MockPDFCollector()
        results = collector.discover_pdfs([])
        assert results == {}

    def test_discover_pdfs_with_timeout(self):
        """Test discovery with timeout handling."""
        # Create a slow collector
        slow_collector = MockPDFCollector(delay=0.1)
        slow_collector.timeout = 0.05  # 50ms timeout

        papers = [
            Paper(
                paper_id="paper_1",
                title="Test",
                authors=[],
                year=2024,
                citations=0,
                venue="Test",
            )
        ]

        # Should timeout and return empty results
        results = slow_collector.discover_pdfs(papers)
        assert len(results) == 0  # Timed out

    def test_collector_logging(self):
        """Test that collector logs activities."""
        with patch("src.pdf_discovery.core.collectors.logger") as mock_logger:
            collector = MockPDFCollector()
            papers = [
                Paper(
                    paper_id="paper_1",
                    title="Test",
                    authors=[],
                    year=2024,
                    citations=0,
                    venue="Test",
                ),
                Paper(
                    paper_id="fail_paper",
                    title="Fail",
                    authors=[],
                    year=2024,
                    citations=0,
                    venue="Test",
                ),
            ]

            collector.discover_pdfs(papers)

            # Check logging calls
            assert mock_logger.info.called
            assert mock_logger.error.called

            # Verify info message about starting discovery
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Starting PDF discovery" in str(call) for call in info_calls)
            assert any("Discovered 1/2" in str(call) for call in info_calls)

    def test_abstract_method_enforcement(self):
        """Test that abstract methods must be implemented."""
        with pytest.raises(TypeError):
            # Should fail because _discover_single is not implemented
            class IncompleteCollector(BasePDFCollector):
                pass

            IncompleteCollector("test")

    def test_collector_statistics_tracking(self):
        """Test that collector tracks statistics."""
        collector = MockPDFCollector()

        # Initial stats
        stats = collector.get_statistics()
        assert stats["attempted"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0

        # After discovery
        papers = [
            Paper(
                paper_id="paper_1",
                title="Success",
                authors=[],
                year=2024,
                citations=0,
                venue="Test",
            ),
            Paper(
                paper_id="fail_paper",
                title="Fail",
                authors=[],
                year=2024,
                citations=0,
                venue="Test",
            ),
        ]

        collector.discover_pdfs(papers)

        stats = collector.get_statistics()
        assert stats["attempted"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1

    def test_batch_discovery(self):
        """Test batch discovery optimization."""
        collector = MockPDFCollector()

        # Override with batch implementation
        def batch_discover(self, papers: List[Paper]) -> Dict[str, PDFRecord]:
            # Simulate batch API call
            return {
                paper.paper_id: PDFRecord(
                    paper_id=paper.paper_id,
                    pdf_url=f"https://batch.com/{paper.paper_id}.pdf",
                    source=self.source_name,
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.95,
                    version_info={},
                    validation_status="batch",
                )
                for paper in papers
            }

        # Monkey patch the batch method
        collector.discover_pdfs_batch = batch_discover.__get__(
            collector, MockPDFCollector
        )

        papers = [
            Paper(
                paper_id=f"paper_{i}",
                title=f"Test {i}",
                authors=[],
                year=2024,
                citations=0,
                venue="Test",
            )
            for i in range(10)
        ]

        # Enable batch mode
        collector.supports_batch = True
        results = collector.discover_pdfs(papers)

        assert len(results) == 10
        assert all(record.validation_status == "batch" for record in results.values())
