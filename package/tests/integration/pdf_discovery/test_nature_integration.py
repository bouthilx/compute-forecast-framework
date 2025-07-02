"""Integration tests for Nature PDF collector."""

import pytest
from unittest.mock import patch, Mock

from src.pdf_discovery.sources.nature_collector import NaturePDFCollector
from src.data.models import Paper, Author


@pytest.mark.integration
class TestNatureIntegration:
    """Integration tests for Nature PDF collector."""
    
    @pytest.fixture
    def collector(self):
        """Create a Nature collector instance with test email."""
        return NaturePDFCollector(email="test@academic.edu")
    
    @pytest.fixture
    def real_nature_comms_paper(self):
        """A real Nature Communications paper that might be open access."""
        return Paper(
            title="Global warming of 1.5°C",
            authors=[Author(name="Masson-Delmotte, V.")],
            venue="Nature Communications",
            year=2018,
            citations=100,
            paper_id="nature_comms_test",
            doi="10.1038/s41558-018-0091-3"  # Example Nature Climate Change paper
        )
    
    @pytest.fixture
    def real_sci_reports_paper(self):
        """A real Scientific Reports paper (typically open access)."""
        return Paper(
            title="A global map of travel time to cities to assess inequalities in accessibility in 2015",
            authors=[Author(name="Weiss, D. J.")],
            venue="Scientific Reports", 
            year=2018,
            citations=50,
            paper_id="sci_reports_test",
            doi="10.1038/nature25181"  # Example Nature paper
        )
    
    @pytest.mark.skip(reason="Integration tests disabled by default")
    def test_real_nature_discovery(self, collector, real_nature_comms_paper):
        """Test actual discovery against Nature website (when enabled)."""
        try:
            pdf_record = collector._discover_single(real_nature_comms_paper)
            
            # If we get here, we found a PDF
            assert pdf_record.paper_id == "nature_comms_test"
            assert pdf_record.source in ["nature", "nature_via_doi"]
            assert pdf_record.pdf_url is not None
            assert pdf_record.confidence_score > 0.7
            
        except Exception as e:
            # This is expected if the paper is not open access
            assert "No open access PDF found" in str(e)
    
    def test_nature_doi_patterns(self, collector):
        """Test various Nature DOI patterns."""
        test_cases = [
            # (DOI, expected_article_id, expected_journal)
            ("10.1038/s41467-023-36000-6", "s41467-023-36000-6", "Nature Communications"),
            ("10.1038/s41467-022-12345-1", "s41467-022-12345-1", "Nature Communications"),
            ("10.1038/srep12345", "srep12345", "Scientific Reports"),
            ("10.1038/srep54321", "srep54321", "Scientific Reports"),
            ("10.1038/ncomms1234", "ncomms1234", "Nature Communications"),
        ]
        
        for doi, expected_id, expected_journal in test_cases:
            paper = Paper(
                title="Test Paper",
                authors=[],
                venue="",
                year=2023,
                citations=0,
                paper_id=f"test_{doi}",
                doi=doi
            )
            
            # Test DOI pattern recognition
            assert collector.is_nature_paper(paper) is True
            
            # Test article ID extraction
            article_id = collector._extract_article_id_from_doi(doi)
            assert article_id == expected_id
            
            # Test journal identification
            journal = collector._identify_journal(paper)
            assert journal == expected_journal
    
    def test_venue_variations(self, collector):
        """Test recognition of various venue name formats."""
        venue_variations = [
            "Nature Communications",
            "Nat Commun",
            "Nat. Commun.",
            "nature communications",
            "NATURE COMMUNICATIONS",
            "Scientific Reports",
            "Sci Rep",
            "Sci. Rep.",
            "scientific reports",
        ]
        
        for venue in venue_variations:
            paper = Paper(
                title="Test Paper",
                authors=[],
                venue=venue,
                year=2023,
                citations=0,
                paper_id=f"test_{venue}"
            )
            assert collector.is_nature_paper(paper) is True
    
    @patch('requests.head')
    def test_mock_integration_flow(self, mock_head, collector):
        """Test the full integration flow with mocked HTTP responses."""
        # Create test paper
        paper = Paper(
            title="Deep learning for molecular design",
            authors=[Author(name="Smith, J.")],
            venue="Nature Communications",
            year=2023,
            citations=10,
            paper_id="integration_test",
            doi="10.1038/s41467-023-12345-6"
        )
        
        # Mock successful open access check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'application/pdf',
            'Content-Length': '1234567'
        }
        mock_head.return_value = mock_response
        
        # Run discovery
        pdf_record = collector._discover_single(paper)
        
        # Verify the result
        assert pdf_record.paper_id == "integration_test"
        assert pdf_record.pdf_url == "https://www.nature.com/articles/s41467-023-12345-6.pdf"
        assert pdf_record.source == "nature"
        assert pdf_record.confidence_score == 0.95
        assert pdf_record.license == "CC-BY"
        assert pdf_record.version_info['journal'] == "Nature Communications"
        
        # Verify rate limiting was applied
        mock_head.assert_called_once()
        call_args = mock_head.call_args
        assert "User-Agent" in call_args[1]['headers']
        assert "test@academic.edu" in call_args[1]['headers']['User-Agent']
    
    @patch('requests.head')
    def test_fallback_to_doi_resolver(self, mock_head, collector):
        """Test fallback to DOI resolver when direct access fails."""
        paper = Paper(
            title="Machine learning in chemistry",
            authors=[],
            venue="Nature Communications",
            year=2023,
            citations=5,
            paper_id="fallback_test",
            doi="10.1038/s41467-023-98765-4"
        )
        
        # Mock authentication required (not open access on Nature)
        mock_response = Mock()
        mock_response.status_code = 303
        mock_response.headers = {'Location': 'https://idp.nature.com/authorize?...'}
        mock_head.return_value = mock_response
        
        # Mock DOI resolver success
        mock_doi_record = Mock()
        mock_doi_record.paper_id = "fallback_test"
        mock_doi_record.pdf_url = "https://repository.example.com/pdf/12345.pdf"
        mock_doi_record.source = "doi_resolver"
        mock_doi_record.confidence_score = 0.85
        mock_doi_record.version_info = {}
        
        with patch.object(collector.doi_resolver, '_discover_single', return_value=mock_doi_record):
            pdf_record = collector._discover_single(paper)
            
            # Verify fallback worked
            assert pdf_record.source == "nature_via_doi"
            assert pdf_record.pdf_url == "https://repository.example.com/pdf/12345.pdf"
            assert pdf_record.version_info['nature_paper'] is True
            assert pdf_record.version_info['journal'] == "Nature Communications"
    
    def test_statistics_tracking(self, collector):
        """Test that collector properly tracks statistics."""
        papers = [
            Paper(
                title="Test 1",
                authors=[],
                venue="Nature Communications",
                year=2023,
                citations=0,
                paper_id="1",
                doi="10.1038/s41467-023-11111-1"
            ),
            Paper(
                title="Test 2",
                authors=[],
                venue="Scientific Reports",
                year=2023,
                citations=0,
                paper_id="2",
                doi="10.1038/srep22222"
            ),
            Paper(
                title="Test 3",
                authors=[],
                venue="ICML",
                year=2023,
                citations=0,
                paper_id="3"
            )  # Not a Nature paper
        ]
        
        with patch.object(collector, '_discover_single') as mock_discover:
            # First two succeed, third fails
            mock_discover.side_effect = [
                Mock(paper_id="1"),
                Mock(paper_id="2"),
                Exception("Not a Nature paper")
            ]
            
            results = collector.discover_pdfs(papers)
            
            # Check results
            assert len(results) == 2
            
            # Check statistics
            stats = collector.get_statistics()
            assert stats['attempted'] == 3
            assert stats['successful'] == 2
            assert stats['failed'] == 1