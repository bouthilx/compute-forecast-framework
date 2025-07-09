"""Unit tests for PDF discovery models."""

from datetime import datetime
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import (
    PDFRecord,
    DiscoveryResult,
)


class TestPDFRecord:
    """Test PDFRecord data model."""

    def test_pdf_record_creation(self):
        """Test creating a PDFRecord with all fields."""
        record = PDFRecord(
            paper_id="paper_123",
            pdf_url="https://example.com/paper.pdf",
            source="arxiv",
            discovery_timestamp=datetime(2025, 1, 2, 10, 30),
            confidence_score=0.95,
            version_info={"version": "v2", "date": "2024-12-01"},
            validation_status="validated",
            file_size_bytes=1048576,
            license="CC-BY-4.0",
        )

        assert record.paper_id == "paper_123"
        assert record.pdf_url == "https://example.com/paper.pdf"
        assert record.source == "arxiv"
        assert record.confidence_score == 0.95
        assert record.validation_status == "validated"
        assert record.file_size_bytes == 1048576
        assert record.license == "CC-BY-4.0"
        assert record.version_info["version"] == "v2"

    def test_pdf_record_optional_fields(self):
        """Test PDFRecord with optional fields as None."""
        record = PDFRecord(
            paper_id="paper_456",
            pdf_url="https://example.com/paper2.pdf",
            source="semantic_scholar",
            discovery_timestamp=datetime.now(),
            confidence_score=0.8,
            version_info={},
            validation_status="pending",
            file_size_bytes=None,
            license=None,
        )

        assert record.file_size_bytes is None
        assert record.license is None

    def test_pdf_record_equality(self):
        """Test PDFRecord equality based on paper_id and pdf_url."""
        timestamp = datetime.now()
        record1 = PDFRecord(
            paper_id="paper_789",
            pdf_url="https://example.com/paper3.pdf",
            source="openreview",
            discovery_timestamp=timestamp,
            confidence_score=0.9,
            version_info={},
            validation_status="validated",
        )

        record2 = PDFRecord(
            paper_id="paper_789",
            pdf_url="https://example.com/paper3.pdf",
            source="different_source",
            discovery_timestamp=timestamp,
            confidence_score=0.8,
            version_info={},
            validation_status="pending",
        )

        assert record1 == record2

    def test_pdf_record_hash(self):
        """Test PDFRecord hashing for use in sets/dicts."""
        record1 = PDFRecord(
            paper_id="paper_999",
            pdf_url="https://example.com/paper4.pdf",
            source="pmlr",
            discovery_timestamp=datetime.now(),
            confidence_score=0.85,
            version_info={},
            validation_status="validated",
        )

        record2 = PDFRecord(
            paper_id="paper_999",
            pdf_url="https://example.com/paper4.pdf",
            source="different",
            discovery_timestamp=datetime.now(),
            confidence_score=0.75,
            version_info={},
            validation_status="pending",
        )

        assert hash(record1) == hash(record2)

        # Different URL should have different hash
        record3 = PDFRecord(
            paper_id="paper_999",
            pdf_url="https://different.com/paper4.pdf",
            source="pmlr",
            discovery_timestamp=datetime.now(),
            confidence_score=0.85,
            version_info={},
            validation_status="validated",
        )

        assert hash(record1) != hash(record3)

    def test_pdf_record_str_representation(self):
        """Test string representation of PDFRecord."""
        record = PDFRecord(
            paper_id="paper_111",
            pdf_url="https://example.com/paper5.pdf",
            source="cvf",
            discovery_timestamp=datetime(2025, 1, 2, 10, 30),
            confidence_score=0.92,
            version_info={"version": "final"},
            validation_status="validated",
        )

        str_repr = str(record)
        assert "paper_111" in str_repr
        assert "cvf" in str_repr
        assert "0.92" in str_repr


class TestDiscoveryResult:
    """Test DiscoveryResult container."""

    def test_discovery_result_creation(self):
        """Test creating a DiscoveryResult."""
        records = [
            PDFRecord(
                paper_id="paper_1",
                pdf_url="https://example.com/1.pdf",
                source="arxiv",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="validated",
            ),
            PDFRecord(
                paper_id="paper_2",
                pdf_url="https://example.com/2.pdf",
                source="openreview",
                discovery_timestamp=datetime.now(),
                confidence_score=0.85,
                version_info={},
                validation_status="validated",
            ),
        ]

        result = DiscoveryResult(
            total_papers=10,
            discovered_count=2,
            records=records,
            failed_papers=["paper_3", "paper_4"],
            source_statistics={
                "arxiv": {"attempted": 5, "successful": 1},
                "openreview": {"attempted": 5, "successful": 1},
            },
            execution_time_seconds=3.5,
        )

        assert result.total_papers == 10
        assert result.discovered_count == 2
        assert len(result.records) == 2
        assert len(result.failed_papers) == 2
        assert result.source_statistics["arxiv"]["successful"] == 1
        assert result.execution_time_seconds == 3.5

    def test_discovery_result_discovery_rate(self):
        """Test calculation of discovery rate."""
        result = DiscoveryResult(
            total_papers=100,
            discovered_count=85,
            records=[],
            failed_papers=[],
            source_statistics={},
            execution_time_seconds=10.0,
        )

        assert result.discovery_rate == 0.85

    def test_discovery_result_zero_papers(self):
        """Test discovery rate with zero total papers."""
        result = DiscoveryResult(
            total_papers=0,
            discovered_count=0,
            records=[],
            failed_papers=[],
            source_statistics={},
            execution_time_seconds=0.1,
        )

        assert result.discovery_rate == 0.0

    def test_discovery_result_summary(self):
        """Test summary generation for DiscoveryResult."""
        result = DiscoveryResult(
            total_papers=50,
            discovered_count=45,
            records=[],
            failed_papers=["p1", "p2", "p3", "p4", "p5"],
            source_statistics={
                "arxiv": {"attempted": 25, "successful": 23},
                "semantic_scholar": {"attempted": 25, "successful": 22},
            },
            execution_time_seconds=5.5,
        )

        summary = result.summary()
        assert "45/50" in summary
        assert "90.0%" in summary
        assert "5.5s" in summary
        assert "arxiv: 23/25" in summary
        assert "semantic_scholar: 22/25" in summary
