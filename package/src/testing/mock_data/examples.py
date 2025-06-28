"""Example usage of the mock data generation framework."""

import json
from pathlib import Path

from src.testing.mock_data import DataQuality, MockDataConfig, MockDataGenerator


def generate_sample_datasets():
    """Generate sample datasets for different quality levels."""
    generator = MockDataGenerator()
    output_dir = Path("sample_data")
    output_dir.mkdir(exist_ok=True)

    # Generate normal quality dataset
    print("Generating normal quality dataset...")
    normal_config = MockDataConfig(quality=DataQuality.NORMAL, size=100, seed=42)
    normal_papers = generator.generate(normal_config)

    # Save to JSON with datetime handling
    normal_data = [paper.to_dict() for paper in normal_papers]
    with open(output_dir / "normal_quality_papers.json", "w") as f:
        json.dump(normal_data, f, indent=2, default=str)

    print(f"✓ Generated {len(normal_papers)} normal quality papers")

    # Generate edge case dataset
    print("\nGenerating edge case dataset...")
    edge_config = MockDataConfig(quality=DataQuality.EDGE_CASE, size=50, seed=123)
    edge_papers = generator.generate(edge_config)

    edge_data = [paper.to_dict() for paper in edge_papers]
    with open(output_dir / "edge_case_papers.json", "w") as f:
        json.dump(edge_data, f, indent=2, default=str)

    print(f"✓ Generated {len(edge_papers)} edge case papers")

    # Generate corrupted dataset
    print("\nGenerating corrupted dataset...")
    corrupted_config = MockDataConfig(quality=DataQuality.CORRUPTED, size=30, seed=999)
    corrupted_papers = generator.generate(corrupted_config)

    corrupted_data = [paper.to_dict() for paper in corrupted_papers]
    with open(output_dir / "corrupted_papers.json", "w") as f:
        json.dump(corrupted_data, f, indent=2, default=str)

    print(f"✓ Generated {len(corrupted_papers)} corrupted papers")

    # Generate statistics
    print("\n=== Dataset Statistics ===")

    # Normal dataset stats
    print("\nNormal Quality Dataset:")
    papers_with_comp = sum(1 for p in normal_papers if p.computational_analysis)
    papers_with_auth = sum(1 for p in normal_papers if p.authorship_analysis)
    papers_with_venue = sum(1 for p in normal_papers if p.venue_analysis)
    print(
        f"  - Papers with computational analysis: {papers_with_comp}/{len(normal_papers)}"
    )
    print(
        f"  - Papers with authorship analysis: {papers_with_auth}/{len(normal_papers)}"
    )
    print(f"  - Papers with venue analysis: {papers_with_venue}/{len(normal_papers)}")

    # Citation distribution
    citations = [p.citations for p in normal_papers]
    print(f"  - Citation range: {min(citations)} - {max(citations)}")
    print(f"  - Average citations: {sum(citations) / len(citations):.1f}")

    # Year distribution
    years = [p.year for p in normal_papers]
    year_counts = {}
    for year in years:
        year_counts[year] = year_counts.get(year, 0) + 1
    print("  - Year distribution:")
    for year in sorted(year_counts.keys()):
        print(f"    {year}: {year_counts[year]} papers")

    print(f"\n✓ Sample datasets saved to {output_dir.absolute()}")


def demonstrate_usage():
    """Demonstrate various usage patterns."""
    generator = MockDataGenerator()

    print("=== Mock Data Generator Usage Examples ===\n")

    # Example 1: Basic usage
    print("1. Basic usage - Generate 10 normal quality papers:")
    config = MockDataConfig(quality=DataQuality.NORMAL, size=10)
    papers = generator.generate(config)
    print(f"   Generated {len(papers)} papers")
    print(f"   First paper title: {papers[0].title}")
    print(f"   Authors: {', '.join(a.name for a in papers[0].authors)}")

    # Example 2: Validation
    print("\n2. Validation - Check if generated data meets quality requirements:")
    is_valid = generator.validate_output(papers, config)
    print(f"   Validation result: {is_valid}")

    # Example 3: Custom seed for reproducibility
    print("\n3. Reproducible generation with custom seed:")
    config1 = MockDataConfig(quality=DataQuality.NORMAL, size=5, seed=12345)
    config2 = MockDataConfig(quality=DataQuality.NORMAL, size=5, seed=12345)
    papers1 = generator.generate(config1)
    papers2 = generator.generate(config2)
    print(
        f"   Papers match: {all(p1.paper_id == p2.paper_id for p1, p2 in zip(papers1, papers2))}"
    )

    # Example 4: Edge cases for testing
    print("\n4. Generate edge case data for testing:")
    edge_config = MockDataConfig(quality=DataQuality.EDGE_CASE, size=5)
    edge_papers = generator.generate(edge_config)
    for i, paper in enumerate(edge_papers[:3]):
        print(f"   Paper {i + 1}:")
        print(
            f"     - Abstract length: {len(paper.abstract) if paper.abstract else 'None'}"
        )
        print(f"     - Keywords: {len(paper.keywords) if paper.keywords else 'None'}")
        print(f"     - Citation velocity: {paper.citation_velocity}")

    # Example 5: Integration with existing code
    print("\n5. Integration example - Filter papers by venue:")
    papers = generator.generate(MockDataConfig(quality=DataQuality.NORMAL, size=50))
    neurips_papers = [p for p in papers if "NeurIPS" in p.venue]
    print(f"   Found {len(neurips_papers)} NeurIPS papers out of {len(papers)}")

    # Example 6: Performance testing
    print("\n6. Performance test - Generate large dataset:")
    import time

    start = time.time()
    large_config = MockDataConfig(quality=DataQuality.NORMAL, size=1000)
    large_papers = generator.generate(large_config)
    elapsed = time.time() - start
    print(f"   Generated {len(large_papers)} papers in {elapsed:.2f} seconds")
    print(f"   Rate: {len(large_papers) / elapsed:.0f} papers/second")


if __name__ == "__main__":
    # Run demonstrations
    demonstrate_usage()

    print("\n" + "=" * 50 + "\n")

    # Generate sample datasets
    generate_sample_datasets()
