"""Integration tests for IEEE Xplore PDF collector."""

import pytest
from unittest.mock import patch, Mock
import os

from compute_forecast.pdf_discovery.sources.ieee_xplore_collector import IEEEXplorePDFCollector
from compute_forecast.pdf_discovery.core.framework import PDFDiscoveryFramework
from compute_forecast.data.models import Paper


class TestIEEEXploreIntegration:
    """Integration tests for IEEE Xplore collector within the PDF discovery framework."""
    
    @pytest.fixture
    def ieee_papers(self):
        """Create test papers that would typically be from IEEE venues."""
        papers = []
        
        # ICRA paper with DOI
        paper1 = Mock(spec=Paper)
        paper1.paper_id = "icra_2024_001"
        paper1.title = "Robot Navigation using Deep Learning"
        paper1.doi = "10.1109/ICRA48891.2024.123456"
        paper1.venue = "ICRA"
        paper1.year = 2024
        papers.append(paper1)
        
        # IEEE conference paper without DOI
        paper2 = Mock(spec=Paper)
        paper2.paper_id = "iros_2023_042"
        paper2.title = "Multi-Robot Coordination Framework"
        paper2.doi = None
        paper2.venue = "IROS"
        paper2.year = 2023
        papers.append(paper2)
        
        # IEEE journal paper
        paper3 = Mock(spec=Paper)
        paper3.paper_id = "tra_2024_015"
        paper3.title = "Adaptive Control for Robotic Manipulation"
        paper3.doi = "10.1109/TRA.2024.987654"
        paper3.venue = "IEEE Transactions on Robotics and Automation"
        paper3.year = 2024
        papers.append(paper3)
        
        return papers
    
    @pytest.mark.skipif(not os.getenv('IEEE_XPLORE_API_KEY'), reason="IEEE API key not available")
    def test_real_api_discovery(self):
        """Test with real IEEE Xplore API (requires API key)."""
        collector = IEEEXplorePDFCollector()
        
        # Create a paper with known IEEE DOI
        paper = Mock(spec=Paper)
        paper.paper_id = "test_real_001"
        paper.title = "Deep Learning"  # Generic title likely to have results
        paper.doi = None  # Search by title
        paper.venue = "IEEE Conference"
        paper.year = 2023
        
        # Try to discover PDF
        results = collector.discover_pdfs([paper])
        
        # We can't guarantee results, but the API call should complete
        assert isinstance(results, dict)
        stats = collector.get_statistics()
        assert stats["attempted"] == 1
        assert stats["successful"] + stats["failed"] == 1
    
    def test_framework_integration(self, ieee_papers):
        """Test IEEE collector integration with the PDF discovery framework."""
        # Mock the collector to avoid real API calls
        with patch('src.pdf_discovery.sources.ieee_xplore_collector.IEEEXplorePDFCollector') as MockCollector:
            mock_instance = Mock()
            MockCollector.return_value = mock_instance
            
            # Set up mock responses
            mock_instance.source_name = "ieee_xplore"
            mock_instance.discover_pdfs.return_value = {
                "icra_2024_001": Mock(
                    paper_id="icra_2024_001",
                    pdf_url="https://ieeexplore.ieee.org/iel7/123/456/123456.pdf",
                    source="ieee_xplore",
                    confidence_score=0.95
                ),
                "tra_2024_015": Mock(
                    paper_id="tra_2024_015",
                    pdf_url="https://ieeexplore.ieee.org/iel7/789/012/789012.pdf",
                    source="ieee_xplore",
                    confidence_score=0.95
                )
            }
            
            # Create framework and add IEEE collector
            framework = PDFDiscoveryFramework()
            framework.collectors.append(mock_instance)
            
            # Discover PDFs
            result = framework.discover_pdfs(ieee_papers)
            
            # Verify results
            assert result.total_papers == 3
            assert result.discovered_count >= 2  # At least the mocked ones
            assert "ieee_xplore" in result.source_statistics
    
    def test_collector_error_handling_in_framework(self, ieee_papers):
        """Test how framework handles IEEE collector errors."""
        with patch('src.pdf_discovery.sources.ieee_xplore_collector.IEEEXplorePDFCollector') as MockCollector:
            mock_instance = Mock()
            MockCollector.return_value = mock_instance
            
            # Simulate API failure
            mock_instance.source_name = "ieee_xplore"
            mock_instance.discover_pdfs.side_effect = Exception("API key invalid")
            mock_instance.get_statistics.return_value = {
                "attempted": 3,
                "successful": 0,
                "failed": 3
            }
            
            # Create framework
            framework = PDFDiscoveryFramework()
            framework.collectors.append(mock_instance)
            
            # Should handle error gracefully
            result = framework.discover_pdfs(ieee_papers)
            
            assert result.total_papers == 3
            assert result.discovered_count == 0
            assert len(result.failed_papers) == 3
    
    def test_rate_limiting_with_multiple_papers(self):
        """Test rate limiting behavior with multiple papers."""
        import time
        
        with patch.dict(os.environ, {'IEEE_XPLORE_API_KEY': 'test_key'}):
            collector = IEEEXplorePDFCollector()
            
            # Mock the API calls
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "articles": [{
                        "article_number": "123456",
                        "pdf_url": "https://test.pdf",
                        "access_type": "OPEN_ACCESS"
                    }],
                    "total_records": 1
                }
                mock_get.return_value = mock_response
                
                # Create multiple papers
                papers = []
                for i in range(3):
                    paper = Mock(spec=Paper)
                    paper.paper_id = f"test_{i}"
                    paper.title = f"Test Paper {i}"
                    paper.doi = f"10.1109/TEST.{i}"
                    papers.append(paper)
                
                # Time the discovery
                start_time = time.time()
                results = collector.discover_pdfs(papers)
                elapsed = time.time() - start_time
                
                # Should have enforced rate limiting (at least 2 seconds for 3 papers)
                assert elapsed >= 2.0
                assert len(results) == 3
    
    def test_venue_specific_behavior(self):
        """Test collector behavior for specific IEEE venues."""
        with patch.dict(os.environ, {'IEEE_XPLORE_API_KEY': 'test_key'}):
            collector = IEEEXplorePDFCollector()
            
            # Test ICRA paper
            icra_paper = Mock(spec=Paper)
            icra_paper.paper_id = "icra_test"
            icra_paper.title = "ICRA Test Paper"
            icra_paper.doi = "10.1109/ICRA.2024.123"
            icra_paper.venue = "ICRA"
            icra_paper.year = 2024
            
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "articles": [{
                        "article_number": "ICRA123",
                        "pdf_url": "https://ieeexplore.ieee.org/iel7/icra/123.pdf",
                        "access_type": "OPEN_ACCESS",
                        "content_type": "Conferences",
                        "publication_title": "2024 IEEE International Conference on Robotics and Automation (ICRA)"
                    }],
                    "total_records": 1
                }
                mock_get.return_value = mock_response
                
                pdf_record = collector._discover_single(icra_paper)
                
                # Verify ICRA-specific handling
                assert pdf_record.version_info["content_type"] == "Conferences"
                assert "ICRA" in pdf_record.version_info["publication_title"]
                assert pdf_record.confidence_score == 0.95  # High confidence with DOI