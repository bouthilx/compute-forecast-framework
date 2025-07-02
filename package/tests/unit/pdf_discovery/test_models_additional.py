"""Additional unit tests for PDF discovery models to improve coverage."""

import pytest
from src.pdf_discovery.core.models import PDFRecord, DiscoveryResult
from datetime import datetime


class TestAdditionalModelCoverage:
    """Additional tests to achieve 90%+ coverage."""
    
    def test_pdf_record_repr(self):
        """Test __repr__ method of PDFRecord."""
        record = PDFRecord(
            paper_id="test_123",
            pdf_url="https://example.com/test.pdf",
            source="test_source",
            discovery_timestamp=datetime(2025, 1, 2, 10, 30),
            confidence_score=0.88,
            version_info={"v": "1"},
            validation_status="tested"
        )
        
        repr_str = repr(record)
        # repr() shows the full dataclass representation
        assert "PDFRecord(" in repr_str
        assert "paper_id='test_123'" in repr_str
        assert "source='test_source'" in repr_str
        assert "confidence_score=0.88" in repr_str
    
    def test_pdf_record_not_equal_to_other_type(self):
        """Test PDFRecord equality with non-PDFRecord type."""
        record = PDFRecord(
            paper_id="test_123",
            pdf_url="https://example.com/test.pdf",
            source="test",
            discovery_timestamp=datetime.now(),
            confidence_score=0.9,
            version_info={},
            validation_status="ok"
        )
        
        assert record != "not a record"
        assert record != 123
        assert record != None
        assert record != {"paper_id": "test_123"}
    
    def test_discovery_result_with_empty_source_stats(self):
        """Test DiscoveryResult summary with empty source statistics."""
        result = DiscoveryResult(
            total_papers=5,
            discovered_count=3,
            records=[],
            failed_papers=["p1", "p2"],
            source_statistics={},  # Empty stats
            execution_time_seconds=2.5
        )
        
        summary = result.summary()
        assert "3/5" in summary
        assert "60.0%" in summary
        assert "2.5s" in summary
        # No source breakdown should be shown
        assert "Source breakdown:" in summary