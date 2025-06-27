"""
Example usage of Computational Research Filtering (Issue #8).
Shows how to integrate the filtering system with paper collection.
"""

import logging
from typing import List

from src.data.models import Paper, Author
from src.data.collectors.api_integration_layer import APIIntegrationLayer
from src.filtering import (
    ComputationalResearchFilter,
    FilteringConfig,
    FilteringPipelineIntegration,
    setup_computational_filtering
)
from src.monitoring.metrics_collector import MetricsCollector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_filtering():
    """Example of basic computational filtering."""
    print("\n=== Basic Computational Filtering Example ===")
    
    # Create filter with custom configuration
    config = FilteringConfig(
        min_computational_richness=0.4,  # Moderate computational content required
        min_venue_score=0.5,             # Accept mid-tier venues and above
        allow_industry_collaboration=True,  # Allow industry papers
        min_combined_score=0.5           # Overall threshold
    )
    
    filter = ComputationalResearchFilter(config)
    
    # Example papers
    papers = [
        Paper(
            title="Deep Reinforcement Learning for Robotics Control",
            authors=[
                Author(name="Alice Chen", affiliation="MIT CSAIL"),
                Author(name="Bob Smith", affiliation="Google DeepMind")
            ],
            venue="ICRA 2024",
            year=2024,
            citations=15,
            abstract="""We present a deep reinforcement learning approach for 
            robotic control tasks. Our method uses a novel neural network 
            architecture trained on 100K hours of simulation data. Experiments 
            on real robots demonstrate 90% success rate on manipulation tasks."""
        ),
        Paper(
            title="Survey of Ethical Considerations in AI",
            authors=[
                Author(name="Carol Johnson", affiliation="Philosophy Department")
            ],
            venue="AI Ethics Conference",
            year=2024,
            citations=5,
            abstract="A comprehensive survey of ethical considerations in AI systems."
        ),
        Paper(
            title="Efficient Graph Algorithms for Social Network Analysis",
            authors=[
                Author(name="David Lee", affiliation="Stanford University"),
                Author(name="Eve Wang", affiliation="Facebook Research")
            ],
            venue="WWW 2024",
            year=2024,
            citations=25,
            abstract="""We develop efficient algorithms for analyzing large-scale 
            social networks. Our parallel implementation processes graphs with 
            billions of edges in under an hour using distributed computing."""
        )
    ]
    
    # Filter papers
    results = filter.batch_filter(papers, return_all=True)
    
    # Display results
    for result in results:
        print(f"\nPaper: {result.paper.title}")
        print(f"  Passed: {result.passed}")
        print(f"  Score: {result.score:.2f}")
        print(f"  Computational Richness: {result.computational_analysis.computational_richness:.2f}")
        print(f"  Venue Score: {result.venue_analysis.venue_score:.2f}")
        print(f"  Author Category: {result.authorship_analysis.category}")
        print(f"  Reasons: {result.reasons[0]}")
    
    # Show statistics
    stats = filter.get_statistics()
    print(f"\nFiltering Statistics:")
    print(f"  Total Processed: {stats['total_processed']}")
    print(f"  Pass Rate: {stats['pass_rate']:.1%}")


def example_pipeline_integration():
    """Example of integrating filtering with API collection pipeline."""
    print("\n\n=== Pipeline Integration Example ===")
    
    # Create API integration layer (mock for example)
    api_config = {
        'semantic_scholar': {'api_key': 'mock_key'},
        'openalex': {'email': 'test@example.com'}
    }
    api_layer = APIIntegrationLayer(api_config)
    
    # Create monitoring system (mock for example)
    monitoring = MetricsCollector()
    
    # Set up computational filtering with custom config
    filter_config = FilteringConfig(
        min_computational_richness=0.3,
        min_venue_score=0.4,
        require_academic_eligible=False,  # Don't require pure academic
        allow_industry_collaboration=True,  # Allow industry papers
        strict_mode=False  # Use combined scoring
    )
    
    # Easy one-line setup
    pipeline = setup_computational_filtering(
        api_layer=api_layer,
        monitoring_system=monitoring,
        filter_config=filter_config
    )
    
    print("Computational filtering integrated with collection pipeline!")
    print("\nFiltering Configuration:")
    print(f"  Min Computational Richness: {filter_config.min_computational_richness}")
    print(f"  Min Venue Score: {filter_config.min_venue_score}")
    print(f"  Allow Industry: {filter_config.allow_industry_collaboration}")
    print(f"  Strict Mode: {filter_config.strict_mode}")
    
    # Example: Process some papers through the pipeline
    test_papers = [
        Paper(
            title=f"Machine Learning Paper {i}",
            authors=[Author(name=f"Author {i}", affiliation="MIT" if i % 2 else "Google")],
            venue="NeurIPS" if i < 3 else "Workshop",
            year=2024,
            citations=i * 10,
            abstract="Neural network training with distributed systems." if i < 3 
                    else "Basic analysis of data."
        )
        for i in range(5)
    ]
    
    # Filter papers (this would normally happen inside the API layer)
    filtered_papers = pipeline.filter_papers_realtime(test_papers)
    
    print(f"\nFiltered {len(test_papers)} papers -> {len(filtered_papers)} passed")
    
    # Get performance stats
    perf_stats = pipeline.get_performance_stats()
    print(f"\nPerformance Statistics:")
    print(f"  Average filter time: {perf_stats['avg_filter_time_ms']:.1f}ms per paper")
    print(f"  Papers per second: {perf_stats['papers_per_second']:.1f}")
    
    # Clean up
    pipeline.shutdown()


def example_advanced_configuration():
    """Example of advanced filtering configuration."""
    print("\n\n=== Advanced Configuration Example ===")
    
    # Create strict configuration for high-quality papers only
    strict_config = FilteringConfig(
        # Computational requirements
        min_computational_richness=0.6,  # High computational content
        min_computational_confidence=0.7,  # High confidence required
        
        # Author requirements  
        require_academic_eligible=True,  # Academic papers only
        allow_industry_collaboration=False,  # No industry authors
        min_authorship_confidence=0.8,  # High confidence in classification
        
        # Venue requirements
        min_venue_score=0.7,  # Top venues only
        min_domain_relevance=0.8,  # Highly relevant domains
        max_venue_importance_ranking=2,  # Top 2 tiers only
        
        # Overall requirements
        min_combined_score=0.7,  # High overall score
        strict_mode=True  # ALL criteria must be met
    )
    
    filter = ComputationalResearchFilter(strict_config)
    
    # Test with various papers
    test_cases = [
        ("Top ML Paper", "NeurIPS", "MIT", True),
        ("Workshop Paper", "ICML Workshop", "Stanford", False),
        ("Industry Paper", "CVPR", "Google Research", False),
        ("Low Venue Paper", "Unknown Conference", "MIT", False)
    ]
    
    for title, venue, affiliation, expected_pass in test_cases:
        paper = Paper(
            title=f"{title}: Deep Learning Advances",
            authors=[Author(name="Test Author", affiliation=affiliation)],
            venue=venue,
            year=2024,
            citations=50,
            abstract="""Advanced deep learning algorithm with novel architecture. 
            Trained on massive datasets using distributed GPUs. State-of-the-art 
            results on multiple benchmarks with extensive experiments."""
        )
        
        result = filter.filter_paper(paper)
        print(f"\n{title}:")
        print(f"  Expected to pass: {expected_pass}")
        print(f"  Actually passed: {result.passed}")
        print(f"  Score: {result.score:.2f}")
        if not result.passed:
            print(f"  Failed because: {result.reasons[0]}")


def example_custom_callbacks():
    """Example of using callbacks for custom processing."""
    print("\n\n=== Custom Callbacks Example ===")
    
    # Create pipeline
    pipeline = FilteringPipelineIntegration()
    
    # Track papers by venue
    venue_stats = {}
    
    def track_venue_stats(result):
        """Custom callback to track venue statistics."""
        venue = result.paper.venue
        if venue not in venue_stats:
            venue_stats[venue] = {'total': 0, 'passed': 0}
        
        venue_stats[venue]['total'] += 1
        if result.passed:
            venue_stats[venue]['passed'] += 1
    
    # Set callbacks
    pipeline.on_paper_passed = lambda r: track_venue_stats(r)
    pipeline.on_paper_filtered = lambda r: track_venue_stats(r)
    
    # Process papers from different venues
    papers = []
    for venue in ["NeurIPS", "ICML", "CVPR", "CHI", "Unknown Conf"]:
        for i in range(3):
            papers.append(Paper(
                title=f"{venue} Paper {i}",
                authors=[Author(name="Author", affiliation="University")],
                venue=venue,
                year=2024,
                citations=10,
                abstract="Machine learning research." if venue in ["NeurIPS", "ICML", "CVPR"] 
                        else "User study research."
            ))
    
    # Filter papers
    pipeline.filter_papers_realtime(papers)
    
    # Display venue statistics
    print("\nVenue Statistics:")
    for venue, stats in venue_stats.items():
        pass_rate = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {venue}: {stats['passed']}/{stats['total']} passed ({pass_rate:.0%})")
    
    pipeline.shutdown()


if __name__ == "__main__":
    # Run all examples
    example_basic_filtering()
    example_pipeline_integration()
    example_advanced_configuration()
    example_custom_callbacks()
    
    print("\n\nAll examples completed successfully!")