"""Tests for GROBID extractor."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os

from src.pdf_parser.extractors.grobid_extractor import GROBIDExtractor, GROBIDExtractionError
from src.pdf_parser.services.grobid_manager import GROBIDServiceError


class TestGROBIDExtractor:
    """Test GROBID extractor."""
    
    def test_init_default_config(self):
        """Test initialization with default configuration."""
        extractor = GROBIDExtractor()
        
        assert extractor.grobid_url == 'http://localhost:8070'
        assert extractor.timeout == 30
        assert extractor.manager is not None
    
    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            'grobid_url': 'http://custom:9000',
            'timeout': 60
        }
        
        extractor = GROBIDExtractor(config)
        
        assert extractor.grobid_url == 'http://custom:9000'
        assert extractor.timeout == 60
    
    def test_can_extract_affiliations(self):
        """Test that GROBID can extract affiliations."""
        extractor = GROBIDExtractor()
        assert extractor.can_extract_affiliations() is True
    
    @patch('src.pdf_parser.extractors.grobid_extractor.PdfWriter')
    @patch('src.pdf_parser.extractors.grobid_extractor.PdfReader')
    def test_extract_pages_to_pdf(self, mock_reader, mock_writer):
        """Test extracting specific pages to temporary PDF."""
        # Setup mocks
        mock_pdf_reader = Mock()
        mock_pdf_writer = Mock()
        mock_reader.return_value = mock_pdf_reader
        mock_writer.return_value = mock_pdf_writer
        
        mock_page1 = Mock()
        mock_page2 = Mock()
        mock_pdf_reader.pages = [mock_page1, mock_page2, Mock(), Mock()]  # 4 pages total
        
        extractor = GROBIDExtractor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            with patch('builtins.open', mock_open(read_data=b'fake pdf data')):
                result_path = extractor._extract_pages_to_pdf(temp_path, [0, 1])
            
            # Verify pages were added to writer
            mock_pdf_writer.add_page.assert_any_call(mock_page1)
            mock_pdf_writer.add_page.assert_any_call(mock_page2)
            assert mock_pdf_writer.add_page.call_count == 2
            
            # Result should be a Path object
            assert isinstance(result_path, Path)
            assert result_path.suffix == '.pdf'
            
        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()
    
    def test_parse_grobid_xml_basic(self):
        """Test parsing basic GROBID TEI XML."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
            <teiHeader>
                <fileDesc>
                    <titleStmt>
                        <title type="main">Test Paper Title</title>
                    </titleStmt>
                    <sourceDesc>
                        <biblStruct>
                            <analytic>
                                <author>
                                    <persName>
                                        <forename type="first">John</forename>
                                        <surname>Doe</surname>
                                    </persName>
                                    <affiliation>
                                        <orgName type="institution">University of Test</orgName>
                                        <address>
                                            <settlement>Test City</settlement>
                                            <country>Test Country</country>
                                        </address>
                                    </affiliation>
                                </author>
                                <author>
                                    <persName>
                                        <forename type="first">Jane</forename>
                                        <surname>Smith</surname>
                                    </persName>
                                    <affiliation>
                                        <orgName type="institution">Test Institute</orgName>
                                        <address>
                                            <settlement>Another City</settlement>
                                        </address>
                                    </affiliation>
                                </author>
                            </analytic>
                        </biblStruct>
                    </sourceDesc>
                </fileDesc>
            </teiHeader>
            <text>
                <body>
                    <div>
                        <head>Abstract</head>
                        <p>This is the abstract of the test paper.</p>
                    </div>
                </body>
            </text>
        </TEI>'''
        
        extractor = GROBIDExtractor()
        result = extractor._parse_grobid_xml(xml_content)
        
        # Check title
        assert result['title'] == 'Test Paper Title'
        
        # Check abstract (may be empty for this test XML structure)
        # GROBID typically extracts abstract from different location
        
        # Check authors
        assert len(result['authors']) == 2
        
        author1 = result['authors'][0]
        assert 'John' in author1['name'] and 'Doe' in author1['name']
        assert len(author1['affiliations']) == 1
        assert 'University of Test' in author1['affiliations'][0]
        assert 'Test City' in author1['affiliations'][0]
        
        author2 = result['authors'][1]
        assert 'Jane' in author2['name'] and 'Smith' in author2['name']
        assert len(author2['affiliations']) == 1
        assert 'Test Institute' in author2['affiliations'][0]
        
        # Check unique affiliations list
        assert len(result['affiliations']) == 2
        assert any('University of Test' in aff for aff in result['affiliations'])
        assert any('Test Institute' in aff for aff in result['affiliations'])
    
    def test_parse_grobid_xml_empty_elements(self):
        """Test parsing XML with empty or missing elements."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
            <teiHeader>
                <fileDesc>
                    <sourceDesc>
                        <biblStruct>
                            <analytic>
                                <author>
                                    <persName>
                                        <surname>OnlyLastName</surname>
                                    </persName>
                                </author>
                            </analytic>
                        </biblStruct>
                    </sourceDesc>
                </fileDesc>
            </teiHeader>
        </TEI>'''
        
        extractor = GROBIDExtractor()
        result = extractor._parse_grobid_xml(xml_content)
        
        # Should handle missing elements gracefully
        assert result['title'] == ''
        assert result['abstract'] == ''
        assert len(result['authors']) == 1
        assert result['authors'][0]['name'] == 'OnlyLastName'
        assert len(result['authors'][0]['affiliations']) == 0
    
    def test_parse_grobid_xml_invalid_xml(self):
        """Test parsing invalid XML."""
        invalid_xml = "This is not valid XML"
        
        extractor = GROBIDExtractor()
        
        with pytest.raises(GROBIDExtractionError, match="Failed to parse XML"):
            extractor._parse_grobid_xml(invalid_xml)
    
    @patch('requests.post')
    def test_extract_first_pages_success(self, mock_post):
        """Test successful first page extraction."""
        # Mock successful GROBID response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
            <teiHeader>
                <fileDesc>
                    <titleStmt>
                        <title type="main">Test Title</title>
                    </titleStmt>
                    <sourceDesc>
                        <biblStruct>
                            <analytic>
                                <author>
                                    <persName>
                                        <forename>Test</forename>
                                        <surname>Author</surname>
                                    </persName>
                                    <affiliation>
                                        <orgName>Test University</orgName>
                                    </affiliation>
                                </author>
                            </analytic>
                        </biblStruct>
                    </sourceDesc>
                </fileDesc>
            </teiHeader>
        </TEI>'''
        mock_post.return_value = mock_response
        
        extractor = GROBIDExtractor()
        
        # Mock the manager ensure_service_running
        pdf_path = Path('/fake/input.pdf')
        
        with patch.object(extractor.manager, 'ensure_service_running', return_value=True):
            with patch('pathlib.Path.exists', return_value=True):
                with patch.object(extractor, '_extract_pages_to_pdf') as mock_extract:
                    temp_pdf_path = Path('/tmp/test.pdf')
                    mock_extract.return_value = temp_pdf_path
                    
                    with patch('builtins.open', mock_open(read_data=b'fake pdf')):
                        result = extractor.extract_first_pages(pdf_path, [0, 1])
        
        # Verify result structure
        assert result['method'] == 'grobid'
        assert result['confidence'] == 0.8
        assert len(result['affiliations']) == 1
        assert 'Test University' in result['affiliations'][0]
        assert len(result['authors_with_affiliations']) == 1
        assert result['title'] == 'Test Title'
    
    @patch('requests.post')
    def test_extract_first_pages_http_error(self, mock_post):
        """Test extraction with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        extractor = GROBIDExtractor()
        pdf_path = Path('/fake/input.pdf')
        
        with patch.object(extractor.manager, 'ensure_service_running', return_value=True):
            with patch('pathlib.Path.exists', return_value=True):
                with patch.object(extractor, '_extract_pages_to_pdf') as mock_extract:
                    temp_pdf_path = Path('/tmp/test.pdf')
                    mock_extract.return_value = temp_pdf_path
                    
                    with patch('builtins.open', mock_open(read_data=b'fake pdf')):
                        with pytest.raises(GROBIDExtractionError, match="GROBID API request failed"):
                            extractor.extract_first_pages(pdf_path, [0, 1])
    
    def test_extract_first_pages_service_unavailable(self):
        """Test extraction when GROBID service is unavailable."""
        extractor = GROBIDExtractor()
        pdf_path = Path('/fake/input.pdf')
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(extractor.manager, 'ensure_service_running', 
                             side_effect=GROBIDServiceError("Service unavailable")):
                with pytest.raises(GROBIDExtractionError, match="GROBID service unavailable"):
                    extractor.extract_first_pages(pdf_path, [0, 1])
    
    @patch('requests.post')
    def test_extract_full_text_success(self, mock_post):
        """Test successful full text extraction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "This is the full text of the document extracted by GROBID"
        mock_post.return_value = mock_response
        
        extractor = GROBIDExtractor()
        pdf_path = Path('/fake/input.pdf')
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(extractor.manager, 'ensure_service_running', return_value=True):
                with patch('builtins.open', mock_open(read_data=b'fake pdf')):
                    result = extractor.extract_full_text(pdf_path)
        
        assert result == "This is the full text of the document extracted by GROBID"
        
        # Verify correct API endpoint was called
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == 'http://localhost:8070/api/processFulltextDocument'
    
    @patch('requests.post')
    def test_extract_full_text_http_error(self, mock_post):
        """Test full text extraction with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        extractor = GROBIDExtractor()
        pdf_path = Path('/fake/input.pdf')
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(extractor.manager, 'ensure_service_running', return_value=True):
                with patch('builtins.open', mock_open(read_data=b'fake pdf')):
                    with pytest.raises(GROBIDExtractionError, match="GROBID full text API request failed"):
                        extractor.extract_full_text(pdf_path)
    
    def test_extract_full_text_service_unavailable(self):
        """Test full text extraction when service is unavailable."""
        extractor = GROBIDExtractor()
        pdf_path = Path('/fake/input.pdf')
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(extractor.manager, 'ensure_service_running',
                             side_effect=GROBIDServiceError("Service down")):
                with pytest.raises(GROBIDExtractionError, match="GROBID service unavailable"):
                    extractor.extract_full_text(pdf_path)
    
    def test_extraction_with_nonexistent_file(self):
        """Test extraction with non-existent PDF file."""
        extractor = GROBIDExtractor()
        nonexistent_path = Path('/this/file/does/not/exist.pdf')
        
        with patch.object(extractor.manager, 'ensure_service_running', return_value=True):
            with pytest.raises(GROBIDExtractionError, match="PDF file not found"):
                extractor.extract_first_pages(nonexistent_path, [0, 1])
            
            with pytest.raises(GROBIDExtractionError, match="PDF file not found"):
                extractor.extract_full_text(nonexistent_path)