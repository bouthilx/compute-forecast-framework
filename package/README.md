# Compute Forecast

A comprehensive tool for analyzing and forecasting computational requirements in machine learning research.

## Overview

Compute Forecast helps research institutions and organizations understand and project their computational needs by:

- Collecting research papers from multiple academic sources
- Extracting computational requirements from publications
- Analyzing trends in computational usage
- Generating evidence-based forecasts for future needs

## Installation

### From PyPI (coming soon)
```bash
pip install compute-forecast
```

### From Source
```bash
git clone https://github.com/compute-forecast/compute-forecast.git
cd compute-forecast
pip install -e .
```

### With Development Dependencies
```bash
pip install -e ".[dev,test]"
```

## Quick Start

### Command Line Interface

```bash
# Check version
compute-forecast --version

# Collect papers from a venue
compute-forecast collect --venue NeurIPS --year 2024 --limit 100

# Analyze computational requirements
compute-forecast analyze --input papers.json --output analysis.json

# Generate forecast report
compute-forecast report --input analysis.json --output forecast.pdf
```

### Python API

```python
from compute_forecast.data.collectors import CitationCollector
from compute_forecast.data.models import CollectionQuery

# Initialize collector
collector = CitationCollector()

# Create query
query = CollectionQuery(
    domain="machine_learning",
    year=2024,
    venue="NeurIPS",
    max_results=100
)

# Collect papers
results = collector.collect_from_all_sources(query)
papers = collector.get_combined_papers(results)

# Process PDFs
from compute_forecast.pdf_parser.core.processor import OptimizedPDFProcessor
processor = OptimizedPDFProcessor()

for paper in papers:
    # Process each paper's PDF
    result = processor.process_pdf(pdf_path, paper)
```

## Architecture

The package is organized into several key modules:

- **`data/`**: Paper collection from citation sources (OpenAlex, Semantic Scholar, Google Scholar)
- **`pdf_discovery/`**: Finding downloadable PDFs from various sources
- **`pdf_parser/`**: Extracting text and information from PDFs
- **`analysis/`**: Analyzing computational requirements and trends
- **`core/`**: Shared utilities and configuration

## Features

### Paper Collection
- Multiple citation source support (OpenAlex, Semantic Scholar, Google Scholar)
- Venue-based and keyword-based search
- Automatic deduplication
- Rate limiting and error recovery

### PDF Processing
- Multiple PDF extraction methods
- Intelligent fallback strategies
- Batch processing support
- Quality assessment

### Analysis Capabilities
- Computational requirement extraction
- Trend analysis across years
- Venue comparison
- Suppressed demand quantification

## Examples

See the `examples/` directory for complete working examples:

- `example_neurips_pipeline.py`: End-to-end pipeline for NeurIPS papers
- More examples coming soon

## Development

### Running Tests
```bash
uv run pytest
```

### Code Quality
```bash
uv run ruff check .
uv run black .
```

### Building Documentation
```bash
uv run mkdocs build
```

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to our repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use Compute Forecast in your research, please cite:

```bibtex
@software{compute_forecast,
  title = {Compute Forecast: Analyzing and Forecasting ML Computational Requirements},
  year = {2024},
  url = {https://github.com/compute-forecast/compute-forecast}
}
```