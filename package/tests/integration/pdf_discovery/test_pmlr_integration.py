"""Integration tests for PMLR collector with PDF discovery framework."""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime

from compute_forecast.pdf_discovery.core.framework import PDFDiscoveryFramework
from compute_forecast.pdf_discovery.sources.pmlr_collector import PMLRCollector
from compute_forecast.data.models import Paper, Author


class TestPMLRIntegration:
    """Test PMLR collector integration with framework."""
    
    @pytest.fixture
    def framework(self):
        """Create framework with PMLR collector."""
        framework = PDFDiscoveryFramework()
        collector = PMLRCollector()
        framework.add_collector(collector)
        return framework
    
    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        return [
            Paper(
                title="Deep Reinforcement Learning",
                authors=[Author(name="Alice Smith")],
                venue="ICML",
                year=2023,
                citations=50,
                paper_id="icml_2023_drl"
            ),
            Paper(
                title="Bayesian Optimization Methods",
                authors=[Author(name="Bob Jones")],
                venue="AISTATS",
                year=2024,
                citations=20,
                paper_id="aistats_2024_bo"
            ),
            Paper(
                title="Unknown Conference Paper",
                authors=[Author(name="Charlie Brown")],
                venue="UNKNOWN",
                year=2023,
                citations=5,
                paper_id="unknown_2023"
            )
        ]
    
    @patch('requests.get')
    def test_framework_discovery_with_pmlr(self, mock_get, framework, sample_papers):
        """Test PDF discovery through framework."""
        # Mock ICML proceedings page
        icml_response = Mock()
        icml_response.status_code = 200
        icml_response.text = '''
        <html>
        <body>
        <div class="paper">
            <a href="/v202/smith23a.html">Deep Reinforcement Learning</a>
        </div>
        </body>
        </html>
        '''
        
        # Mock AISTATS proceedings page
        aistats_response = Mock()
        aistats_response.status_code = 200
        aistats_response.text = '''
        <html>
        <body>
        <div class="paper">
            <a href="/v238/jones24b.html">Bayesian Optimization Methods</a>
        </div>
        </body>
        </html>
        '''
        
        # Configure mock responses
        def side_effect(url, **kwargs):
            if "v202" in url:
                return icml_response
            elif "v238" in url:
                return aistats_response
            else:
                raise Exception("Unknown URL")
        
        mock_get.side_effect = side_effect
        
        # Discover PDFs
        result = framework.discover_pdfs(sample_papers)
        
        # Verify results
        assert result.total_papers == 3
        assert result.discovered_count == 2  # ICML and AISTATS found
        assert len(result.failed_papers) == 1  # Unknown conference failed
        assert "unknown_2023" in result.failed_papers
        
        # Check discovered PDFs
        discovered_ids = {r.paper_id for r in result.records}
        assert "icml_2023_drl" in discovered_ids
        assert "aistats_2024_bo" in discovered_ids
        
        # Verify PDF URLs
        icml_record = next(r for r in result.records if r.paper_id == "icml_2023_drl")
        assert icml_record.pdf_url == "https://proceedings.mlr.press/v202/smith23a.pdf"
        
        aistats_record = next(r for r in result.records if r.paper_id == "aistats_2024_bo")
        assert aistats_record.pdf_url == "https://proceedings.mlr.press/v238/jones24b.pdf"
    
    def test_venue_priorities_with_pmlr(self, framework):
        """Test that PMLR respects venue priorities."""
        # Set PMLR as priority for ML conferences
        framework.set_venue_priorities({
            "ICML": ["pmlr", "arxiv"],
            "AISTATS": ["pmlr", "semantic_scholar"],
            "default": ["semantic_scholar", "arxiv", "pmlr"]
        })
        
        # Verify priorities were set
        assert framework.venue_priorities["ICML"][0] == "pmlr"
        assert framework.venue_priorities["AISTATS"][0] == "pmlr"
    
    @patch('requests.get')
    def test_pmlr_caching_in_framework(self, mock_get, framework):
        """Test that caching works when used through framework."""
        # Test direct collector caching
        collector = framework.collectors[0]
        
        # Mock proceedings page
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
        <body>
        <div class="paper">
            <a href="/v202/test23.html">Test Paper Title</a>
        </div>
        </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        # First search
        paper_id1 = collector._search_proceedings_page("v202", "Test Paper Title")
        assert paper_id1 == "test23"
        assert mock_get.call_count == 1
        
        # Second search with same volume and title should use cache
        paper_id2 = collector._search_proceedings_page("v202", "Test Paper Title")
        assert paper_id2 == "test23"
        assert mock_get.call_count == 1  # Should not increase
        
        # Different title should trigger new request
        paper_id3 = collector._search_proceedings_page("v202", "Different Paper")
        assert mock_get.call_count == 2
    
    def test_pmlr_statistics_through_framework(self, framework, sample_papers):
        """Test that statistics are properly collected."""
        # Remove unknown paper for cleaner test
        papers = sample_papers[:2]
        
        with patch('requests.get') as mock_get:
            # Mock successful responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '<html><body><a href="/v202/test.html">Test Paper</a></body></html>'
            mock_get.return_value = mock_response
            
            # Discover PDFs
            result = framework.discover_pdfs(papers)
            
            # Check statistics
            assert "pmlr" in result.source_statistics
            stats = result.source_statistics["pmlr"]
            assert stats["attempted"] == 2
            # Note: May not be successful if title matching fails
            assert stats["failed"] >= 0
            assert stats["successful"] + stats["failed"] == stats["attempted"]