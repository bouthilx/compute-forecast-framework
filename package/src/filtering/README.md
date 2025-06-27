# Computational Research Filtering System (Issue #8)

Real-time filtering system for identifying computational research papers based on content analysis, author affiliations, and venue relevance.

## Overview

This filtering system provides intelligent, real-time filtering of research papers to identify those with high computational content. It integrates seamlessly with the paper collection pipeline to ensure only relevant computational research is collected.

## Components

### 1. Computational Analyzer (`computational_analyzer.py`)
Analyzes papers for computational richness using:
- **Keyword Analysis**: Detects algorithms, ML, systems, complexity terms
- **Resource Metrics**: Identifies compute resources (GPUs, datasets, etc.)
- **Experimental Indicators**: Distinguishes implementation vs. theoretical work
- **Confidence Scoring**: Assesses reliability of the analysis

### 2. Authorship Classifier (`authorship_classifier.py`)
Classifies paper authorship patterns:
- **Academic vs. Industry**: Identifies author affiliations
- **Collaboration Patterns**: Detects academic-industry collaborations
- **Confidence Assessment**: Rates classification reliability
- **Institution Recognition**: Knows major universities and companies

### 3. Venue Relevance Scorer (`venue_relevance_scorer.py`)
Scores venues based on computational focus:
- **Domain Classification**: Maps venues to computational domains
- **Importance Ranking**: Rates venue prestige (1-5 scale)
- **Computational Focus**: Assesses venue's computational emphasis
- **Relevance Scoring**: Combined metric for filtering

### 4. Computational Filter (`computational_filter.py`)
Main filtering engine that:
- **Combines All Analyses**: Integrates all component scores
- **Configurable Thresholds**: Flexible filtering criteria
- **Batch Processing**: Efficient multi-paper filtering
- **Statistics Tracking**: Monitors filtering performance

### 5. Pipeline Integration (`pipeline_integration.py`)
Seamless integration with collection system:
- **Real-time Filtering**: Minimal latency impact
- **Multi-threaded Processing**: Parallel paper analysis
- **Performance Monitoring**: Tracks filtering metrics
- **Callback Support**: Custom processing hooks

## Usage

### Basic Filtering

```python
from src.filtering import ComputationalResearchFilter, FilteringConfig

# Configure filtering thresholds
config = FilteringConfig(
    min_computational_richness=0.4,
    min_venue_score=0.5,
    allow_industry_collaboration=True
)

# Create filter
filter = ComputationalResearchFilter(config)

# Filter papers
result = filter.filter_paper(paper)
if result.passed:
    print(f"Paper passed with score: {result.score}")
```

### Pipeline Integration

```python
from src.filtering import setup_computational_filtering

# One-line integration with existing pipeline
pipeline = setup_computational_filtering(
    api_layer=api_integration_layer,
    monitoring_system=monitoring,
    filter_config=config
)
```

## Configuration

Key configuration parameters:

- `min_computational_richness`: Minimum computational content score (0-1)
- `min_venue_score`: Minimum venue quality score (0-1)
- `require_academic_eligible`: Only accept pure academic papers
- `allow_industry_collaboration`: Accept papers with industry authors
- `strict_mode`: Require ALL criteria to be met (vs. combined score)

## Performance

- **Latency**: <10ms per paper typical
- **Throughput**: 100+ papers/second with 4 workers
- **Accuracy**: Configurable precision/recall tradeoff
- **Scalability**: Thread pool for parallel processing

## Examples

See `examples/computational_filtering_usage.py` for:
- Basic filtering examples
- Pipeline integration
- Advanced configuration
- Custom callback usage

## Testing

Run tests with:
```bash
pytest tests/unit/test_computational_filtering.py -v
```

## Integration Points

- **API Integration Layer**: Filters papers during collection
- **Quality Assessment**: Works alongside quality thresholds
- **Monitoring Dashboard**: Sends filtering metrics
- **State Management**: Preserves filtering decisions