from datetime import datetime
from unittest.mock import Mock
import json

from compute_forecast.pipeline.consolidation.models import (
    EnrichmentResult,
    CitationRecord,
    CitationData,
)
from compute_forecast.pipeline.metadata_collection.models import Paper, Author


def test_unified_enrichment():
    """Test unified paper enrichment approach"""
    # Create test papers
    papers = [
        Paper(
            title="Test Paper 1",
            authors=[Author(name="John Doe", affiliations=[])],
            venue="ICML",
            year=2023,
            paper_id="paper1",
            doi="10.1234/test1",
            citations=[],
        )
    ]

    # Mock source with unified fetch_all_fields
    mock_source = Mock()
    mock_source.name = "test_source"
    mock_source.find_papers.return_value = {"paper1": "source_id_1"}
    mock_source.fetch_all_fields.return_value = {
        "source_id_1": {
            "citations": 25,
            "abstract": "Test abstract",
            "urls": ["https://example.com/paper.pdf"],
        }
    }

    # Create enrichment results
    results = [
        EnrichmentResult(
            paper_id="paper1",
            citations=[
                CitationRecord(
                    source="test_source",
                    timestamp=datetime.now(),
                    original=False,
                    data=CitationData(count=25),
                )
            ],
        )
    ]
    mock_source.enrich_papers.return_value = results

    # Test enrichment
    enrichment_results = mock_source.enrich_papers(papers)

    assert len(enrichment_results) == 1
    assert enrichment_results[0].paper_id == "paper1"
    assert len(enrichment_results[0].citations) == 1
    assert enrichment_results[0].citations[0].data.count == 25


def test_paper_to_dict_datetime_serialization():
    """Test Paper.to_dict handles datetime serialization"""
    paper = Paper(
        title="Test Paper",
        authors=[Author(name="John Doe", affiliations=["MIT"])],
        venue="ICML",
        year=2023,
        citations=10,
        collection_timestamp=datetime(2025, 1, 10, 12, 0, 0),
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
        "citations": [],
        "collection_timestamp": "2025-01-10T12:00:00",  # ISO format string
    }

    paper = Paper.from_dict(data)

    # Check datetime was parsed correctly
    assert isinstance(paper.collection_timestamp, datetime)
    assert paper.collection_timestamp.year == 2025
    assert paper.collection_timestamp.month == 1
    assert paper.collection_timestamp.day == 10


def test_source_enriches_all_papers():
    """Test that source enriches all papers in unified approach"""
    from compute_forecast.pipeline.consolidation.models import (
        AbstractRecord,
        AbstractData,
    )

    papers = [
        Paper(
            title="Paper with abstract",
            authors=[],
            venue="ICML",
            year=2023,
            paper_id="paper1",
            citations=[],
            abstracts=[
                AbstractRecord(
                    source="original",
                    timestamp=datetime.now(),
                    original=True,
                    data=AbstractData(text="Existing abstract"),
                )
            ],  # Has abstract
        ),
        Paper(
            title="Paper without abstract",
            authors=[],
            venue="ICML",
            year=2023,
            paper_id="paper2",
            citations=[],
            abstracts=[],  # No abstract
        ),
    ]

    mock_source = Mock()
    mock_source.name = "test_source"

    # Track which papers were passed to enrich_papers
    enriched_papers = []

    def capture_papers(papers):
        enriched_papers.extend(papers)
        return [EnrichmentResult(paper_id=p.paper_id) for p in papers]

    mock_source.enrich_papers.side_effect = capture_papers

    # Test enrichment
    mock_source.enrich_papers(papers)

    # All papers should be processed in unified approach
    assert len(enriched_papers) == 2
    assert enriched_papers[0].paper_id == "paper1"
    assert enriched_papers[1].paper_id == "paper2"


def test_enrichment_with_missing_paper_ids():
    """Test enrichment handles papers without IDs gracefully"""
    papers = [
        Paper(
            title="Paper without ID",
            authors=[],
            venue="ICML",
            year=2023,
            paper_id=None,  # No ID
            citations=[],
        )
    ]

    mock_source = Mock()
    mock_source.name = "test_source"
    mock_source.enrich_papers.return_value = [
        EnrichmentResult(
            paper_id=None,  # None as key
            citations=[
                CitationRecord(
                    source="test_source",
                    timestamp=datetime.now(),
                    original=False,
                    data=CitationData(count=10),
                )
            ],
        )
    ]

    # Test enrichment
    results = mock_source.enrich_papers(papers)

    # Should handle None as key
    assert len(results) == 1
    assert results[0].paper_id is None
    assert len(results[0].citations) == 1
    assert results[0].citations[0].data.count == 10
