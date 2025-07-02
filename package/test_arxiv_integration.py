#!/usr/bin/env python3
"""Integration test for ArXiv collector with PDF discovery framework."""

import sys
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from src.data.models import Paper, Author
from src.pdf_discovery.core.framework import PDFDiscoveryFramework
from src.pdf_discovery.sources.arxiv_collector import ArXivPDFCollector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_papers():
    """Create test papers for integration testing."""
    return [
        Paper(
            paper_id="attention_paper",
            title="Attention Is All You Need",
            authors=[Author(name="Vaswani, Ashish"), Author(name="Shazeer, Noam")],
            abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
            year=2017,
            venue="NeurIPS",
            citations=10000,
            arxiv_id="1706.03762v5",
            doi="10.5555/3295222.3295349",
            urls=["https://arxiv.org/abs/1706.03762"]
        ),
        Paper(
            paper_id="resnet_paper",
            title="Deep Residual Learning for Image Recognition",
            authors=[Author(name="He, Kaiming"), Author(name="Zhang, Xiangyu")],
            abstract="Deeper neural networks are more difficult to train...",
            year=2016,
            venue="CVPR",
            citations=50000,
            arxiv_id=None,  # Will test URL extraction
            doi="10.1109/CVPR.2016.90",
            urls=["https://arxiv.org/pdf/1512.03385.pdf"]
        ),
        Paper(
            paper_id="non_arxiv_paper",
            title="Some Conference Paper Without ArXiv",
            authors=[Author(name="Smith, John"), Author(name="Doe, Jane")],
            abstract="This paper is not on arXiv...",
            year=2020,
            venue="ICML",
            citations=100,
            arxiv_id=None,
            doi="10.1000/example",
            urls=["https://example.com/paper.pdf"]
        )
    ]

def test_arxiv_integration():
    """Test ArXiv collector integration with PDF discovery framework."""
    logger.info("Starting ArXiv integration test...")
    
    # Create framework and add ArXiv collector
    framework = PDFDiscoveryFramework()
    arxiv_collector = ArXivPDFCollector()
    framework.add_collector(arxiv_collector)
    
    # Create test papers
    papers = create_test_papers()
    logger.info(f"Testing with {len(papers)} papers")
    
    # Discover PDFs
    def progress_callback(completed, total, source):
        logger.info(f"Progress: {completed}/{total} sources completed (current: {source})")
    
    try:
        result = framework.discover_pdfs(papers, progress_callback)
        
        # Print results
        logger.info("PDF Discovery Results:")
        logger.info(f"Total papers: {result.total_papers}")
        logger.info(f"Discovered: {result.discovered_count}")
        logger.info(f"Success rate: {result.discovery_rate * 100:.1f}%")
        logger.info(f"Execution time: {result.execution_time_seconds:.2f}s")
        
        # Show detailed results
        for record in result.records:
            logger.info(f"✅ {record.paper_id}: {record.pdf_url} (confidence: {record.confidence_score:.2f})")
        
        for failed_id in result.failed_papers:
            logger.info(f"❌ {failed_id}: No PDF found")
        
        # Show source statistics
        for source, stats in result.source_statistics.items():
            logger.info(f"Source {source}: {stats['successful']}/{stats['attempted']} successful")
        
        # Test expectations
        expected_successful = 2  # attention paper and resnet paper should be found
        if result.discovered_count >= expected_successful:
            logger.info("✅ Integration test PASSED")
            return True
        else:
            logger.error(f"❌ Integration test FAILED: Expected at least {expected_successful} papers, got {result.discovered_count}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Integration test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_arxiv_integration()
    sys.exit(0 if success else 1)