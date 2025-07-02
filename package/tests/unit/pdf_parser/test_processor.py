"""Tests for OptimizedPDFProcessor orchestration class."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.core.base_extractor import BaseExtractor


class MockExtractor(BaseExtractor):
    """Mock extractor for testing."""
    
    def __init__(self, name: str, can_affiliations: bool = True, 
                 confidence: float = 0.8, should_fail: bool = False):
        self.name = name
        self.can_affiliations = can_affiliations
        self.confidence = confidence
        self.should_fail = should_fail
    
    def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
        if self.should_fail:
            raise Exception(f"Mock failure in {self.name}")
        
        return {
            'text': f'Sample text from {self.name}',
            'method': self.name,
            'confidence': self.confidence,
            'affiliations': [{'name': 'Test University', 'country': 'Test Country'}]
        }
    
    def extract_full_text(self, pdf_path: Path) -> str:
        if self.should_fail:
            raise Exception(f"Mock failure in {self.name}")
        return f'Full text from {self.name}'
    
    def can_extract_affiliations(self) -> bool:
        return self.can_affiliations


class TestOptimizedPDFProcessor:
    """Test OptimizedPDFProcessor orchestration."""
    
    def test_processor_initialization(self):
        """Test processor can be initialized with config."""
        config = {'cache_dir': './test_cache'}
        processor = OptimizedPDFProcessor(config)
        
        assert processor.config == config
        assert processor.extractors == {}
    
    def test_register_extractor(self):
        """Test extractor registration with priority levels."""
        processor = OptimizedPDFProcessor({})
        extractor = MockExtractor('test_extractor')
        
        processor.register_extractor('test', extractor, level=1)
        
        assert 'test' in processor.extractors
        assert processor.extractors['test']['extractor'] == extractor
        assert processor.extractors['test']['level'] == 1
    
    def test_process_pdf_basic_structure(self):
        """Test basic PDF processing returns required structure."""
        processor = OptimizedPDFProcessor({})
        extractor = MockExtractor('mock')
        processor.register_extractor('mock', extractor, level=1)
        
        pdf_path = Path('/fake/path.pdf')
        paper_metadata = {'title': 'Test Paper', 'authors': ['Test Author']}
        
        with patch('src.pdf_parser.core.processor.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            
            result = processor.process_pdf(pdf_path, paper_metadata)
        
        assert 'affiliations' in result
        assert 'full_text' in result
        assert 'computational_specs' in result
        assert 'extraction_timestamp' in result
        assert 'method' in result
    
    def test_extractor_priority_ordering(self):
        """Test extractors are tried in priority order (lowest level first)."""
        processor = OptimizedPDFProcessor({})
        
        # Register extractors in non-priority order
        high_priority = MockExtractor('high_priority', confidence=0.9)
        low_priority = MockExtractor('low_priority', confidence=0.5, should_fail=True)
        
        processor.register_extractor('low', low_priority, level=3)
        processor.register_extractor('high', high_priority, level=1)
        
        pdf_path = Path('/fake/path.pdf')
        paper_metadata = {'title': 'Test Paper'}
        
        result = processor.process_pdf(pdf_path, paper_metadata)
        
        # Should use high priority extractor (level 1) first
        assert result['method'] == 'high_priority'
    
    def test_extractor_fallback(self):
        """Test fallback to next extractor when first fails."""
        processor = OptimizedPDFProcessor({})
        
        failing_extractor = MockExtractor('failing', should_fail=True)
        working_extractor = MockExtractor('working')
        
        processor.register_extractor('failing', failing_extractor, level=1)
        processor.register_extractor('working', working_extractor, level=2)
        
        pdf_path = Path('/fake/path.pdf')
        paper_metadata = {'title': 'Test Paper'}
        
        result = processor.process_pdf(pdf_path, paper_metadata)
        
        # Should fallback to working extractor
        assert result['method'] == 'working'
    
    def test_no_suitable_extractors(self):
        """Test handling when no extractors can process affiliations."""
        processor = OptimizedPDFProcessor({})
        extractor = MockExtractor('non_affiliation', can_affiliations=False)
        processor.register_extractor('test', extractor, level=1)
        
        pdf_path = Path('/fake/path.pdf')
        paper_metadata = {'title': 'Test Paper'}
        
        result = processor.process_pdf(pdf_path, paper_metadata)
        
        assert result['affiliations'] == []
        assert result['method'] == 'failed'
    
    def test_all_extractors_fail(self):
        """Test handling when all extractors fail."""
        processor = OptimizedPDFProcessor({})
        
        failing1 = MockExtractor('failing1', should_fail=True)
        failing2 = MockExtractor('failing2', should_fail=True)
        
        processor.register_extractor('f1', failing1, level=1)
        processor.register_extractor('f2', failing2, level=2)
        
        pdf_path = Path('/fake/path.pdf')
        paper_metadata = {'title': 'Test Paper'}
        
        result = processor.process_pdf(pdf_path, paper_metadata)
        
        assert result['affiliations'] == []
        assert result['method'] == 'failed'