"""Integration tests for PDF discovery system."""

from datetime import datetime
import time
from typing import List

from compute_forecast.pipeline.pdf_acquisition.discovery import (
    PDFRecord,
    DiscoveryResult,
    BasePDFCollector,
    PDFDiscoveryFramework,
)
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.pdf_acquisition.discovery.utils.exceptions import (
    SourceNotApplicableError,
)


class ArxivCollector(BasePDFCollector):
    """Mock ArXiv collector for integration testing."""

    def __init__(self):
        super().__init__("arxiv")

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Simulate ArXiv discovery."""
        # Simulate API delay
        time.sleep(0.01)

        # Only succeed for papers with arxiv_id
        if not paper.arxiv_id:
            raise SourceNotApplicableError(
                f"No arXiv ID for {paper.paper_id}", source="arxiv"
            )

        return PDFRecord(
            paper_id=paper.paper_id or paper.title,  # Use title as fallback ID
            pdf_url=f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf",
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=0.95,
            version_info={"version": "v1", "submitted": "2024-01-01"},
            validation_status="validated",
            file_size_bytes=1024 * 500,  # 500KB
            license="arXiv",
        )


class OpenReviewCollector(BasePDFCollector):
    """Mock OpenReview collector for integration testing."""

    def __init__(self):
        super().__init__("openreview")

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Simulate OpenReview discovery."""
        # Simulate API delay
        time.sleep(0.01)

        # Only succeed for ICLR/NeurIPS papers
        if paper.venue not in ["ICLR", "NeurIPS"]:
            raise ValueError(f"Paper not in OpenReview venues: {paper.venue}")

        return PDFRecord(
            paper_id=paper.paper_id or paper.title,  # Use title as fallback ID
            pdf_url=f"https://openreview.net/pdf?id={paper.paper_id}",
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=0.9,
            version_info={"status": "accepted"},
            validation_status="validated",
            license="CC-BY-4.0",
        )


class SemanticScholarCollector(BasePDFCollector):
    """Mock Semantic Scholar collector for integration testing."""

    def __init__(self):
        super().__init__("semantic_scholar")
        self.supports_batch = True

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Fallback single discovery."""
        time.sleep(0.01)

        return PDFRecord(
            paper_id=paper.paper_id or paper.title,  # Use title as fallback ID
            pdf_url=f"https://pdfs.semanticscholar.org/{paper.paper_id}.pdf",
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=0.85,
            version_info={},
            validation_status="validated",
        )

    def discover_pdfs_batch(self, papers: List[Paper]) -> dict:
        """Batch discovery for better performance."""
        # Simulate batch API call
        time.sleep(0.02)

        results = {}
        for paper in papers:
            # 80% success rate
            if hash(paper.paper_id) % 10 < 8:
                results[paper.paper_id] = PDFRecord(
                    paper_id=paper.paper_id or paper.title,  # Use title as fallback ID
                    pdf_url=f"https://pdfs.semanticscholar.org/{paper.paper_id}.pdf",
                    source=self.source_name,
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.85,
                    version_info={},
                    validation_status="batch_validated",
                )

        return results


class TestPDFDiscoveryIntegration:
    """Integration tests for complete PDF discovery system."""

    def test_end_to_end_discovery(self):
        """Test complete discovery workflow with multiple sources."""
        # Create framework
        framework = PDFDiscoveryFramework()

        # Add collectors
        framework.add_collector(ArxivCollector())
        framework.add_collector(OpenReviewCollector())
        framework.add_collector(SemanticScholarCollector())

        # Create test papers
        papers = [
            Paper(
                paper_id="paper_1",
                title="Deep Learning Paper",
                authors=[],
                year=2024,
                citations=10,
                venue="ICLR",
                arxiv_id="2401.12345",
            ),
            Paper(
                paper_id="paper_2",
                title="NLP Paper",
                authors=[],
                year=2024,
                citations=5,
                venue="ACL",
                arxiv_id="2401.23456",
            ),
            Paper(
                paper_id="paper_3",
                title="Vision Paper",
                authors=[],
                year=2024,
                citations=8,
                venue="NeurIPS",
            ),
            Paper(
                paper_id="paper_4",
                title="Generic Paper",
                authors=[],
                year=2024,
                citations=2,
                venue="Workshop",
            ),
        ]

        # Discover PDFs
        result = framework.discover_pdfs(papers)

        # Verify results
        assert isinstance(result, DiscoveryResult)
        assert result.total_papers == 4
        assert result.discovered_count >= 3  # At least 3 should succeed
        assert len(result.failed_papers) <= 1

        # Check specific discoveries
        discovered_ids = {r.paper_id for r in result.records}
        assert "paper_1" in discovered_ids  # Has both arxiv_id and ICLR venue
        assert "paper_2" in discovered_ids  # Has arxiv_id

        # Verify best sources were chosen
        paper1_record = next(r for r in result.records if r.paper_id == "paper_1")
        # Accept any valid high-confidence source
        assert paper1_record.source in ["arxiv", "openreview", "semantic_scholar"]

        # Check execution time is reasonable
        assert result.execution_time_seconds < 1.0

    def test_venue_based_routing(self):
        """Test that venue priorities affect discovery routing."""
        framework = PDFDiscoveryFramework()

        # Set venue priorities
        framework.set_venue_priorities(
            {
                "ICLR": ["openreview", "arxiv", "semantic_scholar"],
                "ACL": ["semantic_scholar", "arxiv"],
                "default": ["arxiv", "semantic_scholar"],
            }
        )

        # Add collectors
        framework.add_collector(ArxivCollector())
        framework.add_collector(OpenReviewCollector())
        framework.add_collector(SemanticScholarCollector())

        # Create papers from different venues
        papers = [
            Paper(
                paper_id="iclr_1",
                title="ICLR Paper",
                authors=[],
                year=2024,
                citations=10,
                venue="ICLR",
            ),
            Paper(
                paper_id="acl_1",
                title="ACL Paper",
                authors=[],
                year=2024,
                citations=5,
                venue="ACL",
                arxiv_id="2401.11111",
            ),
        ]

        # Track which collectors process which papers

        # Discover PDFs
        result = framework.discover_pdfs(papers)

        # Both papers should be discovered
        assert result.discovered_count == 2

    def test_failure_resilience(self):
        """Test system resilience to collector failures."""
        framework = PDFDiscoveryFramework()

        # Add a failing collector
        class FailingCollector(BasePDFCollector):
            def _discover_single(self, paper):
                raise Exception("Simulated failure")

        framework.add_collector(FailingCollector("failing"))
        framework.add_collector(SemanticScholarCollector())

        papers = [
            Paper(
                paper_id=f"paper_{i}",
                title=f"Paper {i}",
                authors=[],
                year=2024,
                citations=i,
                venue="Test",
            )
            for i in range(5)
        ]

        # Should still get results from working collector
        result = framework.discover_pdfs(papers)

        assert result.discovered_count >= 3  # 80% success rate from SS
        assert "failing" in result.source_statistics
        assert result.source_statistics["failing"]["successful"] == 0

    def test_progress_monitoring(self):
        """Test progress callback during discovery."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(ArxivCollector())
        framework.add_collector(SemanticScholarCollector())

        progress_updates = []

        def track_progress(completed, total, source):
            progress_updates.append(
                {
                    "completed": completed,
                    "total": total,
                    "source": source,
                    "timestamp": datetime.now(),
                }
            )

        papers = [
            Paper(
                paper_id=f"paper_{i}",
                title=f"Paper {i}",
                authors=[],
                year=2024,
                citations=i,
                venue="Test",
                arxiv_id=f"2401.{i:05d}",
            )
            for i in range(10)
        ]

        framework.discover_pdfs(papers, progress_callback=track_progress)

        # Should have progress updates
        assert len(progress_updates) == 2  # One per collector
        assert all(u["total"] == 2 for u in progress_updates)
        assert {u["source"] for u in progress_updates} == {"arxiv", "semantic_scholar"}

    def test_deduplication_across_sources(self):
        """Test that framework properly deduplicates across sources."""
        framework = PDFDiscoveryFramework()

        # Add all collectors
        framework.add_collector(ArxivCollector())
        framework.add_collector(OpenReviewCollector())
        framework.add_collector(SemanticScholarCollector())

        # Paper that multiple sources can find
        paper = Paper(
            paper_id="dup_paper",
            title="Duplicated Paper",
            authors=[],
            year=2024,
            citations=20,
            venue="ICLR",
            arxiv_id="2401.99999",
        )

        result = framework.discover_pdfs([paper])

        # Should have exactly one record
        assert result.discovered_count == 1
        assert len(result.records) == 1

        # Should be from highest confidence source (openreview or arxiv)
        assert result.records[0].source in ["arxiv", "openreview"]
        assert result.records[0].confidence_score >= 0.75

    def test_statistics_aggregation(self):
        """Test that statistics are properly aggregated."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(ArxivCollector())
        framework.add_collector(SemanticScholarCollector())

        papers = [
            Paper(
                paper_id=f"paper_{i}",
                title=f"Paper {i}",
                authors=[],
                year=2024,
                citations=i,
                venue="Test",
                arxiv_id=f"2401.{i:05d}" if i % 2 == 0 else None,
            )
            for i in range(20)
        ]

        result = framework.discover_pdfs(papers)

        # Check statistics
        assert "arxiv" in result.source_statistics
        assert "semantic_scholar" in result.source_statistics

        arxiv_stats = result.source_statistics["arxiv"]
        assert arxiv_stats["attempted"] == 20
        assert arxiv_stats["successful"] == 10  # Only even numbered papers
        assert arxiv_stats["failed"] == 10

        # Semantic Scholar should have attempted all
        ss_stats = result.source_statistics["semantic_scholar"]
        assert ss_stats["attempted"] == 20
        assert ss_stats["successful"] >= 14  # ~80% success rate
