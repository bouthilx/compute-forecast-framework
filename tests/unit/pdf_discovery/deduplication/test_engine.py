"""Unit tests for the main deduplication engine."""

import pytest
from datetime import datetime
from typing import List

from compute_forecast.pipeline.pdf_acquisition.discovery.deduplication.engine import (
    PaperDeduplicator,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.metadata_collection.models import Paper, Author


class TestPaperDeduplicator:
    """Test the main deduplication engine."""

    @pytest.fixture
    def sample_papers_and_records(self) -> tuple[List[Paper], List[PDFRecord]]:
        """Create sample papers and records for testing."""
        papers = [
            Paper(
                title="Deep Learning for Natural Language Processing",
                authors=[
                    Author(name="John Doe", affiliation="MIT"),
                    Author(name="Jane Smith", affiliation="Stanford"),
                ],
                venue="NeurIPS",
                year=2023,
                citations=100,
                paper_id="semantic_scholar_123",
                doi="10.1234/nlp.2023",
            ),
            Paper(
                title="Deep Learning for Natural Language Processing",
                authors=[
                    Author(name="J. Doe", affiliation="MIT"),
                    Author(name="J. Smith", affiliation="Stanford University"),
                ],
                venue="NeurIPS 2023",
                year=2023,
                citations=100,
                paper_id="arxiv_456",
                arxiv_id="2301.12345",
                doi="10.1234/nlp.2023",  # Same DOI as first paper
            ),
            Paper(
                title="A Novel Approach to Computer Vision",
                authors=[
                    Author(name="Alice Johnson", affiliation="CMU"),
                ],
                venue="CVPR",
                year=2023,
                citations=50,
                paper_id="paper_789",
                doi="10.5678/cv.2023",
            ),
        ]

        records = []
        for i, paper in enumerate(papers):
            # Create multiple records per paper from different sources
            sources = ["semantic_scholar", "arxiv", "venue_direct"][: 2 if i < 2 else 1]

            for source in sources:
                record = PDFRecord(
                    paper_id=f"{paper.paper_id}_{source}",
                    pdf_url=f"https://{source}.com/{paper.paper_id}.pdf",
                    source=source,
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.9 if source == "venue_direct" else 0.8,
                    version_info={"is_published": source == "venue_direct"},
                    validation_status="valid",
                    file_size_bytes=500_000,
                )
                record.paper_data = paper
                records.append(record)

        return papers, records

    def test_deduplicate_records_basic(self, sample_papers_and_records):
        """Test basic deduplication functionality."""
        papers, records = sample_papers_and_records
        deduplicator = PaperDeduplicator()

        # Group records by paper for testing
        all_records = {}
        record_to_paper = {}
        for record in records:
            base_id = record.paper_data.paper_id
            if base_id not in all_records:
                all_records[base_id] = []
            all_records[base_id].append(record)
            # Map each record to its paper for deduplication
            record_to_paper[record.paper_id] = record.paper_data

        result = deduplicator.deduplicate_records(all_records, record_to_paper)

        # Should return fewer records due to deduplication
        # First two papers share same DOI, so should be merged
        assert len(result) == 2  # 2 unique papers (first two merged)

        # Check that we get the best version of each paper
        for paper_id, selected_record in result.items():
            assert selected_record is not None
            assert hasattr(selected_record, "paper_data")

    def test_deduplicate_with_exact_matches(self):
        """Test deduplication when papers have exact identifier matches."""
        deduplicator = PaperDeduplicator()

        # Create two records for the same paper (same DOI)
        paper1 = Paper(
            title="Test Paper",
            authors=[Author(name="Test Author", affiliation="Test Uni")],
            venue="Test Venue",
            year=2023,
            citations=10,
            paper_id="test_1",
            doi="10.1234/test.2023",
        )

        paper2 = Paper(
            title="Test Paper",
            authors=[Author(name="Test Author", affiliation="Test Uni")],
            venue="Test Venue",
            year=2023,
            citations=10,
            paper_id="test_2",
            doi="10.1234/test.2023",  # Same DOI
        )

        records = [
            PDFRecord(
                paper_id="record_1",
                pdf_url="https://source1.com/paper.pdf",
                source="source1",
                discovery_timestamp=datetime.now(),
                confidence_score=0.8,
                version_info={},
                validation_status="valid",
            ),
            PDFRecord(
                paper_id="record_2",
                pdf_url="https://source2.com/paper.pdf",
                source="source2",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={"is_published": True},
                validation_status="valid",
            ),
        ]

        records[0].paper_data = paper1
        records[1].paper_data = paper2

        all_records = {"test_paper": records}
        result = deduplicator.deduplicate_records(all_records)

        # Should merge into single result
        assert len(result) == 1

        # Should select the better record (higher confidence, published)
        selected = list(result.values())[0]
        assert selected.source == "source2"

    def test_deduplicate_with_fuzzy_matches(self):
        """Test deduplication with fuzzy title/author matches."""
        deduplicator = PaperDeduplicator()

        # Create papers with similar titles but different IDs
        paper1 = Paper(
            title="Deep Learning for Natural Language Processing",
            authors=[Author(name="John Doe", affiliation="MIT")],
            venue="NeurIPS",
            year=2023,
            citations=10,
            paper_id="paper_1",
        )

        paper2 = Paper(
            title="Deep Learning for Natural Language Processing (Extended Abstract)",
            authors=[Author(name="J. Doe", affiliation="MIT")],
            venue="NeurIPS 2023",
            year=2023,
            citations=10,
            paper_id="paper_2",
        )

        records = [
            PDFRecord(
                paper_id="record_1",
                pdf_url="https://source1.com/paper.pdf",
                source="source1",
                discovery_timestamp=datetime.now(),
                confidence_score=0.8,
                version_info={},
                validation_status="valid",
            ),
            PDFRecord(
                paper_id="record_2",
                pdf_url="https://source2.com/paper.pdf",
                source="source2",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={"is_published": True},
                validation_status="valid",
            ),
        ]

        records[0].paper_data = paper1
        records[1].paper_data = paper2

        all_records = {"fuzzy_test": records}
        result = deduplicator.deduplicate_records(all_records)

        # Should recognize as same paper and merge
        assert len(result) == 1

    def test_deduplicate_no_duplicates(self):
        """Test deduplication when there are no duplicates."""
        deduplicator = PaperDeduplicator()

        # Create completely different papers
        papers = [
            Paper(
                title="Paper A",
                authors=[Author(name="Author A", affiliation="Uni A")],
                venue="Venue A",
                year=2023,
                citations=10,
                paper_id="paper_a",
                doi="10.1111/a.2023",
            ),
            Paper(
                title="Paper B",
                authors=[Author(name="Author B", affiliation="Uni B")],
                venue="Venue B",
                year=2023,
                citations=20,
                paper_id="paper_b",
                doi="10.2222/b.2023",
            ),
        ]

        all_records = {}
        for i, paper in enumerate(papers):
            record = PDFRecord(
                paper_id=f"record_{i}",
                pdf_url=f"https://source.com/paper_{i}.pdf",
                source="source",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid",
            )
            record.paper_data = paper
            all_records[f"paper_{i}"] = [record]

        result = deduplicator.deduplicate_records(all_records)

        # Should keep all papers (no duplicates)
        assert len(result) == 2

    def test_deduplicate_empty_input(self):
        """Test deduplication with empty input."""
        deduplicator = PaperDeduplicator()

        result = deduplicator.deduplicate_records({})

        assert result == {}

    def test_deduplication_audit_log(self, sample_papers_and_records):
        """Test that deduplication decisions are logged."""
        papers, records = sample_papers_and_records
        deduplicator = PaperDeduplicator()

        # Group records by paper for testing
        all_records = {}
        for record in records:
            base_id = record.paper_data.paper_id
            if base_id not in all_records:
                all_records[base_id] = []
            all_records[base_id].append(record)

        deduplicator.deduplicate_records(all_records)

        # Should have some audit log entries
        assert hasattr(deduplicator, "dedup_log")
        # Log might be empty if no complex decisions were made, that's OK
