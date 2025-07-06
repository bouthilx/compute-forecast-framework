"""Tests for DOI resolver collector functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from compute_forecast.pdf_discovery.sources.doi_resolver_collector import DOIResolverCollector
from compute_forecast.pdf_discovery.core.models import PDFRecord
from compute_forecast.data.models import Paper, Author, APIResponse, ResponseMetadata


class TestDOIResolverCollector:
    """Test DOI resolver collector functionality."""
    
    @pytest.fixture
    def collector(self):
        """Create a DOI resolver collector instance."""
        return DOIResolverCollector(email="test@example.com")
    
    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper with DOI."""
        return Paper(
            title="Test Paper",
            authors=[Author(name="John Doe")],
            venue="Test Journal",
            year=2021,
            citations=10,
            doi="10.1038/nature12373",
            paper_id="test_paper_1"
        )
    
    @pytest.fixture
    def sample_paper_no_doi(self):
        """Create a sample paper without DOI."""
        return Paper(
            title="Test Paper No DOI",
            authors=[Author(name="Jane Smith")],
            venue="Test Journal",
            year=2021,
            citations=5,
            doi="",  # No DOI
            paper_id="test_paper_2"
        )
    
    @pytest.fixture
    def mock_crossref_response(self):
        """Mock successful CrossRef response."""
        return APIResponse(
            success=True,
            papers=[Paper(
                title="Test Paper",
                authors=[Author(name="John Doe")],
                venue="Test Journal",
                year=2021,
                citations=10,
                doi="10.1038/nature12373",
                urls=["https://publisher.com/paper.pdf"],
                paper_id="crossref_10.1038/nature12373"
            )],
            metadata=ResponseMetadata(
                total_results=1,
                returned_count=1,
                query_used="10.1038/nature12373",
                response_time_ms=100,
                api_name="crossref",
                timestamp=datetime.now()
            ),
            errors=[]
        )
    
    @pytest.fixture
    def mock_unpaywall_response(self):
        """Mock successful Unpaywall response."""
        return APIResponse(
            success=True,
            papers=[Paper(
                title="Test Paper",
                authors=[Author(name="John Doe")],
                venue="Test Journal", 
                year=2021,
                citations=0,
                doi="10.1038/nature12373",
                urls=["https://arxiv.org/pdf/2105.12345.pdf"],
                paper_id="unpaywall_10.1038/nature12373"
            )],
            metadata=ResponseMetadata(
                total_results=1,
                returned_count=1,
                query_used="10.1038/nature12373",
                response_time_ms=150,
                api_name="unpaywall",
                timestamp=datetime.now()
            ),
            errors=[]
        )
    
    def test_init_requires_email(self):
        """Test that DOIResolverCollector requires an email."""
        with pytest.raises(ValueError, match="Email is required"):
            DOIResolverCollector(email=None)
    
    def test_discover_single_success_both_sources(
        self, collector, sample_paper, mock_crossref_response, mock_unpaywall_response
    ):
        """Test successful discovery from both CrossRef and Unpaywall."""
        with patch.object(collector.crossref_client, 'lookup_doi') as mock_crossref, \
             patch.object(collector.unpaywall_client, 'find_open_access') as mock_unpaywall:
            
            mock_crossref.return_value = mock_crossref_response
            mock_unpaywall.return_value = mock_unpaywall_response
            
            result = collector._discover_single(sample_paper)
            
            assert result.paper_id == "test_paper_1"
            assert result.source == "doi_resolver"
            assert result.confidence_score > 0.8  # High confidence for both sources
            assert len(result.version_info["crossref_urls"]) == 1
            assert len(result.version_info["unpaywall_urls"]) == 1
            assert "https://publisher.com/paper.pdf" in result.pdf_url
            
            # Both APIs should be called
            mock_crossref.assert_called_once_with("10.1038/nature12373")
            mock_unpaywall.assert_called_once_with("10.1038/nature12373")
    
    def test_discover_single_crossref_only(
        self, collector, sample_paper, mock_crossref_response
    ):
        """Test discovery with only CrossRef success."""
        with patch.object(collector.crossref_client, 'lookup_doi') as mock_crossref, \
             patch.object(collector.unpaywall_client, 'find_open_access') as mock_unpaywall:
            
            mock_crossref.return_value = mock_crossref_response
            mock_unpaywall.return_value = APIResponse(
                success=False, papers=[], metadata=None, errors=[]
            )
            
            result = collector._discover_single(sample_paper)
            
            assert result.paper_id == "test_paper_1"
            assert result.source == "doi_resolver"
            assert result.confidence_score > 0.6  # Medium confidence for one source
            assert len(result.version_info["crossref_urls"]) == 1
            assert len(result.version_info["unpaywall_urls"]) == 0
    
    def test_discover_single_unpaywall_only(
        self, collector, sample_paper, mock_unpaywall_response
    ):
        """Test discovery with only Unpaywall success."""
        with patch.object(collector.crossref_client, 'lookup_doi') as mock_crossref, \
             patch.object(collector.unpaywall_client, 'find_open_access') as mock_unpaywall:
            
            mock_crossref.return_value = APIResponse(
                success=False, papers=[], metadata=None, errors=[]
            )
            mock_unpaywall.return_value = mock_unpaywall_response
            
            result = collector._discover_single(sample_paper)
            
            assert result.paper_id == "test_paper_1"
            assert result.source == "doi_resolver"
            assert result.confidence_score > 0.6  # Medium confidence for one source
            assert len(result.version_info["crossref_urls"]) == 0
            assert len(result.version_info["unpaywall_urls"]) == 1
    
    def test_discover_single_no_doi(self, collector, sample_paper_no_doi):
        """Test discovery fails for paper without DOI."""
        with pytest.raises(Exception, match="Paper does not have a DOI"):
            collector._discover_single(sample_paper_no_doi)
    
    def test_discover_single_no_results(self, collector, sample_paper):
        """Test discovery when both sources fail."""
        with patch.object(collector.crossref_client, 'lookup_doi') as mock_crossref, \
             patch.object(collector.unpaywall_client, 'find_open_access') as mock_unpaywall:
            
            mock_crossref.return_value = APIResponse(
                success=False, papers=[], metadata=None, errors=[]
            )
            mock_unpaywall.return_value = APIResponse(
                success=False, papers=[], metadata=None, errors=[]
            )
            
            with pytest.raises(Exception, match="No PDFs found"):
                collector._discover_single(sample_paper)
    
    def test_merge_pdf_urls(self, collector):
        """Test PDF URL merging and deduplication."""
        crossref_urls = ["https://publisher.com/paper.pdf", "https://shared.com/paper.pdf"]
        unpaywall_urls = ["https://arxiv.org/paper.pdf", "https://shared.com/paper.pdf"]
        
        merged = collector._merge_pdf_urls(crossref_urls, unpaywall_urls)
        
        # Should prioritize CrossRef URLs and remove duplicates
        expected = [
            "https://publisher.com/paper.pdf",
            "https://shared.com/paper.pdf", 
            "https://arxiv.org/paper.pdf"
        ]
        assert merged == expected
    
    def test_calculate_confidence_score(self, collector):
        """Test confidence score calculation."""
        # Both sources with multiple URLs
        score1 = collector._calculate_confidence_score(
            crossref_urls=["url1", "url2"],
            unpaywall_urls=["url3", "url4"]
        )
        assert score1 > 0.8
        
        # One source with multiple URLs
        score2 = collector._calculate_confidence_score(
            crossref_urls=["url1", "url2"],
            unpaywall_urls=[]
        )
        assert 0.6 < score2 < 0.8
        
        # One source with one URL
        score3 = collector._calculate_confidence_score(
            crossref_urls=["url1"],
            unpaywall_urls=[]
        )
        assert 0.6 < score3 <= 0.7
        
        # No URLs
        score4 = collector._calculate_confidence_score(
            crossref_urls=[],
            unpaywall_urls=[]
        )
        assert score4 == 0.0
    
    def test_get_validation_status(self, collector):
        """Test validation status determination."""
        assert collector._get_validation_status(0.9) == "high_confidence"
        assert collector._get_validation_status(0.7) == "medium_confidence"
        assert collector._get_validation_status(0.5) == "low_confidence"
        assert collector._get_validation_status(0.2) == "needs_validation"
    
    def test_source_name(self, collector):
        """Test that source name is correctly set."""
        assert collector.source_name == "doi_resolver"