"""Simplified test for venue priority functionality."""

from datetime import datetime

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


class SimpleCollector(BasePDFCollector):
    """Simple collector for testing venue priorities."""

    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Simple mock discovery."""
        return PDFRecord(
            paper_id=paper.paper_id or f"test_{self.source_name}",
            pdf_url=f"https://{self.source_name}.com/{paper.paper_id or 'test'}.pdf",
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=0.8,
            version_info={},
            validation_status="valid",
        )


def test_venue_priority_api_compatibility():
    """Test that venue priority API works without breaking the framework."""
    framework = PDFDiscoveryFramework()

    # Configure venue priorities (API should work)
    framework.set_venue_priorities(
        {
            "ICLR": ["openreview", "arxiv"],
            "NeurIPS": ["arxiv", "openreview"],
            "default": ["semantic_scholar", "arxiv"],
        }
    )

    # Verify priorities were set
    assert framework.venue_priorities["ICLR"] == ["openreview", "arxiv"]
    assert framework.venue_priorities["NeurIPS"] == ["arxiv", "openreview"]

    # Create collectors
    framework.add_collector(SimpleCollector("arxiv"))
    framework.add_collector(SimpleCollector("openreview"))

    # Test that framework works with venue priorities set
    paper = create_test_paper(
        paper_id="test_paper",
        title="Test Paper for Venue Priorities",
        authors=[Author(name="Test Author", affiliations=["Test Uni"])],
        year=2024,
        citation_count=0,
        venue="ICLR",
    )

    result = framework.discover_pdfs([paper])

    # Should successfully discover the paper
    assert result.discovered_count == 1
    assert len(result.records) == 1
    assert result.records[0].source in ["arxiv", "openreview"]

    # Verify deduplication stats are available
    stats = framework.get_deduplication_stats()
    assert "total_decisions" in stats
