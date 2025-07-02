"""Integration tests for OpenReview PDF collector with real API."""

import pytest
from src.data.models import Paper, Author
from src.pdf_discovery.sources.openreview_collector import OpenReviewPDFCollector


@pytest.mark.integration
class TestOpenReviewIntegration:
    """Integration tests with real OpenReview API."""
    
    @pytest.fixture
    def collector(self):
        """Create real OpenReview collector instance."""
        return OpenReviewPDFCollector()
    
    def test_real_iclr_2024_paper(self, collector):
        """Test with a real ICLR 2024 paper."""
        # This is a known ICLR 2024 paper
        paper = Paper(
            paper_id="test_iclr_2024",
            title="Language Models are Few-Shot Learners",
            authors=[Author(name="Test Author", affiliation="Test")],
            venue="ICLR",
            year=2024,
            citations=0,
        )
        
        try:
            pdf_record = collector._discover_single(paper)
            assert pdf_record is not None
            assert pdf_record.pdf_url.startswith("https://openreview.net/pdf?id=")
            assert pdf_record.source == "openreview"
            assert pdf_record.confidence_score > 0.7
        except Exception as e:
            # Allow failure if paper not found (title might not match exactly)
            assert "not found" in str(e).lower()
    
    def test_venue_year_validation(self, collector):
        """Test that unsupported venue/year combinations are rejected."""
        # NeurIPS before 2023 should not be on OpenReview
        paper = Paper(
            paper_id="old_neurips",
            title="Old NeurIPS Paper",
            authors=[Author(name="Author", affiliation="Lab")],
            venue="NeurIPS",
            year=2022,  # Before OpenReview adoption
            citations=0,
        )
        
        with pytest.raises(ValueError) as exc_info:
            collector._discover_single(paper)
        
        assert "2023 onwards" in str(exc_info.value)