# Mila Paper Processing Summary Report

**Date**: 2025-07-01  
**Issue**: #30 - M4-1: Mila Paper Processing

## Executive Summary

Extracted computational requirements and suppression indicators from 124 Mila papers (2019-2024) selected from the paperoni dataset. The extraction yielded limited results due to many papers lacking abstracts, but identified key computational patterns and one high-suppression case.

## Data Processing Overview

### Paper Selection
- **Source**: paperoni dataset with 2,786 Mila-affiliated papers
- **Selected**: 124 papers meeting criteria:
  - Computational richness score ≥ 0.1
  - Balanced across years: 12-30 papers/year
  - Domain distribution: NLP (32), CV (43), RL (41), Other (8)
  - Top-tier venues: 77 papers (62%)

### Extraction Results
- **Total processed**: 124 papers
- **Successful extractions**: 7 papers (5.6%)
- **With suppression data**: 124 papers (100%)
- **High suppression detected**: 1 paper

## Key Findings

### 1. Computational Requirements Extracted

| Year | Papers with Data | Key Examples |
|------|-----------------|--------------|
| 2021 | 1 | Goal-driven models: 72 GPU-hours |
| 2022 | 1 | MCVD Video Diffusion: 48 GPU-hours |
| 2023 | 3 | StarCoder: 15.5B params; lo-fi: 1.3B params |
| 2024 | 2 | DINOv2: 1B params |

### 2. Suppression Indicators

Only 1 paper showed high suppression (score ≥ 0.5):
- **"Laughing Hyena Distillery"** (2023): 1.3B parameters with suppression score 1.0
  - Likely efficiency-focused work extracting compact models from larger ones

### 3. Domain Distribution

```
NLP: 32 papers (25.8%)
CV:  43 papers (34.7%)
RL:  41 papers (33.1%)
Other: 8 papers (6.4%)
```

### 4. Temporal Trends

Papers per year show growth:
- 2019: 12 papers
- 2020: 15 papers
- 2021: 15 papers
- 2022: 22 papers
- 2023: 30 papers (cap)
- 2024: 30 papers (cap)

## Limitations & Challenges

### 1. Abstract Availability
- Only 49.4% of papers in paperoni dataset have abstracts
- Extraction heavily relies on abstract content
- Titles alone provide limited computational information

### 2. Low Extraction Rate
- Only 5.6% of papers yielded computational requirements
- Most papers don't explicitly state GPU counts, training times
- Parameter counts more commonly mentioned (5 of 7 extractions)

### 3. Suppression Detection Challenges
- Most papers show no explicit suppression indicators
- Efficiency-focused methods may not explicitly state constraints
- Need PDF content analysis for better detection

## Recommendations

### For Immediate Use
1. The 7 papers with extracted data provide baseline computational requirements
2. Parameter trends show growth: 1B (2023) → 15.5B (2023)
3. Training times when mentioned: 48-72 hours

### For Enhanced Analysis
1. **PDF Processing**: Implement PDF extraction to access full paper content
2. **Manual Review**: Review high-impact papers manually for missing data
3. **External Sources**: Cross-reference with model cards, GitHub repos
4. **Benchmark Comparison**: Compare these 7 data points with external benchmarks

## Data Files Generated

1. **mila_selected_papers.json**: 124 selected papers
2. **mila_computational_requirements.json**: Full extraction results
3. **mila_computational_requirements.csv**: Simplified tabular format
4. **mila_selection_summary.json**: Selection statistics

## Next Steps

1. Manual review of high-impact papers without extracted data
2. Cross-validation with known Mila computational resources
3. Integration with benchmark data for gap analysis
4. Generate visualizations for temporal trends

## Conclusion

While the extraction rate was lower than hoped due to abstract limitations, the pipeline successfully:
- Identified and classified 124 relevant Mila papers
- Extracted computational data from 7 papers showing parameter counts up to 15.5B
- Detected one high-suppression case indicating efficiency-focused research
- Created a foundation for manual enhancement and benchmark comparison

The limited extraction highlights the need for either PDF processing or manual curation to build a comprehensive computational requirements dataset for Mila.