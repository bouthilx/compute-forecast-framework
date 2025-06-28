# Mock Data Generation Framework

## Overview

The Mock Data Generation Framework provides realistic test data for the analysis pipeline. It generates `Paper` objects with varying quality levels to support comprehensive testing scenarios including normal operations, edge cases, and error handling.

## Features

- **Realistic Data Generation**: Creates papers with believable titles, authors, venues, and metadata
- **Quality Levels**: Three data quality modes (Normal, Edge Case, Corrupted)
- **Deterministic Generation**: Seed-based generation for reproducible tests
- **Performance**: Generates 5000+ papers in under 30 seconds
- **Comprehensive Analysis**: Includes computational, authorship, and venue analysis
- **Validation**: Built-in validation to ensure data meets quality requirements

## Quick Start

```python
from src.testing.mock_data import MockDataGenerator, MockDataConfig, DataQuality

# Create generator
generator = MockDataGenerator()

# Generate normal quality papers
config = MockDataConfig(quality=DataQuality.NORMAL, size=100, seed=42)
papers = generator.generate(config)

# Validate output
is_valid = generator.validate_output(papers, config)
```

## Data Quality Levels

### Normal Quality (95% field population)
- All required fields populated
- ~95% of optional fields populated
- Realistic distributions for citations, years, venues
- Suitable for integration testing

### Edge Case Quality (70% field population)
- Some missing fields
- Unusual but valid values (e.g., empty abstracts, extreme citation velocities)
- Tests boundary conditions

### Corrupted Quality (30% field population)
- Many missing fields
- Minimal data
- Tests error handling and robustness

## Generated Data Structure

Each generated `Paper` includes:

### Core Fields (Always Present)
- `paper_id`: Unique identifier
- `title`: Realistic ML/AI paper title
- `authors`: List of Author objects with affiliations
- `venue`: Conference/journal name
- `year`: Publication year (2019-2024)
- `citations`: Citation count based on age

### Optional Fields (Based on Quality)
- `abstract`: Generated paper abstract
- `keywords`: Relevant ML/AI keywords
- `arxiv_id`: ArXiv identifier
- `openalex_id`: OpenAlex identifier
- `citation_velocity`: Citation growth rate
- `computational_analysis`: GPU usage, parameters, etc.
- `authorship_analysis`: Academic/industry classification
- `venue_analysis`: Venue importance metrics

## Usage Examples

### Basic Generation
```python
# Generate 50 papers with default seed
config = MockDataConfig(quality=DataQuality.NORMAL, size=50)
papers = generator.generate(config)
```

### Reproducible Testing
```python
# Same seed produces same data
config1 = MockDataConfig(quality=DataQuality.NORMAL, size=10, seed=12345)
config2 = MockDataConfig(quality=DataQuality.NORMAL, size=10, seed=12345)

papers1 = generator.generate(config1)
papers2 = generator.generate(config2)
# papers1 and papers2 will be identical
```

### Testing Edge Cases
```python
# Generate papers with missing/unusual data
config = MockDataConfig(quality=DataQuality.EDGE_CASE, size=20)
edge_papers = generator.generate(config)

# Some papers may have:
# - Empty abstracts
# - No keywords
# - Extreme citation velocities (0.0 or 100+)
# - Single author or 20+ authors
```

### Validation
```python
# Check if generated data meets quality requirements
papers = generator.generate(config)
if not generator.validate_output(papers, config):
    print("Generated data doesn't meet quality threshold")
```

### Integration Testing
```python
# Use with existing analysis components
from src.analysis.classifier import PaperClassifier

papers = generator.generate(MockDataConfig(quality=DataQuality.NORMAL, size=100))
classifier = PaperClassifier()
results = classifier.classify_papers(papers)
```

### Performance Testing
```python
# Generate large datasets
import time

start = time.time()
config = MockDataConfig(quality=DataQuality.NORMAL, size=5000)
papers = generator.generate(config)
print(f"Generated {len(papers)} papers in {time.time() - start:.2f} seconds")
```

## Realistic Data Distributions

The generator creates realistic distributions for:

### Venues
- Top-tier: NeurIPS, ICML, ICLR, CVPR (higher frequency)
- Second-tier: ECCV, EMNLP, KDD, etc.
- Workshops and ArXiv papers

### Publication Years
- Recent years (2023-2024) have more papers
- Follows exponential growth pattern

### Citations
- Power-law distribution
- Older papers generally have more citations
- Venue quality affects citation patterns

### Author Affiliations
- Mix of academic institutions (70%)
- Industry research labs (30%)
- Some authors without affiliations

## Advanced Features

### Computational Analysis
Papers may include computational requirements:
- GPU hours and types
- Model parameters
- Training time
- Confidence scores

### Authorship Analysis
Classification of author teams:
- Academic eligible
- Industry eligible
- Needs manual review

### Venue Analysis
Venue importance metrics:
- Venue score (0-1)
- Domain relevance
- Computational focus
- Importance ranking

## Running Examples

Generate sample datasets:
```bash
python -m src.testing.mock_data.examples
```

This creates:
- `sample_data/normal_quality_papers.json`
- `sample_data/edge_case_papers.json`
- `sample_data/corrupted_papers.json`

## Best Practices

1. **Use consistent seeds** for reproducible tests
2. **Mix quality levels** to test robustness
3. **Validate output** before using in tests
4. **Check performance** with your specific use case
5. **Customize generation** by extending the generator

## Implementation Details

The framework uses:
- Deterministic random generation with seeds
- Realistic templates for titles and abstracts
- Weighted distributions for venues and years
- Correlation between fields (e.g., venue affects citations)
- Existing data models from `src.data.models`

## Performance Characteristics

- **Small datasets** (< 100): < 0.1 seconds
- **Medium datasets** (100-1000): < 1 second
- **Large datasets** (1000-5000): < 5 seconds
- **Memory usage**: ~200KB per paper

## Future Enhancements

Potential improvements:
- Domain-specific paper generation
- Custom venue distributions
- Time-series data generation
- Collaboration network simulation
- Citation graph generation