import pytest
from datetime import datetime
from unittest.mock import Mock
import json

from compute_forecast.pipeline.consolidation.enrichment.citation_enricher import CitationEnricher
from compute_forecast.pipeline.consolidation.enrichment.abstract_enricher import AbstractEnricher
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


def test_paper_from_dict_with_scraper_format():
    """Test Paper.from_dict handles scraper data format"""
    # Typical scraper output format
    scraper_data = {
        "title": "Test Paper",
        "authors": ["John Doe", "Jane Smith"],  # String authors, not dicts
        "venue": "NeurIPS",
        "year": 2023,
        "abstract": None,  # None instead of empty string
        "pdf_urls": ["https://example.com/paper.pdf"],  # pdf_urls instead of urls
        "keywords": [],
        "doi": None,
        "arxiv_id": None,
        "paper_id": None,
        # Scraper-specific fields
        "source_scraper": "pmlr",
        "source_url": "https://proceedings.mlr.press/v202/",
        "scraped_at": "2025-01-10T10:00:00",
        "extraction_confidence": 0.95,
        "metadata_completeness": 0.8
    }
    
    # Convert to Paper
    paper = Paper.from_dict(scraper_data)
    
    # Check conversions
    assert paper.title == "Test Paper"
    assert len(paper.authors) == 2
    assert paper.authors[0].name == "John Doe"
    assert paper.authors[0].affiliations == []  # Empty list for string authors
    assert paper.authors[1].name == "Jane Smith"
    
    assert paper.abstract == ""  # None converted to empty string
    assert paper.doi == ""  # None converted to empty string
    assert paper.urls == ["https://example.com/paper.pdf"]  # pdf_urls mapped to urls
    assert paper.citations == 0  # Default value added
    
    # Check scraper fields were removed
    assert not hasattr(paper, "source_scraper")
    assert not hasattr(paper, "scraped_at")
    assert not hasattr(paper, "extraction_confidence")


def test_paper_from_dict_with_old_author_format():
    """Test Paper.from_dict handles old author format with affiliation string"""
    old_format_data = {
        "title": "Test Paper",
        "authors": [
            {
                "name": "John Doe",
                "affiliation": "MIT",  # Old format: single string
                "author_id": "12345"  # Old field to be removed
            }
        ],
        "venue": "ICML",
        "year": 2023,
        "citations": 5
    }
    
    paper = Paper.from_dict(old_format_data)
    
    assert paper.authors[0].name == "John Doe"
    assert paper.authors[0].affiliations == ["MIT"]  # Converted to list
    assert not hasattr(paper.authors[0], "author_id")  # Removed


def test_paper_to_dict_datetime_serialization():
    """Test Paper.to_dict handles datetime serialization"""
    paper = Paper(
        title="Test Paper",
        authors=[Author(name="John Doe", affiliations=["MIT"])],
        venue="ICML",
        year=2023,
        citations=10,
        collection_timestamp=datetime(2025, 1, 10, 12, 0, 0)
    )
    
    # Convert to dict
    paper_dict = paper.to_dict()
    
    # Check datetime was serialized to ISO format string
    assert isinstance(paper_dict["collection_timestamp"], str)
    assert paper_dict["collection_timestamp"] == "2025-01-10T12:00:00"
    
    # Ensure it's JSON serializable
    json_str = json.dumps(paper_dict)
    assert json_str  # Should not raise


def test_paper_from_dict_datetime_deserialization():
    """Test Paper.from_dict handles datetime deserialization"""
    data = {
        "title": "Test Paper",
        "authors": [],
        "venue": "ICML",
        "year": 2023,
        "citations": 10,
        "collection_timestamp": "2025-01-10T12:00:00"  # ISO format string
    }
    
    paper = Paper.from_dict(data)
    
    # Check datetime was parsed correctly
    assert isinstance(paper.collection_timestamp, datetime)
    assert paper.collection_timestamp.year == 2025
    assert paper.collection_timestamp.month == 1
    assert paper.collection_timestamp.day == 10


def test_abstract_enricher_skips_papers_with_abstracts():
    """Test AbstractEnricher skips papers that already have abstracts"""
    papers = [
        Paper(
            title="Paper with abstract",
            authors=[],
            venue="ICML",
            year=2023,
            paper_id="paper1",
            citations=0,
            abstract="Existing abstract"  # Has abstract
        ),
        Paper(
            title="Paper without abstract",
            authors=[],
            venue="ICML",
            year=2023,
            paper_id="paper2",
            citations=0,
            abstract=""  # No abstract
        )
    ]
    
    mock_source = Mock()
    mock_source.name = "test_source"
    
    # Track which papers were passed to enrich_papers
    enriched_papers = []
    def capture_papers(papers):
        enriched_papers.extend(papers)
        return []
    
    mock_source.enrich_papers.side_effect = capture_papers
    
    enricher = AbstractEnricher([mock_source])
    enricher.enrich(papers)
    
    # Only paper2 should have been processed
    assert len(enriched_papers) == 1
    assert enriched_papers[0].paper_id == "paper2"


def test_enrichment_with_missing_paper_ids():
    """Test enrichment handles papers without IDs gracefully"""
    papers = [
        Paper(
            title="Paper without ID",
            authors=[],
            venue="ICML",
            year=2023,
            paper_id=None,  # No ID
            citations=0
        )
    ]
    
    mock_source = Mock()
    mock_source.name = "test_source"
    mock_source.enrich_papers.return_value = [
        Mock(
            paper_id=None,  # None as key
            citations=[Mock(
                source="test_source",
                timestamp=datetime.now(),
                data=Mock(count=10)
            )]
        )
    ]
    
    enricher = CitationEnricher([mock_source])
    results = enricher.enrich(papers)
    
    # Should handle None as key
    assert None in results
    assert len(results[None]) == 1
    assert results[None][0].data.count == 10