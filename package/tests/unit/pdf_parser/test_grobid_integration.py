"""Integration tests for GROBID extractor with PDF processor framework."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.extractors.grobid_extractor import GROBIDExtractor
from src.pdf_parser.services.grobid_manager import GROBIDServiceError


class TestGROBIDIntegration:
    """Test GROBID extractor integration with PDF processor framework."""
    
    def test_grobid_extractor_registration(self):
        """Test registering GROBID extractor with processor."""
        processor = OptimizedPDFProcessor({})
        extractor = GROBIDExtractor()
        
        # Register extractor
        processor.register_extractor('grobid', extractor, level=1)
        
        # Verify registration
        assert 'grobid' in processor.extractors
        assert processor.extractors['grobid']['extractor'] == extractor
        assert processor.extractors['grobid']['level'] == 1
    
    def test_grobid_extractor_can_extract_affiliations(self):
        """Test that GROBID extractor is suitable for affiliation extraction."""
        processor = OptimizedPDFProcessor({})
        extractor = GROBIDExtractor()
        
        processor.register_extractor('grobid', extractor, level=1)
        
        # Should be included in suitable extractors
        suitable_extractors = [
            (info['level'], name, info['extractor'])
            for name, info in processor.extractors.items()
            if info['extractor'].can_extract_affiliations()
        ]
        
        assert len(suitable_extractors) == 1
        assert suitable_extractors[0][1] == 'grobid'
    
    @patch('requests.post')
    def test_processor_uses_grobid_for_affiliations(self, mock_post):
        """Test that processor successfully uses GROBID for affiliation extraction."""
        # Mock GROBID response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
            <teiHeader>
                <fileDesc>
                    <titleStmt>
                        <title type="main">Test Paper</title>
                    </titleStmt>
                    <sourceDesc>
                        <biblStruct>
                            <analytic>
                                <author>
                                    <persName>
                                        <forename>John</forename>
                                        <surname>Doe</surname>
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
        
        processor = OptimizedPDFProcessor({})
        extractor = GROBIDExtractor()
        
        processor.register_extractor('grobid', extractor, level=1)
        
        pdf_path = Path('/fake/test.pdf')
        metadata = {'title': 'Test Paper', 'authors': ['John Doe']}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(extractor.manager, 'ensure_service_running', return_value=True):
                with patch.object(extractor, '_extract_pages_to_pdf') as mock_extract:
                    mock_extract.return_value = Path('/tmp/test.pdf')
                    
                    with patch('builtins.open'):
                        result = processor._extract_affiliations(pdf_path, metadata)
        
        # Verify result structure
        assert result['method'] == 'grobid'
        assert result['confidence'] == 0.8
        assert len(result['affiliations']) == 1
        assert result['affiliations'][0]['name'] == 'Test University'
    
    def test_processor_fallback_when_grobid_fails(self):
        """Test processor fallback behavior when GROBID service fails."""
        processor = OptimizedPDFProcessor({})
        
        # Create mock fallback extractor
        fallback_extractor = Mock()
        fallback_extractor.can_extract_affiliations.return_value = True
        fallback_extractor.extract_first_pages.return_value = {
            'affiliations': ['Fallback University'],
            'method': 'fallback',
            'confidence': 0.6
        }
        
        # Register GROBID (will fail) and fallback extractor
        grobid_extractor = GROBIDExtractor()
        processor.register_extractor('grobid', grobid_extractor, level=1)
        processor.register_extractor('fallback', fallback_extractor, level=2)
        
        pdf_path = Path('/fake/test.pdf')
        metadata = {'title': 'Test Paper'}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(grobid_extractor.manager, 'ensure_service_running',
                             side_effect=GROBIDServiceError("Service down")):
                # Mock validation to accept fallback result
                with patch.object(processor.validator, 'validate_affiliations', return_value=True):
                    result = processor._extract_affiliations(pdf_path, metadata)
        
        # Should use fallback extractor
        assert result['method'] == 'fallback'
        assert 'Fallback University' in result['affiliations']
    
    def test_cost_tracking_integration(self):
        """Test that GROBID costs are properly tracked in processor."""
        processor = OptimizedPDFProcessor({})
        extractor = GROBIDExtractor()
        
        processor.register_extractor('grobid', extractor, level=1)
        
        pdf_path = Path('/fake/test.pdf')
        metadata = {'title': 'Test Paper'}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(extractor.manager, 'ensure_service_running', return_value=True):
                with patch.object(extractor, 'extract_first_pages') as mock_extract:
                    mock_extract.return_value = {
                        'affiliations': ['Test University'],
                        'method': 'grobid',
                        'confidence': 0.8
                    }
                    
                    with patch.object(processor.validator, 'validate_affiliations', return_value=True):
                        processor._extract_affiliations(pdf_path, metadata)
        
        # Check cost tracking
        cost_summary = processor.get_cost_summary()
        assert 'grobid' in cost_summary['by_extractor']
        assert cost_summary['by_extractor']['grobid'] == 0.0  # GROBID is free
        assert 'affiliation_extraction' in cost_summary['by_operation']
    
    def test_grobid_priority_over_other_extractors(self):
        """Test that GROBID is prioritized when multiple extractors are available."""
        processor = OptimizedPDFProcessor({})
        
        # Create multiple extractors
        grobid_extractor = Mock()
        grobid_extractor.can_extract_affiliations.return_value = True
        grobid_extractor.extract_first_pages.return_value = {
            'affiliations': ['GROBID University'],
            'method': 'grobid',
            'confidence': 0.8
        }
        
        other_extractor = Mock()
        other_extractor.can_extract_affiliations.return_value = True
        other_extractor.extract_first_pages.return_value = {
            'affiliations': ['Other University'],
            'method': 'other',
            'confidence': 0.7
        }
        
        # Register with GROBID at higher priority (lower level number)
        processor.register_extractor('grobid', grobid_extractor, level=1)
        processor.register_extractor('other', other_extractor, level=2)
        
        pdf_path = Path('/fake/test.pdf')
        metadata = {'title': 'Test Paper'}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(processor.validator, 'validate_affiliations', return_value=True):
                result = processor._extract_affiliations(pdf_path, metadata)
        
        # Should use GROBID (higher priority)
        assert result['method'] == 'grobid'
        assert 'GROBID University' in result['affiliations']
        
        # Other extractor should not be called
        other_extractor.extract_first_pages.assert_not_called()
    
    @patch('requests.post')
    def test_end_to_end_pdf_processing_with_grobid(self, mock_post):
        """Test end-to-end PDF processing using GROBID."""
        # Mock GROBID responses
        header_response = Mock()
        header_response.status_code = 200
        header_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
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
                                        <forename>Jane</forename>
                                        <surname>Smith</surname>
                                    </persName>
                                    <affiliation>
                                        <orgName>Research Institute</orgName>
                                    </affiliation>
                                </author>
                            </analytic>
                        </biblStruct>
                    </sourceDesc>
                </fileDesc>
            </teiHeader>
        </TEI>'''
        
        fulltext_response = Mock()
        fulltext_response.status_code = 200
        fulltext_response.text = "Full text of the paper with GPU training and computational requirements."
        
        # Configure mock to return different responses for different endpoints
        def mock_post_side_effect(url, **kwargs):
            if 'processHeaderDocument' in url:
                return header_response
            elif 'processFulltextDocument' in url:
                return fulltext_response
            return Mock()
        
        mock_post.side_effect = mock_post_side_effect
        
        processor = OptimizedPDFProcessor({})
        extractor = GROBIDExtractor()
        processor.register_extractor('grobid', extractor, level=1)
        
        pdf_path = Path('/fake/research_paper.pdf')
        metadata = {
            'title': 'Test Paper Title',
            'authors': ['Jane Smith']
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(extractor.manager, 'ensure_service_running', return_value=True):
                with patch.object(extractor, '_extract_pages_to_pdf') as mock_extract:
                    mock_extract.return_value = Path('/tmp/test.pdf')
                    
                    with patch('builtins.open'):
                        result = processor.process_pdf(pdf_path, metadata)
        
        # Verify complete result structure
        assert result['method'] == 'grobid'
        assert result['confidence'] == 0.8
        assert len(result['affiliations']) == 1
        assert result['affiliations'][0]['name'] == 'Research Institute'
        assert 'GPU training' in result['full_text']
        assert result['computational_specs']['has_computational_content'] is True
        assert 'extraction_timestamp' in result