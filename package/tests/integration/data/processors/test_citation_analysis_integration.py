"""Integration tests for citation analysis system."""

import pytest
from datetime import datetime
from unittest.mock import patch
import numpy as np

from src.data.models import Paper, Author
from src.data.collectors.state_structures import VenueConfig
from src.data.processors.citation_analyzer import CitationAnalyzer
from src.data.processors.breakthrough_detector import BreakthroughDetector
from src.data.processors.adaptive_threshold_calculator import AdaptiveThresholdCalculator


class TestCitationAnalysisIntegration:
    """Test integration of citation analysis components."""
    
    @pytest.fixture
    def venue_configs(self):
        """Create realistic venue configurations."""
        return [
            VenueConfig(venue_name="NeurIPS", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=100),
            VenueConfig(venue_name="ICML", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=100),
            VenueConfig(venue_name="ICLR", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=100),
            VenueConfig(venue_name="CVPR", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=80),
            VenueConfig(venue_name="AAAI", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=80),
            VenueConfig(venue_name="UAI", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=50),
            VenueConfig(venue_name="AISTATS", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=50)
        ]
    
    @pytest.fixture
    def realistic_papers(self):
        """Create realistic paper dataset with various citation patterns."""
        papers = []
        
        # High-impact papers from top venues
        venues = ["NeurIPS", "ICML", "ICLR"]
        for venue in venues:
            for year in [2020, 2021, 2022, 2023]:
                # Add some high-impact papers
                for i in range(5):
                    citations = np.random.poisson(100 - (2023 - year) * 20)
                    papers.append(Paper(
                        paper_id=f"{venue}_{year}_high_{i}",
                        title=f"High Impact {venue} Paper {i}",
                        abstract="This paper presents state-of-the-art results using novel methods.",
                        venue=venue,
                        normalized_venue=venue,
                        year=year,
                        citations=max(citations, 10),
                        authors=[Author(name=f"Famous Author {i}")]
                    ))
                
                # Add medium-impact papers
                for i in range(10):
                    citations = np.random.poisson(30 - (2023 - year) * 5)
                    papers.append(Paper(
                        paper_id=f"{venue}_{year}_med_{i}",
                        title=f"Medium Impact {venue} Paper {i}",
                        venue=venue,
                        normalized_venue=venue,
                        year=year,
                        citations=max(citations, 0),
                        authors=[Author(name=f"Regular Author {i}")]
                    ))
        
        # Add breakthrough papers
        breakthrough_titles = [
            "Attention Is All You Need: Introducing the Transformer Architecture",
            "BERT: Pre-training of Deep Bidirectional Transformers",
            "GPT-3: Language Models are Few-Shot Learners",
            "Diffusion Models Beat GANs on Image Synthesis"
        ]
        
        for idx, title in enumerate(breakthrough_titles):
            papers.append(Paper(
                paper_id=f"breakthrough_{idx}",
                title=title,
                abstract="We present a groundbreaking new approach that achieves unprecedented results.",
                venue="NeurIPS" if idx % 2 == 0 else "ICML",
                normalized_venue="NeurIPS" if idx % 2 == 0 else "ICML",
                year=2022 + idx % 2,
                citations=200 + idx * 50,
                authors=[
                    Author(name="Geoffrey Hinton"),
                    Author(name="Yann LeCun")
                ]
            ))
        
        # Add zero-citation papers
        for i in range(20):
            papers.append(Paper(
                paper_id=f"zero_{i}",
                title=f"Zero Citation Paper {i}",
                venue="AISTATS",
                normalized_venue="AISTATS",
                year=2023,
                citations=0,
                authors=[Author(name=f"New Author {i}")]
            ))
        
        return papers
    
    def test_end_to_end_citation_analysis(self, venue_configs, realistic_papers):
        """Test complete citation analysis workflow."""
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(venue_configs)
        
        # Step 1: Analyze citation distributions
        analysis_report = analyzer.analyze_citation_distributions(realistic_papers)
        
        assert analysis_report.papers_analyzed == len(realistic_papers)
        assert len(analysis_report.venue_analysis) >= 4  # At least 4 venues
        assert len(analysis_report.breakthrough_candidates) >= 4  # The breakthrough papers
        assert len(analysis_report.zero_citation_papers) == 20
        
        # Step 2: Filter papers with breakthrough preservation
        filter_result = analyzer.filter_papers_by_citations(
            realistic_papers, 
            preserve_breakthroughs=True
        )
        
        assert filter_result.filtered_count < filter_result.original_count
        assert filter_result.breakthrough_preservation_rate > 0.9  # Most breakthroughs preserved
        
        # Step 3: Validate filtering quality
        quality_report = analyzer.validate_filtering_quality(
            realistic_papers,
            filter_result.papers_above_threshold
        )
        
        assert quality_report.venue_coverage_rate > 0.5  # At least half venues preserved
        assert quality_report.impact_preservation_rate > 0.8  # Most high-impact preserved
        assert quality_report.citation_improvement_ratio > 1.0  # Better average citations
    
    def test_adaptive_threshold_across_venues(self, venue_configs):
        """Test that adaptive thresholds vary appropriately across venues."""
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(venue_configs)
        
        # Create papers for different venues
        papers_by_venue = {
            "NeurIPS": [],  # tier1
            "CVPR": [],     # tier2
            "UAI": []       # tier3
        }
        
        for venue in papers_by_venue:
            for i in range(20):
                papers_by_venue[venue].append(Paper(
                    paper_id=f"{venue}_{i}",
                    title=f"{venue} Paper {i}",
                    venue=venue,
                    normalized_venue=venue,
                    year=2023,
                    citations=np.random.poisson(30 if venue == "NeurIPS" else 20 if venue == "CVPR" else 10),
                    authors=[Author(name=f"Author {i}")]
                ))
        
        # Calculate thresholds
        thresholds = {}
        for venue, papers in papers_by_venue.items():
            threshold = analyzer.calculate_adaptive_threshold(venue, 2023, papers)
            thresholds[venue] = threshold.threshold
        
        # Verify tier-based ordering
        assert thresholds["NeurIPS"] >= thresholds["CVPR"]
        assert thresholds["CVPR"] >= thresholds["UAI"]
    
    def test_breakthrough_detection_integration(self, realistic_papers):
        """Test breakthrough detection integrated with citation analysis."""
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            detector = BreakthroughDetector()
        
        breakthrough_papers = detector.detect_breakthrough_papers(realistic_papers)
        
        # Should detect the explicitly created breakthrough papers
        breakthrough_ids = {bp.paper.paper_id for bp in breakthrough_papers}
        assert any("breakthrough_" in pid for pid in breakthrough_ids)
        
        # Breakthrough papers should have high scores
        for bp in breakthrough_papers:
            if "breakthrough_" in bp.paper.paper_id:
                assert bp.breakthrough_score > 0.7
                assert len(bp.breakthrough_indicators) > 2
                assert bp.citation_velocity_score > 0.5
    
    def test_filtering_preserves_venue_diversity(self, venue_configs, realistic_papers):
        """Test that filtering maintains representation from all venues."""
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(venue_configs)
        
        # Get original venue distribution
        original_venues = set(p.normalized_venue for p in realistic_papers if p.normalized_venue)
        
        # Filter with moderate threshold
        filter_result = analyzer.filter_papers_by_citations(realistic_papers)
        
        # Check venue preservation
        filtered_venues = set(p.normalized_venue for p in filter_result.papers_above_threshold if p.normalized_venue)
        
        # Should preserve most venues
        venue_preservation_rate = len(filtered_venues) / len(original_venues)
        assert venue_preservation_rate > 0.7
    
    def test_year_based_threshold_adaptation(self, venue_configs):
        """Test that thresholds adapt based on paper age."""
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            with patch('src.data.processors.adaptive_threshold_calculator.datetime') as mock_datetime:
                mock_datetime.now.return_value = datetime(2024, 1, 1)
                
                calculator = AdaptiveThresholdCalculator()
                calculator.current_year = 2024
        
        papers_2023 = [
            Paper(paper_id=str(i), title=f"Paper {i}", venue="ICML", year=2023, citations=i*5, authors=[Author(name="Test")])
            for i in range(20)
        ]
        
        papers_2020 = [
            Paper(paper_id=str(i), title=f"Paper {i}", venue="ICML", year=2020, citations=i*5, authors=[Author(name="Test")])
            for i in range(20)
        ]
        
        # Calculate thresholds
        threshold_2023 = calculator.calculate_venue_threshold("ICML", 2023, papers_2023, "tier1")
        threshold_2020 = calculator.calculate_venue_threshold("ICML", 2020, papers_2020, "tier1")
        
        # Older papers should have higher threshold
        assert threshold_2020 > threshold_2023
    
    def test_quality_metrics_consistency(self, venue_configs, realistic_papers):
        """Test consistency of quality metrics across analysis and filtering."""
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(venue_configs)
        
        # Analyze
        analysis_report = analyzer.analyze_citation_distributions(realistic_papers)
        
        # Filter
        filter_result = analyzer.filter_papers_by_citations(realistic_papers)
        
        # Validate
        quality_report = analyzer.validate_filtering_quality(
            realistic_papers,
            filter_result.papers_above_threshold
        )
        
        # Check consistency
        assert quality_report.total_papers_original == analysis_report.papers_analyzed
        assert quality_report.total_papers_filtered == filter_result.filtered_count
        
        # Quality should improve after filtering
        original_mean = analysis_report.quality_indicators.get("mean_citations", 0)
        filtered_mean = quality_report.average_citations_filtered
        assert filtered_mean >= original_mean
    
    def test_performance_with_mixed_data_quality(self, venue_configs):
        """Test system performance with mixed data quality (missing values, etc.)."""
        mixed_papers = []
        
        # Papers with complete data
        for i in range(100):
            mixed_papers.append(Paper(
                paper_id=f"complete_{i}",
                title=f"Complete Paper {i}",
                venue="NeurIPS",
                normalized_venue="NeurIPS",
                year=2022,
                citations=np.random.poisson(20),
                authors=[Author(name=f"Author {i}")]
            ))
        
        # Papers with missing citations
        for i in range(50):
            mixed_papers.append(Paper(
                paper_id=f"no_cite_{i}",
                title=f"No Citation Paper {i}",
                venue="ICML",
                normalized_venue="ICML",
                year=2022,
                citations=None,
                authors=[Author(name=f"Author {i}")]
            ))
        
        # Papers with missing venue
        for i in range(30):
            mixed_papers.append(Paper(
                paper_id=f"no_venue_{i}",
                title=f"No Venue Paper {i}",
                venue=None,
                normalized_venue=None,
                year=2022,
                citations=10,
                authors=[Author(name=f"Author {i}")]
            ))
        
        with patch('src.data.processors.breakthrough_detector.Path.exists', return_value=False):
            analyzer = CitationAnalyzer(venue_configs)
        
        # Should handle mixed data without errors
        analysis_report = analyzer.analyze_citation_distributions(mixed_papers)
        filter_result = analyzer.filter_papers_by_citations(mixed_papers)
        
        assert analysis_report.papers_analyzed == len(mixed_papers)
        assert filter_result.filtering_statistics.get("no_citation_data", 0) == 50