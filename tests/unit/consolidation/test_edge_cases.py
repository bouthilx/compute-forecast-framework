"""Edge case tests for consolidation based on real-world issues found"""

import pytest
from datetime import datetime
from compute_forecast.pipeline.metadata_collection.models import Paper, Author


def test_paper_with_all_none_fields():
    """Test Paper.from_dict handles all None fields from scrapers"""
    data = {
        "title": "Test Paper",
        "authors": [],
        "venue": "ICML",
        "year": 2023,
        # All these fields might be None from scrapers
        "abstract": None,
        "doi": None,
        "arxiv_id": None,
        "paper_id": None,
        "keywords": None,
        "urls": None,
        # Missing required field
        # "citations" is missing
    }
    
    paper = Paper.from_dict(data)
    
    # None values should be converted to appropriate defaults
    assert paper.abstract == ""
    assert paper.doi == ""
    assert paper.arxiv_id is None  # Optional field can stay None
    assert paper.paper_id is None  # Optional field can stay None
    assert paper.keywords == []  # None should become empty list
    assert paper.urls == []  # None should become empty list
    assert paper.citations == 0  # Missing field gets default


def test_paper_with_nested_none_in_authors():
    """Test handling of None values in author data"""
    data = {
        "title": "Test Paper",
        "authors": [
            {
                "name": "John Doe",
                "affiliation": None,  # Old format with None
                "email": None
            },
            {
                "name": "Jane Smith",
                "affiliations": None  # New format with None
            }
        ],
        "venue": "ICML",
        "year": 2023,
        "citations": 5
    }
    
    paper = Paper.from_dict(data)
    
    assert len(paper.authors) == 2
    assert paper.authors[0].affiliations == []  # None -> empty list
    assert paper.authors[0].email == ""  # Default value when not provided
    assert paper.authors[1].affiliations == []  # None -> empty list


def test_paper_serialization_with_complex_types():
    """Test Paper.to_dict handles all field types correctly"""
    from compute_forecast.pipeline.consolidation.models import CitationRecord, CitationData, AbstractRecord, AbstractData
    
    paper = Paper(
        title="Test Paper",
        authors=[
            Author(name="John Doe", affiliations=["MIT", "Stanford"]),
            Author(name="Jane Smith", affiliations=[])
        ],
        venue="NeurIPS",
        year=2023,
        citations=10,
        abstract="Test abstract",
        doi="10.1234/test",
        urls=["https://example.com/paper.pdf"],
        paper_id="test-123",
        keywords=["ml", "ai"],
        collection_timestamp=datetime(2025, 1, 10, 15, 30, 45)
    )
    
    # Add enrichment history
    paper.citations_history = [
        CitationRecord(
            source="semantic_scholar",
            timestamp=datetime(2025, 1, 10, 16, 0, 0),
            data=CitationData(count=25)
        )
    ]
    paper.abstracts_history = [
        AbstractRecord(
            source="openalex",
            timestamp=datetime(2025, 1, 10, 16, 0, 0),
            data=AbstractData(text="Enhanced abstract", language="en")
        )
    ]
    
    # Convert to dict
    paper_dict = paper.to_dict()
    
    # Check all fields are properly serialized
    assert paper_dict["title"] == "Test Paper"
    assert len(paper_dict["authors"]) == 2
    assert paper_dict["authors"][0]["name"] == "John Doe"
    assert paper_dict["authors"][0]["affiliations"] == ["MIT", "Stanford"]
    assert paper_dict["collection_timestamp"] == "2025-01-10T15:30:45"
    
    # Enrichment history IS included but converted to dict
    assert "citations_history" in paper_dict
    assert len(paper_dict["citations_history"]) == 1
    # It's converted to dict via __dict__
    assert isinstance(paper_dict["citations_history"][0], dict)
    assert paper_dict["citations_history"][0]["source"] == "semantic_scholar"
    # But the nested objects are not fully serialized
    assert isinstance(paper_dict["citations_history"][0]["timestamp"], datetime)
    
    
def test_paper_round_trip_serialization():
    """Test Paper can be serialized and deserialized without data loss"""
    original = Paper(
        title="Round Trip Test",
        authors=[Author(name="Test Author", affiliations=["Uni"])],
        venue="ICML",
        year=2024,
        citations=42,
        abstract="Test abstract",
        doi="10.1234/roundtrip",
        urls=["https://test.com/paper.pdf"],
        paper_id="round-trip-123",
        keywords=["test", "serialization"],
        collection_timestamp=datetime.now()
    )
    
    # Serialize
    paper_dict = original.to_dict()
    
    # Deserialize
    restored = Paper.from_dict(paper_dict)
    
    # Check key fields match
    assert restored.title == original.title
    assert len(restored.authors) == len(original.authors)
    assert restored.authors[0].name == original.authors[0].name
    assert restored.authors[0].affiliations == original.authors[0].affiliations
    assert restored.venue == original.venue
    assert restored.year == original.year
    assert restored.citations == original.citations
    assert restored.abstract == original.abstract
    assert restored.doi == original.doi
    assert restored.urls == original.urls
    assert restored.paper_id == original.paper_id
    assert restored.keywords == original.keywords
    
    
def test_paper_from_dict_field_type_coercion():
    """Test Paper.from_dict handles incorrect field types gracefully"""
    data = {
        "title": "Type Coercion Test",
        "authors": ["String Author"],  # String instead of dict - handled
        "venue": "ICML",
        "year": 2023,
        "citations": 10,
        "abstract": "",
        "urls": []
    }
    
    paper = Paper.from_dict(data)
    assert paper.authors[0].name == "String Author"
    assert paper.authors[0].affiliations == []