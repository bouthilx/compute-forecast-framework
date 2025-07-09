"""Tests for AAAI adapter using OAI-PMH protocol."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import xml.etree.ElementTree as ET

from compute_forecast.data.sources.scrapers.paperoni_adapters.aaai import AAAIAdapter
from compute_forecast.data.sources.scrapers.models import SimplePaper


class TestAAAIAdapter:
    """Test AAAI adapter functionality."""
    
    @pytest.fixture
    def adapter(self):
        """Create an AAAI adapter instance."""
        return AAAIAdapter()
    
    def test_get_supported_venues(self, adapter):
        """Test that adapter returns supported AAAI venues."""
        venues = adapter.get_supported_venues()
        
        assert "aaai" in venues
        assert "aies" in venues  # AI, Ethics, and Society
        assert "hcomp" in venues  # Human Computation and Crowdsourcing
        assert "icwsm" in venues  # Web and Social Media
        assert len(venues) >= 4
    
    def test_get_available_years(self, adapter):
        """Test available years for different venues."""
        current_year = datetime.now().year
        
        # AAAI - oldest conference (1980)
        aaai_years = adapter.get_available_years("aaai")
        assert 1980 in aaai_years
        assert current_year in aaai_years
        assert len(aaai_years) > 40
        
        # AIES - started 2018
        aies_years = adapter.get_available_years("aies")
        assert min(aies_years) == 2018
        assert current_year in aies_years
        
        # HCOMP - started 2013
        hcomp_years = adapter.get_available_years("hcomp")
        assert min(hcomp_years) == 2013
        assert current_year in hcomp_years
        
        # ICWSM - started 2007
        icwsm_years = adapter.get_available_years("icwsm")
        assert min(icwsm_years) == 2007
        assert current_year in icwsm_years
        
        # Unknown venue
        unknown_years = adapter.get_available_years("unknown")
        assert unknown_years == []
    
    def test_venue_to_journal_mapping(self, adapter):
        """Test that venues map correctly to OJS journal names."""
        assert adapter._get_journal_name("aaai") == "AAAI"
        assert adapter._get_journal_name("aies") == "AIES"
        assert adapter._get_journal_name("hcomp") == "HCOMP"
        assert adapter._get_journal_name("icwsm") == "ICWSM"
        assert adapter._get_journal_name("unknown") is None
    
    def test_create_paperoni_scraper(self, adapter):
        """Test creation of OAI-PMH client."""
        client = adapter._create_paperoni_scraper()
        
        assert client is not None
        # Should configure session with proper headers
        assert 'User-Agent' in adapter.session.headers
        assert 'Accept' in adapter.session.headers
    
    def test_parse_oai_record_success(self, adapter):
        """Test parsing of OAI-PMH record."""
        # Mock OAI-PMH XML response with proper namespaces
        xml_response = """<?xml version="1.0"?>
        <record xmlns="http://www.openarchives.org/OAI/2.0/" 
                xmlns:oai="http://www.openarchives.org/OAI/2.0/"
                xmlns:dc="http://purl.org/dc/elements/1.1/">
            <header>
                <identifier>oai:ojs.aaai.org:article/32043</identifier>
                <datestamp>2025-04-11T09:18:53Z</datestamp>
            </header>
            <metadata>
                <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/">
                    <dc:title>GoBERT: Gene Ontology Graph Informed BERT</dc:title>
                    <dc:creator>Miao, Yuwei</dc:creator>
                    <dc:creator>Guo, Yuzhi</dc:creator>
                    <dc:description>Abstract text here</dc:description>
                    <dc:date>2025-04-11</dc:date>
                    <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/32043</dc:identifier>
                    <dc:identifier>10.1609/aaai.v39i1.32043</dc:identifier>
                    <dc:relation>https://ojs.aaai.org/index.php/AAAI/article/view/32043/34198</dc:relation>
                    <dc:source>Proceedings of the AAAI Conference on Artificial Intelligence; Vol. 39 No. 1</dc:source>
                </oai_dc:dc>
            </metadata>
        </record>"""
        
        root = ET.fromstring(xml_response)
        paper = adapter._parse_oai_record(root, "aaai", 2025)
        
        assert paper is not None
        assert paper.title == "GoBERT: Gene Ontology Graph Informed BERT"
        assert paper.authors == ["Miao, Yuwei", "Guo, Yuzhi"]
        assert paper.venue == "AAAI"
        assert paper.year == 2025
        assert paper.abstract == "Abstract text here"
        assert paper.doi == "10.1609/aaai.v39i1.32043"
        assert paper.paper_id == "32043"
        assert paper.source_url == "https://ojs.aaai.org/index.php/AAAI/article/view/32043"
        assert paper.pdf_urls == ["https://ojs.aaai.org/index.php/AAAI/article/view/32043/34198"]
    
    def test_call_paperoni_scraper_success(self, adapter):
        """Test successful paper collection from OAI-PMH."""
        # Mock XML response
        xml_response = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <responseDate>2025-01-09T19:25:52Z</responseDate>
            <request verb="ListRecords">https://ojs.aaai.org/index.php/AAAI/oai</request>
            <ListRecords>
                <record>
                    <header>
                        <identifier>oai:ojs.aaai.org:article/32043</identifier>
                    </header>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Test Paper Title</dc:title>
                            <dc:creator>Author One</dc:creator>
                            <dc:date>2024-01-01</dc:date>
                            <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/32043</dc:identifier>
                            <dc:identifier>10.1609/aaai.v38i1.32043</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </ListRecords>
        </OAI-PMH>"""
        
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response
        
        with patch.object(adapter.session, 'get', return_value=mock_response):
            papers = adapter._call_paperoni_scraper(None, "aaai", 2024)
        
        assert len(papers) == 1
        paper = papers[0]
        
        assert isinstance(paper, SimplePaper)
        assert paper.title == "Test Paper Title"
        assert paper.authors == ["Author One"]
        assert paper.venue == "AAAI"
        assert paper.year == 2024
    
    def test_call_paperoni_scraper_with_date_filtering(self, adapter):
        """Test that date filtering is applied correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords></ListRecords>
        </OAI-PMH>"""
        
        with patch.object(adapter.session, 'get', return_value=mock_response) as mock_get:
            adapter._call_paperoni_scraper(None, "aaai", 2023)
            
            # Check that the request included date filtering
            args, kwargs = mock_get.call_args
            assert 'params' in kwargs
            assert 'from' in kwargs['params']
            assert 'until' in kwargs['params']
            assert kwargs['params']['from'] == '2023-01-01'
            assert kwargs['params']['until'] == '2023-12-31'
    
    def test_call_paperoni_scraper_empty_results(self, adapter):
        """Test handling of empty results."""
        xml_response = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords></ListRecords>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response
        
        with patch.object(adapter.session, 'get', return_value=mock_response):
            papers = adapter._call_paperoni_scraper(None, "aaai", 2024)
        
        assert papers == []
    
    def test_call_paperoni_scraper_api_error(self, adapter):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch.object(adapter.session, 'get', return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                adapter._call_paperoni_scraper(None, "aaai", 2024)
        
        assert "OAI-PMH error" in str(exc_info.value)
    
    def test_call_paperoni_scraper_invalid_venue(self, adapter):
        """Test handling of invalid venue."""
        papers = adapter._call_paperoni_scraper(None, "invalid-venue", 2024)
        assert papers == []
    
    def test_pagination_handling(self, adapter):
        """Test that adapter handles pagination correctly."""
        # First response with resumption token
        xml_response_1 = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords>
                <record>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Paper 1</dc:title>
                            <dc:creator>Author 1</dc:creator>
                            <dc:date>2024-01-01</dc:date>
                            <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/1</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
                <resumptionToken>token123</resumptionToken>
            </ListRecords>
        </OAI-PMH>"""
        
        # Second response without resumption token
        xml_response_2 = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords>
                <record>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Paper 2</dc:title>
                            <dc:creator>Author 2</dc:creator>
                            <dc:date>2024-01-01</dc:date>
                            <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/2</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </ListRecords>
        </OAI-PMH>"""
        
        # Set batch size to allow multiple requests
        adapter.config.batch_size = 10
        
        # Mock responses
        mock_responses = [
            Mock(status_code=200, text=xml_response_1),
            Mock(status_code=200, text=xml_response_2)
        ]
        
        with patch.object(adapter.session, 'get', side_effect=mock_responses):
            papers = adapter._call_paperoni_scraper(None, "aaai", 2024)
        
        assert len(papers) == 2
        assert papers[0].title == "Paper 1"
        assert papers[1].title == "Paper 2"
    
    def test_extract_article_id(self, adapter):
        """Test extraction of article ID from OAI identifier."""
        assert adapter._extract_article_id("oai:ojs.aaai.org:article/32043") == "32043"
        assert adapter._extract_article_id("oai:ojs.aaai.org:article/1234") == "1234"
        assert adapter._extract_article_id("invalid-format") is None