"""
Unit tests for Enhanced Collection Orchestrator
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import time

from src.data.collectors.enhanced_orchestrator import (
    EnhancedCollectionOrchestrator, CollectionResult
)
from src.data.models import (
    Paper, Author, APIResponse, CollectionQuery,
    ResponseMetadata, APIError
)


class TestEnhancedCollectionOrchestrator:
    """Test enhanced collection orchestrator functionality"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked API clients"""
        with patch('src.data.collectors.enhanced_orchestrator.EnhancedSemanticScholarClient'), \
             patch('src.data.collectors.enhanced_orchestrator.EnhancedOpenAlexClient'), \
             patch('src.data.collectors.enhanced_orchestrator.EnhancedCrossrefClient'), \
             patch('src.data.collectors.enhanced_orchestrator.GoogleScholarClient'):
            return EnhancedCollectionOrchestrator()
    
    @pytest.fixture
    def sample_query(self):
        """Create sample collection query"""
        return CollectionQuery(
            domain="machine learning",
            year=2023,
            venue="NeurIPS",
            keywords=["deep", "learning"],
            min_citations=0,
            max_results=50
        )
    
    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing"""
        return [
            Paper(
                title="Paper 1",
                authors=[Author(name="Author A")],
                venue="NeurIPS",
                year=2023,
                citations=10,
                collection_source="semantic_scholar"
            ),
            Paper(
                title="Paper 2",
                authors=[Author(name="Author B")],
                venue="ICML",
                year=2023,
                citations=20,
                collection_source="openalex"
            )
        ]
    
    def test_initialization_default(self):
        """Test orchestrator initialization without API keys"""
        with patch('src.data.collectors.enhanced_orchestrator.EnhancedSemanticScholarClient') as mock_ss, \
             patch('src.data.collectors.enhanced_orchestrator.EnhancedOpenAlexClient') as mock_oa, \
             patch('src.data.collectors.enhanced_orchestrator.EnhancedCrossrefClient') as mock_cr, \
             patch('src.data.collectors.enhanced_orchestrator.GoogleScholarClient') as mock_gs:
            
            orchestrator = EnhancedCollectionOrchestrator()
            
            # Verify clients were created
            mock_ss.assert_called_once_with(api_key=None)
            mock_oa.assert_called_once_with(email=None)
            mock_cr.assert_called_once_with(email=None)
            mock_gs.assert_called_once_with(use_proxy=False)
            
            # Verify sources are available
            assert len(orchestrator.sources) == 4
            assert "semantic_scholar" in orchestrator.sources
            assert "openalex" in orchestrator.sources
            assert "crossref" in orchestrator.sources
            assert "google_scholar" in orchestrator.sources
    
    def test_initialization_with_api_keys(self):
        """Test orchestrator initialization with API keys"""
        api_keys = {
            "semantic_scholar": "test_key",
            "openalex_email": "test@example.com",
            "crossref_email": "test@example.com",
            "google_scholar_proxy": True
        }
        
        with patch('src.data.collectors.enhanced_orchestrator.EnhancedSemanticScholarClient') as mock_ss, \
             patch('src.data.collectors.enhanced_orchestrator.EnhancedOpenAlexClient') as mock_oa, \
             patch('src.data.collectors.enhanced_orchestrator.EnhancedCrossrefClient') as mock_cr, \
             patch('src.data.collectors.enhanced_orchestrator.GoogleScholarClient') as mock_gs:
            
            orchestrator = EnhancedCollectionOrchestrator(api_keys)
            
            # Verify clients were created with keys
            mock_ss.assert_called_once_with(api_key="test_key")
            mock_oa.assert_called_once_with(email="test@example.com")
            mock_cr.assert_called_once_with(email="test@example.com")
            mock_gs.assert_called_once_with(use_proxy=True)
    
    def test_collect_from_all_sources_parallel_success(self, orchestrator, sample_query, sample_papers):
        """Test successful parallel collection from all sources"""
        # Mock successful responses
        mock_response = APIResponse(
            success=True,
            papers=sample_papers,
            metadata=ResponseMetadata(
                total_results=2,
                returned_count=2,
                query_used="test",
                response_time_ms=100,
                api_name="test",
                timestamp=datetime.now()
            ),
            errors=[]
        )
        
        # Mock each source to return papers
        for source in orchestrator.sources.values():
            source.search_venue_batch = Mock(return_value=mock_response)
        
        # Mock rate limiter
        orchestrator.rate_limiter.wait_if_needed = Mock(return_value=0)
        orchestrator.rate_limiter.record_request = Mock()
        
        # Perform collection
        result = orchestrator.collect_from_all_sources(sample_query, parallel=True)
        
        # Verify results
        assert isinstance(result, CollectionResult)
        assert len(result.papers) == 8  # 2 papers x 4 sources
        assert result.source_counts["semantic_scholar"] == 2
        assert result.source_counts["openalex"] == 2
        assert result.source_counts["crossref"] == 2
        assert result.source_counts["google_scholar"] == 2
        assert len(result.errors) == 0
        assert result.collection_time > 0
    
    def test_collect_from_all_sources_sequential(self, orchestrator, sample_query):
        """Test sequential collection from all sources"""
        # Mock responses
        mock_response = APIResponse(
            success=True,
            papers=[],
            metadata=ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used="test",
                response_time_ms=100,
                api_name="test",
                timestamp=datetime.now()
            ),
            errors=[]
        )
        
        # Mock sources
        for source in orchestrator.sources.values():
            source.search_venue_batch = Mock(return_value=mock_response)
        
        # Mock rate limiter
        orchestrator.rate_limiter.wait_if_needed = Mock(return_value=0)
        orchestrator.rate_limiter.record_request = Mock()
        
        # Perform sequential collection
        result = orchestrator.collect_from_all_sources(sample_query, parallel=False)
        
        # Verify sequential execution
        assert isinstance(result, CollectionResult)
        assert all(count == 0 for count in result.source_counts.values())
    
    def test_collect_with_source_failure(self, orchestrator, sample_query):
        """Test collection when some sources fail"""
        # Mock one source to fail
        orchestrator.sources["semantic_scholar"].search_venue_batch = Mock(
            side_effect=Exception("API error")
        )
        
        # Mock other sources to succeed
        mock_response = APIResponse(
            success=True,
            papers=[],
            metadata=ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used="test",
                response_time_ms=100,
                api_name="test",
                timestamp=datetime.now()
            ),
            errors=[]
        )
        
        for source_name in ["openalex", "crossref", "google_scholar"]:
            orchestrator.sources[source_name].search_venue_batch = Mock(return_value=mock_response)
        
        # Mock rate limiter
        orchestrator.rate_limiter.wait_if_needed = Mock(return_value=0)
        orchestrator.rate_limiter.record_request = Mock()
        
        # Perform collection
        result = orchestrator.collect_from_all_sources(sample_query, parallel=True)
        
        # Verify partial success
        assert len(result.errors) == 1
        assert "semantic_scholar" in result.errors[0]
        assert result.source_counts["semantic_scholar"] == 0
        assert all(count == 0 for name, count in result.source_counts.items() 
                  if name != "semantic_scholar")
    
    def test_collect_with_fallback_success(self, orchestrator, sample_query, sample_papers):
        """Test fallback collection strategy"""
        # Mock first source to fail (semantic scholar uses venue search since sample_query has venue)
        mock_failed_response = APIResponse(
            success=False,
            papers=[],
            metadata=ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used="test",
                response_time_ms=100,
                api_name="semantic_scholar",
                timestamp=datetime.now()
            ),
            errors=[]
        )
        orchestrator.sources["semantic_scholar"].search_venue_batch = Mock(return_value=mock_failed_response)
        
        mock_response = APIResponse(
            success=True,
            papers=sample_papers,
            metadata=ResponseMetadata(
                total_results=2,
                returned_count=2,
                query_used="test",
                response_time_ms=100,
                api_name="openalex",
                timestamp=datetime.now()
            ),
            errors=[]
        )
        orchestrator.sources["openalex"].search_venue_batch = Mock(return_value=mock_response)
        
        # Mock rate limiter
        orchestrator.rate_limiter.wait_if_needed = Mock(return_value=0)
        orchestrator.rate_limiter.record_request = Mock()
        
        # Perform fallback collection
        preferred_sources = ["semantic_scholar", "openalex", "crossref"]
        result = orchestrator.collect_with_fallback(sample_query, preferred_sources)
        
        # Verify fallback worked
        assert len(result.papers) == 2
        assert result.source_counts.get("openalex") == 2
        assert len(result.errors) == 0  # No errors since the API returned success=False rather than throwing
    
    def test_rate_limiting_enforcement(self, orchestrator, sample_query):
        """Test that rate limiting is properly enforced"""
        # Mock rate limiter to simulate wait
        orchestrator.rate_limiter.wait_if_needed = Mock(return_value=2.5)
        orchestrator.rate_limiter.record_request = Mock()
        
        # Mock source response
        mock_response = APIResponse(
            success=True,
            papers=[],
            metadata=ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used="test",
                response_time_ms=100,
                api_name="test",
                timestamp=datetime.now()
            ),
            errors=[]
        )
        orchestrator.sources["semantic_scholar"].search_papers = Mock(return_value=mock_response)
        
        # Collect from single source
        papers = orchestrator._collect_from_source_with_rate_limit(
            "semantic_scholar", sample_query
        )
        
        # Verify rate limiting was called
        orchestrator.rate_limiter.wait_if_needed.assert_called_once_with("semantic_scholar")
        orchestrator.rate_limiter.record_request.assert_called_once()
    
    def test_query_with_keywords(self, orchestrator, sample_query):
        """Test query construction with keywords"""
        # Mock source
        mock_response = APIResponse(
            success=True,
            papers=[],
            metadata=ResponseMetadata(
                total_results=0,
                returned_count=0,
                query_used="test",
                response_time_ms=100,
                api_name="test",
                timestamp=datetime.now()
            ),
            errors=[]
        )
        orchestrator.sources["semantic_scholar"].search_papers = Mock(return_value=mock_response)
        
        # Mock rate limiter
        orchestrator.rate_limiter.wait_if_needed = Mock(return_value=0)
        orchestrator.rate_limiter.record_request = Mock()
        
        # Remove venue to test keyword search
        sample_query.venue = None
        
        # Collect
        papers = orchestrator._collect_from_source_with_rate_limit(
            "semantic_scholar", sample_query
        )
        
        # Verify query construction
        expected_query = "machine learning deep learning"
        orchestrator.sources["semantic_scholar"].search_papers.assert_called_once_with(
            expected_query, 2023, limit=50
        )
    
    def test_get_source_statistics(self, orchestrator):
        """Test source statistics retrieval"""
        # Mock rate limiter usage
        from src.data.models import RateLimitStatus
        mock_status = RateLimitStatus(
            api_name="semantic_scholar",
            requests_in_window=50,
            window_capacity=100,
            next_available_slot=datetime.now(),
            current_delay_seconds=1.0,
            health_multiplier=1.0
        )
        
        orchestrator.rate_limiter.get_current_usage = Mock(return_value=mock_status)
        
        # Get statistics
        stats = orchestrator.get_source_statistics()
        
        # Verify statistics
        assert "semantic_scholar" in stats
        assert stats["semantic_scholar"]["available"] is True
        assert stats["semantic_scholar"]["rate_limit"]["requests_in_window"] == 50
        assert stats["semantic_scholar"]["rate_limit"]["window_capacity"] == 100
        assert stats["semantic_scholar"]["rate_limit"]["current_delay"] == 1.0
        assert stats["semantic_scholar"]["rate_limit"]["health_multiplier"] == 1.0