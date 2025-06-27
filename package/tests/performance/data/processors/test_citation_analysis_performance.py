"""Performance tests for citation analysis system."""

import pytest
import time
import numpy as np
from datetime import datetime
from unittest.mock import patch
import psutil
import os

from src.data.models import Paper, Author
from src.data.collectors.state_structures import VenueConfig
from src.data.processors.citation_analyzer import CitationAnalyzer
from src.data.processors.breakthrough_detector import BreakthroughDetector


class TestCitationAnalysisPerformance:
    """Test performance characteristics of citation analysis."""
    
    @pytest.fixture
    def large_venue_configs(self):
        """Create venue configurations for performance testing."""
        venues = ["NeurIPS", "ICML", "ICLR", "CVPR", "AAAI", "IJCAI", "ECCV", "ICCV", 
                 "ACL", "EMNLP", "NAACL", "UAI", "AISTATS", "KDD", "WWW", "SIGIR"]
        
        return [
            VenueConfig(
                venue_name=venue,
                target_years=[2018, 2019, 2020, 2021, 2022, 2023],
                max_papers_per_year=200
            )
            for venue in venues
        ]
    
    def generate_large_dataset(self, num_papers: int) -> list[Paper]:
        """Generate large dataset for performance testing."""
        papers = []
        venues = ["NeurIPS", "ICML", "ICLR", "CVPR", "AAAI", "IJCAI", "ECCV", "ICCV"]
        
        # Use numpy for efficient generation
        np.random.seed(42)  # For reproducibility
        
        # Generate in batches for efficiency
        batch_size = 1000
        num_batches = num_papers // batch_size
        
        for batch in range(num_batches):
            # Generate batch data using numpy
            venue_indices = np.random.randint(0, len(venues), batch_size)
            years = np.random.randint(2018, 2024, batch_size)
            citations = np.random.poisson(20, batch_size)
            
            for i in range(batch_size):
                paper_id = batch * batch_size + i
                papers.append(Paper(
                    paper_id=f"paper_{paper_id}",
                    title=f"Paper {paper_id}",
                    abstract="This is a test paper for performance evaluation.",
                    venue=venues[venue_indices[i]],
                    normalized_venue=venues[venue_indices[i]],
                    year=int(years[i]),
                    citations=int(citations[i]),
                    authors=[
                        Author(name=f"Author {paper_id % 1000}"),
                        Author(name=f"CoAuthor {paper_id % 500}")
                    ]
                ))
        
        return papers
    
    def test_analyze_50k_papers_performance(self, large_venue_configs):
        """Test analysis performance with 50,000 papers."""
        papers = self.generate_large_dataset(50000)
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(large_venue_configs)
        
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        report = analyzer.analyze_citation_distributions(papers)
        
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        duration = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Performance requirements
        assert duration < 120, f"Analysis took {duration:.2f}s, should be < 120s"
        assert memory_used < 1024, f"Used {memory_used:.2f}MB, should be < 1GB"
        
        # Verify correctness
        assert report.papers_analyzed == 50000
        assert len(report.venue_analysis) > 0
        assert len(report.year_analysis) > 0
        
        print(f"\nPerformance metrics for 50K papers:")
        print(f"  Time: {duration:.2f} seconds")
        print(f"  Memory: {memory_used:.2f} MB")
        print(f"  Papers/second: {50000/duration:.0f}")
    
    def test_analyze_100k_papers_performance(self, large_venue_configs):
        """Test analysis performance with 100,000 papers."""
        papers = self.generate_large_dataset(100000)
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(large_venue_configs)
        
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        report = analyzer.analyze_citation_distributions(papers)
        
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        duration = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Relaxed requirements for 100K papers
        assert duration < 240, f"Analysis took {duration:.2f}s, should be < 240s"
        assert memory_used < 1024, f"Used {memory_used:.2f}MB, should be < 1GB"
        
        print(f"\nPerformance metrics for 100K papers:")
        print(f"  Time: {duration:.2f} seconds")
        print(f"  Memory: {memory_used:.2f} MB")
        print(f"  Papers/second: {100000/duration:.0f}")
    
    def test_breakthrough_detection_performance(self):
        """Test breakthrough detection performance per paper."""
        papers = self.generate_large_dataset(1000)
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            detector = BreakthroughDetector()
        
        # Test individual paper processing time
        times = []
        for paper in papers[:100]:  # Test first 100 papers
            start = time.perf_counter()
            score = detector.calculate_breakthrough_score(paper)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = np.mean(times)
        max_time = np.max(times)
        
        # Requirement: <10ms per paper
        assert avg_time < 10, f"Average time {avg_time:.2f}ms, should be < 10ms"
        assert max_time < 20, f"Max time {max_time:.2f}ms, should be < 20ms"
        
        print(f"\nBreakthrough detection performance:")
        print(f"  Average: {avg_time:.2f}ms per paper")
        print(f"  Max: {max_time:.2f}ms per paper")
        print(f"  Min: {np.min(times):.2f}ms per paper")
    
    def test_filtering_performance(self, large_venue_configs):
        """Test filtering performance with large dataset."""
        papers = self.generate_large_dataset(50000)
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(large_venue_configs)
        
        start_time = time.time()
        
        result = analyzer.filter_papers_by_citations(papers, preserve_breakthroughs=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be fast even with breakthrough preservation
        assert duration < 60, f"Filtering took {duration:.2f}s, should be < 60s"
        
        print(f"\nFiltering performance for 50K papers:")
        print(f"  Time: {duration:.2f} seconds")
        print(f"  Papers/second: {50000/duration:.0f}")
        print(f"  Filtered count: {result.filtered_count}")
        print(f"  Reduction: {(1 - result.filtered_count/result.original_count)*100:.1f}%")
    
    def test_threshold_calculation_performance(self, large_venue_configs):
        """Test adaptive threshold calculation performance."""
        papers = self.generate_large_dataset(10000)
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(large_venue_configs)
        
        # Group papers by venue/year
        venue_year_groups = {}
        for paper in papers:
            key = (paper.venue, paper.year)
            if key not in venue_year_groups:
                venue_year_groups[key] = []
            venue_year_groups[key].append(paper)
        
        start_time = time.time()
        
        # Calculate thresholds for all venue/year combinations
        thresholds = {}
        for (venue, year), group_papers in venue_year_groups.items():
            threshold = analyzer.calculate_adaptive_threshold(venue, year, group_papers)
            thresholds[(venue, year)] = threshold
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Requirement: <1 second per venue/year
        avg_time_per_group = duration / len(venue_year_groups)
        assert avg_time_per_group < 1.0, f"Average {avg_time_per_group:.2f}s per group, should be < 1s"
        
        print(f"\nThreshold calculation performance:")
        print(f"  Total groups: {len(venue_year_groups)}")
        print(f"  Total time: {duration:.2f} seconds")
        print(f"  Average per group: {avg_time_per_group:.3f} seconds")
    
    def test_memory_efficiency_scaling(self, large_venue_configs):
        """Test memory usage scales linearly with data size."""
        sizes = [10000, 20000, 40000]
        memory_usage = []
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(large_venue_configs)
        
        for size in sizes:
            papers = self.generate_large_dataset(size)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            
            report = analyzer.analyze_citation_distributions(papers)
            
            end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            memory_used = end_memory - start_memory
            memory_usage.append(memory_used)
            
            print(f"\nMemory for {size} papers: {memory_used:.2f} MB")
        
        # Check that memory scales roughly linearly
        # Ratio between consecutive sizes should be < 2.5 (allowing for overhead)
        for i in range(1, len(memory_usage)):
            ratio = memory_usage[i] / memory_usage[i-1]
            size_ratio = sizes[i] / sizes[i-1]
            assert ratio < size_ratio * 1.5, f"Memory scaling non-linear: {ratio:.2f}x for {size_ratio}x data"
    
    def test_percentile_calculation_performance(self):
        """Test performance of percentile calculations."""
        # Generate various citation distributions
        distributions = [
            np.random.poisson(20, 10000),      # Poisson
            np.random.lognormal(3, 1, 10000),  # Log-normal (common for citations)
            np.random.exponential(20, 10000),  # Exponential
            np.zeros(10000)                    # All zeros (edge case)
        ]
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer([])
        
        for dist_name, citations in zip(["Poisson", "Log-normal", "Exponential", "Zeros"], distributions):
            citations = [int(c) for c in citations]
            
            start = time.perf_counter()
            percentiles = analyzer._calculate_percentiles(citations)
            duration = (time.perf_counter() - start) * 1000
            
            assert duration < 50, f"{dist_name} took {duration:.2f}ms, should be < 50ms"
            print(f"\nPercentile calculation for {dist_name}: {duration:.2f}ms")
    
    def test_concurrent_processing_simulation(self, large_venue_configs):
        """Simulate concurrent processing scenarios."""
        # Generate shared dataset
        papers = self.generate_large_dataset(30000)
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(large_venue_configs)
        
        # Simulate multiple operations
        operations = []
        
        # Operation 1: Full analysis
        start = time.time()
        report = analyzer.analyze_citation_distributions(papers)
        operations.append(("Analysis", time.time() - start))
        
        # Operation 2: Filtering
        start = time.time()
        filter_result = analyzer.filter_papers_by_citations(papers)
        operations.append(("Filtering", time.time() - start))
        
        # Operation 3: Quality validation
        start = time.time()
        quality = analyzer.validate_filtering_quality(papers, filter_result.papers_above_threshold)
        operations.append(("Validation", time.time() - start))
        
        # All operations should complete efficiently
        total_time = sum(duration for _, duration in operations)
        assert total_time < 180, f"Total time {total_time:.2f}s, should be < 180s"
        
        print("\nConcurrent operations simulation:")
        for op_name, duration in operations:
            print(f"  {op_name}: {duration:.2f} seconds")
        print(f"  Total: {total_time:.2f} seconds")