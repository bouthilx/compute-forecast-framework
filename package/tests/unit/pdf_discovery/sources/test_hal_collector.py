"""Unit tests for HAL OAI-PMH collector."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import xml.etree.ElementTree as ET

from src.data.models import Paper, Author
from src.pdf_discovery.sources.hal_collector import HALPDFCollector
from src.pdf_discovery.core.models import PDFRecord
from src.pdf_discovery.utils import APIError, NoResultsError, NoPDFFoundError


class TestHALPDFCollector:
    """Tests for HAL PDF collector."""
    
    @pytest.fixture
    def collector(self):
        """Create a HAL collector instance."""
        return HALPDFCollector()
    
    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper for testing."""
        return Paper(
            paper_id="test_paper_1",
            title="Test Paper on Deep Learning",
            authors=[Author(name="Author A"), Author(name="Author B")],
            year=2023,
            doi="10.1234/test.2023.001",
            venue="Test Conference",
            citations=50
        )
    
    @pytest.fixture
    def hal_oai_response(self):
        """Mock HAL OAI-PMH response with PDF URL."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <responseDate>2023-12-01T12:00:00Z</responseDate>
            <request verb="GetRecord">https://api.archives-ouvertes.fr/oai/hal</request>
            <GetRecord>
                <record>
                    <header>
                        <identifier>oai:HAL:hal-03456789v1</identifier>
                        <datestamp>2023-01-01</datestamp>
                    </header>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Test Paper on Deep Learning</dc:title>
                            <dc:creator>Author A</dc:creator>
                            <dc:creator>Author B</dc:creator>
                            <dc:identifier>https://hal.science/hal-03456789/document</dc:identifier>
                            <dc:identifier>https://hal.science/hal-03456789/file/paper.pdf</dc:identifier>
                            <dc:identifier>10.1234/test.2023.001</dc:identifier>
                            <dc:date>2023</dc:date>
                            <dc:type>info:eu-repo/semantics/article</dc:type>
                            <dc:language>en</dc:language>
                            <dc:rights>info:eu-repo/semantics/openAccess</dc:rights>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </GetRecord>
        </OAI-PMH>"""
    
    @pytest.fixture
    def hal_search_response(self):
        """Mock HAL search API response."""
        return {
            "response": {
                "numFound": 1,
                "docs": [{
                    "docid": "hal-03456789",
                    "title_s": ["Test Paper on Deep Learning"],
                    "authFullName_s": ["Author A", "Author B"],
                    "files_s": [
                        "https://hal.science/hal-03456789/document",
                        "https://hal.science/hal-03456789/file/paper.pdf"
                    ],
                    "doiId_s": "10.1234/test.2023.001",
                    "publicationDate_s": "2023",
                    "openAccess_bool": True
                }]
            }
        }
    
    def test_discover_single_success_oai(self, collector, sample_paper, hal_oai_response):
        """Test successful PDF discovery from HAL via OAI-PMH."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = hal_oai_response
            mock_response.content = hal_oai_response.encode('utf-8')
            mock_get.return_value = mock_response
            
            result = collector._discover_single(sample_paper)
            
            assert isinstance(result, PDFRecord)
            assert result.paper_id == sample_paper.paper_id
            assert result.pdf_url == "https://hal.science/hal-03456789/file/paper.pdf"
            assert result.source == "hal"
            assert result.confidence_score == 0.85
            assert result.validation_status == "verified"
            assert result.license == "open_access"
    
    def test_discover_single_success_search_api(self, collector, sample_paper, hal_search_response):
        """Test successful PDF discovery from HAL via Search API."""
        with patch('requests.get') as mock_get:
            # First call fails with OAI-PMH
            oai_response = Mock()
            oai_response.status_code = 200
            oai_response.text = """<?xml version="1.0" encoding="UTF-8"?>
            <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
                <error code="noRecordsMatch">No matching records</error>
            </OAI-PMH>"""
            
            # Second call succeeds with Search API
            search_response = Mock()
            search_response.status_code = 200
            search_response.json.return_value = hal_search_response
            
            mock_get.side_effect = [oai_response, search_response]
            
            result = collector._discover_single(sample_paper)
            
            assert result.pdf_url == "https://hal.science/hal-03456789/file/paper.pdf"
            assert result.source == "hal"
    
    def test_discover_single_no_pdf(self, collector, sample_paper):
        """Test when HAL has no PDF available."""
        response_no_pdf = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <GetRecord>
                <record>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Test Paper on Deep Learning</dc:title>
                            <dc:identifier>10.1234/test.2023.001</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </GetRecord>
        </OAI-PMH>"""
        
        search_response_no_pdf = {
            "response": {
                "numFound": 1,
                "docs": [{
                    "docid": "hal-03456789",
                    "title_s": ["Test Paper on Deep Learning"],
                    "files_s": [],  # No PDF files
                    "doiId_s": "10.1234/test.2023.001"
                }]
            }
        }
        
        with patch('requests.get') as mock_get:
            # First OAI response has no PDF
            oai_response = Mock()
            oai_response.status_code = 200
            oai_response.text = response_no_pdf
            oai_response.content = response_no_pdf.encode('utf-8')
            
            # Search API response also has no PDF
            search_response = Mock()
            search_response.status_code = 200
            search_response.json.return_value = search_response_no_pdf
            
            mock_get.side_effect = [oai_response, search_response]
            
            with pytest.raises(NoPDFFoundError, match="No PDF found"):
                collector._discover_single(sample_paper)
    
    def test_discover_single_no_results(self, collector, sample_paper):
        """Test when HAL returns no results."""
        error_response = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <error code="noRecordsMatch">No matching records</error>
        </OAI-PMH>"""
        
        with patch('requests.get') as mock_get:
            # Both OAI and Search API return no results
            oai_response = Mock()
            oai_response.status_code = 200
            oai_response.text = error_response
            
            search_response = Mock()
            search_response.status_code = 200
            search_response.json.return_value = {"response": {"numFound": 0, "docs": []}}
            
            mock_get.side_effect = [oai_response, search_response]
            
            with pytest.raises(NoResultsError, match="No results found"):
                collector._discover_single(sample_paper)
    
    def test_extract_pdf_url_from_identifiers(self, collector):
        """Test PDF URL extraction from various identifier formats."""
        # Test with multiple identifiers
        identifiers = [
            "https://hal.science/hal-03456789",
            "https://hal.science/hal-03456789/document",
            "https://hal.science/hal-03456789/file/paper.pdf",
            "10.1234/test.2023.001"
        ]
        
        pdf_url = collector._extract_pdf_url_from_identifiers(identifiers)
        assert pdf_url == "https://hal.science/hal-03456789/file/paper.pdf"
        
        # Test with only document URL
        identifiers = [
            "https://hal.science/hal-03456789",
            "https://hal.science/hal-03456789/document"
        ]
        
        pdf_url = collector._extract_pdf_url_from_identifiers(identifiers)
        assert pdf_url == "https://hal.science/hal-03456789/document"
        
        # Test with no valid URLs
        identifiers = ["10.1234/test.2023.001"]
        
        pdf_url = collector._extract_pdf_url_from_identifiers(identifiers)
        assert pdf_url is None
    
    def test_rate_limiting(self, collector, sample_paper, hal_oai_response):
        """Test that rate limiting is applied."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = hal_oai_response
            mock_response.content = hal_oai_response.encode('utf-8')
            mock_get.return_value = mock_response
            
            # Make multiple requests
            with patch('time.sleep') as mock_sleep:
                collector._discover_single(sample_paper)
                collector._discover_single(sample_paper)
                
                # Verify rate limiter was called
                assert mock_sleep.called
    
    def test_build_oai_identifier(self, collector, sample_paper):
        """Test OAI identifier construction."""
        # With DOI
        identifier = collector._build_oai_identifier(sample_paper)
        assert identifier == "oai:HAL:10.1234/test.2023.001"
        
        # Without DOI but with HAL ID in URLs
        paper_with_hal_url = Paper(
            paper_id="test2",
            title="Test",
            urls=["https://hal.science/hal-12345678"],
            authors=[Author(name="Test Author")],
            venue="Test Venue",
            year=2023,
            citations=0
        )
        identifier = collector._build_oai_identifier(paper_with_hal_url)
        assert identifier == "oai:HAL:hal-12345678v1"
    
    def test_parse_oai_response_error_handling(self, collector):
        """Test OAI-PMH response parsing with errors."""
        # Test malformed XML
        with pytest.raises(ET.ParseError):
            collector._parse_oai_response("<invalid xml")
        
        # Test OAI error response
        error_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <error code="badArgument">Invalid request</error>
        </OAI-PMH>"""
        
        root = ET.fromstring(error_xml)
        with pytest.raises(APIError, match="OAI-PMH error"):
            collector._parse_oai_response(error_xml)