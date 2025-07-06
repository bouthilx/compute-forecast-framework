# Milestone 1 Implementation Plan: Mila-Driven Paper Selection

## Phase 1: Mila Publication Analysis (2-3 hours)

### Mila Corpus Analysis
```python
# Extract from Mila papers (2019-2024):
mila_venues = extract_publication_venues(mila_corpus)
mila_domains = categorize_research_domains(mila_corpus)
mila_coauthors = extract_collaboration_patterns(mila_corpus)
```

### Expected Outputs
- **Research domains**: Natural classification from Mila's actual research
- **Relevant venues**: Conferences/journals where Mila publishes
- **Temporal patterns**: How Mila's research focus evolved 2019-2024
- **Collaboration networks**: External institutions Mila works with

### Domain and Venue Identification
- **Automatic categorization**: Cluster Mila papers by research topics
- **Venue ranking**: Frequency of Mila publications by conference/journal
- **Temporal analysis**: Domain emergence and evolution at Mila
- **External validation**: Cross-reference with standard ML venue rankings

## Phase 2: Academic Benchmark Collection (3-4 hours)

### Citation-Based Collection Strategy
```python
for domain in mila_domains:
    for venue in mila_relevant_venues[domain]:
        for year in [2019, 2020, 2021, 2022, 2023, 2024]:
            papers = get_top_cited_papers(venue, year, min_citations=threshold)
            papers = filter_majority_academic(papers)  # >75% academic authors, <25% industry
            papers = filter_computational_content(papers)
            benchmark_papers[domain][year].extend(papers[:10])  # Top 5-10 per year
```

### Citation Data Sources (in priority order)
1. **Google Scholar** (via `scholarly` library): Best coverage, real-time citations
2. **Semantic Scholar API**: Good computational paper coverage, influence metrics
3. **OpenAlex**: Open access, good venue coverage
4. **CrossRef**: DOI-based, reliable but less computational focus

### Academic Paper Filtering
- **Author affiliation analysis**: Majority academic authors (>75% academic affiliations)
- **Industry collaboration acceptable**: <25% industry co-authors allowed
- **Citation threshold**: Dynamic by year (recent papers need fewer citations)
- **Computational content**: Methodology sections mention training, GPUs, computational requirements
- **Venue validation**: Papers from venues where Mila publishes

## Phase 3: Industry Benchmark Collection (2-3 hours)

### Industry Source Tracking
```python
industry_sources = {
    'OpenAI': ['openai.com/research', 'arxiv.org authors:OpenAI'],
    'DeepMind': ['deepmind.com/research', 'nature.com authors:DeepMind'],
    'Meta AI': ['ai.facebook.com/research', 'arxiv.org authors:Meta'],
    'Google Research': ['research.google authors', 'arxiv.org authors:Google'],
    'Microsoft Research': ['microsoft.com/research', 'arxiv.org authors:Microsoft']
}
```

### Industry Paper Selection
- **Domain mapping**: Same domains as identified from Mila analysis
- **Citation requirement**: High-impact papers with >100 citations (adjusted by year)
- **Breakthrough identification**: Papers that define new computational paradigms
- **Computational transparency**: Papers with documented resource requirements

### Industry Collection Strategy
- **Direct source monitoring**: Company research pages and blogs
- **ArXiv tracking**: Papers with industry author affiliations
- **Conference keynotes**: Breakthrough papers presented at major venues
- **Citation cascade**: Papers heavily cited by academic benchmark papers

## Phase 4: Quality Control and Validation (1-2 hours)

### Sanity Check Institution List
```python
expected_academic_institutions = [
    'MIT', 'Stanford', 'CMU', 'Berkeley', 'Oxford', 'Cambridge',
    'ETH Zurich', 'University of Toronto', 'NYU', 'Princeton',
    'Harvard', 'Yale', 'University of Washington', 'EPFL'
]

# Verify representation in collected papers
for institution in expected_academic_institutions:
    papers_count = count_papers_by_institution(academic_papers, institution)
    if papers_count == 0:
        flag_potential_collection_issue(institution)
```

### Citation Data Verification
- **Cross-validation**: Check citation counts across multiple sources
- **Temporal consistency**: Ensure citation growth patterns are reasonable
- **Outlier detection**: Identify and investigate papers with suspicious citation patterns
- **Quality threshold**: Remove papers below minimum citation requirements

### Computational Content Validation
- **Quick scan**: Verify papers have methodology/experimental sections
- **Keyword presence**: Training, GPU, computational requirements, resources
- **Supplementary check**: Include papers with computational details in appendices
- **Priority scoring**: Rank papers by computational content richness

## Practical Implementation Tools

### Python Libraries
```python
# Citation data collection
from scholarly import scholarly
import requests  # For Semantic Scholar API
import arxiv     # For ArXiv paper metadata

# Data processing
import pandas as pd
import numpy as np
from collections import defaultdict

# Text analysis for domain classification
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
```

### Data Collection Pipeline
```python
def collect_benchmark_papers():
    # Step 1: Analyze Mila corpus
    mila_analysis = analyze_mila_publications()
    
    # Step 2: Collect academic benchmarks
    academic_papers = collect_academic_benchmarks(mila_analysis)
    
    # Step 3: Collect industry benchmarks  
    industry_papers = collect_industry_benchmarks(mila_analysis)
    
    # Step 4: Validate and organize
    validated_papers = validate_paper_collection(academic_papers, industry_papers)
    
    return validated_papers
```

## Expected Timeline and Outputs

### Hour-by-Hour Breakdown
- **Hours 1-3**: Mila corpus analysis → domains, venues, patterns
- **Hours 4-7**: Academic benchmark collection → 180-360 papers
- **Hours 7-9**: Industry benchmark collection → 180-360 papers  
- **Hours 9-10**: Quality control and validation

### Deliverables
1. **Mila analysis report**: Domains, venues, research evolution
2. **Academic benchmark dataset**: 5-10 papers × domains × 6 years
3. **Industry benchmark dataset**: 5-10 papers × domains × 6 years
4. **Quality validation report**: Citation verification, content assessment
5. **Collection methodology**: Replicable process documentation

## Risk Mitigation

### Citation Data Unavailable
- **Backup sources**: Multiple citation databases
- **Proxy metrics**: Venue prestige, download counts, influence scores
- **Manual curation**: Domain expert knowledge for critical papers

### Computational Content Sparse
- **Broader search**: Include papers with partial computational information
- **Supplementary materials**: Extend search to appendices and repos
- **Industry reports**: Technical blogs and white papers for computational details

### Collection Bias
- **Sanity check**: Expected institution representation verification
- **Temporal balance**: Ensure reasonable distribution across years
- **Domain coverage**: Validate all Mila research areas represented

**Success metric**: 360-720 benchmark papers with verified citations and computational relevance, organized by Mila-derived domains and venues.