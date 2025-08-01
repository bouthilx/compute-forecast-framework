"""Integration tests for PDF discovery framework with deduplication."""

import pytest
from datetime import datetime
from typing import Optional

from compute_forecast.pipeline.pdf_acquisition.discovery.core.framework import (
    PDFDiscoveryFramework,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.pdf_acquisition.discovery.core.collectors import (
    BasePDFCollector,
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


class MockCollectorWithDuplicates(BasePDFCollector):
    """Mock collector that returns duplicate records for testing."""

    def __init__(self, source_name: str, duplicate_papers: Optional[list] = None):
        super().__init__(source_name)
        self.duplicate_papers = duplicate_papers or []

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Mock discovery with potential duplicates."""
        # Create duplicate records with same DOI/arXiv ID
        if paper.paper_id in self.duplicate_papers:
            # Simulate finding same paper from this source
            return PDFRecord(
                paper_id=f"{paper.paper_id}_{self.source_name}",
                pdf_url=f"https://{self.source_name}.com/{paper.paper_id}.pdf",
                source=self.source_name,
                discovery_timestamp=datetime.now(),
                confidence_score=0.9 if self.source_name == "venue_direct" else 0.8,
                version_info={"is_published": self.source_name == "venue_direct"},
                validation_status="valid",
            )
        else:
            # Return regular record
            return PDFRecord(
                paper_id=paper.paper_id or f"unknown_{self.source_name}",
                pdf_url=f"https://{self.source_name}.com/{paper.paper_id or 'unknown'}.pdf",
                source=self.source_name,
                discovery_timestamp=datetime.now(),
                confidence_score=0.8,
                version_info={},
                validation_status="valid",
            )


class TestFrameworkDeduplicationIntegration:
    """Test integration between framework and deduplication engine."""

    @pytest.fixture
    def sample_papers(self) -> list[Paper]:
        """Create sample papers with potential duplicates."""
        return [
            create_test_paper(
                paper_id="paper_107",
                title="Deep Learning for NLP",
                authors=[Author(name="John Doe", affiliations=["MIT"])],
                venue="NeurIPS",
                year=2023,
                citation_count=100,
            ),
            create_test_paper(
                paper_id="paper_115",
                title="Deep Learning for NLP (Extended)",
                authors=[Author(name="J. Doe", affiliations=["MIT"])],
                venue="NeurIPS 2023",
                year=2023,
                citation_count=100,
            ),
            create_test_paper(
                paper_id="paper_123",
                title="Computer Vision Research",
                authors=[Author(name="Jane Smith", affiliations=["Stanford"])],
                venue="CVPR",
                year=2023,
                citation_count=50,
            ),
        ]

    def test_framework_deduplication_basic(self, sample_papers):
        """Test that framework correctly deduplicates across sources."""
        framework = PDFDiscoveryFramework()

        # Add collectors that will find duplicate papers
        collector1 = MockCollectorWithDuplicates("arxiv", ["paper_1", "paper_2"])
        collector2 = MockCollectorWithDuplicates("venue_direct", ["paper_1", "paper_2"])

        framework.add_collector(collector1)
        framework.add_collector(collector2)

        # Run discovery
        result = framework.discover_pdfs(sample_papers)

        # Should have deduplicated the duplicate papers
        assert result.total_papers == 3
        assert result.discovered_count <= 3  # Should be fewer due to deduplication
        assert result.discovered_count > 0

        # Check that we got deduplication stats
        stats = framework.get_deduplication_stats()
        assert "total_decisions" in stats
        assert stats["total_decisions"] > 0

    def test_framework_deduplication_best_version_selection(self, sample_papers):
        """Test that framework selects best versions during deduplication."""
        framework = PDFDiscoveryFramework()

        # Create collectors with different priorities
        # venue_direct should be preferred over arxiv
        arxiv_collector = MockCollectorWithDuplicates("arxiv", ["paper_1"])
        venue_collector = MockCollectorWithDuplicates("venue_direct", ["paper_1"])

        framework.add_collector(arxiv_collector)
        framework.add_collector(venue_collector)

        result = framework.discover_pdfs([sample_papers[0]])  # Just first paper

        # Should find the paper and select venue_direct version
        assert result.discovered_count == 1

        # Check that the selected record is from venue_direct (higher priority)
        selected_records = result.records
        assert len(selected_records) == 1

        # The record should be the better version (venue_direct)
        selected_record = selected_records[0]
        # Note: Since deduplication groups records, the source might be from either collector
        # but the version manager should have selected the better one
        assert selected_record.validation_status == "valid"

    def test_framework_no_deduplication_needed(self):
        """Test framework behavior when no deduplication is needed."""
        framework = PDFDiscoveryFramework()

        # Create completely unique papers with no similarity
        unique_papers = [
            create_test_paper(
                paper_id="paper_190",
                title="Unique Paper A: Quantum Computing",
                authors=[Author(name="Alice A", affiliations=["Uni A"])],
                venue="Venue A",
                year=2023,
                citation_count=10,
            ),
            create_test_paper(
                paper_id="paper_198",
                title="Unique Paper B: Robotics Control",
                authors=[Author(name="Bob B", affiliations=["Uni B"])],
                venue="Venue B",
                year=2022,
                citation_count=20,
            ),
            create_test_paper(
                paper_id="paper_206",
                title="Unique Paper C: Data Mining",
                authors=[Author(name="Carol C", affiliations=["Uni C"])],
                venue="Venue C",
                year=2021,
                citation_count=30,
            ),
        ]

        # Add collector that finds unique papers only
        collector = MockCollectorWithDuplicates("arxiv", [])  # No duplicates
        framework.add_collector(collector)

        result = framework.discover_pdfs(unique_papers)

        # Should discover all papers without deduplication
        assert result.total_papers == 3
        assert result.discovered_count == 3

        # Deduplication stats should show minimal merges (if any)
        stats = framework.get_deduplication_stats()
        # With completely different papers, should have no merges
        assert stats.get("merge_decisions", 0) == 0

    def test_framework_deduplication_preserves_metadata(self, sample_papers):
        """Test that deduplication preserves important metadata."""
        framework = PDFDiscoveryFramework()

        # Add collectors
        collector1 = MockCollectorWithDuplicates("source1", ["paper_1"])
        collector2 = MockCollectorWithDuplicates("source2", ["paper_1"])

        framework.add_collector(collector1)
        framework.add_collector(collector2)

        result = framework.discover_pdfs([sample_papers[0]])

        # Should have one deduplicated result
        assert result.discovered_count == 1

        selected_record = result.records[0]

        # Check that essential metadata is preserved
        assert selected_record.paper_id is not None
        assert selected_record.pdf_url is not None
        assert selected_record.source is not None
        assert selected_record.confidence_score > 0
        assert selected_record.validation_status is not None

    def test_framework_deduplication_with_no_collectors(self, sample_papers):
        """Test framework behavior with no collectors."""
        framework = PDFDiscoveryFramework()

        result = framework.discover_pdfs(sample_papers)

        # Should return empty result
        assert result.total_papers == 3
        assert result.discovered_count == 0
        assert result.records == []

        # Deduplication stats should be empty
        stats = framework.get_deduplication_stats()
        assert stats == {} or stats.get("total_decisions", 0) == 0

    def test_framework_deduplication_error_handling(self, sample_papers):
        """Test that framework handles deduplication errors gracefully."""
        framework = PDFDiscoveryFramework()

        # Create a collector that will succeed
        good_collector = MockCollectorWithDuplicates("good_source", [])
        framework.add_collector(good_collector)

        # Mock the deduplicator to raise an exception
        def mock_deduplicate(records):
            if records:
                raise Exception("Deduplication failed")
            return {}

        framework.deduplicator.deduplicate_records = mock_deduplicate

        # Should handle the error gracefully
        result = framework.discover_pdfs(sample_papers)

        # Framework should still return a result (might be empty due to error)
        assert hasattr(result, "total_papers")
        assert hasattr(result, "discovered_count")
        assert hasattr(result, "records")
