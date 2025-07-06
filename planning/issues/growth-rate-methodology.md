# Growth Rate Methodology for 2-Year Projections

## Issue
Define mathematical approach for calculating and applying growth rates in compute projections.

## Interface Contract
```yaml
inputs:
  - name: weighted_usage_data
    format: pandas.DataFrame
    schema: [timestamp, user_id, compute_hours, domain, weight_factor]
    source: data-weighting-strategy
  - name: cluster_assignments
    format: dict[str, str]
    schema: {user_id: cluster_label}
    source: pattern-granularity-decision
  - name: constraint_scores
    format: dict[str, float]
    schema: {user_id: constraint_score}
    source: constraint-vs-sufficiency-detection
  - name: normalized_benchmarks
    format: pandas.DataFrame
    schema: [institution, year, normalized_growth_rate, similarity_score, weight]
    source: external-benchmark-integration
  - name: author_similarity_matrix
    format: numpy.ndarray
    schema: symmetric matrix of collaboration scores
    source: co-authorship-analysis-depth

outputs:
  - name: growth_rates
    format: dict[str, dict]
    schema: {cluster_label: {rate: float, confidence: tuple, model: str, scenario: str}}
    consumers: [uncertainty-quantification]
  - name: projection_scenarios
    format: dict[str, dict]
    schema: {scenario: {cluster_label: projected_usage}}
    consumers: [uncertainty-quantification]
  - name: model_performance_metrics
    format: dict[str, float]
    schema: {model_name: validation_score}
    consumers: [uncertainty-quantification]
```

## Dependencies
- **Phase**: 3 (requires all Phase 1 and Phase 2 outputs)
- **Blocks**: uncertainty-quantification (final integration)
- **Parallel with**: None (sequential dependency)

## Context
- Need robust methodology for 2-year forecasting
- Handle discontinuous growth from new research areas
- Account for potential saturation effects
- **Configuration**: Use projection_horizon, models, and scenario_labels from shared config

## Key Questions
1. Linear vs. exponential vs. logistic growth models?
2. Domain-specific vs. pattern-specific growth rates?
3. How to handle breakthrough technologies and new research areas?
4. Account for natural limits or saturation effects?
5. **Integration**: How to combine constraint-adjusted data with external benchmarks?

## Proposed Approaches
- **Ensemble modeling**: Combine multiple growth models for robustness
- **Segmented growth**: Different models for different research maturity levels
- **Constraint-adjusted**: Account for historical resource limitations in growth calculations
- **Scenario-based**: Multiple growth trajectories (conservative/realistic/optimistic)
- **Benchmark validation**: Use external data to bound growth rate estimates

## Model Considerations
- Research areas have different growth lifecycles
- Infrastructure constraints affect observed vs. actual growth
- External factors (funding, technological breakthroughs) influence trends
- Need uncertainty quantification for decision-making
- **Temporal alignment**: 2-year projection horizon matching other analyses

## Mathematical Framework
- **Constraint adjustment**: actual_growth = observed_growth / (1 - constraint_score)
- **Weight application**: Apply temporal and capacity weights from data-weighting-strategy
- **Model ensemble**: Weighted average of linear, exponential, and logistic models
- **Scenario generation**: Conservative (10th percentile), Realistic (median), Optimistic (90th percentile)

## Model Selection Criteria
- **Cross-validation accuracy**: Hold-out validation on historical data
- **Benchmark consistency**: Alignment with external institutional growth patterns
- **Cluster stability**: Robustness to cluster assignment variations
- **Constraint sensitivity**: Appropriate response to resource constraint levels

## Implementation Specifications
- **Validation split**: 20% holdout for model selection (config: validation_split)
- **Bootstrap samples**: 1000 iterations for confidence intervals (config: bootstrap_samples)
- **Scenario labels**: Use standardized labels from shared config
- **Model weights**: Ensemble weights based on cross-validation performance

## Quality Assurance
- **Plausibility bounds**: Growth rates within reasonable ranges (0.5x to 5x annually)
- **Consistency checks**: Scenario ordering (conservative < realistic < optimistic)
- **Benchmark validation**: Growth rates within external institutional ranges
- **Cluster coherence**: Similar growth patterns for similar research groups

## Integration Testing
- Mock data validation with known growth patterns
- Sensitivity analysis for key parameters (constraint scores, weights)
- Cross-reference with historical infrastructure expansion periods
- Consistency verification across all three scenarios

## Output Validation
- Statistical significance testing for growth rate estimates
- Confidence interval coverage verification
- Scenario spread analysis (appropriate uncertainty ranges)
- Cross-cluster consistency checks
