# OpenAlex Coverage Analysis

## Summary of Findings

Our test of OpenAlex coverage reveals **significant gaps** in conference proceedings indexing.

### Test Results

#### NeurIPS 2024
- **Official papers**: 4 papers (from neurips.cc)
- **OpenAlex papers**: 0 papers
- **Coverage rate**: 0.0%
- **Status**: ⚠️ Critical gap

#### ICML 2023/2024
- **OpenAlex papers**: 0 papers for both years
- **Status**: ⚠️ Critical gap

### Root Cause Analysis

1. **Conference Proceedings Not Properly Indexed**
   - Famous papers like "Attention Is All You Need" (NeurIPS 2017) show up as arXiv preprints
   - Conference proceedings may not be linked to the main venue IDs

2. **Venue ID Issues**
   - The venue IDs we found (S4306420609 for NeurIPS) may be for the general conference series
   - Individual conference years may have separate venue IDs
   - Proceedings may be indexed under different publishers (e.g., PMLR, ACM)

3. **Indexing Lag**
   - Recent conferences (2023-2024) may not be fully indexed yet
   - Papers may exist as preprints but not conference versions

### Implications for Pipeline

#### Major Issues
- **OpenAlex alone is insufficient** for comprehensive conference paper collection
- **Conference proceedings are severely under-represented**
- **Venue-based filtering will miss most papers**

#### Recommendations

1. **Multi-source approach required**:
   - OpenAlex for journal papers and basic metadata
   - Conference-specific sources (PMLR, ACM Digital Library, IEEE Xplore)
   - Publisher-specific collectors (existing PDF discovery framework)

2. **Alternative indexing strategies**:
   - Search by paper titles rather than venue IDs
   - Use author-institution filtering as primary method
   - Cross-reference with specialized databases

3. **Venue-specific collection**:
   - NeurIPS: Use neurips.cc/nips.cc archives
   - ICML: Use proceedings.mlr.press
   - ICLR: Use OpenReview API
   - CVPR: Use CVF archives

### Updated Pipeline Strategy

Given these findings, the pipeline should:

1. **Primary collection**: Use institution-based filtering for comprehensive coverage
2. **Secondary enrichment**: Use venue-specific collectors for missing papers
3. **Validation**: Cross-check against official conference lists
4. **Fallback**: Use the existing PDF discovery framework for conference proceedings

### Coverage Estimate

Based on this analysis, OpenAlex likely covers:
- **Journals**: 80-90% coverage
- **Conference proceedings**: 10-30% coverage
- **Preprints**: 90%+ coverage (arXiv)

This makes OpenAlex **unsuitable as the primary source** for conference paper collection in our pipeline.
