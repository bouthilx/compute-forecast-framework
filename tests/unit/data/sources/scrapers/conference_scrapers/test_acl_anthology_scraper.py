"""Unit tests for ACL Anthology scraper"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from compute_forecast.data.sources.scrapers.conference_scrapers.acl_anthology_scraper import (
    ACLAnthologyScraper
)
from compute_forecast.data.sources.scrapers import ScrapingConfig, ScrapingResult


class TestACLAnthologyScraper:
    """Test ACL Anthology scraper functionality"""
    
    def setup_method(self):
        """Set up test instance"""
        self.scraper = ACLAnthologyScraper()
        
    def test_init(self):
        """Test scraper initialization"""
        assert self.scraper.source_name == "acl_anthology"
        assert self.scraper.base_url == "https://aclanthology.org/"
        assert isinstance(self.scraper.venue_mappings, dict)
        
    def test_venue_mappings(self):
        """Test venue name mappings"""
        mappings = self.scraper._load_venue_mappings()
        
        # Check key venues are mapped
        assert "ACL" in mappings
        assert mappings["ACL"] == "acl"
        assert "EMNLP" in mappings
        assert mappings["EMNLP"] == "emnlp"
        assert "NAACL" in mappings
        assert mappings["NAACL"] == "naacl"
        assert "COLING" in mappings
        assert mappings["COLING"] == "coling"
        
        # Verify all major NLP venues
        expected_venues = ["ACL", "EMNLP", "NAACL", "COLING", "EACL", "CoNLL"]
        for venue in expected_venues:
            assert venue in mappings
            
    def test_get_supported_venues(self):
        """Test getting list of supported venues"""
        venues = self.scraper.get_supported_venues()
        
        assert isinstance(venues, list)
        assert len(venues) > 0
        assert "ACL" in venues
        assert "EMNLP" in venues
        
    @patch('requests.Session.get')
    def test_get_available_years_success(self, mock_get):
        """Test getting available years for a venue"""
        # Mock response with year links
        mock_response = Mock()
        mock_response.content = b"""
        <html>
        <body>
            <a href="/events/acl-2024/">ACL 2024</a>
            <a href="/events/acl-2023/">ACL 2023</a>
            <a href="/volumes/2022.acl-main/">ACL 2022</a>
            <a href="/volumes/P21-1234/">Paper from 2021</a>
        </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        years = self.scraper.get_available_years("ACL")
        
        assert isinstance(years, list)
        assert 2024 in years
        assert 2023 in years
        assert 2022 in years
        assert 2021 in years
        assert years == sorted(years, reverse=True)
        
    @patch('requests.Session.get')
    def test_get_available_years_unsupported_venue(self, mock_get):
        """Test getting years for unsupported venue"""
        years = self.scraper.get_available_years("UNKNOWN")
        assert years == []
        
    @patch('requests.Session.get')
    def test_get_available_years_fallback(self, mock_get):
        """Test fallback when venue page fails"""
        mock_get.side_effect = Exception("Network error")
        
        years = self.scraper.get_available_years("ACL")
        
        # Should return recent years as fallback
        current_year = datetime.now().year
        assert isinstance(years, list)
        assert current_year in years
        assert 2018 in years
        
    def test_get_proceedings_url(self):
        """Test URL construction for proceedings"""
        url = self.scraper.get_proceedings_url("ACL", 2024)
        assert url == "https://aclanthology.org/events/acl-2024/"
        
        url = self.scraper.get_proceedings_url("EMNLP", 2023)
        assert url == "https://aclanthology.org/events/emnlp-2023/"
        
    def test_extract_volume_urls(self):
        """Test extracting volume URLs from event page"""
        html = """
        <html>
        <body>
            <a href="/volumes/2024.acl-main/">Main Conference Papers</a>
            <a href="/volumes/2024.acl-short/">Short Papers</a>
            <a href="/volumes/2024.acl-demo/">System Demonstrations</a>
            <a href="/volumes/2024.acl-findings/">Findings</a>
        </body>
        </html>
        """
        
        volumes = self.scraper._extract_volume_urls(html, "ACL", 2024)
        
        assert "main" in volumes
        assert volumes["main"] == "https://aclanthology.org/volumes/2024.acl-main/"
        assert "short" in volumes
        assert "demo" in volumes
        assert "findings" in volumes
        
    def test_extract_paper_from_entry(self):
        """Test extracting paper data from HTML entry"""
        entry_html = """
        <div>
            <a href="/2024.acl-long.123/">Understanding Large Language Models</a>
            <i>John Doe, Jane Smith, Bob Johnson</i>
            <a href="/2024.acl-long.123.pdf">PDF</a>
        </div>
        """
        
        from bs4 import BeautifulSoup
        entry = BeautifulSoup(entry_html, 'html.parser')
        
        paper = self.scraper._extract_paper_from_entry(entry, "ACL", 2024, "https://test.com")
        
        assert paper is not None
        assert paper.title == "Understanding Large Language Models"
        assert paper.authors == ["John Doe", "Jane Smith", "Bob Johnson"]
        assert paper.venue == "ACL"
        assert paper.year == 2024
        assert len(paper.pdf_urls) == 1
        assert paper.pdf_urls[0] == "https://aclanthology.org/2024.acl-long.123.pdf"
        assert paper.paper_id == "acl_2024.acl-long.123"
        
    def test_extract_pdf_url_patterns(self):
        """Test PDF URL extraction with different ACL Anthology patterns"""
        # Test new format pattern
        entry1 = self._create_entry('<a href="/2024.acl-long.0/">Paper Title</a>')
        pdf_url1 = self.scraper._extract_pdf_url(entry1, "https://aclanthology.org/2024.acl-long.0/")
        assert pdf_url1 == "https://aclanthology.org/2024.acl-long.0.pdf"
        
        # Test old format pattern  
        entry2 = self._create_entry('<a href="/P24-1234/">Paper Title</a>')
        pdf_url2 = self.scraper._extract_pdf_url(entry2, "https://aclanthology.org/P24-1234/")
        assert pdf_url2 == "https://aclanthology.org/P24-1234.pdf"
        
        # Test with explicit PDF link
        entry3 = self._create_entry('<a href="/2024.acl-long.0.pdf">PDF</a>')
        pdf_url3 = self.scraper._extract_pdf_url(entry3, "https://aclanthology.org/2024.acl-long.0/")
        assert pdf_url3 == "https://aclanthology.org/2024.acl-long.0.pdf"
        
        # Test other volume types
        entry4 = self._create_entry('<a href="/2024.acl-short.15/">Short Paper</a>')
        pdf_url4 = self.scraper._extract_pdf_url(entry4, "https://aclanthology.org/2024.acl-short.15/")
        assert pdf_url4 == "https://aclanthology.org/2024.acl-short.15.pdf"
        
    def test_extract_authors_various_formats(self):
        """Test author extraction with different formats"""
        # Test comma-separated authors
        entry1 = self._create_entry('<i>Alice Chen, Bob Smith, Carol Jones</i>')
        authors1 = self.scraper._extract_authors_from_entry(entry1)
        assert authors1 == ["Alice Chen", "Bob Smith", "Carol Jones"]
        
        # Test 'and' separator
        entry2 = self._create_entry('<span>David Lee and Emma Wilson</span>')
        authors2 = self.scraper._extract_authors_from_entry(entry2)
        assert authors2 == ["David Lee", "Emma Wilson"]
        
        # Test semicolon separator
        entry3 = self._create_entry('<div>Frank Brown; Grace Taylor; Henry Davis</div>')
        authors3 = self.scraper._extract_authors_from_entry(entry3)
        assert authors3 == ["Frank Brown", "Grace Taylor", "Henry Davis"]
        
    def test_calculate_completeness(self):
        """Test metadata completeness calculation"""
        # Full metadata
        score1 = self.scraper._calculate_completeness(
            "A Very Interesting Paper Title",
            ["Author One", "Author Two"],
            "https://example.com/paper.pdf"
        )
        assert score1 == 1.0
        
        # Missing PDF
        score2 = self.scraper._calculate_completeness(
            "Another Paper Title",
            ["Author"],
            None
        )
        assert score2 == 0.7
        
        # Missing authors but has PDF
        score3 = self.scraper._calculate_completeness(
            "Title Only Here",
            [],
            "https://example.com/paper.pdf"
        )
        assert score3 == 0.7
        
        # Missing authors and PDF but good title
        score4 = self.scraper._calculate_completeness(
            "A Good Long Title Here",
            [],
            None
        )
        assert score4 == 0.8
        
        # Short title
        score5 = self.scraper._calculate_completeness(
            "Short",
            ["Author"],
            "https://example.com/paper.pdf"
        )
        assert score5 == 0.6
        
    @patch('requests.Session.get')
    def test_scrape_venue_year_unsupported(self, mock_get):
        """Test scraping unsupported venue"""
        result = self.scraper.scrape_venue_year("UNKNOWN", 2024)
        
        assert not result.success
        assert result.papers_collected == 0
        assert "not supported" in result.errors[0]
        
    @patch('requests.Session.get')
    def test_scrape_venue_year_success(self, mock_get):
        """Test successful venue/year scraping"""
        # Mock event page response
        event_response = Mock()
        event_response.text = """
        <html>
        <body>
            <a href="/volumes/2024.acl-main/">Main Papers</a>
        </body>
        </html>
        """
        event_response.raise_for_status = Mock()
        
        # Mock volume page response
        volume_response = Mock()
        volume_response.text = """
        <html>
        <body>
            <div class="paper-entry">
                <a href="/2024.acl-main.1/">First Paper</a>
                <i>Author One, Author Two</i>
            </div>
            <div class="paper-entry">
                <a href="/2024.acl-main.2/">Second Paper</a>
                <i>Author Three</i>
            </div>
        </body>
        </html>
        """
        volume_response.raise_for_status = Mock()
        
        # Set up mock responses
        mock_get.side_effect = [event_response, volume_response]
        
        result = self.scraper.scrape_venue_year("ACL", 2024)
        
        assert result.success
        assert result.papers_collected == 2
        assert len(result.metadata["papers"]) == 2
        
    def test_try_direct_volume_urls(self):
        """Test fallback direct volume URL attempts"""
        with patch.object(self.scraper, '_scrape_volume_page') as mock_scrape:
            # Mock successful scrape of one volume type
            mock_scrape.side_effect = [
                Exception("Not found"),  # main fails
                [Mock(title="Paper 1"), Mock(title="Paper 2")],  # long succeeds
                Exception("Not found"),  # others fail
            ]
            
            papers = self.scraper._try_direct_volume_urls("ACL", 2024)
            
            assert len(papers) == 2
            # Verify it tried multiple patterns
            assert mock_scrape.call_count >= 2
            
    def _create_entry(self, html):
        """Helper to create BeautifulSoup entry from HTML"""
        from bs4 import BeautifulSoup
        return BeautifulSoup(f"<div>{html}</div>", 'html.parser')