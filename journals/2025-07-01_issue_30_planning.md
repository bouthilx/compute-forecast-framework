# Issue #30 Planning: Mila Paper Processing

**Date**: 2025-07-01
**Issue**: #30 - M4-1: Mila Paper Processing

## Analysis Summary

### Issue Requirements
- Extract computational requirements from 90-180 Mila papers (2019-2024)
- Balanced across NLP, CV, RL domains (15-30 papers/year, 5-10 per domain/year)
- Include suppression indicators (per issue comment) to measure suppressed demand
- Quality control and validation
- Multiple export formats

### Codebase Assessment

#### Existing Infrastructure ✓
1. **Extraction Templates**: Found in `src/extraction/default_templates.py`
   - nlp_training_v1, cv_training_v1, rl_training_v1 templates exist
   - Template engine with comprehensive computational patterns

2. **Organization Classification**: Mila is configured
   - `config/organizations.yaml` and `organizations_enhanced.yaml` include Mila
   - Classification infrastructure exists in `src/analysis/classification/`

3. **Computational Extraction**: Well-developed
   - Regex patterns for GPU, training time, parameters, costs
   - Edge case handlers and pattern types
   - Extraction workflow and forms

4. **Paper Collection**: Infrastructure exists
   - Multiple data sources (OpenAlex, Semantic Scholar, etc.)
   - Collection executors and orchestrators

#### Missing Components ❌
1. **Mila Paper Filtering**: No specific implementation to filter papers by Mila affiliation
2. **Suppression Indicators**: Not implemented (needed per issue comment)
3. **Issue-specific Pipeline**: No dedicated script for this extraction task
4. **Export Formats**: Need to implement CSV/JSON exports with suppression metrics

### Implementation Plan

Created 8 todos covering:
1. Mila paper filtering mechanism (HIGH)
2. Suppression indicators extension (HIGH)
3. Paper selection logic (HIGH)
4. Extraction pipeline script (HIGH)
5. Quality validation (MEDIUM)
6. Export functionality (MEDIUM)
7. Summary statistics generation (MEDIUM)
8. Manual review process (LOW)

### Key Insights

The infrastructure is mostly ready - we have extraction templates, computational patterns, and organization classification. The main work is:
1. Adding Mila-specific filtering to the existing infrastructure
2. Extending templates with suppression indicators
3. Creating a dedicated pipeline script that ties everything together

### Estimated Timeline
Based on L(1d) estimate:
- Hours 1-3: Paper filtering and selection (todos 1,3)
- Hours 4-5: Suppression indicators and extraction pipeline (todos 2,4)
- Hours 6-7: Quality validation and exports (todos 5,6,7)
- Hour 8: Manual review and final validation (todo 8)

### Next Steps
Start with todo #1: Create Mila paper filtering mechanism to extract Mila-affiliated papers from collected data
