"""Tests for CVF scraper following TDD approach."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from compute_forecast.data.sources.scrapers.conference_scrapers.cvf_scraper import CVFScraper
from compute_forecast.data.sources.scrapers.models import SimplePaper
from compute_forecast.data.sources.scrapers.base import ScrapingResult


class TestCVFScraper:
    """Test suite for CVF scraper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = CVFScraper()
    
    def test_get_supported_venues(self):
        """Test that CVF scraper supports correct venues."""
        expected_venues = ["CVPR", "ICCV", "ECCV", "WACV", "cvpr", "iccv", "eccv", "wacv"]
        assert self.scraper.get_supported_venues() == expected_venues
    
    def test_get_available_years_cvpr_annual(self):
        """Test that CVPR returns annual years."""
        years = self.scraper.get_available_years("CVPR")
        
        # Should include recent years and be annual
        assert 2024 in years
        assert 2023 in years 
        assert 2022 in years
        # Should be sorted in descending order
        assert years == sorted(years, reverse=True)
    
    def test_get_available_years_iccv_odd_only(self):
        """Test that ICCV returns only odd years."""
        years = self.scraper.get_available_years("ICCV")
        
        # Should only include odd years
        for year in years:
            assert year % 2 == 1, f"ICCV year {year} should be odd"
        
        # Should include recent odd years
        assert 2023 in years
        assert 2021 in years
        # Should NOT include even years
        assert 2022 not in years
        assert 2024 not in years
    
    def test_get_available_years_eccv_even_only(self):
        """Test that ECCV returns only even years."""
        years = self.scraper.get_available_years("ECCV")
        
        # Should only include even years
        for year in years:
            assert year % 2 == 0, f"ECCV year {year} should be even"
        
        # Should include recent even years
        assert 2024 in years
        assert 2022 in years
        # Should NOT include odd years
        assert 2023 not in years
        assert 2021 not in years
    
    def test_get_available_years_wacv_annual(self):
        """Test that WACV returns annual years."""
        years = self.scraper.get_available_years("WACV")
        
        # Should include recent years and be annual
        assert 2024 in years
        assert 2023 in years
        assert 2022 in years
    
    def test_get_available_years_unsupported_venue(self):
        """Test that unsupported venue returns empty list."""
        years = self.scraper.get_available_years("INVALID")
        assert years == []
    
    def test_case_insensitive_venue_support(self):
        """Test that venue names are handled case-insensitively."""
        # Test lowercase venue
        years_lower = self.scraper.get_available_years("cvpr")
        years_upper = self.scraper.get_available_years("CVPR")
        assert years_lower == years_upper
        
        # Test URL generation is case-insensitive
        url_lower = self.scraper.get_proceedings_url("cvpr", 2024)
        url_upper = self.scraper.get_proceedings_url("CVPR", 2024)
        assert url_lower == url_upper
    
    def test_get_proceedings_url(self):
        """Test proceedings URL construction."""
        url = self.scraper.get_proceedings_url("CVPR", 2024)
        expected = "https://openaccess.thecvf.com/CVPR2024?day=all"
        assert url == expected
        
        url = self.scraper.get_proceedings_url("ICCV", 2023)
        expected = "https://openaccess.thecvf.com/ICCV2023?day=all"
        assert url == expected
    
    @patch('compute_forecast.data.sources.scrapers.conference_scrapers.cvf_scraper.CVFScraper._make_request')
    def test_scrape_venue_year_success(self, mock_make_request):
        """Test successful venue/year scraping."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = self._get_sample_cvf_html()
        mock_make_request.return_value = mock_response
        
        result = self.scraper.scrape_venue_year("CVPR", 2024)
        
        assert isinstance(result, ScrapingResult)
        assert result.success is True
        assert result.papers_collected > 0
        assert len(result.errors) == 0
        assert result.metadata["venue"] == "CVPR"
        assert result.metadata["year"] == 2024
    
    @patch('requests.get')
    def test_scrape_venue_year_unsupported_venue(self, mock_get):
        """Test scraping unsupported venue fails gracefully."""
        result = self.scraper.scrape_venue_year("INVALID", 2024)
        
        assert isinstance(result, ScrapingResult)
        assert result.success is False
        assert result.papers_collected == 0
        assert "not supported" in result.errors[0]
        mock_get.assert_not_called()
    
    @patch('requests.get')
    def test_scrape_venue_year_invalid_schedule(self, mock_get):
        """Test scraping invalid year for venue schedule fails."""
        # Try to scrape ICCV 2024 (even year)
        result = self.scraper.scrape_venue_year("ICCV", 2024)
        
        assert isinstance(result, ScrapingResult)
        assert result.success is False
        assert result.papers_collected == 0
        assert "not available (conference schedule)" in result.errors[0]
        mock_get.assert_not_called()
    
    @patch('compute_forecast.data.sources.scrapers.conference_scrapers.cvf_scraper.CVFScraper._make_request')
    def test_scrape_venue_year_network_error(self, mock_make_request):
        """Test network error handling."""
        mock_make_request.side_effect = Exception("Network error")
        
        result = self.scraper.scrape_venue_year("CVPR", 2024)
        
        assert isinstance(result, ScrapingResult)
        assert result.success is False
        assert result.papers_collected == 0
        assert len(result.errors) > 0
        assert "Network error" in result.errors[0]
    
    def test_parse_proceedings_page(self):
        """Test parsing CVF proceedings HTML."""
        html = self._get_sample_cvf_html()
        papers = self.scraper.parse_proceedings_page(html, "CVPR", 2024)
        
        assert len(papers) > 0
        
        # Check first paper structure
        paper = papers[0]
        assert isinstance(paper, SimplePaper)
        assert paper.title is not None
        assert len(paper.title) > 10
        assert paper.venue == "CVPR"
        assert paper.year == 2024
        assert paper.source_scraper == "cvf"
        assert len(paper.authors) > 0
        assert paper.pdf_urls is not None
        assert paper.metadata_completeness > 0
        assert paper.extraction_confidence > 0.9
    
    def test_parse_paper_with_pdf_link(self):
        """Test parsing paper entry with PDF link."""
        # This will be implemented when we have the actual parsing logic
        pass
    
    def test_parse_authors_from_forms(self):
        """Test extracting authors from CVF's form-based structure."""
        # This will be implemented when we have the actual parsing logic
        pass
    
    def test_metadata_completeness_calculation(self):
        """Test metadata completeness scoring."""
        # Test with complete data
        score = self.scraper._calculate_completeness(
            title="Test Paper Title",
            authors=["Author 1", "Author 2"],
            pdf_url="http://test.com/paper.pdf"
        )
        assert score == 1.0
        
        # Test with partial data
        score = self.scraper._calculate_completeness(
            title="Test Paper Title",
            authors=[],
            pdf_url=None
        )
        assert 0 < score < 1.0
    
    def _get_sample_cvf_html(self):
        """Get sample CVF HTML for testing."""
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>CVPR 2024</title></head>
        <body>
        <div id="content">
            <h3>Papers</h3>
            <dl>
                <dt class="ptitle"><br><a href="/content/CVPR2024/html/Test_Paper_Title_CVPR_2024_paper.html">Test Paper Title for Computer Vision</a></dt>
                <dd>
                    <form id="form-Author1" action="/CVPR2024" method="post" class="authsearch">
                        <input type="hidden" name="query_author" value="Author One">
                        <a href="#" onclick="document.getElementById('form-Author1').submit();">Author One</a>,
                    </form>
                    <form id="form-Author2" action="/CVPR2024" method="post" class="authsearch">
                        <input type="hidden" name="query_author" value="Author Two">
                        <a href="#" onclick="document.getElementById('form-Author2').submit();">Author Two</a>
                    </form>
                </dd>
                <dd>
                    [<a href="/content/CVPR2024/papers/Test_Paper_Title_CVPR_2024_paper.pdf">pdf</a>]
                    [<a href="/content/CVPR2024/supplemental/Test_Paper_CVPR_2024_supplemental.pdf">supp</a>]
                </dd>
                
                <dt class="ptitle"><br><a href="/content/CVPR2024/html/Another_Paper_CVPR_2024_paper.html">Another Paper Title</a></dt>
                <dd>
                    <form id="form-AuthorX" action="/CVPR2024" method="post" class="authsearch">
                        <input type="hidden" name="query_author" value="Author X">
                        <a href="#" onclick="document.getElementById('form-AuthorX').submit();">Author X</a>
                    </form>
                </dd>
                <dd>
                    [<a href="/content/CVPR2024/papers/Another_Paper_CVPR_2024_paper.pdf">pdf</a>]
                </dd>
            </dl>
        </div>
        </body>
        </html>
        '''