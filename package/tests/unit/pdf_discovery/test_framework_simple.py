"""Simplified test for venue priority functionality."""

import pytest
from datetime import datetime

from src.pdf_discovery.core.framework import PDFDiscoveryFramework
from src.pdf_discovery.core.models import PDFRecord
from src.pdf_discovery.core.collectors import BasePDFCollector
from src.data.models import Paper, Author


class SimpleCollector(BasePDFCollector):
    """Simple collector for testing venue priorities."""
    
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Simple mock discovery."""
        return PDFRecord(
            paper_id=paper.paper_id,
            pdf_url=f"https://{self.source_name}.com/{paper.paper_id}.pdf",
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=0.8,
            version_info={},
            validation_status="valid"
        )


def test_venue_priority_api_compatibility():
    """Test that venue priority API works without breaking the framework."""
    framework = PDFDiscoveryFramework()
    
    # Configure venue priorities (API should work)
    framework.set_venue_priorities({
        "ICLR": ["openreview", "arxiv"],
        "NeurIPS": ["arxiv", "openreview"],
        "default": ["semantic_scholar", "arxiv"]
    })
    
    # Verify priorities were set
    assert framework.venue_priorities["ICLR"] == ["openreview", "arxiv"]
    assert framework.venue_priorities["NeurIPS"] == ["arxiv", "openreview"]
    
    # Create collectors
    framework.add_collector(SimpleCollector("arxiv"))
    framework.add_collector(SimpleCollector("openreview"))
    
    # Test that framework works with venue priorities set
    paper = Paper(
        paper_id="test_paper",
        title="Test Paper for Venue Priorities",
        authors=[Author(name="Test Author", affiliation="Test Uni")],
        year=2024, citations=0, venue="ICLR",
        doi="10.1111/test.2024"
    )
    
    result = framework.discover_pdfs([paper])
    
    # Should successfully discover the paper
    assert result.discovered_count == 1
    assert len(result.records) == 1
    assert result.records[0].source in ["arxiv", "openreview"]
    
    # Verify deduplication stats are available
    stats = framework.get_deduplication_stats()
    assert "total_decisions" in stats