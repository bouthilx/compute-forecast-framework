"""Integration tests for PDF parser framework with existing systems."""

from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

from src.pdf_parser.core.processor import OptimizedPDFProcessor
from src.pdf_parser.core.base_extractor import BaseExtractor


class MockComputationalExtractor(BaseExtractor):
    """Mock extractor that simulates computational paper extraction."""
    
    def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
        return {
            'text': '''
            GPU-Accelerated Deep Learning for Large Language Models
            
            Authors: Jane Doe¹, John Smith²
            ¹MIT Computer Science Laboratory, Cambridge, MA, USA
            ²Stanford AI Lab, Stanford, CA, USA
            
            Abstract: We present a novel approach for training large language models
            using distributed GPU computing across multiple nodes...
            ''',
            'method': 'mock_computational',
            'confidence': 0.9,
            'affiliations': [
                {'name': 'MIT Computer Science Laboratory', 'country': 'USA'},
                {'name': 'Stanford AI Lab', 'country': 'USA'}
            ]
        }
    
    def extract_full_text(self, pdf_path: Path) -> str:
        return '''
        GPU-Accelerated Deep Learning for Large Language Models
        
        Abstract: We present a novel approach for training large language models
        using distributed GPU computing across multiple nodes. Our method utilizes
        NVIDIA A100 GPUs with 80GB memory and achieves 3.2x speedup compared to
        previous approaches.
        
        1. Introduction
        Large language models require significant computational resources.
        We trained our model on a cluster of 64 NVIDIA A100 GPUs for 2 weeks.
        
        2. Methodology
        Our training setup uses:
        - 64x NVIDIA A100 80GB GPUs
        - 256 CPU cores (AMD EPYC 7742)
        - 2TB RAM per node
        - InfiniBand interconnect
        
        3. Results
        Training time: 336 hours (2 weeks)
        Peak memory usage: 4.8TB
        Total compute: 21,504 GPU-hours
        
        4. Conclusion
        Our approach demonstrates the feasibility of training large language models
        with careful resource management and distributed computing strategies.
        '''
    
    def can_extract_affiliations(self) -> bool:
        return True


class TestPDFParserIntegration:
    """Test integration between PDF parser and existing systems."""
    
    def test_full_pipeline_computational_paper(self):
        """Test complete processing pipeline for computational paper."""
        processor = OptimizedPDFProcessor({})
        extractor = MockComputationalExtractor()
        processor.register_extractor('mock_computational', extractor, level=1)
        
        pdf_path = Path('/fake/computational_paper.pdf')
        paper_metadata = {
            'title': 'GPU-Accelerated Deep Learning for Large Language Models',
            'authors': ['Jane Doe', 'John Smith'],
            'venue': 'NeurIPS 2024'
        }
        
        result = processor.process_pdf(pdf_path, paper_metadata)
        
        # Check basic structure
        assert 'affiliations' in result
        assert 'full_text' in result
        assert 'computational_specs' in result
        assert 'extraction_timestamp' in result
        assert 'method' in result
        
        # Check affiliations were extracted
        assert len(result['affiliations']) == 2
        assert result['affiliations'][0]['name'] == 'MIT Computer Science Laboratory'
        assert result['affiliations'][1]['name'] == 'Stanford AI Lab'
        
        # Check full text extraction
        assert 'NVIDIA A100' in result['full_text']
        assert 'GPU-hours' in result['full_text']
        
        # Check computational specs (basic keyword detection)
        specs = result['computational_specs']
        assert specs['has_computational_content'] is True
        assert 'GPU' in specs['found_keywords']
        assert 'memory' in specs['found_keywords']
        
        # Check cost tracking
        cost_summary = processor.get_cost_summary()
        assert cost_summary['total_operations'] == 2  # affiliation + full text
        assert cost_summary['total_cost'] == 0.0  # Mock extractor is free
    
    def test_extractor_cost_calculation(self):
        """Test cost calculation for different extractors."""
        processor = OptimizedPDFProcessor({})
        
        # Simulate Google Vision extraction
        mock_result = {
            'text': 'Sample affiliation text',
            'affiliations': [{'name': 'Test University', 'country': 'USA'}],
            'confidence': 0.8
        }
        
        # Test cost calculation
        google_cost = processor._calculate_extraction_cost('google_vision', 'affiliation_extraction', mock_result)
        claude_cost = processor._calculate_extraction_cost('claude_vision', 'affiliation_extraction', mock_result)
        pymupdf_cost = processor._calculate_extraction_cost('pymupdf', 'full_text', mock_result)
        
        assert google_cost == 0.05
        assert claude_cost == 0.10
        assert pymupdf_cost == 0.0
    
    def test_validation_integration(self):
        """Test validation system integration."""
        processor = OptimizedPDFProcessor({})
        
        # Test with high-quality extraction
        good_result = {
            'text': 'Authors: Jane Doe (MIT), John Smith (Stanford University)',
            'confidence': 0.9,
            'affiliations': [
                {'name': 'MIT', 'country': 'USA'},
                {'name': 'Stanford University', 'country': 'USA'}
            ]
        }
        
        paper_metadata = {
            'title': 'Test Paper',
            'authors': ['Jane Doe', 'John Smith']
        }
        
        is_valid = processor.validator.validate_affiliations(good_result, paper_metadata)
        assert is_valid is True
        
        # Test with poor extraction
        poor_result = {
            'text': 'abc',  # Too short
            'confidence': 0.3,  # Too low
            'affiliations': []  # Empty
        }
        
        is_valid = processor.validator.validate_affiliations(poor_result, paper_metadata)
        assert is_valid is False
    
    @patch('src.pdf_parser.core.processor.logger')
    def test_error_handling_and_logging(self, mock_logger):
        """Test error handling and logging integration."""
        processor = OptimizedPDFProcessor({})
        
        # Create failing extractor
        failing_extractor = Mock(spec=BaseExtractor)
        failing_extractor.can_extract_affiliations.return_value = True
        failing_extractor.extract_first_pages.side_effect = Exception("Mock extraction failed")
        failing_extractor.extract_full_text.return_value = ""  # Return empty string for full text
        
        processor.register_extractor('failing', failing_extractor, level=1)
        
        pdf_path = Path('/fake/path.pdf')
        paper_metadata = {'title': 'Test Paper'}
        
        result = processor.process_pdf(pdf_path, paper_metadata)
        
        # Should handle failure gracefully
        assert result['affiliations'] == []
        assert result['method'] == 'failed'
        
        # Check that error was logged
        mock_logger.error.assert_called()
    
    def test_processor_configuration(self):
        """Test processor configuration options."""
        config = {
            'cache_dir': './test_cache',
            'max_retries': 3,
            'timeout': 30
        }
        
        processor = OptimizedPDFProcessor(config)
        
        assert processor.config == config
        assert processor.config['max_retries'] == 3
        assert processor.config['timeout'] == 30