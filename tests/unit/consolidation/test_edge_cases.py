"""Edge case tests for consolidation based on real-world issues found"""

import pytest
from datetime import datetime
from compute_forecast.pipeline.metadata_collection.models import Paper, Author


def test_paper_with_all_none_fields():
    """Test Paper.from_dict handles all None fields"""
    data = {
        "title": "Test Paper",
        "authors": [],
        "venue": "ICML",
        "year": 2023,
        # All these fields might be None
        "doi": None,
        "arxiv_id": None,
        "paper_id": None,
        "keywords": None,
    }
    
    paper = Paper.from_dict(data)
    
    # None values should be converted to appropriate defaults
    assert paper.doi == ""
    assert paper.arxiv_id is None  # Optional field can stay None
    assert paper.paper_id is None  # Optional field can stay None
    assert paper.keywords == []  # None should become empty list
    assert paper.citations == []  # Default empty list
    assert paper.abstracts == []  # Default empty list
    assert paper.urls == []  # Default empty list


def test_paper_with_nested_none_in_authors():
    """Test handling of None values in author data"""
    data = {
        "title": "Test Paper",
        "authors": [
            {
                "name": "John Doe",
                "affiliations": None,  # None affiliations
                "email": None
            },
            {
                "name": "Jane Smith",
                "affiliations": None
            }
        ],
        "venue": "ICML",
        "year": 2023
    }
    
    paper = Paper.from_dict(data)
    
    assert len(paper.authors) == 2
    assert paper.authors[0].affiliations == []  # None -> empty list
    assert paper.authors[0].email == ""  # None -> empty string
    assert paper.authors[1].affiliations == []  # None -> empty list


def test_paper_serialization_with_complex_types():
    """Test Paper.to_dict handles all field types correctly"""
    from compute_forecast.pipeline.consolidation.models import CitationRecord, CitationData, AbstractRecord, AbstractData, URLRecord, URLData
    
    paper = Paper(
        title="Test Paper",
        authors=[
            Author(name="John Doe", affiliations=["MIT", "Stanford"]),
            Author(name="Jane Smith", affiliations=[])
        ],
        venue="NeurIPS",
        year=2023,
        citations=[CitationRecord(
            source="semantic_scholar",
            timestamp=datetime(2025, 1, 10, 16, 0, 0),
            original=False,
            data=CitationData(count=25)
        )],
        abstracts=[AbstractRecord(
            source="openalex",
            timestamp=datetime(2025, 1, 10, 16, 0, 0),
            original=False,
            data=AbstractData(text="Enhanced abstract", language="en")
        )],
        doi="10.1234/test",
        urls=[URLRecord(
            source="scraper",
            timestamp=datetime(2025, 1, 10, 15, 30, 45),
            original=True,
            data=URLData(url="https://example.com/paper.pdf")
        )],
        paper_id="test-123",
        keywords=["ml", "ai"],
        collection_timestamp=datetime(2025, 1, 10, 15, 30, 45)
    )
    
    # Convert to dict
    paper_dict = paper.to_dict()
    
    # Check all fields are properly serialized
    assert paper_dict["title"] == "Test Paper"
    assert len(paper_dict["authors"]) == 2
    assert paper_dict["authors"][0]["name"] == "John Doe"
    assert paper_dict["authors"][0]["affiliations"] == ["MIT", "Stanford"]
    assert paper_dict["collection_timestamp"] == "2025-01-10T15:30:45"
    
    # Citations are properly serialized
    assert "citations" in paper_dict
    assert len(paper_dict["citations"]) == 1
    assert paper_dict["citations"][0]["source"] == "semantic_scholar"
    assert paper_dict["citations"][0]["timestamp"] == "2025-01-10T16:00:00"
    assert paper_dict["citations"][0]["original"] == False
    assert paper_dict["citations"][0]["data"]["count"] == 25
    
    # Abstracts are properly serialized
    assert "abstracts" in paper_dict
    assert len(paper_dict["abstracts"]) == 1
    assert paper_dict["abstracts"][0]["source"] == "openalex"
    assert paper_dict["abstracts"][0]["data"]["text"] == "Enhanced abstract"
    
    # URLs are properly serialized
    assert "urls" in paper_dict
    assert len(paper_dict["urls"]) == 1
    assert paper_dict["urls"][0]["source"] == "scraper"
    assert paper_dict["urls"][0]["original"] == True
    assert paper_dict["urls"][0]["data"]["url"] == "https://example.com/paper.pdf"
    
    
def test_paper_round_trip_serialization():
    """Test Paper can be serialized and deserialized without data loss"""
    from compute_forecast.pipeline.consolidation.models import CitationRecord, CitationData, AbstractRecord, AbstractData, URLRecord, URLData
    
    original = Paper(
        title="Round Trip Test",
        authors=[Author(name="Test Author", affiliations=["Uni"])],
        venue="ICML",
        year=2024,
        citations=[CitationRecord(
            source="original",
            timestamp=datetime(2025, 1, 10, 12, 0, 0),
            original=True,
            data=CitationData(count=42)
        )],
        abstracts=[AbstractRecord(
            source="original",
            timestamp=datetime(2025, 1, 10, 12, 0, 0),
            original=True,
            data=AbstractData(text="Test abstract")
        )],
        doi="10.1234/roundtrip",
        urls=[URLRecord(
            source="original",
            timestamp=datetime(2025, 1, 10, 12, 0, 0),
            original=True,
            data=URLData(url="https://test.com/paper.pdf")
        )],
        paper_id="round-trip-123",
        keywords=["test", "serialization"],
        collection_timestamp=datetime(2025, 1, 10, 12, 0, 0)
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
    assert restored.doi == original.doi
    assert restored.paper_id == original.paper_id
    assert restored.keywords == original.keywords
    
    # Check provenance records
    assert len(restored.citations) == 1
    assert restored.citations[0].source == "original"
    assert restored.citations[0].original == True
    assert restored.citations[0].data.count == 42
    
    assert len(restored.abstracts) == 1
    assert restored.abstracts[0].data.text == "Test abstract"
    
    assert len(restored.urls) == 1
    assert restored.urls[0].data.url == "https://test.com/paper.pdf"
    
    
def test_paper_from_dict_with_string_authors():
    """Test Paper.from_dict handles string authors"""
    data = {
        "title": "Type Coercion Test",
        "authors": ["String Author"],  # String instead of dict - handled
        "venue": "ICML",
        "year": 2023
    }
    
    paper = Paper.from_dict(data)
    assert paper.authors[0].name == "String Author"
    assert paper.authors[0].affiliations == []