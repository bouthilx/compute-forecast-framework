"""Integration tests for JMLR/TMLR PDF collector."""

import pytest

from compute_forecast.data.models import Paper
from compute_forecast.pdf_discovery.sources.jmlr_collector import JMLRCollector


@pytest.mark.integration
class TestJMLRIntegration:
    """Integration tests for JMLR/TMLR collector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.collector = JMLRCollector()
    
    @pytest.mark.skip(reason="Requires network access to jmlr.org")
    def test_discover_real_jmlr_paper(self):
        """Test discovering a real JMLR paper."""
        # This is a real JMLR paper that should exist
        paper = Paper(
            paper_id="test_jmlr_1",
            title="A Dual Coordinate Descent Method for Large-scale Linear SVM",
            venue="Journal of Machine Learning Research",
            authors=[],
            year=2008,
            citations=0,
            urls=["https://jmlr.org/papers/v9/hsieh08a.html"]
        )
        
        record = self.collector._discover_single(paper)
        
        assert record is not None
        assert record.paper_id == "test_jmlr_1"
        assert record.pdf_url == "https://jmlr.org/papers/v9/hsieh08a.pdf"
        assert record.source == "jmlr_tmlr"
        assert record.confidence_score > 0.9
        assert record.validation_status == "verified"
    
    @pytest.mark.skip(reason="Requires network access to jmlr.org")
    def test_discover_real_tmlr_paper(self):
        """Test discovering a real TMLR paper."""
        # This would need a real TMLR paper title
        paper = Paper(
            paper_id="test_tmlr_1",
            title="Example TMLR Paper Title",  # Replace with real paper
            venue="Transactions on Machine Learning Research",
            authors=[],
            year=2023,
            citations=0
        )
        
        try:
            record = self.collector._discover_single(paper)
            
            assert record is not None
            assert record.paper_id == "test_tmlr_1"
            assert record.source == "jmlr_tmlr"
            assert record.pdf_url.startswith("https://jmlr.org/tmlr/papers/")
            assert record.pdf_url.endswith(".pdf")
        except ValueError as e:
            # Expected if the paper doesn't exist
            assert "Could not find TMLR paper" in str(e)
    
    def test_collector_statistics(self):
        """Test that collector tracks statistics correctly."""
        papers = [
            Paper(
                paper_id="test1",
                title="Test Paper 1",
                venue="JMLR",
                authors=[],
                year=2023,
                citations=0,
                urls=["https://jmlr.org/papers/v9/test1.html"]
            ),
            Paper(
                paper_id="test2",
                title="Test Paper 2",
                venue="NeurIPS",  # Not JMLR/TMLR
                authors=[],
                year=2023,
                citations=0
            )
        ]
        
        # Run discovery (will fail for both in test environment)
        self.collector.discover_pdfs(papers)
        
        stats = self.collector.get_statistics()
        assert stats["attempted"] == 2
        assert stats["failed"] == 2  # Both should fail without network
        assert stats["successful"] == 0