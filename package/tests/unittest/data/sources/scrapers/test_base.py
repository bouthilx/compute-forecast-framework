"""Tests for base scraper classes"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests
from typing import List, Dict

from compute_forecast.data.sources.scrapers.base import (
    ScrapingConfig,
    ScrapingResult,
    BaseScaper,
    ConferenceProceedingsScaper,
    JournalPublisherScaper,
    APIEnhancedScaper,
)
from compute_forecast.data.models import Paper, Author


# Test implementations for abstract classes
class MockScraperImpl(BaseScaper):
    """Concrete implementation for testing BaseScaper"""
    
    def __init__(self, supported_venues=None, available_years=None, config=None):
        super().__init__("test_scraper", config)
        self._supported_venues = supported_venues or ["NeurIPS", "ICML"]
        self._available_years = available_years or {
            "NeurIPS": [2022, 2023, 2024],
            "ICML": [2022, 2023]
        }
        
    def get_supported_venues(self) -> List[str]:
        return self._supported_venues
        
    def get_available_years(self, venue: str) -> List[int]:
        return self._available_years.get(venue, [])
        
    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        if venue == "error_venue":
            raise Exception("Test error")
        return ScrapingResult.success_result(papers_count=10)


class MockConferenceScraperImpl(ConferenceProceedingsScaper):
    """Concrete implementation for testing ConferenceProceedingsScaper"""
    
    def __init__(self, config=None):
        super().__init__("test_conference_scraper", config)
    
    def get_supported_venues(self) -> List[str]:
        return ["NeurIPS", "ICML"]
        
    def get_available_years(self, venue: str) -> List[int]:
        return [2022, 2023, 2024]
        
    def get_proceedings_url(self, venue: str, year: int) -> str:
        return f"https://example.com/{venue}/{year}"
        
    def parse_proceedings_page(self, html: str, venue: str, year: int) -> List[Paper]:
        # Mock parsing
        papers = []
        for i in range(5):
            papers.append(Paper(
                title=f"Test Paper {i}",
                authors=[Author(name=f"Author {i}")],
                venue=venue,
                year=year,
                citations=0
            ))
        return papers


class MockJournalScraperImpl(JournalPublisherScaper):
    """Concrete implementation for testing JournalPublisherScaper"""
    
    def __init__(self, config=None):
        super().__init__("test_journal_scraper", config)
    
    def get_supported_venues(self) -> List[str]:
        return ["Nature", "Science"]
        
    def get_available_years(self, venue: str) -> List[int]:
        return list(range(2020, 2025))
        
    def search_papers(self, journal: str, keywords: List[str], year_range) -> List[Paper]:
        papers = []
        for i in range(3):
            papers.append(Paper(
                title=f"Journal Paper {i}",
                authors=[Author(name=f"Author {i}")],
                venue=journal,
                year=year_range[0],
                citations=0
            ))
        return papers


class MockAPIScraperImpl(APIEnhancedScaper):
    """Concrete implementation for testing APIEnhancedScaper"""
    
    def __init__(self, auth_success=True, config=None):
        super().__init__("test_api_scraper", config)
        self.auth_success = auth_success
        self.api_calls = []
        
    def get_supported_venues(self) -> List[str]:
        return ["CVPR", "ICCV"]
        
    def get_available_years(self, venue: str) -> List[int]:
        return [2022, 2023, 2024]
        
    def authenticate(self) -> bool:
        return self.auth_success
        
    def make_api_request(self, endpoint: str, params: Dict) -> Dict:
        self.api_calls.append((endpoint, params))
        
        # Simulate paginated response
        offset = params.get("offset", 0)
        if offset == 0:
            return {"papers": [{"title": f"Paper {i}"} for i in range(100)]}
        elif offset == 100:
            return {"papers": [{"title": f"Paper {i}"} for i in range(50)]}
        else:
            return {"papers": []}


class TestScrapingConfig:
    """Test ScrapingConfig dataclass"""
    
    def test_default_values(self):
        config = ScrapingConfig()
        assert config.rate_limit_delay == 1.0
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.batch_size == 100
        assert config.cache_enabled is True
        assert "ComputeForecast" in config.user_agent
        
    def test_custom_values(self):
        config = ScrapingConfig(
            rate_limit_delay=2.0,
            max_retries=5,
            timeout=60,
            batch_size=50,
            cache_enabled=False,
            user_agent="CustomAgent/1.0"
        )
        assert config.rate_limit_delay == 2.0
        assert config.max_retries == 5
        assert config.timeout == 60
        assert config.batch_size == 50
        assert config.cache_enabled is False
        assert config.user_agent == "CustomAgent/1.0"


class TestScrapingResult:
    """Test ScrapingResult dataclass"""
    
    def test_success_result(self):
        result = ScrapingResult.success_result(
            papers_count=10,
            metadata={"venue": "NeurIPS"}
        )
        assert result.success is True
        assert result.papers_collected == 10
        assert result.errors == []
        assert result.metadata == {"venue": "NeurIPS"}
        assert isinstance(result.timestamp, datetime)
        
    def test_failure_result(self):
        errors = ["Connection error", "Parse error"]
        result = ScrapingResult.failure_result(
            errors=errors,
            metadata={"venue": "ICML"}
        )
        assert result.success is False
        assert result.papers_collected == 0
        assert result.errors == errors
        assert result.metadata == {"venue": "ICML"}
        assert isinstance(result.timestamp, datetime)


class TestBaseScaper:
    """Test BaseScaper abstract class"""
    
    def test_initialization(self):
        scraper = MockScraperImpl()
        assert scraper.source_name == "test_scraper"
        assert isinstance(scraper.config, ScrapingConfig)
        assert scraper._session is None
        assert scraper._cache == {}
        
    def test_custom_config(self):
        config = ScrapingConfig(rate_limit_delay=2.0)
        scraper = MockScraperImpl(config=config)
        assert scraper.config.rate_limit_delay == 2.0
        
    def test_session_creation(self):
        scraper = MockScraperImpl()
        session = scraper.session
        assert isinstance(session, requests.Session)
        assert scraper._session is session  # Same instance on subsequent calls
        assert scraper.config.user_agent in session.headers['User-Agent']
        
    @patch('requests.Session.get')
    def test_make_request(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        scraper = MockScraperImpl()
        with patch('time.sleep') as mock_sleep:
            response = scraper._make_request("https://example.com")
            
        mock_sleep.assert_called_once_with(1.0)  # rate limit delay
        mock_get.assert_called_once()
        assert response == mock_response
        
    def test_validate_venue_year(self):
        scraper = MockScraperImpl()
        
        # Valid venue and year
        errors = scraper.validate_venue_year("NeurIPS", 2023)
        assert errors == []
        
        # Invalid venue
        errors = scraper.validate_venue_year("InvalidVenue", 2023)
        assert len(errors) == 1
        assert "not supported" in errors[0]
        
        # Invalid year
        errors = scraper.validate_venue_year("NeurIPS", 2020)
        assert len(errors) == 1
        assert "not available" in errors[0]
        
    def test_scrape_multiple_venues(self):
        scraper = MockScraperImpl()
        
        with patch('time.sleep'):  # Skip delays in tests
            results = scraper.scrape_multiple_venues({
                "NeurIPS": [2023, 2024],
                "ICML": [2023],
                "InvalidVenue": [2023]
            })
            
        assert "NeurIPS_2023" in results
        assert results["NeurIPS_2023"].success is True
        assert results["NeurIPS_2023"].papers_collected == 10
        
        assert "NeurIPS_2024" in results
        assert results["NeurIPS_2024"].success is True
        
        assert "ICML_2023" in results
        assert results["ICML_2023"].success is True
        
        assert "InvalidVenue" in results
        assert results["InvalidVenue"].success is False
        assert "not supported" in results["InvalidVenue"].errors[0]
        
    def test_scrape_multiple_venues_with_error(self):
        scraper = MockScraperImpl(supported_venues=["error_venue"])
        
        with patch('time.sleep'):
            results = scraper.scrape_multiple_venues({
                "error_venue": [2023]
            })
            
        assert "error_venue_2023" in results
        assert results["error_venue_2023"].success is False
        assert "Test error" in results["error_venue_2023"].errors[0]


class TestConferenceProceedingsScaper:
    """Test ConferenceProceedingsScaper"""
    
    @patch('requests.Session.get')
    def test_scrape_venue_year_success(self, mock_get):
        mock_response = Mock()
        mock_response.text = "<html>Mock proceedings page</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        scraper = MockConferenceScraperImpl()
        
        with patch('time.sleep'):
            result = scraper.scrape_venue_year("NeurIPS", 2023)
            
        assert result.success is True
        assert result.papers_collected == 5
        assert result.metadata["venue"] == "NeurIPS"
        assert result.metadata["year"] == 2023
        assert result.metadata["url"] == "https://example.com/NeurIPS/2023"
        assert len(result.metadata["papers"]) == 5
        
    def test_scrape_venue_year_invalid_venue(self):
        scraper = MockConferenceScraperImpl()
        result = scraper.scrape_venue_year("InvalidVenue", 2023)
        
        assert result.success is False
        assert "not supported" in result.errors[0]
        
    @patch('requests.Session.get')
    def test_scrape_venue_year_network_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Network error")
        
        scraper = MockConferenceScraperImpl()
        
        with patch('time.sleep'):
            result = scraper.scrape_venue_year("NeurIPS", 2023)
            
        assert result.success is False
        assert "Network error" in result.errors[0]


class TestJournalPublisherScaper:
    """Test JournalPublisherScaper"""
    
    def test_scrape_venue_year_success(self):
        scraper = MockJournalScraperImpl()
        result = scraper.scrape_venue_year("Nature", 2023)
        
        assert result.success is True
        assert result.papers_collected == 3
        assert result.metadata["journal"] == "Nature"
        assert result.metadata["year"] == 2023
        assert len(result.metadata["papers"]) == 3
        
    def test_scrape_venue_year_with_error(self):
        scraper = MockJournalScraperImpl()
        
        # Mock search_papers to raise exception
        scraper.search_papers = Mock(side_effect=Exception("Search failed"))
        
        result = scraper.scrape_venue_year("Nature", 2023)
        
        assert result.success is False
        assert "Search failed" in result.errors[0]


class TestAPIEnhancedScaper:
    """Test APIEnhancedScaper"""
    
    def test_authentication_success(self):
        scraper = MockAPIScraperImpl(auth_success=True)
        assert scraper.authenticate() is True
        
    def test_authentication_failure(self):
        scraper = MockAPIScraperImpl(auth_success=False)
        assert scraper.authenticate() is False
        
    def test_ensure_authenticated(self):
        scraper = MockAPIScraperImpl(auth_success=True)
        assert scraper._authenticated is False
        
        scraper._ensure_authenticated()
        assert scraper._authenticated is True
        
        # Should not authenticate again
        with patch.object(scraper, 'authenticate') as mock_auth:
            scraper._ensure_authenticated()
            mock_auth.assert_not_called()
            
    def test_ensure_authenticated_failure(self):
        scraper = MockAPIScraperImpl(auth_success=False)
        
        with pytest.raises(RuntimeError, match="Failed to authenticate"):
            scraper._ensure_authenticated()
            
    def test_scrape_venue_year_success(self):
        scraper = MockAPIScraperImpl(auth_success=True)
        
        with patch('time.sleep'):
            result = scraper.scrape_venue_year("CVPR", 2023)
            
        assert result.success is True
        assert result.papers_collected == 150  # 100 + 50 from pagination
        assert len(scraper.api_calls) == 2  # Two paginated requests
        
        # Check pagination parameters
        assert scraper.api_calls[0][1]["venue"] == "CVPR"
        assert scraper.api_calls[0][1]["year"] == 2023
        assert scraper.api_calls[0][1]["limit"] == 100
        assert scraper.api_calls[0][1]["offset"] == 0
        assert scraper.api_calls[1][1]["offset"] == 100
        
    def test_scrape_venue_year_auth_failure(self):
        scraper = MockAPIScraperImpl(auth_success=False)
        
        result = scraper.scrape_venue_year("CVPR", 2023)
        
        assert result.success is False
        assert "Failed to authenticate" in result.errors[0]
        
    def test_scrape_venue_year_invalid_venue(self):
        scraper = MockAPIScraperImpl(auth_success=True)
        
        result = scraper.scrape_venue_year("InvalidVenue", 2023)
        
        assert result.success is False
        assert "not supported" in result.errors[0]