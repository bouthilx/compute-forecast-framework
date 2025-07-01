# Issue #30 Revised Planning: Mila Paper Processing

**Date**: 2025-07-01
**Issue**: #30 - M4-1: Mila Paper Processing

## Major Update: Existing Mila Dataset Available

### Dataset Analysis
- **Path**: `/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json`
- **Total papers**: 2,786
- **Mila-affiliated**: 2,758 (98.9% are Mila papers!)
- **ML/AI papers**: 1,507 (54.6% of Mila papers)

### Papers by Year
- 2019: 119 papers
- 2020: 213 papers  
- 2021: 279 papers
- 2022: 427 papers
- 2023: 714 papers
- 2024: 837 papers
- **Total 2019-2024**: 2,589 papers

### Key Insights
1. **No need to collect papers** - Dataset already contains Mila papers
2. **Papers have PDF links** - Many have arxiv.pdf links for extraction
3. **Filtering needed** - Need to select 90-180 high-quality ML/AI papers
4. **Domain classification needed** - Papers need NLP/CV/RL categorization

## Revised Implementation Plan

### Updated Todo List
1. **Filter & Select Papers** (HIGH) - Select 15-30/year from paperoni dataset, balanced across domains
2. **Extend Templates** (HIGH) - Add suppression indicators to existing templates
3. **Domain Classification** (HIGH) - Classify papers as NLP/CV/RL and verify computational content
4. **Extraction Pipeline** (HIGH) - Process selected papers with templates + suppression
5. **Quality Validation** (MEDIUM) - Cross-reference and validate extractions
6. **Export Functionality** (MEDIUM) - CSV/JSON with computational + suppression data
7. **Summary Statistics** (MEDIUM) - Generate reports and visualizations
8. **Manual Review** (LOW) - Review low-confidence extractions

### Key Changes from Original Plan
- **Removed**: Paper collection infrastructure (not needed)
- **Removed**: Mila affiliation filtering (dataset is pre-filtered)
- **Added**: Domain classification step (papers not pre-classified)
- **Focus**: Selection quality over collection quantity

### Timeline Remains Same (L=1d)
- Hours 1-3: Paper selection & domain classification
- Hours 4-5: Template extension & extraction pipeline
- Hours 6-7: Quality validation & exports
- Hour 8: Manual review & final validation

### Next Steps
Start with todo #1: Filter and select high-quality ML/AI papers from the paperoni dataset, ensuring balanced distribution across years and domains.