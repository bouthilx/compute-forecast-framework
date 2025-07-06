"""Unit tests for version manager."""

import pytest
from datetime import datetime

from compute_forecast.pdf_discovery.deduplication.version_manager import VersionManager, SourcePriority
from compute_forecast.pdf_discovery.core.models import PDFRecord


class TestSourcePriority:
    """Test source priority configuration."""
    
    def test_source_priority_creation(self):
        """Test creating source priority configuration."""
        priorities = SourcePriority(
            source_rankings={
                "venue_direct": 10,
                "arxiv": 5,
                "other": 1,
            },
            prefer_published=True
        )
        
        assert priorities.get_priority("venue_direct") == 10
        assert priorities.get_priority("arxiv") == 5
        assert priorities.get_priority("unknown") == 0  # Default for unknown sources


class TestVersionManager:
    """Test version management functionality."""
    
    @pytest.fixture
    def sample_records(self) -> list[PDFRecord]:
        """Create sample PDF records for testing."""
        return [
            PDFRecord(
                paper_id="paper1",
                pdf_url="https://venue.com/paper1.pdf",
                source="venue_direct",
                discovery_timestamp=datetime(2024, 1, 15),
                confidence_score=0.95,
                version_info={"is_published": True},
                validation_status="valid",
                file_size_bytes=500_000,
            ),
            PDFRecord(
                paper_id="paper1",
                pdf_url="https://arxiv.org/pdf/2301.12345.pdf",
                source="arxiv",
                discovery_timestamp=datetime(2024, 1, 10),
                confidence_score=0.90,
                version_info={"is_preprint": True},
                validation_status="valid",
                file_size_bytes=450_000,
            ),
            PDFRecord(
                paper_id="paper1",
                pdf_url="https://repository.com/paper1.pdf",
                source="repository",
                discovery_timestamp=datetime(2024, 1, 20),
                confidence_score=0.85,
                version_info={},
                validation_status="unknown",
                file_size_bytes=30_000,  # Small file
            ),
        ]
    
    def test_select_best_version_single(self):
        """Test selecting best version with single record."""
        manager = VersionManager()
        record = PDFRecord(
            paper_id="test",
            pdf_url="https://test.com/paper.pdf",
            source="test",
            discovery_timestamp=datetime.now(),
            confidence_score=0.9,
            version_info={},
            validation_status="valid",
        )
        
        assert manager.select_best_version([record]) == record
    
    def test_select_best_version_empty(self):
        """Test selecting best version with no records."""
        manager = VersionManager()
        
        with pytest.raises(ValueError, match="No versions provided"):
            manager.select_best_version([])
    
    def test_select_best_version_default_priorities(self, sample_records):
        """Test version selection with default priorities."""
        manager = VersionManager()
        
        best = manager.select_best_version(sample_records)
        
        # Should select venue_direct (highest priority, published, valid)
        assert best.source == "venue_direct"
        assert best.pdf_url == "https://venue.com/paper1.pdf"
    
    def test_select_best_version_custom_priorities(self, sample_records):
        """Test version selection with custom priorities."""
        manager = VersionManager()
        
        # Set custom priorities preferring arxiv
        custom = SourcePriority(
            source_rankings={
                "arxiv": 10,
                "venue_direct": 5,
                "repository": 1,
            },
            prefer_published=False
        )
        manager.set_priorities(custom)
        
        best = manager.select_best_version(sample_records)
        
        # Should select arxiv (highest custom priority)
        assert best.source == "arxiv"
        assert best.pdf_url == "https://arxiv.org/pdf/2301.12345.pdf"
    
    def test_version_score_calculation(self):
        """Test version score calculation logic."""
        manager = VersionManager()
        
        # High score record: valid, published, good source, high confidence
        high_score = PDFRecord(
            paper_id="test",
            pdf_url="https://venue.com/paper.pdf",
            source="venue_direct",
            discovery_timestamp=datetime.now(),
            confidence_score=0.95,
            version_info={"is_published": True},
            validation_status="valid",
            file_size_bytes=500_000,
        )
        
        # Low score record: invalid, preprint, poor source, low confidence
        low_score = PDFRecord(
            paper_id="test",
            pdf_url="https://other.com/paper.pdf",
            source="other",
            discovery_timestamp=datetime.now(),
            confidence_score=0.5,
            version_info={"is_preprint": True},
            validation_status="invalid",
            file_size_bytes=10_000,
        )
        
        high = manager._calculate_version_score(high_score, manager.default_priorities)
        low = manager._calculate_version_score(low_score, manager.default_priorities)
        
        assert high > low
        assert high > 70  # Should score well
        assert low < 30   # Should score poorly
    
    def test_validation_status_priority(self):
        """Test that validation status is prioritized correctly."""
        manager = VersionManager()
        
        records = [
            PDFRecord(
                paper_id="test",
                pdf_url="https://test1.com/paper.pdf",
                source="other",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="invalid",
            ),
            PDFRecord(
                paper_id="test",
                pdf_url="https://test2.com/paper.pdf",
                source="other",
                discovery_timestamp=datetime.now(),
                confidence_score=0.8,
                version_info={},
                validation_status="valid",
            ),
        ]
        
        best = manager.select_best_version(records)
        
        # Should prefer valid even with lower confidence
        assert best.validation_status == "valid"
    
    def test_file_size_consideration(self):
        """Test that file size is considered in scoring."""
        manager = VersionManager()
        
        records = [
            PDFRecord(
                paper_id="test",
                pdf_url="https://test1.com/paper.pdf",
                source="arxiv",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid",
                file_size_bytes=500_000,  # Good size
            ),
            PDFRecord(
                paper_id="test",
                pdf_url="https://test2.com/paper.pdf",
                source="arxiv",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid",
                file_size_bytes=10_000,  # Too small
            ),
        ]
        
        best = manager.select_best_version(records)
        
        # Should prefer the one with reasonable file size
        assert best.file_size_bytes == 500_000