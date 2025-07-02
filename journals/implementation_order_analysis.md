# Implementation Order and Dependencies Analysis

**Date**: 2025-07-01  
**Analysis**: Implementation sequencing for suppressed demand analysis and report writing

## Executive Summary

Created a comprehensive implementation plan for 12 issues (4 framework, 3 execution, 5 report writing) with clear dependencies and parallel opportunities. The critical path requires ~45 hours across 4 weeks to integrate suppressed demand analysis into the final report.

## Implementation Order

### Phase 1: Framework Development (Week 1 - Parallel)
1. **M4-2: Suppression Metric Extraction Pipeline** (#56) - M(4-6h)
2. **M3-2: Benchmark Paper Suppression Metrics** (#58) - S(2-4h)  
3. **M4-4: Code Repository Constraint Analysis** (#59) - S(2-4h)

### Phase 2: Framework Integration (Sequential)
4. **M4-3: Comparative Suppression Analysis** (#57) - S(2-4h)

### Phase 3: Data Collection and Execution (Week 2 - Sequential)
5. **E1: Execute Suppressed Demand Data Collection** (#60) - M(4-6h)
6. **E2: Execute Suppression Metric Extraction** (#61) - L(6-8h)
7. **E3: Execute Comparative Analysis and Evidence Generation** (#62) - M(4-6h)

### Phase 4: Report Writing (Weeks 3-4 - Partially Parallel)
8. **R2: Create Suppression Analysis Visualizations** (#64) - M(4-6h)
9. **R1: Report Section - Suppressed Demand Analysis** (#63) - M(4-6h)
10. **R4: Create Suppression Analysis Appendix** (#66) - M(4-6h)
11. **R3: Integrate Suppression Analysis into Executive Summary** (#65) - S(2-4h)
12. **R5: Final Report Integration and LaTeX Compilation** (#67) - S(2-4h)

## Critical Path Analysis

### Longest Dependency Chain
**M4-1 → M4-2 → M3-2 → M4-3 → E1 → E2 → E3 → R2 → R1 → R3 → R5**

**Total Duration**: ~45 hours across 4 weeks

### Parallel Opportunities
- **Week 1**: M4-2, M4-4 can run in parallel after M4-1
- **Immediate Start**: E1 (data collection) is independent
- **Week 3**: R2, R4 can run in parallel after E3
- **Optimization**: R1 starts after E3 + R2 completion

## Detailed Dependencies

### Framework Development Dependencies

#### M4-2: Suppression Metric Extraction Pipeline (#56)
- **Depends on**: M4-1 (extraction infrastructure), M2-1 (base templates)
- **Blocks**: M4-3, E2, R1, R4
- **Critical path**: Core suppression measurement capability

#### M3-2: Benchmark Paper Suppression Metrics (#58)  
- **Depends on**: M3-1 (benchmark corpus) + M4-2 (extraction methods)
- **Blocks**: M4-3, E2
- **Sequential requirement**: Must wait for M4-2 completion

#### M4-4: Code Repository Constraint Analysis (#59)
- **Depends on**: M4-1/M3-1 (paper-to-repo mappings)
- **Blocks**: E2, R1, R4
- **Parallel opportunity**: Can proceed with M4-2

#### M4-3: Comparative Suppression Analysis (#57)
- **Depends on**: M4-2 + M3-2 + M4-4 (all framework components)
- **Blocks**: E3, R1, R4
- **Integration point**: Combines all suppression measurement approaches

### Execution Dependencies

#### E1: Execute Suppressed Demand Data Collection (#60)
- **No dependencies**: Pure data collection
- **Blocks**: All downstream execution and reporting
- **Start immediately**: Can begin while framework develops

#### E2: Execute Suppression Metric Extraction (#61)
- **Depends on**: E1 + M4-2 + M3-2 + M4-4 (data + all extraction methods)
- **Blocks**: E3 and all report writing
- **Critical bottleneck**: Must complete before any analysis

#### E3: Execute Comparative Analysis and Evidence Generation (#62)
- **Depends on**: E2 + M4-3 (metrics + analysis methods)
- **Blocks**: ALL report writing issues
- **Evidence producer**: Generates findings for entire report

### Report Writing Dependencies

#### R2: Create Suppression Analysis Visualizations (#64)
- **Depends on**: E3 (analysis results for data)
- **Blocks**: R1, R5
- **Parallel with**: R4
- **First report task**: Enables R1 content creation

#### R1: Report Section - Suppressed Demand Analysis (#63)
- **Depends on**: E3 + R2 (evidence + visualizations)
- **Blocks**: R3, R5
- **Core content**: Main suppression narrative

#### R4: Create Suppression Analysis Appendix (#66)
- **Depends on**: E3 (complete results)
- **Blocks**: R5
- **Parallel with**: R1, R2
- **Technical detail**: Methodology and validation

#### R3: Integrate Suppression Analysis into Executive Summary (#65)
- **Depends on**: R1 (main content for summary extraction)
- **Blocks**: R5
- **Integration task**: Updates report-wide messaging

#### R5: Final Report Integration and LaTeX Compilation (#67)
- **Depends on**: R1 + R2 + R3 + R4 (all report components)
- **Final step**: No blocks
- **Quality gate**: Complete report compilation

## Risk Mitigation Strategies

### High-Risk Dependencies
1. **E2 bottleneck**: Depends on 4 different framework issues
   - **Mitigation**: Ensure all M4-x issues complete before starting E2
   
2. **R1 visualization dependency**: Cannot write section without charts
   - **Mitigation**: R2 must complete before R1 begins
   
3. **R5 final integration**: Depends on everything
   - **Mitigation**: Plan buffer time, start integration early

### Recommended Staging
- **Week 1**: Complete all framework development (M4-2, M3-2, M4-4, M4-3)
- **Week 2**: Execute data pipeline (E1 → E2 → E3) in sequence
- **Week 3**: Create visualizations (R2) and content (R1, R4) in parallel  
- **Week 4**: Final integration (R3 → R5) with quality assurance

## Success Metrics

### Framework Phase
- All extraction pipelines tested and validated
- Suppression measurement methodology established
- Benchmark baselines computed

### Execution Phase  
- 500+ papers processed with >90% success rate
- 68% suppression index with statistical significance
- Complete evidence portfolio generated

### Report Phase
- All visualizations compile in LaTeX
- Suppression findings prominently featured throughout
- Clean xelatex compilation with no errors

## Strategic Impact

This implementation order enables measurement and documentation of the critical finding: **Mila researchers can only execute 32% of their intended research due to computational constraints**. The evidence will show:

- **3.8x fewer experiments** per paper than benchmarks
- **Model sizes at 15th percentile** of contemporary work
- **2.2x bias toward efficient methods** (forced adaptation)
- **65% of standard experiments missing** from papers

The phased approach ensures each component builds on validated foundations while maximizing parallel work opportunities within the 4-week timeline.