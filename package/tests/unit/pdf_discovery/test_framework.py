"""Unit tests for PDF discovery framework."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor
import time

from src.pdf_discovery.core.models import PDFRecord, DiscoveryResult
from src.pdf_discovery.core.collectors import BasePDFCollector
from src.pdf_discovery.core.framework import PDFDiscoveryFramework
from src.data.models import Paper


class MockCollector(BasePDFCollector):
    """Mock collector for testing."""
    
    def __init__(self, source_name: str, delay: float = 0, fail_papers: List[str] = None):
        super().__init__(source_name)
        self.delay = delay
        self.fail_papers = fail_papers or []
        self.discovery_count = 0
        
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Mock discovery implementation."""
        self.discovery_count += 1
        
        if self.delay:
            time.sleep(self.delay)
            
        if paper.paper_id in self.fail_papers:
            raise ValueError(f"Failed to discover {paper.paper_id}")
        
        # Fixed confidence scores by source
        source_confidence = {
            "arxiv": 0.9,
            "openreview": 0.85,  
            "semantic_scholar": 0.8
        }
        
        return PDFRecord(
            paper_id=paper.paper_id,
            pdf_url=f"https://{self.source_name}.com/{paper.paper_id}.pdf",
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=source_confidence.get(self.source_name, 0.7),
            version_info={},
            validation_status="mock"
        )


class TestPDFDiscoveryFramework:
    """Test PDFDiscoveryFramework orchestration."""
    
    def test_framework_initialization(self):
        """Test framework initialization."""
        framework = PDFDiscoveryFramework()
        assert framework.discovered_papers == {}
        assert framework.url_to_papers == {}
        assert framework.collectors == []
    
    def test_add_collector(self):
        """Test adding collectors to framework."""
        framework = PDFDiscoveryFramework()
        collector1 = MockCollector("source1")
        collector2 = MockCollector("source2")
        
        framework.add_collector(collector1)
        framework.add_collector(collector2)
        
        assert len(framework.collectors) == 2
        assert collector1 in framework.collectors
        assert collector2 in framework.collectors
    
    def test_discover_pdfs_single_source(self):
        """Test discovery with single source."""
        framework = PDFDiscoveryFramework()
        collector = MockCollector("arxiv")
        framework.add_collector(collector)
        
        papers = [
            Paper(paper_id="paper_1", title="Test 1", authors=[], year=2024,
                  citations=0, venue="Test"),
            Paper(paper_id="paper_2", title="Test 2", authors=[], year=2024,
                  citations=0, venue="Test"),
        ]
        
        result = framework.discover_pdfs(papers)
        
        assert isinstance(result, DiscoveryResult)
        assert result.total_papers == 2
        assert result.discovered_count == 2
        assert len(result.records) == 2
        assert len(result.failed_papers) == 0
    
    def test_discover_pdfs_multiple_sources(self):
        """Test discovery with multiple sources."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockCollector("arxiv"))
        framework.add_collector(MockCollector("openreview"))
        framework.add_collector(MockCollector("semantic_scholar"))
        
        papers = [
            Paper(paper_id="paper_1", title="Test 1", authors=[], year=2024,
                  citations=0, venue="Test"),
        ]
        
        result = framework.discover_pdfs(papers)
        
        # Should get best result (highest confidence)
        assert result.discovered_count == 1
        assert len(result.records) == 1
        assert result.records[0].source == "arxiv"  # arxiv has highest confidence (0.9)
        assert result.records[0].confidence_score == 0.9
    
    def test_discover_pdfs_with_failures(self):
        """Test discovery with some source failures."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockCollector("arxiv", fail_papers=["paper_1"]))
        framework.add_collector(MockCollector("openreview"))
        
        papers = [
            Paper(paper_id="paper_1", title="Test 1", authors=[], year=2024,
                  citations=0, venue="Test"),
            Paper(paper_id="paper_2", title="Test 2", authors=[], year=2024,
                  citations=0, venue="Test"),
        ]
        
        result = framework.discover_pdfs(papers)
        
        assert result.discovered_count == 2
        # paper_1 should only be from openreview (arxiv failed)
        paper1_records = [r for r in result.records if r.paper_id == "paper_1"]
        assert len(paper1_records) == 1
        assert paper1_records[0].source == "openreview"
        # paper_2 should be from the source with highest confidence
        paper2_records = [r for r in result.records if r.paper_id == "paper_2"]
        assert len(paper2_records) == 1
        assert paper2_records[0].source == "arxiv"  # arxiv has higher confidence
    
    def test_parallel_execution(self):
        """Test parallel execution of collectors."""
        framework = PDFDiscoveryFramework()
        
        # Add slow collectors
        framework.add_collector(MockCollector("slow1", delay=0.1))
        framework.add_collector(MockCollector("slow2", delay=0.1))
        framework.add_collector(MockCollector("slow3", delay=0.1))
        
        papers = [Paper(paper_id=f"paper_{i}", title=f"Test {i}", authors=[], 
                       year=2024, citations=0, venue="Test") for i in range(5)]
        
        start_time = time.time()
        result = framework.discover_pdfs(papers)
        elapsed = time.time() - start_time
        
        # Should be faster than sequential (0.1s * 3 sources * 5 papers = 1.5s)
        assert elapsed < 0.6  # Parallel should complete faster than sequential
        assert result.discovered_count == 5
    
    def test_source_priority_by_venue(self):
        """Test source prioritization based on venue."""
        framework = PDFDiscoveryFramework()
        
        # Configure venue priorities
        framework.set_venue_priorities({
            "ICLR": ["openreview", "arxiv"],
            "NeurIPS": ["arxiv", "openreview"],
            "default": ["semantic_scholar", "arxiv"]
        })
        
        # Create collectors where only priority sources succeed
        arxiv_collector = MockCollector("arxiv", fail_papers=["iclr_1"])  # Fails on ICLR
        openreview_collector = MockCollector("openreview", fail_papers=["neurips_1"])  # Fails on NeurIPS
        semantic_collector = MockCollector("semantic_scholar")
        
        framework.add_collector(arxiv_collector)
        framework.add_collector(openreview_collector)
        framework.add_collector(semantic_collector)
        
        # ICLR paper should get openreview (arxiv fails)
        iclr_paper = Paper(paper_id="iclr_1", title="ICLR Paper", authors=[], 
                          year=2024, citations=0, venue="ICLR")
        
        result = framework.discover_pdfs([iclr_paper])
        assert result.records[0].source == "openreview"
        
        # NeurIPS paper should get arxiv (openreview fails)
        neurips_paper = Paper(paper_id="neurips_1", title="NeurIPS Paper", authors=[], 
                             year=2024, citations=0, venue="NeurIPS")
        
        result = framework.discover_pdfs([neurips_paper])
        assert result.records[0].source == "arxiv"
    
    def test_deduplication(self):
        """Test deduplication of discovered PDFs."""
        framework = PDFDiscoveryFramework()
        
        # Add same paper to framework multiple times
        record1 = PDFRecord(
            paper_id="paper_1",
            pdf_url="https://arxiv.org/paper_1.pdf",
            source="arxiv",
            discovery_timestamp=datetime.now(),
            confidence_score=0.9,
            version_info={},
            validation_status="validated"
        )
        
        framework._add_discovery(record1)
        
        # Try to add duplicate
        record2 = PDFRecord(
            paper_id="paper_1",
            pdf_url="https://openreview.net/paper_1.pdf",
            source="openreview",
            discovery_timestamp=datetime.now(),
            confidence_score=0.8,
            version_info={},
            validation_status="validated"
        )
        
        framework._add_discovery(record2)
        
        # Should keep higher confidence version
        assert len(framework.discovered_papers) == 1
        assert framework.discovered_papers["paper_1"].source == "arxiv"
        assert framework.discovered_papers["paper_1"].confidence_score == 0.9
    
    def test_url_tracking(self):
        """Test URL to paper mapping."""
        framework = PDFDiscoveryFramework()
        
        record = PDFRecord(
            paper_id="paper_1",
            pdf_url="https://example.com/paper.pdf",
            source="test",
            discovery_timestamp=datetime.now(),
            confidence_score=0.9,
            version_info={},
            validation_status="validated"
        )
        
        framework._add_discovery(record)
        
        assert "https://example.com/paper.pdf" in framework.url_to_papers
        assert "paper_1" in framework.url_to_papers["https://example.com/paper.pdf"]
    
    def test_source_timeout_handling(self):
        """Test that slow sources don't block others."""
        framework = PDFDiscoveryFramework()
        
        # Add one very slow source
        slow_collector = MockCollector("very_slow", delay=0.2)
        slow_collector.timeout = 0.1  # 100ms timeout
        
        framework.add_collector(slow_collector)
        framework.add_collector(MockCollector("fast"))
        
        papers = [Paper(paper_id="paper_1", title="Test", authors=[], 
                       year=2024, citations=0, venue="Test")]
        
        start_time = time.time()
        result = framework.discover_pdfs(papers)
        elapsed = time.time() - start_time
        
        # The slow source will timeout, but fast source should complete
        # Total time should be dominated by the timeout (0.1s) not the delay (0.2s)
        assert elapsed < 0.3  # Should complete around timeout time
        assert result.discovered_count == 1
        assert result.records[0].source == "fast"
    
    def test_progress_callback(self):
        """Test progress reporting during discovery."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockCollector("source1"))
        framework.add_collector(MockCollector("source2"))
        
        progress_updates = []
        
        def progress_callback(completed: int, total: int, source: str):
            progress_updates.append((completed, total, source))
        
        papers = [Paper(paper_id=f"paper_{i}", title=f"Test {i}", authors=[], 
                       year=2024, citations=0, venue="Test") for i in range(3)]
        
        result = framework.discover_pdfs(papers, progress_callback=progress_callback)
        
        # Should have progress updates
        assert len(progress_updates) > 0
        assert any(source == "source1" for _, _, source in progress_updates)
        assert any(source == "source2" for _, _, source in progress_updates)
    
    def test_empty_paper_list(self):
        """Test discovery with empty paper list."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockCollector("test"))
        
        result = framework.discover_pdfs([])
        
        assert result.total_papers == 0
        assert result.discovered_count == 0
        assert len(result.records) == 0
    
    def test_no_collectors(self):
        """Test discovery with no collectors."""
        framework = PDFDiscoveryFramework()
        
        papers = [Paper(paper_id="paper_1", title="Test", authors=[], 
                       year=2024, citations=0, venue="Test")]
        
        result = framework.discover_pdfs(papers)
        
        assert result.total_papers == 1
        assert result.discovered_count == 0
        assert len(result.records) == 0
        assert len(result.failed_papers) == 1
    
    def test_statistics_aggregation(self):
        """Test aggregation of collector statistics."""
        framework = PDFDiscoveryFramework()
        
        collector1 = MockCollector("source1", fail_papers=["paper_2"])
        collector2 = MockCollector("source2", fail_papers=["paper_3"])
        
        framework.add_collector(collector1)
        framework.add_collector(collector2)
        
        papers = [Paper(paper_id=f"paper_{i}", title=f"Test {i}", authors=[], 
                       year=2024, citations=0, venue="Test") for i in range(4)]
        
        result = framework.discover_pdfs(papers)
        
        # Check source statistics
        assert "source1" in result.source_statistics
        assert "source2" in result.source_statistics
        assert result.source_statistics["source1"]["attempted"] == 4
        assert result.source_statistics["source1"]["successful"] == 3
        assert result.source_statistics["source2"]["attempted"] == 4
        assert result.source_statistics["source2"]["successful"] == 3