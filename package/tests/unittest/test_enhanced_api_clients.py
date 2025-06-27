"""
Tests for Enhanced API Clients - Semantic Scholar, OpenAlex, Crossref
Following TDD approach - these tests should drive the real implementation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests
from typing import List

from src.data.models import (
    Paper, Author, APIResponse, ResponseMetadata, APIError
)


class TestEnhancedSemanticScholarClient:
    """Test the Enhanced Semantic Scholar client"""
    
    def setup_method(self):
        """Setup test fixtures"""
        from src.data.sources.enhanced_semantic_scholar import EnhancedSemanticScholarClient
        self.client = EnhancedSemanticScholarClient()
    
    def test_search_papers_basic_functionality(self):
        """Test basic paper search functionality"""
        query = 'venue:"ICML" year:2023'
        year = 2023
        
        # Mock the actual HTTP request
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [
                    {
                        'paperId': 'test_id_1',
                        'title': 'Test Paper 1',
                        'authors': [{'name': 'Author 1'}],
                        'venue': 'ICML',
                        'year': 2023,
                        'citationCount': 10,
                        'abstract': 'Test abstract'
                    }
                ],
                'total': 1
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year, limit=100)
            
            assert isinstance(result, APIResponse)
            assert result.success is True
            assert len(result.papers) == 1
            assert result.papers[0].title == 'Test Paper 1'
            assert result.papers[0].paper_id == 'test_id_1'
            assert result.metadata.api_name == 'semantic_scholar'
    
    def test_search_papers_with_pagination(self):
        """Test pagination handling"""
        query = 'venue:"ICML" year:2023'
        year = 2023
        
        # Should handle offset parameter correctly
        result = self.client.search_papers(query, year, limit=500, offset=100)
        
        assert isinstance(result, APIResponse)
        assert result.metadata.query_used == query
        # Real implementation should include offset in API call
    
    def test_search_papers_with_retry_logic(self):
        """Test retry logic for failed requests"""
        query = 'venue:"ICML" year:2023'
        year = 2023
        
        with patch('requests.get') as mock_get:
            # First call fails, second succeeds
            mock_get.side_effect = [
                requests.exceptions.RequestException("Connection error"),
                Mock(status_code=200, json=lambda: {'data': [], 'total': 0})
            ]
            
            result = self.client.search_papers(query, year)
            
            # Should have retried and succeeded
            assert result.success is True
            assert mock_get.call_count == 2
    
    def test_search_papers_rate_limit_handling(self):
        """Test handling of rate limit responses (429)"""
        query = 'venue:"ICML" year:2023'
        year = 2023
        
        with patch('requests.get') as mock_get:
            # Rate limit response
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {'Retry-After': '60'}
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year)
            
            # Should handle rate limit gracefully
            assert result.success is False
            assert len(result.errors) > 0
            assert 'rate limit' in result.errors[0].error_type.lower()
    
    def test_search_venue_batch_or_query_construction(self):
        """Test batch venue search with OR query construction"""
        venues = ["ICML", "NeurIPS", "ICLR"]
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [
                    {
                        'paperId': 'batch_id_1',
                        'title': 'Batch Paper 1',
                        'authors': [{'name': 'Batch Author 1'}],
                        'venue': 'ICML',
                        'year': 2023,
                        'citationCount': 15,
                        'abstract': 'Batch abstract'
                    }
                ],
                'total': 1
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_venue_batch(venues, year)
            
            # Should construct OR query
            assert isinstance(result, APIResponse)
            # Real implementation should use: (venue:"ICML" OR venue:"NeurIPS" OR venue:"ICLR") AND year:2023
            called_args = mock_get.call_args
            assert 'ICML' in str(called_args)
            assert 'NeurIPS' in str(called_args)
            assert 'ICLR' in str(called_args)
    
    def test_search_venue_batch_large_batch_handling(self):
        """Test handling of large venue batches (8+ venues)"""
        venues = [f"venue_{i}" for i in range(10)]  # 10 venues
        year = 2023
        
        result = self.client.search_venue_batch(venues, year)
        
        # Should handle large batches gracefully
        assert isinstance(result, APIResponse)
        # Real implementation might split large batches or handle query length limits
    
    def test_search_papers_error_handling(self):
        """Test comprehensive error handling"""
        query = 'invalid:query'
        year = 2023
        
        with patch('requests.get') as mock_get:
            # Server error
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year)
            
            assert result.success is False
            assert len(result.errors) > 0
            assert result.errors[0].status_code == 500
    
    def test_response_parsing_and_paper_creation(self):
        """Test parsing of API response into Paper objects"""
        query = 'venue:"ICML" year:2023'
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [
                    {
                        'paperId': 'ss_12345',
                        'title': 'Advanced ML Techniques',
                        'authors': [
                            {'name': 'Dr. Jane Smith'},
                            {'name': 'Prof. John Doe'}
                        ],
                        'venue': 'ICML',
                        'year': 2023,
                        'citationCount': 42,
                        'abstract': 'This paper presents advanced machine learning techniques...',
                        'url': 'https://example.com/paper'
                    }
                ],
                'total': 1
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year)
            
            assert len(result.papers) == 1
            paper = result.papers[0]
            assert paper.paper_id == 'ss_12345'
            assert paper.title == 'Advanced ML Techniques'
            assert len(paper.authors) == 2
            assert paper.authors[0].name == 'Dr. Jane Smith'
            assert paper.venue == 'ICML'
            assert paper.year == 2023
            assert paper.citations == 42
            assert 'advanced machine learning' in paper.abstract.lower()
            assert paper.collection_source == 'semantic_scholar'


class TestEnhancedOpenAlexClient:
    """Test the Enhanced OpenAlex client"""
    
    def setup_method(self):
        """Setup test fixtures"""
        from src.data.sources.enhanced_openalex import EnhancedOpenAlexClient
        self.client = EnhancedOpenAlexClient()
    
    def test_search_papers_basic_functionality(self):
        """Test basic paper search functionality"""
        query = 'venues.display_name:ICML AND publication_year:2023'
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'results': [
                    {
                        'id': 'https://openalex.org/W123456789',
                        'title': 'OpenAlex Test Paper',
                        'authorships': [
                            {'author': {'display_name': 'OA Author 1'}}
                        ],
                        'primary_location': {'source': {'display_name': 'ICML'}},
                        'publication_year': 2023,
                        'cited_by_count': 25,
                        'abstract_inverted_index': {'Test': [0], 'abstract': [1]},
                        'doi': 'https://doi.org/10.1000/test'
                    }
                ],
                'meta': {'count': 1}
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year)
            
            assert isinstance(result, APIResponse)
            assert result.success is True
            assert len(result.papers) == 1
            assert result.papers[0].openalex_id == 'W123456789'
            assert result.metadata.api_name == 'openalex'
    
    def test_search_venue_batch_openAlex_filter_syntax(self):
        """Test OpenAlex-specific filter syntax for venue batching"""
        venues = ["ICML", "NeurIPS", "ICLR"]
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'results': [],
                'meta': {'count': 0}
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_venue_batch(venues, year)
            
            # Should use OpenAlex filter syntax
            called_args = mock_get.call_args
            # Real implementation should use: venues.display_name:ICML|NeurIPS|ICLR
            assert 'venues.display_name' in str(called_args)
    
    def test_abstract_inverted_index_reconstruction(self):
        """Test reconstruction of abstract from inverted index"""
        query = 'venues.display_name:ICML'
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'results': [
                    {
                        'id': 'https://openalex.org/W123456789',
                        'title': 'Test Paper',
                        'authorships': [],
                        'primary_location': {'source': {'display_name': 'ICML'}},
                        'publication_year': 2023,
                        'cited_by_count': 0,
                        'abstract_inverted_index': {
                            'This': [0],
                            'is': [1],
                            'a': [2], 
                            'test': [3],
                            'abstract': [4]
                        }
                    }
                ],
                'meta': {'count': 1}
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year)
            
            # Should reconstruct abstract correctly
            assert result.papers[0].abstract == 'This is a test abstract'
    
    def test_openAlex_cursor_pagination(self):
        """Test OpenAlex cursor-based pagination"""
        query = 'venues.display_name:ICML'
        year = 2023
        
        # OpenAlex uses cursor pagination, not offset
        result = self.client.search_papers(query, year, limit=500, offset=100)
        
        # Real implementation should convert offset to cursor or use page parameter
        assert isinstance(result, APIResponse)


class TestEnhancedCrossrefClient:
    """Test the Enhanced Crossref client"""
    
    def setup_method(self):
        """Setup test fixtures"""
        from src.data.sources.enhanced_crossref import EnhancedCrossrefClient
        self.client = EnhancedCrossrefClient()
    
    def test_search_papers_basic_functionality(self):
        """Test basic paper search functionality"""
        query = 'container-title:ICML AND published:2023'
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'message': {
                    'items': [
                        {
                            'DOI': '10.1000/test.crossref',
                            'title': ['Crossref Test Paper'],
                            'author': [
                                {'given': 'Jane', 'family': 'Smith'}
                            ],
                            'container-title': ['ICML'],
                            'published-print': {'date-parts': [[2023]]},
                            'is-referenced-by-count': 18,
                            'abstract': '<jats:p>Crossref abstract content</jats:p>'
                        }
                    ],
                    'total-results': 1
                }
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year)
            
            assert isinstance(result, APIResponse)
            assert result.success is True
            assert len(result.papers) == 1
            assert result.papers[0].doi == '10.1000/test.crossref'
            assert result.metadata.api_name == 'crossref'
    
    def test_crossref_jats_abstract_cleaning(self):
        """Test cleaning of JATS XML tags from abstracts"""
        query = 'container-title:ICML'
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'message': {
                    'items': [
                        {
                            'DOI': '10.1000/test',
                            'title': ['Test Paper'],
                            'author': [],
                            'container-title': ['ICML'],
                            'published-print': {'date-parts': [[2023]]},
                            'is-referenced-by-count': 0,
                            'abstract': '<jats:p>This is a <jats:italic>test</jats:italic> abstract with <jats:bold>formatting</jats:bold>.</jats:p>'
                        }
                    ],
                    'total-results': 1
                }
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year)
            
            # Should clean JATS XML tags
            expected_abstract = 'This is a test abstract with formatting.'
            assert result.papers[0].abstract == expected_abstract
    
    def test_search_venue_batch_crossref_query_syntax(self):
        """Test Crossref-specific query syntax for venue batching"""
        venues = ["ICML", "NeurIPS", "ICLR"]
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'message': {
                    'items': [],
                    'total-results': 0
                }
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_venue_batch(venues, year)
            
            # Should use Crossref query syntax
            called_args = mock_get.call_args
            # Real implementation should handle container-title querying
            assert 'container-title' in str(called_args) or 'ICML' in str(called_args)
    
    def test_crossref_author_name_parsing(self):
        """Test parsing of Crossref author name format"""
        query = 'container-title:ICML'
        year = 2023
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'message': {
                    'items': [
                        {
                            'DOI': '10.1000/test',
                            'title': ['Test Paper'],
                            'author': [
                                {'given': 'Jane', 'family': 'Smith'},
                                {'given': 'John Q.', 'family': 'Doe'},
                                {'name': 'Single Name Author'}  # Some authors only have name field
                            ],
                            'container-title': ['ICML'],
                            'published-print': {'date-parts': [[2023]]},
                            'is-referenced-by-count': 0
                        }
                    ],
                    'total-results': 1
                }
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_papers(query, year)
            
            # Should parse author names correctly
            authors = result.papers[0].authors
            assert len(authors) == 3
            assert authors[0].name == 'Jane Smith'
            assert authors[1].name == 'John Q. Doe'
            assert authors[2].name == 'Single Name Author'


class TestAPIClientIntegration:
    """Integration tests for all API clients"""
    
    def test_all_clients_return_consistent_paper_format(self):
        """Test that all clients return papers in consistent format"""
        from src.data.sources.enhanced_semantic_scholar import EnhancedSemanticScholarClient
        from src.data.sources.enhanced_openalex import EnhancedOpenAlexClient
        from src.data.sources.enhanced_crossref import EnhancedCrossrefClient
        
        clients = [
            EnhancedSemanticScholarClient(),
            EnhancedOpenAlexClient(), 
            EnhancedCrossrefClient()
        ]
        
        for client in clients:
            result = client.search_papers('test query', 2023, limit=1)
            
            assert isinstance(result, APIResponse)
            assert hasattr(result, 'success')
            assert hasattr(result, 'papers')
            assert hasattr(result, 'metadata')
            assert hasattr(result, 'errors')
            
            if result.papers:
                paper = result.papers[0]
                assert hasattr(paper, 'title')
                assert hasattr(paper, 'authors')
                assert hasattr(paper, 'venue')
                assert hasattr(paper, 'year')
                assert hasattr(paper, 'citations')
                assert hasattr(paper, 'collection_source')
    
    def test_all_clients_support_batch_venue_search(self):
        """Test that all clients support batch venue searching"""
        from src.data.sources.enhanced_semantic_scholar import EnhancedSemanticScholarClient
        from src.data.sources.enhanced_openalex import EnhancedOpenAlexClient
        from src.data.sources.enhanced_crossref import EnhancedCrossrefClient
        
        venues = ["ICML", "NeurIPS"]
        year = 2023
        
        clients = [
            EnhancedSemanticScholarClient(),
            EnhancedOpenAlexClient(),
            EnhancedCrossrefClient()
        ]
        
        for client in clients:
            # Should have search_venue_batch method
            assert hasattr(client, 'search_venue_batch')
            
            result = client.search_venue_batch(venues, year)
            assert isinstance(result, APIResponse)
    
    def test_client_error_recovery_patterns(self):
        """Test error recovery patterns across all clients"""
        from src.data.sources.enhanced_semantic_scholar import EnhancedSemanticScholarClient
        from src.data.sources.enhanced_openalex import EnhancedOpenAlexClient
        from src.data.sources.enhanced_crossref import EnhancedCrossrefClient
        
        clients = [
            EnhancedSemanticScholarClient(),
            EnhancedOpenAlexClient(),
            EnhancedCrossrefClient()
        ]
        
        for client in clients:
            with patch('requests.get') as mock_get:
                # Simulate network timeout
                mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
                
                result = client.search_papers('test', 2023)
                
                # Should handle timeout gracefully
                assert isinstance(result, APIResponse)
                assert result.success is False
                assert len(result.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])