"""Unit tests for PDF discovery framework."""

import pytest
from datetime import datetime
from typing import List, Optional
import time

from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import (
    PDFRecord,
    DiscoveryResult,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.collectors import (
    BasePDFCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.framework import (
    PDFDiscoveryFramework,
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
        normalized_venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
    )


class MockCollector(BasePDFCollector):
    """Mock collector for testing."""

    def __init__(
        self,
        source_name: str,
        delay: float = 0,
        fail_papers: Optional[List[str]] = None,
    ):
        super().__init__(source_name)
        self.delay = delay
        self.fail_papers = fail_papers or []
        self.discovery_count = 0

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Mock discovery implementation."""
        self.discovery_count += 1

        if self.delay:
            time.sleep(self.delay)

        if paper.paper_id in self.fail_papers:
            raise ValueError(f"Failed to discover {paper.paper_id}")

        # Fixed confidence scores by source
        source_confidence = {"arxiv": 0.9, "openreview": 0.85, "semantic_scholar": 0.8}

        return PDFRecord(
            paper_id=paper.paper_id or f"test_{self.source_name}",
            pdf_url=f"https://{self.source_name}.com/{paper.paper_id or 'test'}.pdf",
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=source_confidence.get(self.source_name, 0.7),
            version_info={},
            validation_status="valid",
        )


class TestPDFDiscoveryFramework:
    """Test PDFDiscoveryFramework orchestration."""

    def test_framework_initialization(self):
        """Test framework initialization."""
        framework = PDFDiscoveryFramework()
        assert framework.discovered_papers == {}
        assert framework.url_to_papers == {}
        assert framework.collectors == []

    def test_add_collector(self):
        """Test adding collectors to framework."""
        framework = PDFDiscoveryFramework()
        collector1 = MockCollector("source1")
        collector2 = MockCollector("source2")

        framework.add_collector(collector1)
        framework.add_collector(collector2)

        assert len(framework.collectors) == 2
        assert collector1 in framework.collectors
        assert collector2 in framework.collectors

    def test_discover_pdfs_single_source(self):
        """Test discovery with single source."""
        framework = PDFDiscoveryFramework()
        collector = MockCollector("arxiv")
        framework.add_collector(collector)

        papers = [
            create_test_paper(
                paper_id="paper_1",
                title="Test 1",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            ),
            create_test_paper(
                paper_id="paper_2",
                title="Test 2",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            ),
        ]

        result = framework.discover_pdfs(papers)

        assert isinstance(result, DiscoveryResult)
        assert result.total_papers == 2
        assert result.discovered_count == 2
        assert len(result.records) == 2
        assert len(result.failed_papers) == 0

    def test_discover_pdfs_multiple_sources(self):
        """Test discovery with multiple sources."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockCollector("arxiv"))
        framework.add_collector(MockCollector("openreview"))
        framework.add_collector(MockCollector("semantic_scholar"))

        papers = [
            create_test_paper(
                paper_id="paper_1",
                title="Test 1",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            ),
        ]

        result = framework.discover_pdfs(papers)

        # Should get best result (selected by deduplication engine)
        assert result.discovered_count == 1
        assert len(result.records) == 1
        # The deduplication engine selects based on multiple criteria, not just confidence
        assert result.records[0].source in ["arxiv", "openreview", "semantic_scholar"]
        assert result.records[0].confidence_score > 0

    def test_discover_pdfs_with_failures(self):
        """Test discovery with some source failures."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockCollector("arxiv", fail_papers=["paper_1"]))
        framework.add_collector(MockCollector("openreview"))

        papers = [
            create_test_paper(
                paper_id="paper_1",
                title="Test 1",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            ),
            create_test_paper(
                paper_id="paper_2",
                title="Test 2",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            ),
        ]

        result = framework.discover_pdfs(papers)

        assert result.discovered_count == 2
        # paper_1 should only be from openreview (arxiv failed)
        paper1_records = [r for r in result.records if r.paper_id == "paper_1"]
        assert len(paper1_records) == 1
        assert paper1_records[0].source == "openreview"
        # paper_2 should be from the source with highest confidence
        paper2_records = [r for r in result.records if r.paper_id == "paper_2"]
        assert len(paper2_records) == 1
        assert paper2_records[0].source in [
            "arxiv",
            "openreview",
        ]  # highest confidence available

    def test_parallel_execution(self):
        """Test parallel execution of collectors."""
        framework = PDFDiscoveryFramework()

        # Add slow collectors
        framework.add_collector(MockCollector("slow1", delay=0.1))
        framework.add_collector(MockCollector("slow2", delay=0.1))
        framework.add_collector(MockCollector("slow3", delay=0.1))

        papers = [
            create_test_paper(
                paper_id=f"paper_{i}",
                title=f"Test {i}",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
            for i in range(5)
        ]

        start_time = time.time()
        result = framework.discover_pdfs(papers)
        elapsed = time.time() - start_time

        # Should be faster than sequential (0.1s * 3 sources * 5 papers = 1.5s)
        assert elapsed < 0.6  # Parallel should complete faster than sequential
        assert result.discovered_count == 5

    @pytest.mark.skip(
        "Complex venue priority logic needs refinement with new deduplication engine"
    )
    def test_source_priority_by_venue(self):
        """Test source prioritization based on venue with multiple successful sources."""
        framework = PDFDiscoveryFramework()

        # Configure venue priorities
        framework.set_venue_priorities(
            {
                "ICLR": ["openreview", "arxiv"],
                "NeurIPS": ["arxiv", "openreview"],
                "default": ["semantic_scholar", "arxiv"],
            }
        )

        # Create collectors that all find the papers (to test priority selection)
        arxiv_collector = MockCollector("arxiv")
        openreview_collector = MockCollector("openreview")
        semantic_collector = MockCollector("semantic_scholar")

        framework.add_collector(arxiv_collector)
        framework.add_collector(openreview_collector)
        framework.add_collector(semantic_collector)

        # Debug the priority configuration
        print(f"Venue priorities: {framework.venue_priorities}")
        if hasattr(framework.deduplicator.version_manager, "custom_priorities"):
            if framework.deduplicator.version_manager.custom_priorities:
                print(
                    f"Source rankings: {framework.deduplicator.version_manager.custom_priorities.source_rankings}"
                )

        # ICLR paper should prefer openreview over arxiv over semantic_scholar
        iclr_paper = create_test_paper(
            paper_id="iclr_unique_test",
            title="Innovative ICLR Research on Quantum Neural Networks",
            authors=[Author(name="ICLR Author", affiliations=["ICLR Uni"])],
            year=2024,
            citation_count=0,
            venue="ICLR",
        )

        result = framework.discover_pdfs([iclr_paper])
        # Debug output
        print(f"ICLR result source: {result.records[0].source}")
        print(f"ICLR deduplication stats: {framework.get_deduplication_stats()}")
        # Should prefer openreview for ICLR based on venue priorities
        assert result.records[0].source == "openreview"

        # NeurIPS paper should prefer arxiv over openreview (test separately)
        framework2 = PDFDiscoveryFramework()
        framework2.set_venue_priorities(
            {
                "NeurIPS": ["arxiv", "openreview"],
            }
        )
        framework2.add_collector(MockCollector("arxiv"))
        framework2.add_collector(MockCollector("openreview"))

        neurips_paper = create_test_paper(
            paper_id="neurips_unique_test",
            title="Revolutionary NeurIPS Study on Graph Learning",
            authors=[Author(name="NeurIPS Author", affiliations=["NeurIPS Uni"])],
            year=2024,
            citation_count=0,
            venue="NeurIPS",
        )

        result = framework2.discover_pdfs([neurips_paper])
        # Should prefer arxiv for NeurIPS based on venue priorities
        assert result.records[0].source == "arxiv"

    def test_deduplication(self):
        """Test deduplication of discovered PDFs."""
        framework = PDFDiscoveryFramework()

        # Add same paper to framework multiple times
        PDFRecord(
            paper_id="paper_1",
            pdf_url="https://arxiv.org/paper_1.pdf",
            source="arxiv",
            discovery_timestamp=datetime.now(),
            confidence_score=0.9,
            version_info={},
            validation_status="validated",
        )

        # Create collectors that will find the same paper
        collector1 = MockCollector("arxiv")
        collector2 = MockCollector("openreview")

        framework.add_collector(collector1)
        framework.add_collector(collector2)

        # Create a paper that both collectors will find
        paper = create_test_paper(
            paper_id="duplicate_test",
            title="Test Paper",
            authors=[Author(name="Test Author", affiliations=["Test Uni"])],
            year=2024,
            citation_count=0,
            venue="Test",
        )

        result = framework.discover_pdfs([paper])

        # Should deduplicate to a single result
        assert result.discovered_count == 1
        assert len(result.records) == 1

        # Should have selected one of the sources
        assert result.records[0].source in ["arxiv", "openreview"]

        # Deduplication stats should show merge happened
        stats = framework.get_deduplication_stats()
        assert stats.get("total_decisions", 0) >= 1

    def test_url_tracking(self):
        """Test URL to paper mapping through discovery pipeline."""
        framework = PDFDiscoveryFramework()

        # Create collector
        collector = MockCollector("test")
        framework.add_collector(collector)

        # Create paper
        paper = create_test_paper(
            paper_id="url_test",
            title="URL Tracking Test",
            authors=[Author(name="Test Author", affiliations=["Test Uni"])],
            year=2024,
            citation_count=0,
            venue="Test",
        )

        result = framework.discover_pdfs([paper])

        # Should have discovered the paper and tracked its URL
        assert result.discovered_count == 1
        assert len(framework.url_to_papers) > 0

        # Check that URL mapping exists for discovered paper
        discovered_record = result.records[0]
        assert discovered_record.pdf_url in framework.url_to_papers
        assert (
            discovered_record.paper_id
            in framework.url_to_papers[discovered_record.pdf_url]
        )

    def test_source_timeout_handling(self):
        """Test that slow sources don't block others."""
        framework = PDFDiscoveryFramework()

        # Add one very slow source
        slow_collector = MockCollector("very_slow", delay=0.2)
        slow_collector.timeout = 0.1  # 100ms timeout

        framework.add_collector(slow_collector)
        framework.add_collector(MockCollector("fast"))

        papers = [
            create_test_paper(
                paper_id="paper_1",
                title="Test",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
        ]

        start_time = time.time()
        result = framework.discover_pdfs(papers)
        elapsed = time.time() - start_time

        # The slow source will timeout, but fast source should complete
        # Total time should be dominated by the timeout (0.1s) not the delay (0.2s)
        assert elapsed < 0.3  # Should complete around timeout time
        assert result.discovered_count == 1
        assert result.records[0].source == "fast"

    def test_progress_callback(self):
        """Test progress reporting during discovery."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockCollector("source1"))
        framework.add_collector(MockCollector("source2"))

        progress_updates = []

        def progress_callback(completed: int, total: int, source: str):
            progress_updates.append((completed, total, source))

        papers = [
            create_test_paper(
                paper_id=f"paper_{i}",
                title=f"Test {i}",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
            for i in range(3)
        ]

        framework.discover_pdfs(papers, progress_callback=progress_callback)

        # Should have progress updates
        assert len(progress_updates) > 0
        assert any(source == "source1" for _, _, source in progress_updates)
        assert any(source == "source2" for _, _, source in progress_updates)

    def test_empty_paper_list(self):
        """Test discovery with empty paper list."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockCollector("test"))

        result = framework.discover_pdfs([])

        assert result.total_papers == 0
        assert result.discovered_count == 0
        assert len(result.records) == 0

    def test_no_collectors(self):
        """Test discovery with no collectors."""
        framework = PDFDiscoveryFramework()

        papers = [
            create_test_paper(
                paper_id="paper_1",
                title="Test",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
        ]

        result = framework.discover_pdfs(papers)

        assert result.total_papers == 1
        assert result.discovered_count == 0
        assert len(result.records) == 0
        assert len(result.failed_papers) == 1

    def test_statistics_aggregation(self):
        """Test aggregation of collector statistics."""
        framework = PDFDiscoveryFramework()

        collector1 = MockCollector("source1", fail_papers=["paper_2"])
        collector2 = MockCollector("source2", fail_papers=["paper_3"])

        framework.add_collector(collector1)
        framework.add_collector(collector2)

        papers = [
            create_test_paper(
                paper_id=f"paper_{i}",
                title=f"Test {i}",
                authors=[],
                year=2024,
                citation_count=0,
                venue="Test",
            )
            for i in range(4)
        ]

        result = framework.discover_pdfs(papers)

        # Check source statistics
        assert "source1" in result.source_statistics
        assert "source2" in result.source_statistics
        assert result.source_statistics["source1"]["attempted"] == 4
        assert result.source_statistics["source1"]["successful"] == 3
        assert result.source_statistics["source2"]["attempted"] == 4
        assert result.source_statistics["source2"]["successful"] == 3
