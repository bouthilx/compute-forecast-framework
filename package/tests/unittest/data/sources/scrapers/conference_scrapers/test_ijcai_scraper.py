"""Tests for IJCAI conference proceedings scraper"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from compute_forecast.data.sources.scrapers.conference_scrapers.ijcai_scraper import IJCAIScraper
from compute_forecast.data.sources.scrapers import ScrapingConfig, ScrapingResult, SimplePaper


class TestIJCAIScraper:
    """Test IJCAIScraper implementation"""
    
    @pytest.fixture
    def scraper(self):
        """Create IJCAIScraper instance for testing"""
        return IJCAIScraper()
    
    @pytest.fixture
    def custom_config(self):
        """Create custom config for testing"""
        return ScrapingConfig(
            rate_limit_delay=0.5,
            max_retries=2,
            timeout=10
        )
    
    def test_initialization(self, scraper):
        """Test scraper initialization"""
        assert scraper.source_name == "ijcai"
        assert scraper.base_url == "https://www.ijcai.org/"
        assert scraper.proceedings_pattern == "proceedings/{year}/"
        assert isinstance(scraper.config, ScrapingConfig)
    
    def test_custom_config(self):
        """Test initialization with custom config"""
        config = ScrapingConfig(rate_limit_delay=2.0)
        scraper = IJCAIScraper(config)
        assert scraper.config.rate_limit_delay == 2.0
    
    def test_get_supported_venues(self, scraper):
        """Test supported venues"""
        venues = scraper.get_supported_venues()
        assert venues == ["IJCAI"]
    
    def test_get_proceedings_url(self, scraper):
        """Test proceedings URL construction"""
        url = scraper.get_proceedings_url("IJCAI", 2024)
        assert url == "https://www.ijcai.org/proceedings/2024/"
        
        url = scraper.get_proceedings_url("IJCAI", 2023)
        assert url == "https://www.ijcai.org/proceedings/2023/"
    
    @patch('requests.Session.get')
    def test_get_available_years_success(self, mock_get, scraper):
        """Test getting available years from proceedings index"""
        # Mock proceedings index page
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <a href="/proceedings/2024/">IJCAI 2024</a>
                <a href="/proceedings/2023/">IJCAI 2023</a>
                <a href="/proceedings/2022/">IJCAI 2022</a>
                <a href="/proceedings/2021/">IJCAI 2021</a>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        years = scraper.get_available_years("IJCAI")
        
        # Should return years in descending order
        assert years == [2024, 2023, 2022, 2021]
        mock_get.assert_called_once()
        assert "proceedings/" in mock_get.call_args[0][0]
    
    @patch('requests.Session.get')
    def test_get_available_years_network_error(self, mock_get, scraper):
        """Test fallback when network error occurs"""
        mock_get.side_effect = requests.RequestException("Network error")
        
        years = scraper.get_available_years("IJCAI")
        
        # Should return fallback years
        assert 2024 in years
        assert 2023 in years
        assert 2022 in years
        assert years == sorted(years, reverse=True)
    
    def test_get_available_years_wrong_venue(self, scraper):
        """Test getting years for unsupported venue"""
        years = scraper.get_available_years("NEURIPS")
        assert years == []
    
    def test_scrape_venue_year_wrong_venue(self, scraper):
        """Test scraping unsupported venue"""
        result = scraper.scrape_venue_year("NEURIPS", 2024)
        
        assert result.success is False
        assert result.papers_collected == 0
        assert "not supported" in result.errors[0]
    
    @patch('requests.Session.get')
    def test_parse_proceedings_page_simple(self, mock_get, scraper):
        """Test parsing simple proceedings page"""
        html = """
        <html>
            <body>
                <div>
                    <a href="/proceedings/2024/paper1.pdf">Deep Learning for Robotics</a>
                    <span>John Doe, Jane Smith</span>
                </div>
                <div>
                    <a href="/proceedings/2024/paper2.pdf">Reinforcement Learning in Games</a>
                    <span>Alice Johnson, Bob Wilson</span>
                </div>
            </body>
        </html>
        """
        
        papers = scraper.parse_proceedings_page(html, "IJCAI", 2024)
        
        assert len(papers) == 2
        
        # Check first paper
        paper1 = papers[0]
        assert isinstance(paper1, SimplePaper)
        assert paper1.title == "Deep Learning for Robotics"
        assert paper1.venue == "IJCAI"
        assert paper1.year == 2024
        assert paper1.source_scraper == "ijcai"
        assert len(paper1.pdf_urls) == 1
        assert "paper1.pdf" in paper1.pdf_urls[0]
        
        # Check second paper
        paper2 = papers[1]
        assert paper2.title == "Reinforcement Learning in Games"
        assert "paper2.pdf" in paper2.pdf_urls[0]
    
    def test_extract_paper_from_pdf_link(self, scraper):
        """Test extracting paper metadata from PDF link"""
        # Create mock BeautifulSoup element
        soup = BeautifulSoup(
            '<a href="/proceedings/2024/0123.pdf">Test Paper Title</a>',
            'html.parser'
        )
        pdf_link = soup.find('a')
        
        paper = scraper._extract_paper_from_pdf_link(pdf_link, "IJCAI", 2024)
        
        assert paper is not None
        assert paper.paper_id == "ijcai_2024_0123"
        assert paper.title == "Test Paper Title"
        assert paper.venue == "IJCAI"
        assert paper.year == 2024
        assert len(paper.pdf_urls) == 1
        assert paper.pdf_urls[0] == "https://www.ijcai.org/proceedings/2024/0123.pdf"
        assert paper.source_scraper == "ijcai"
        assert paper.extraction_confidence == 0.9
    
    def test_extract_paper_no_href(self, scraper):
        """Test handling PDF link without href"""
        soup = BeautifulSoup('<a>No href</a>', 'html.parser')
        pdf_link = soup.find('a')
        
        paper = scraper._extract_paper_from_pdf_link(pdf_link, "IJCAI", 2024)
        assert paper is None
    
    def test_extract_authors_simple(self, scraper):
        """Test extracting authors from nearby elements"""
        html = """
        <div>
            <a href="paper.pdf">Title</a>
            <span>John Doe, Jane Smith</span>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        pdf_link = soup.find('a')
        
        authors = scraper._extract_authors_near_element(pdf_link)
        
        assert len(authors) == 2
        assert authors[0] == "John Doe"
        assert authors[1] == "Jane Smith"
    
    def test_calculate_completeness(self, scraper):
        """Test metadata completeness calculation"""
        # Full metadata
        score = scraper._calculate_completeness("Long Title Here", ["Author One", "Author Two"])
        assert score == 1.0
        
        # Title only
        score = scraper._calculate_completeness("Long Title Here", [])
        assert score == 0.4
        
        # Authors only
        score = scraper._calculate_completeness("", ["Author"])
        assert score == 0.4
        
        # Nothing
        score = scraper._calculate_completeness("", [])
        assert score == 0.0
    
    @patch('requests.Session.get')
    def test_scrape_venue_year_success(self, mock_get, scraper):
        """Test successful scraping of venue/year"""
        # Mock response with sample proceedings page
        mock_response = Mock()
        mock_response.text = """
        <html>
            <body>
                <a href="/proceedings/2024/0001.pdf">Paper One</a>
                <a href="/proceedings/2024/0002.pdf">Paper Two</a>
                <a href="/proceedings/2024/0003.pdf">Paper Three</a>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with patch('time.sleep'):  # Skip rate limiting in tests
            result = scraper.scrape_venue_year("IJCAI", 2024)
        
        assert result.success is True
        assert result.papers_collected == 3
        assert result.errors == []
        assert result.metadata["venue"] == "IJCAI"
        assert result.metadata["year"] == 2024
        assert "url" in result.metadata
    
    @patch('requests.Session.get')
    def test_scrape_venue_year_network_error(self, mock_get, scraper):
        """Test handling network errors during scraping"""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        result = scraper.scrape_venue_year("IJCAI", 2024)
        
        assert result.success is False
        assert result.papers_collected == 0
        assert len(result.errors) > 0
        assert "Connection failed" in result.errors[0]
    
    @patch('requests.Session.get')
    def test_parse_proceedings_page_from_url(self, mock_get, scraper):
        """Test fetching and parsing proceedings from URL"""
        mock_response = Mock()
        mock_response.text = '<a href="paper.pdf">Test Paper</a>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = "https://www.ijcai.org/proceedings/2024/"
        papers = scraper.parse_proceedings_page_from_url(url, "IJCAI", 2024)
        
        assert len(papers) == 1
        assert papers[0].title == "Test Paper"
        mock_get.assert_called_once()
    
    def test_retry_decorator_integration(self, scraper):
        """Test that retry decorator is properly applied"""
        # The scrape_venue_year method should have retry decorator
        assert hasattr(scraper.scrape_venue_year, '__wrapped__')