from datetime import datetime
from unittest.mock import Mock

from compute_forecast.pipeline.consolidation.enrichment.citation_enricher import CitationEnricher
from compute_forecast.pipeline.metadata_collection.models import Paper, Author


def test_citation_enricher():
    """Test citation enrichment"""
    # Create test papers
    papers = [
        Paper(
            title="Test Paper 1",
            authors=[Author(name="John Doe")],
            venue="ICML",
            year=2023,
            paper_id="paper1",
            doi="10.1234/test1",
            citations=10
        )
    ]
    
    # Mock source
    mock_source = Mock()
    mock_source.name = "test_source"
    mock_source.enrich_papers.return_value = [
        Mock(
            paper_id="paper1",
            citations=[Mock(
                source="test_source",
                timestamp=datetime.now(),
                data=Mock(count=25)
            )]
        )
    ]
    
    # Test enrichment
    enricher = CitationEnricher([mock_source])
    results = enricher.enrich(papers)
    
    assert "paper1" in results
    assert len(results["paper1"]) == 1
    assert results["paper1"][0].data.count == 25