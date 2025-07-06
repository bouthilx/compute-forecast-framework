# External Benchmark Integration Strategy

## Issue
Define methodology for incorporating external institutional data into Mila's compute projections.

## Interface Contract
```yaml
inputs:
  - name: external_institution_data
    format: pandas.DataFrame
    schema: [institution, year, compute_capacity, researchers, publications, domains]
    source: milestone-03-benchmark-data
  - name: mila_research_profile
    format: dict[str, float]
    schema: {domain: publication_percentage}
    source: milestone-02-extraction-pipeline
  - name: mila_usage_data
    format: pandas.DataFrame
    schema: [timestamp, user_id, compute_hours, domain]
    source: milestone-04-mila-data

outputs:
  - name: normalized_benchmarks
    format: pandas.DataFrame
    schema: [institution, year, normalized_growth_rate, similarity_score, weight]
    consumers: [growth-rate-methodology, uncertainty-quantification]
  - name: validation_metrics
    format: dict[str, dict]
    schema: {metric: {mila_value: float, benchmark_range: tuple, percentile: float}}
    consumers: [uncertainty-quantification]
  - name: institutional_similarity_scores
    format: dict[str, float]
    schema: {institution: similarity_score}
    consumers: [growth-rate-methodology]
```

## Dependencies
- **Phase**: 1 (independent, can run in parallel)
- **Enables**: growth-rate-methodology validation
- **Parallel with**: constraint-vs-sufficiency-detection, data-weighting-strategy

## Context
- Have access to broader range of institutions for context
- Need to normalize for different hardware, scale, and research focus
- Use for validation rather than direct projection
- **Configuration**: Use similarity_threshold and normalization_method from shared config

## Key Questions
1. How to normalize for different hardware generations and capabilities?
2. Account for different institutional sizes and research priorities?
3. Weight by research domain overlap with Mila?
4. Handle varying data quality and completeness across institutions?
5. **Integration**: How to align normalization with Mila's constraint-adjusted data?

## Proposed Approaches
- **Normalized metrics**: Growth rates per researcher, per publication, per research domain
- **Similarity weighting**: Weight external data by research overlap with Mila
- **Validation framework**: Use for sanity checking rather than direct prediction
- **Context setting**: Provide comparative framework for Mila's position
- **Hardware normalization**: Convert all metrics to GPU-hour equivalents

## Implementation Strategy
- Focus on growth trends rather than absolute numbers
- Identify most comparable institutions by research profile
- Use multiple external sources to triangulate trends
- Present as context rather than primary evidence
- **Quality filtering**: Exclude institutions below similarity threshold (config: 0.7)

## Normalization Methodology
- **Hardware equivalents**: Convert to standardized GPU-hour units using hardware benchmarks
- **Scale adjustment**: Normalize by institution size (researchers, publications)
- **Domain weighting**: Apply domain overlap coefficients to adjust relevance
- **Temporal alignment**: Align observation periods with Mila's data timeline

## Similarity Calculation
- **Domain overlap**: Cosine similarity of research domain distributions
- **Scale similarity**: Log-scale institutional size comparison
- **Methodology alignment**: Research approach similarity (theory vs. experimental)
- **Composite score**: Weighted average of all similarity dimensions

## Validation Framework
- **Growth rate bounds**: Establish reasonable ranges from benchmark institutions
- **Percentile positioning**: Determine where Mila falls in institutional distribution
- **Trend validation**: Cross-check Mila's growth patterns against benchmark trends
- **Outlier detection**: Flag unusual patterns for further investigation

## Quality Assurance
- **Data completeness**: Minimum required data points per institution
- **Temporal consistency**: Ensure comparable observation periods
- **Bias detection**: Check for systematic biases in institutional selection
- **Sensitivity analysis**: Test impact of different normalization approaches

## Integration Testing
- Mock external data with known characteristics
- Validation against historical Mila performance
- Cross-reference with published institutional reports
- Consistency checks across multiple benchmark sources

## Output Specifications
- **Benchmark ranges**: 5th, 25th, 50th, 75th, 95th percentiles for each metric
- **Similarity weights**: Normalized to sum to 1.0 across all institutions
- **Confidence intervals**: Statistical bounds on benchmark-derived estimates
- **Quality indicators**: Data completeness and reliability scores per institution