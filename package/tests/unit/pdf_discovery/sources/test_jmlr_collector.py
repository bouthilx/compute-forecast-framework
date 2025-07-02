"""Tests for JMLR/TMLR PDF collector."""

import pytest
from unittest.mock import Mock, patch

from src.data.models import Paper
from src.pdf_discovery.sources.jmlr_collector import JMLRCollector


class TestJMLRCollector:
    """Test suite for JMLR/TMLR collector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.collector = JMLRCollector()
    
    def test_init(self):
        """Test collector initialization."""
        assert self.collector.source_name == "jmlr_tmlr"
        assert self.collector.jmlr_base_url == "https://jmlr.org/papers/"
        assert self.collector.tmlr_base_url == "https://jmlr.org/tmlr/papers/"
    
    def test_discover_jmlr_paper_with_url(self):
        """Test discovering JMLR paper with URL containing volume info."""
        paper = Paper(
            paper_id="test123",
            title="Test Paper",
            venue="Journal of Machine Learning Research",
            authors=[],
            year=2023,
            citations=0,
            urls=["https://jmlr.org/papers/v23/21-1234.html"]
        )
        
        with patch.object(self.collector.session, 'head') as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            
            record = self.collector._discover_single(paper)
            
            assert record.paper_id == "test123"
            assert record.pdf_url == "https://jmlr.org/papers/v23/21-1234.pdf"
            assert record.source == "jmlr_tmlr"
            assert record.confidence_score == 0.95
            assert record.validation_status == "verified"
            assert record.version_info["venue"] == "JMLR"
    
    def test_discover_tmlr_paper(self):
        """Test discovering TMLR paper."""
        paper = Paper(
            paper_id="test456",
            title="Deep Learning for Test Cases",
            venue="Transactions on Machine Learning Research",
            authors=[],
            year=2023,
            citations=0
        )
        
        # Mock HTML response
        mock_html = """
        <html>
        <body>
            <a href="paper123.pdf">Deep Learning for Test Cases</a>
            <a href="paper456.pdf">Another Paper</a>
        </body>
        </html>
        """
        
        with patch.object(self.collector.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            record = self.collector._discover_single(paper)
            
            assert record.paper_id == "test456"
            assert record.pdf_url == "https://jmlr.org/tmlr/papers/paper123.pdf"
            assert record.source == "jmlr_tmlr"
            assert record.confidence_score == 0.90
            assert record.version_info["venue"] == "TMLR"
    
    def test_non_jmlr_tmlr_paper_raises_error(self):
        """Test that non-JMLR/TMLR papers raise ValueError."""
        paper = Paper(
            paper_id="test789",
            title="Test Paper",
            venue="NeurIPS",
            authors=[],
            year=2023,
            citations=0
        )
        
        with pytest.raises(ValueError, match="not from JMLR or TMLR"):
            self.collector._discover_single(paper)
    
    def test_extract_jmlr_volume_info_from_url(self):
        """Test extracting volume info from URL."""
        paper = Paper(
            paper_id="test",
            title="Test",
            venue="JMLR",
            authors=[],
            year=2023,
            citations=0,
            urls=["https://jmlr.org/papers/v23/21-1234.html"]
        )
        
        info = self.collector._extract_jmlr_volume_info(paper)
        
        assert info is not None
        assert info['volume'] == '23'
        assert info['paper_id'] == '21-1234'
    
    def test_extract_jmlr_volume_info_with_volume_field(self):
        """Test extracting volume info when paper has volume field."""
        paper = Mock()
        paper.volume = "23"
        paper.urls = ["https://jmlr.org/papers/21-1234"]
        
        info = self.collector._extract_jmlr_volume_info(paper)
        
        assert info is not None
        assert info['volume'] == '23'
        assert info['paper_id'] == '21-1234'
    
    def test_fuzzy_title_match(self):
        """Test fuzzy title matching."""
        # Exact match
        assert self.collector._fuzzy_title_match(
            "Deep Learning for Test Cases",
            "Deep Learning for Test Cases"
        )
        
        # Case insensitive
        assert self.collector._fuzzy_title_match(
            "deep learning for test cases",
            "DEEP LEARNING FOR TEST CASES"
        )
        
        # With punctuation
        assert self.collector._fuzzy_title_match(
            "Deep Learning: For Test Cases",
            "Deep Learning for Test Cases"
        )
        
        # Substring match
        assert self.collector._fuzzy_title_match(
            "Deep Learning",
            "Deep Learning for Test Cases"
        )
        
        # No match
        assert not self.collector._fuzzy_title_match(
            "Machine Learning",
            "Deep Learning"
        )
    
    def test_discover_jmlr_fallback_to_search(self):
        """Test that JMLR discovery falls back to website search when URL construction fails."""
        paper = Paper(
            paper_id="test123",
            title="Test Paper",
            venue="JMLR",
            authors=[],
            year=2023,
            citations=0
        )
        
        with patch.object(self.collector.session, 'head') as mock_head:
            # Simulate 404 for constructed URL
            mock_response = Mock()
            mock_response.status_code = 404
            mock_head.return_value = mock_response
            
            with pytest.raises(ValueError, match="Website search not implemented"):
                self.collector._discover_single(paper)
    
    def test_tmlr_paper_not_found(self):
        """Test error when TMLR paper is not found on website."""
        paper = Paper(
            paper_id="test456",
            title="Non-existent Paper",
            venue="TMLR",
            authors=[],
            year=2023,
            citations=0
        )
        
        mock_html = """
        <html>
        <body>
            <a href="paper123.pdf">Some Other Paper</a>
        </body>
        </html>
        """
        
        with patch.object(self.collector.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            with pytest.raises(ValueError, match="Could not find TMLR paper"):
                self.collector._discover_single(paper)
    
    def test_journal_field_detection(self):
        """Test detection using journal field instead of venue."""
        paper = Mock()
        paper.paper_id = "test123"
        paper.title = "Test Paper"
        paper.venue = ""  # Empty venue
        paper.journal = "Journal of Machine Learning Research"
        paper.urls = ["https://jmlr.org/papers/v23/21-1234.html"]
        
        with patch.object(self.collector.session, 'head') as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            
            record = self.collector._discover_single(paper)
            
            assert record.pdf_url == "https://jmlr.org/papers/v23/21-1234.pdf"