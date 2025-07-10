# CLI Detailed Design - Compute Forecast Command Interface

**Date**: 2025-01-08
**Analysis**: Comprehensive CLI interface specification for compute-forecast tool

## Executive Summary

This document provides a detailed specification for the compute-forecast CLI, building on the existing draft (`cli.txt`) and the current codebase architecture. The design focuses on creating an intuitive, powerful interface that leverages the existing modular components while providing robust workflow management.

## Current State Analysis

### Existing CLI Structure
- Basic `compute_forecast.cli:main` entry point configured in `pyproject.toml`
- Placeholder implementation with collect/analyze/report commands
- Rich ecosystem of existing modules ready for CLI integration

### Key Integration Points
- **Collection**: `compute_forecast.orchestration.VenueCollectionOrchestrator`
- **Analysis**: `compute_forecast.analysis.*` modules
- **Monitoring**: `compute_forecast.monitoring.DashboardServer`
- **Quality**: `compute_forecast.quality.*` system
- **Configuration**: `compute_forecast.core.config.ConfigManager`

## Command Hierarchy & Detailed Specifications

### 1. Collection Command (`cf collect`)

**Purpose**: Orchestrate paper collection from various sources with robust error handling and progress tracking.

#### Core Usage Patterns
```bash
# Basic collection
cf collect neurips --year 2024 --max-papers 500
cf collect icml --years 2020-2024 --domains "nlp,cv,rl"
cf collect --venue-file venues.yaml --output collected_papers.json

# Collection with filtering
cf collect neurips --year 2024 --min-citations 10 --affiliation-filter mila
cf collect --venues neurips,icml --years 2020-2024 --exclude-workshops
```

#### Detailed Arguments

**Venue Selection**:
```bash
--venue VENUE                    # Single venue (neurips, icml, iclr, etc.)
--venues VENUE1,VENUE2           # Multiple venues
--venue-file PATH                # YAML file with venue specifications
--venue-config PATH              # Custom venue configuration
```

**Time Range**:
```bash
--year YEAR                      # Single year (2024)
--years YEAR1-YEAR2              # Range (2020-2024)
--years YEAR1,YEAR2,YEAR3        # Specific years (2020,2022,2024)
--since YEAR                     # From year onwards (2020-)
--until YEAR                     # Up to year (-2024)
```
**Collection Limits**:
```bash
--max-papers N                   # Maximum papers per venue/year
```
**Parallel Processing**:
```bash
--parallel N                     # Number of parallel workers
--rate-limit RATE                # API rate limit (requests/second)
--batch-size N                   # Batch size for processing
--timeout SECONDS                # Timeout for individual requests
```

**Resume & Recovery**:
```bash
--resume                         # Resume from last checkpoint
--checkpoint-dir PATH            # Directory for checkpoint storage
--checkpoint-interval N          # Checkpoint every N papers
--restore-from PATH              # Restore from specific checkpoint
```

**Output Options**:
```bash
--output PATH                    # Output file path
--format FORMAT                  # Output format (json, csv, yaml)
--compress                       # Compress output files
--split-by FIELD                 # Split output by field (year, venue, domain)
```

### 2. Consolidation Command (`cf consolidate`)

**Purpose**: Enrich collected papers with additional metadata, establish relationships between similar papers, and discover PDF URLs.

#### Core Usage Patterns
```bash
# Basic consolidation
cf consolidate --papers papers.json --fetch citations,pdfs,affiliations
cf consolidate --papers papers.json --output consolidated.json

# Link similar papers (keeping them as separate entities)
cf consolidate --papers papers.json --link-similar --similarity-threshold 0.9
```

#### Detailed Arguments

**Input Sources**:
```bash
--papers PATH                    # Input papers file
--papers-dir PATH                # Directory with multiple paper files
```

**Enrichment Options**:
```bash
--fetch TYPE1,TYPE2              # What to fetch (citations, pdfs, affiliations, venues)
--enrich-all                     # Fetch all available metadata
--update-existing                # Update existing metadata
--force-refresh                  # Force refresh of cached data
```

**Paper Linking**:
```bash
--link-similar                   # Find and link similar papers
--similarity-threshold SCORE     # Similarity threshold (0.0-1.0)
--manual-review                  # Enable manual review of similar papers
```
Note: When similarity threshold is met, papers remain separate but are linked with an explanation of their relationship.

**PDF Discovery**:
```bash
--discover-pdfs                  # Discover PDF URLs (venue-specific collectors)
```
Note: PDF discovery uses hardcoded venue-to-collector mappings (e.g., NeurIPS → NeurIPS PDF collector).
PDF accessibility is always verified automatically.

**Affiliation Processing**:
```bash
--affiliation-resolution         # Resolve and normalize author affiliations
```
Note: Authors are referenced by name as strings; focus is on accurate affiliation data.

### 3. Download Command (`cf download`)

**Purpose**: Download PDFs using URLs discovered by consolidate command, with Google Drive storage and local caching.

#### Core Usage Patterns
```bash
# Basic download
cf download --papers papers.json
cf download --papers papers.json --retry-failed
```

#### Detailed Arguments

**Input**:
```bash
--papers PATH                    # Input papers file (with PDF URLs from consolidate)
```

**Parallel Processing**:
```bash
--parallel N                     # Number of parallel downloads
--rate-limit RATE                # Download rate limit (requests/second)
--timeout SECONDS                # Download timeout per file
```

**Retry & Recovery**:
```bash
--retry-failed                   # Retry previously failed downloads
--max-retries N                  # Maximum retry attempts (default: 3)
--retry-delay SECONDS            # Delay between retries
--exponential-backoff            # Use exponential backoff for retries
```

**Resume**:
```bash
--resume                         # Resume interrupted downloads
```

Note:
- Storage configuration (Google Drive credentials and folder) is handled via .env file
- Local cache directory is configured in .env file
- Cache has no expiration (permanent unless manually cleared)
- PDF quality validation is handled by `cf quality` command
- To replace bad PDFs: delete from cache/storage and re-run with --retry-failed

### 4. Extraction Command (`cf extract`)

**Purpose**: Extract structured information from papers using configurable templates and AI-powered extraction.

#### Standardized Output Structure

```
extraction/
├── computational_extraction.parquet    # Main extracted data
├── extraction_metadata.json            # Extraction quality and stats
├── extraction_summary.txt              # Human-readable summary
├── extraction_logs/                    # Per-paper extraction logs
│   ├── arxiv123.log
│   ├── arxiv456.log
│   └── ...
└── raw_extractions/                    # Optional raw AI responses
    ├── arxiv123.json
    ├── arxiv456.json
    └── ...
```

**Parquet Schema**:
```
paper_id | domain | year | venue | gpu_hours | gpu_count | gpu_type | model_parameters | training_days | dataset_size | batch_size | memory_gb | flops | confidence | extraction_timestamp | log_file
```

#### Core Usage Patterns
```bash
# Basic extraction
cf extract computational --papers papers.json --output extraction/
cf extract experimental --papers papers.json --output extraction/
cf extract authorship --papers papers.json --output extraction/
cf extract classification --papers papers.json --output extraction/

# Extract all types
cf extract --papers papers.json --output extraction/
cf extract --type computational,experimental --papers papers.json --output extraction/
```

#### Detailed Arguments

**Input Sources**:
```bash
--papers PATH                    # Input papers file (JSON format)
--input-dir PATH                 # Directory containing multiple paper files
```

**Extraction Types**:
```bash
--type TYPE                      # Extraction type (computational, experimental, authorship, classification)
                                 # Default: all types if not specified
```

**Processing Options**:
```bash
--parallel N                     # Number of parallel extraction workers
--timeout SECONDS                # Timeout per paper
--max-pages N                    # Maximum pages to process per paper
```

**Quality Control**:
```bash
--min-confidence SCORE           # Minimum confidence threshold (flags for manual review)
--force-review                   # Force manual review for all papers
```

**Output Options**:
```bash
--output PATH                    # Output directory
--include-raw                    # Include raw AI responses in raw_extractions/
```

**Resume Options**:
```bash
--resume                         # Resume from last extraction state
--skip-existing                  # Skip papers already extracted
```

#### Extraction Types Details

**1. Computational Extraction** (`computational`):
- GPU hours, count, and type
- Training duration and type (pre-training, fine-tuning, inference)
- Model parameters and architecture details
- Dataset size and batch configuration
- Memory and infrastructure requirements
- Distributed training strategy

**2. Experimental Extraction** (`experimental`):
- Ablation studies count and types
- Hyperparameter experiments scope
- Baseline comparisons and evaluation metrics
- Statistical significance testing
- Reproducibility information
- Computational constraints with limitation estimates

**3. Authorship Extraction** (`authorship`):
- Author names and their affiliations (multiple per author)
- Primary institution and collaboration type
- Industry collaboration detection
- Mila author identification

**4. Classification Extraction** (`classification`):
- Research domains (multiple, specific)
- Paper type (empirical, theoretical, survey, etc.)
- Quality flags (is_survey, is_theoretical, has_experiments)
- Research category assessment

**Common Output Fields** (all extraction types):
- `paper_id`: Unique identifier
- `extraction_confidence`: Per-field confidence scores
- `source_quotes`: Verbatim text supporting each extraction
- `explanations`: LLM rationale for extracted values
- `extraction_timestamp`: When extraction occurred

Note: AI model configuration (model choice, temperature, etc.) is set globally in `.env` file.

### 5. Analysis Command (`cf analyze`)

**Purpose**: Perform various types of analysis on collected and extracted data.

#### Analysis Types Research & Rationale

**1. Benchmark vs Gap Analysis - Keep Both, They're Sequential**

- **Benchmark Analysis**: Establishes external reference standards by extracting computational requirements from 300-400 external papers. Creates two benchmarks: Academic (MIT, Stanford) and Industry (OpenAI, DeepMind). Outputs normalized computational metrics from peer institutions.

- **Gap Analysis**: Quantifies differences between Mila and benchmarks using benchmark data to calculate computational multipliers (e.g., 15-27x less resources). Tracks gap evolution over time (6.8x → 26.7x from 2019-2024). They work together: Benchmark establishes standards → Gap measures differences.

**2. Domains Analysis - Move to Extraction Phase**

Domain classification should be part of extraction, not a separate analysis command. Papers should be tagged with domains in their metadata during extraction, then analysis commands can use domain as a grouping field.

**3. Computational Analysis - Pattern Summarization**

Should summarize computational patterns by:
- Research domains (NLP, CV, RL)
- Institutions (Mila vs peers)
- Time periods (yearly)
- Computational intensity levels

The existing ComputationalAnalyzer extracts metrics; needs summarization layer to aggregate and compare patterns across groups.

**4. Suppression Analysis - Paper-Based Framework**

Latest definition: Compare what Mila publishes vs benchmarks to reveal ~68% suppressed demand. Measures:
- Experimental scope (3.8x fewer ablations)
- Model scale limitations (85% of benchmarks are larger)
- Method selection bias (2.2x bias toward compute-efficient methods)
- Missing experiments (65% of standard experiments missing)

No Slurm data or proposals needed - purely paper-based analysis.

**5. Trends - Keep as Separate Analysis**

Should remain separate because it:
- Calculates derived metrics (growth rates, not raw values)
- Requires specific statistical methods (time series analysis)
- Produces unique outputs (52% vs 89% growth rates, projections)
- Identifies paradigm shifts and validates trends

`--temporal-analysis` flag adds time breakdown to other analyses, while `trends` calculates growth and projections.

**Recommended Core Analyses**:
1. `computational` - Summarize computational patterns
2. `benchmark` - Extract external standards
3. `gap` - Quantify Mila vs benchmark differences
4. `suppression` - Measure suppressed demand indicators
5. `trends` - Calculate growth rates and projections
#### Core Usage Patterns
```bash
# Computational analysis - outputs pandas parquet files
cf analyze computational --papers papers.json --output analysis/
cf analyze computational --papers papers.json --output analysis/ --institutions mila,academic,industry

# Benchmark analysis - establishes external standards
cf analyze benchmark --papers external_papers.json --output analysis/
cf analyze benchmark --papers papers.json --benchmark-type academic,industry --output analysis/

# Gap analysis - calculates multipliers between Mila and benchmarks
cf analyze gap --mila mila_papers.json --benchmark benchmark_papers.json --output analysis/
cf analyze gap --computational-stats analysis/computational_stats.parquet --output analysis/

# Suppression analysis - quantifies hidden demand
cf analyze suppression --constrained mila_papers.json --unconstrained benchmark_papers.json --output analysis/

# Trends analysis - growth rates and projections
cf analyze trends --papers all_papers.json --output analysis/
cf analyze trends --computational-stats analysis/computational_stats.parquet --output analysis/
```

#### Analysis Types & Arguments

**Computational Analysis**:
```bash
cf analyze computational [OPTIONS]
--papers PATH                    # Input papers file with extracted computational data
--output PATH                    # Output directory for parquet files
--institutions INST1,INST2       # Institutions to analyze (default: auto-detect)
--domains DOMAIN1,DOMAIN2        # Domains to include (default: all)
--years YEAR1-YEAR2              # Year range (default: all available)
--metrics METRIC1,METRIC2        # Specific metrics (default: gpu_hours,model_parameters,ablation_studies)
--statistics STAT1,STAT2         # Statistics to compute (default: p25,p50,p75,p90,p95,mean,count)
```

Outputs:
- `computational_stats.parquet`: Flattened table with institution|domain|year|metric|statistic|value|count
- `computational_metadata.json`: Data quality, sample sizes, extraction confidence
- `computational_summary.txt`: Human-readable key findings

**Benchmark Analysis**:
```bash
cf analyze benchmark [OPTIONS]
--papers PATH                    # External papers file (MIT, Stanford, OpenAI, etc.)
--output PATH                    # Output directory for parquet files
--benchmark-type TYPE            # Type classification (academic, industry, auto-detect)
--institutions INST1,INST2       # Specific institutions to include
--domains DOMAIN1,DOMAIN2        # Domains to analyze (default: all)
--years YEAR1-YEAR2              # Year range (default: all available)
--metrics METRIC1,METRIC2        # Metrics to benchmark (default: gpu_hours,model_parameters,ablation_studies)
```

Outputs:
- `benchmark_standards.parquet`: Table with benchmark_type|domain|metric|statistic|value|count|institutions
- `benchmark_metadata.json`: Institution lists, sample sizes, data quality
- `benchmark_summary.txt`: Key benchmark findings

**Gap Analysis**:
```bash
cf analyze gap [OPTIONS]
--mila PATH                      # Mila papers or computational_stats.parquet
--benchmark PATH                 # Benchmark papers or benchmark_standards.parquet
--output PATH                    # Output directory for parquet files
--benchmark-types TYPE1,TYPE2    # Compare against academic, industry, or both (default: both)
--domains DOMAIN1,DOMAIN2        # Domains to analyze (default: all)
--years YEAR1-YEAR2              # Year range for temporal analysis
--metrics METRIC1,METRIC2        # Gap metrics (default: gpu_hours,model_parameters,ablation_studies)
```

Outputs:
- `gap_analysis.parquet`: Table with comparison|domain|year|metric|gap_multiplier|mila_value|benchmark_value
- `gap_evolution.parquet`: Temporal gap evolution with growth rates
- `gap_summary.txt`: Key gap findings and multipliers

**Suppression Analysis**:
```bash
cf analyze suppression [OPTIONS]
--constrained PATH               # Mila papers with computational data
--unconstrained PATH             # Benchmark papers or benchmark_standards.parquet
--output PATH                    # Output directory for parquet files
--benchmark-type TYPE            # Compare against academic or industry (default: both)
--domains DOMAIN1,DOMAIN2        # Domains to analyze (default: all)
--years YEAR1-YEAR2              # Year range for temporal analysis
```

Outputs:
- `suppression_components.parquet`: Component breakdown (experimental_scope, model_scale, method_selection)
- `suppression_index.parquet`: Overall suppression rates by domain and year
- `missed_opportunities.parquet`: Quantified missed research opportunities
- `suppression_summary.txt`: Key findings including ~68% headline

**Trends Analysis**:
```bash
cf analyze trends [OPTIONS]
--papers PATH                    # All papers or computational_stats.parquet
--output PATH                    # Output directory for parquet files
--institutions INST1,INST2       # Institutions to analyze (default: mila,academic,industry)
--domains DOMAIN1,DOMAIN2        # Domains to project (default: all)
--projection-years YEARS         # Years to project forward (default: 2025-2027)
--confidence-level LEVEL         # Confidence interval level (default: 0.95)
--growth-model MODEL             # Growth model type (exponential, linear, auto)
```

Outputs:
- `growth_rates.parquet`: Annual growth rates by institution/domain/metric
- `projections_2027.parquet`: Future requirement projections with confidence intervals
- `gap_projections.parquet`: Projected gap evolution
- `paradigm_shifts.parquet`: Detected discontinuities in trends
- `trends_summary.txt`: Key growth insights and 2027 predictions

### 6. Progress Monitoring

**Note**: All long-running operations (collection, download, extraction, analysis) will show progress bars by default. Progress bars include:
- Current item being processed
- Items completed / total items
- Estimated time remaining
- Success/failure counts

Users can disable progress bars with `--no-progress` flag if needed (e.g., for CI/CD pipelines).

### 6. Quality Command (`cf quality`)

**Purpose**: Quality assessment and validation throughout the pipeline stages.

**Note**: For complete quality requirements and failure mode analysis, see `journals/2025-01-08_quality_checks.md`.

#### Core Usage Patterns
```bash
# Quality checks at each pipeline stage
cf quality check --papers papers.json --stage collection
cf quality check --papers papers.json --stage consolidation
cf quality check --papers papers.json --stage download
cf quality check --papers papers.json --stage extraction
cf quality check --papers papers.json --stage pre-analysis
cf quality check --analysis-results results.json --stage analysis

# With options
cf quality check --papers papers.json --stage collection --output issues.json
cf quality check --papers papers.json --stage collection --strict
```

#### Quality Stages

1. **collection**: Metadata completeness, basic venue validation, duplicate detection
2. **consolidation**: Enrichment success, linking accuracy, PDF URL validity
3. **download**: File integrity, content verification
4. **extraction**: Confidence scores, value validation, computational relevance
5. **pre-analysis**: Data readiness for statistical analysis
6. **analysis**: Result validation and consistency checks

#### Key Features

- **Hardcoded Rules**: Quality rules built-in for each stage (thresholds configurable in .env)
- **Issue Flagging**: Problems stored in paper metadata `quality_issues` field
- **Before/After Stats**: Progress tracking for download and other stages
- **Strict Mode**: `--strict` flag enforces quality gates and stops on threshold violations
- **Auto-execution**: Quality checks run automatically after each pipeline stage
- **Progress Integration**: Quality metrics shown in progress bars during execution

### 7. Configuration Command (`cf config`)

**Purpose**: Simple `.env` file management and system setup.

#### Core Usage Patterns
```bash
# View current configuration
cf config show
cf config show --keys storage,api

# Set configuration values
cf config set GOOGLE_DRIVE_FOLDER_ID "your-folder-id"
cf config set SEMANTIC_SCHOLAR_API_KEY "your-api-key"

# Generate template .env file
cf config init
cf config init --overwrite
```

#### Configuration Management

**View Configuration**:
```bash
cf config show                   # Show all non-sensitive config
cf config show --keys KEY1,KEY2  # Show specific keys
cf config check                  # Validate configuration completeness
```

**Set Values**:
```bash
cf config set KEY VALUE          # Set single configuration value
cf config unset KEY              # Remove configuration value
```

**Initialization**:
```bash
cf config init                   # Generate template .env file
cf config init --overwrite       # Overwrite existing .env
```

**Key Configuration Areas**:
- **Storage**: `GOOGLE_DRIVE_FOLDER_ID`, `LOCAL_CACHE_DIR`
- **APIs**: `SEMANTIC_SCHOLAR_API_KEY`, `OPENAI_API_KEY`
- **Quality Thresholds**: `QUALITY_METADATA_COMPLETENESS_THRESHOLD`, `QUALITY_CONFIDENCE_THRESHOLD`
- **Processing**: `DEFAULT_PARALLEL_WORKERS`, `DEFAULT_RATE_LIMIT`

### 8. Plot Command (`cf plot`)

**Purpose**: Generate publication-ready visualizations from analysis results stored in pandas parquet files.

#### Core Usage Patterns
```bash
# Generate specific visualizations from analysis results
cf plot computational --analysis analysis/computational_stats.parquet --type evolution --output figures/
cf plot gap --analysis analysis/gap_analysis.parquet --type evolution --output figures/gap_evolution.png
cf plot suppression --analysis analysis/suppression_components.parquet --type breakdown --output figures/
cf plot trends --analysis analysis/projections_2027.parquet --type projections --output figures/trends.png

# Generate all default plots for an analysis type
cf plot computational --analysis analysis/computational_stats.parquet --output figures/computational/
cf plot gap --analysis analysis/ --output figures/gap/  # Auto-detects gap_*.parquet files
```

#### Plot Commands by Analysis Type

**Computational Analysis Plots**:
```bash
cf plot computational [OPTIONS]
--analysis PATH                  # Path to computational_stats.parquet
--type TYPE                      # Plot type (see below)
--output PATH                    # Output directory or file
--domains DOMAIN1,DOMAIN2        # Filter by domains (default: all)
--institutions INST1,INST2       # Filter by institutions (default: all)
--years YEAR1-YEAR2              # Year range (default: all)

Plot types:
--type evolution                 # GPU hours time series by institution
--type cross-domain-areas        # Faceted stacked areas by domain
--type landscape                 # Overall computational landscape
--type boxplots                  # Current state distributions
--type growth-rates              # Growth rate comparison bars
```

**Gap Analysis Plots**:
```bash
cf plot gap [OPTIONS]
--analysis PATH                  # Path to gap_analysis.parquet or directory
--type TYPE                      # Plot type (see below)
--output PATH                    # Output directory or file
--y-axis-scale SCALE             # shared (default) or independent
--domains DOMAIN1,DOMAIN2        # Domains to plot (default: auto-select highest)
--confidence-level LEVEL         # Confidence interval level (default: 0.95)

Plot types:
--type evolution                 # Two-panel gap evolution with shared scale
--type growth-rates              # Gap acceleration analysis
--type matrix                    # Domain×benchmark gap heatmap
--type waterfall                 # Year-by-year progression (default: top 3 domains)
--type acceleration              # Before/after scatter plot
```

**Suppression Analysis Plots**:
```bash
cf plot suppression [OPTIONS]
--analysis PATH                  # Path to suppression_*.parquet files
--type TYPE                      # Plot type (see below)
--output PATH                    # Output directory or file
--color-scale SCALE              # Heatmap color scale (default: white-red)

Plot types:
--type evolution                 # Overall suppression index over time
--type components                # Multi-line component evolution
--type matrix                    # Domain×benchmark suppression heatmap
--type evidence                  # Quantified evidence bars
--type benchmark-comparison      # Two-panel academic vs industry
```

**Trends Analysis Plots**:
```bash
cf plot trends [OPTIONS]
--analysis PATH                  # Path to trends analysis files
--type TYPE                      # Plot type (see below)
--output PATH                    # Output directory or file
--confidence-level LEVEL         # Confidence bands (default: 0.95, configurable)
--domains DOMAIN1,DOMAIN2        # Domains for projections (default: auto-select)

Plot types:
--type gap-forecast              # Gap evolution with future projections
--type growth-comparison         # Institutional growth rate bars
--type domain-projections        # Multi-panel domain-specific forecasts
--type requirements-2027         # Heatmap of projected 2027 needs
--type validation                # Statistical model validation display
```

#### Common Plot Options

**Output Control**:
```bash
--output PATH                    # Output file or directory
--format FORMAT                  # Output format (png, pdf, svg, eps)
--dpi DPI                        # Resolution (default: 300)
--figsize WIDTH,HEIGHT           # Figure size in inches
```

**Styling**:
```bash
--style STYLE                    # Matplotlib style (default: seaborn-v0_8-whitegrid)
--color-palette PALETTE          # Color palette name
--font-size SIZE                 # Base font size (default: 12)
--title TITLE                    # Custom plot title
--no-title                       # Suppress automatic title
```

**Data Selection**:
```bash
--metric METRIC                  # Specific metric to plot (default: gpu_hours)
--statistic STAT                 # Statistic to plot (default: p50/median)
--year YEAR                      # Specific year for static plots
```


## Error Handling & Recovery

### Built-in Resume Functionality

Each long-running command has built-in resume capability:

```bash
# Collection with automatic checkpointing
cf collect neurips --year 2024 --resume      # Resumes from last checkpoint if interrupted

# Download with state tracking
cf download --papers papers.json --resume    # Skips already downloaded files

# Extraction with progress saving
cf extract --papers papers.json --resume     # Continues from last processed paper

# Analysis commands are typically fast enough to not need resume
```

**How it works**:
- Commands automatically save progress to `.cf_state/` directory
- On `--resume`, commands check for existing state and continue from there
- State is command-specific (collect saves different state than download)
- No manual checkpoint management needed

**State locations**:
- Collection: `.cf_state/collect/venue_year_checkpoint.json`
- Download: `.cf_state/download/download_progress.json`
- Extraction: `.cf_state/extract/extraction_progress.json`

## Global Options

All commands support these global options:

```bash
--verbose, -vv                   # Verbose level (counts)
--quiet, -q                      # Quiet output
--config PATH                    # Configuration file
--profile PROFILE                # Configuration profile
--dry-run                        # Preview mode without execution
--force                          # Force execution (skip confirmations)
--help, -h                       # Show help
--version                        # Show version
```

## Implementation Priority

### Phase 1: Core collection
1. `cf collect` - Basic collection with venue/year filtering
2. `cf quality check --stage collection` - Metadata completeness validation
3. `cf consolidate` - Basic metadata enrichment and PDF discovery
4. `cf quality check --stage consolidation` - Enrichment validation
5. `cf config` - Basic .env file management

### Phase 2: Core extraction
1. `cf download` - PDF downloading with Google Drive integration
2. `cf quality check --stage download` - PDF integrity validation
3. `cf extract` - Computational information extraction
4. `cf quality check --stage extraction` - Extraction confidence validation

### Phase 3: Analysis & Visualization
1. `cf analyze computational` - Baseline computational patterns (outputs parquet)
2. `cf analyze benchmark` - External standards establishment (outputs parquet)
3. `cf analyze gap` - Gap multiplier calculations (outputs parquet)
4. `cf analyze suppression` - Hidden demand quantification (outputs parquet)
5. `cf analyze trends` - Growth rates and projections (outputs parquet)
6. `cf plot computational` - Computational visualizations from parquet data
7. `cf plot gap` - Gap evolution and acceleration visualizations
8. `cf plot suppression` - 68% suppression story visualizations
9. `cf plot trends` - Future projection visualizations

## Success Metrics

1. **Usability**: Commands are intuitive and self-documenting
2. **Robustness**: Graceful handling of interruptions and errors
3. **Performance**: Efficient parallel processing and caching
4. **Integration**: Seamless integration with existing codebase
5. **Extensibility**: Plugin system for custom analysis types

This comprehensive CLI specification provides a robust foundation for the compute-forecast tool, balancing power with usability while leveraging the existing codebase architecture.
