# Uncertainty Quantification in Compute Projections

## Issue
Develop methodology for quantifying and communicating uncertainty in 2-year compute projections.

## Interface Contract
```yaml
inputs:
  - name: growth_rates
    format: dict[str, dict]
    schema: {cluster_label: {rate: float, confidence: tuple, model: str, scenario: str}}
    source: growth-rate-methodology
  - name: projection_scenarios
    format: dict[str, dict]
    schema: {scenario: {cluster_label: projected_usage}}
    source: growth-rate-methodology
  - name: cluster_characteristics
    format: dict[str, dict]
    schema: {cluster_label: {size: int, domain_mix: dict, avg_constraint: float}}
    source: pattern-granularity-decision
  - name: clustering_quality_metrics
    format: dict[str, float]
    schema: {metric_name: score}
    source: pattern-granularity-decision
  - name: validation_metrics
    format: dict[str, dict]
    schema: {metric: {mila_value: float, benchmark_range: tuple, percentile: float}}
    source: external-benchmark-integration
  - name: capacity_normalization_factors
    format: dict[str, float]
    schema: {time_period: normalization_factor}
    source: data-weighting-strategy
  - name: methodology_clusters
    format: dict[str, str]
    schema: {user_id: methodology_type}
    source: constraint-vs-sufficiency-detection
  - name: merge_recommendations
    format: dict[str, list]
    schema: {target_cluster: [similar_authors]}
    source: co-authorship-analysis-depth

outputs:
  - name: uncertainty_bounds
    format: dict[str, dict]
    schema: {metric: {lower: float, upper: float, confidence: float}}
    consumers: [final-report]
  - name: sensitivity_analysis
    format: dict[str, dict]
    schema: {parameter: {impact_score: float, worst_case: float, best_case: float}}
    consumers: [final-report]
  - name: scenario_projections
    format: dict[str, dict]
    schema: {scenario: {total_compute: float, breakdown: dict, confidence_interval: tuple}}
    consumers: [final-report]
  - name: recommendation_confidence
    format: dict[str, float]
    schema: {recommendation: confidence_score}
    consumers: [final-report]
```

## Dependencies
- **Phase**: 3 (final integration, requires all other outputs)
- **Blocks**: None (terminal analysis)
- **Parallel with**: None (sequential, final step)

## Context
- Multiple sources of uncertainty: clustering, growth models, external factors
- Need confidence intervals for decision-making
- Balance statistical rigor with practical communication
- **Configuration**: Use monte_carlo_iterations, confidence_intervals from shared config

## Key Questions
1. How to combine uncertainties from clustering + growth + external validation?
2. Statistical methods for confidence intervals vs. scenario analysis?
3. How to present uncertainty to non-technical decision-makers?
4. What confidence levels are appropriate for resource planning?
5. **Integration**: How to propagate uncertainties from all upstream analyses?

## Proposed Approaches
- **Bootstrap resampling**: For clustering and growth rate confidence intervals
- **Monte Carlo simulation**: For propagating multiple uncertainty sources
- **Scenario analysis**: Conservative/realistic/optimistic projections
- **Sensitivity analysis**: Impact of key parameter variations
- **Bayesian updating**: Incorporate external benchmark information

## Communication Strategy
- Present ranges rather than point estimates
- Use scenario narratives for different growth assumptions
- Highlight most sensitive parameters and assumptions
- Provide recommendations with associated confidence levels
- **Decision support**: Clear guidance for resource planning decisions

## Uncertainty Sources and Methods
- **Clustering uncertainty**: Bootstrap cluster assignments, measure stability
- **Growth model uncertainty**: Ensemble model variance, parameter uncertainty
- **Constraint estimation uncertainty**: Constraint score confidence intervals
- **External validation uncertainty**: Benchmark similarity and quality scores
- **Data quality uncertainty**: Missing data impact, temporal coverage
- **Integration uncertainty**: Error propagation through analysis pipeline

## Statistical Framework
- **Monte Carlo propagation**:
  - Sample from all input uncertainty distributions
  - Run complete projection pipeline for each sample
  - Generate output distribution and confidence intervals
- **Sensitivity coefficients**: First-order derivatives of projections w.r.t. key parameters
- **Variance decomposition**: Identify which uncertainty sources contribute most
- **Cross-validation**: Out-of-sample prediction intervals

## Implementation Specifications
- **Simulation runs**: 10,000 Monte Carlo iterations (config: monte_carlo_iterations)
- **Confidence levels**: 80%, 90%, 95% intervals (config: confidence_intervals)
- **Sensitivity parameters**: growth_rate, cluster_assignments, constraint_levels (config)
- **Bootstrap samples**: 1000 resamples for each uncertainty source

## Scenario Construction
- **Conservative**: 10th percentile growth + high constraint assumptions + clustering uncertainty
- **Realistic**: Median growth + expected constraints + best-estimate clustering
- **Optimistic**: 90th percentile growth + low constraint assumptions + stable clustering
- **Stress test**: Worst-case parameter combinations

## Quality Assurance
- **Coverage validation**: Check if confidence intervals have correct coverage rates
- **Consistency checks**: Ensure scenario ordering and logical relationships
- **Sensitivity validation**: Verify sensitive parameters match domain expectations
- **Communication testing**: Ensure uncertainty presentation is interpretable

## Output Specifications
- **Projection ranges**: Central estimate ± confidence intervals for total compute needs
- **Cluster-level breakdown**: Uncertainty bounds for each usage pattern
- **Scenario narratives**: Qualitative descriptions with quantitative ranges
- **Sensitivity rankings**: Most impactful parameters with quantified effects
- **Decision recommendations**: Preferred strategies with associated confidence levels

## Integration Validation
- **End-to-end testing**: Full pipeline uncertainty propagation validation
- **Component verification**: Individual uncertainty source validation
- **Benchmark comparison**: External validation of uncertainty estimates
- **Historical backtesting**: Test uncertainty predictions against known outcomes

## Risk Assessment
- **Model risk**: Limitations of growth models and clustering approaches
- **Data risk**: Impact of missing or biased historical data
- **Assumption risk**: Sensitivity to key modeling assumptions
- **Implementation risk**: Uncertainty in translating projections to infrastructure decisions

## Communication Outputs
- **Executive summary**: High-level ranges with key drivers
- **Technical appendix**: Detailed methodology and validation results
- **Decision matrices**: Scenarios vs. infrastructure options with confidence scores
- **Sensitivity charts**: Visual representation of parameter impact on projections
