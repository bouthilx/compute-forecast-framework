# Distinguishing Constraint vs. Sufficiency in Usage Patterns

## Issue
How to identify whether usage plateaus indicate resource constraints vs. research sufficiency, varying by research domain and methodology.

## Interface Contract
```yaml
inputs:
  - name: usage_data
    format: pandas.DataFrame
    schema: [timestamp, user_id, compute_hours, domain, allocation_limit]
    source: milestone-04-mila-data
  - name: breakpoint_timeline
    format: pandas.DataFrame
    schema: [start_date, end_date, capacity_era, weight_multiplier]
    source: data-weighting-strategy
  - name: paper_requirements
    format: dict[str, dict]
    schema: {paper_id: {compute_estimate: float, methodology: str}}
    source: milestone-02-extraction-pipeline

outputs:
  - name: constraint_scores
    format: dict[str, float]
    schema: {user_id: constraint_score}  # 0-1 scale, 1=fully constrained
    consumers: [co-authorship-analysis-depth, pattern-granularity-decision]
  - name: domain_constraint_thresholds
    format: dict[str, float]
    schema: {domain: threshold_ratio}
    consumers: [growth-rate-methodology]
  - name: methodology_clusters
    format: dict[str, str]
    schema: {user_id: methodology_type}
    consumers: [pattern-granularity-decision, uncertainty-quantification]
```

## Dependencies
- **Phase**: 1 (independent, can run in parallel)
- **Enables**: co-authorship-analysis-depth, pattern-granularity-decision
- **Parallel with**: external-benchmark-integration, data-weighting-strategy

## Context
- Most research groups have been severely resource constrained historically
- Few groups may have had sufficient resources for their research needs
- Constraint levels vary by:
  - Research domain (NLP vs. computer vision vs. theory)
  - Model type and scale (large single models vs. many small experiments)
  - Training/evaluation methodology (single training vs. hyperparameter optimization)
  - Analysis scale (proof-of-concept vs. comprehensive studies)
- **Configuration**: Use constraint_threshold from shared config (0.8 default)

## Key Insights
- **Domain-specific constraints**: Different research areas have fundamentally different resource needs
- **Methodology impact**: "Train once huge model" vs. "train thousands small models" have similar total requirements but different constraint experiences
- **Limited unconstrained signals**: If majority of groups were always constrained, unconstrained periods may be rare
- **Temporal consistency**: Infrastructure changes create constraint regime shifts

## Proposed Detection Methods
1. **Usage vs. allocation ratios**: Identify groups consistently hitting limits vs. those with headroom
2. **Research output analysis**: Compare computational requirements mentioned in papers vs. actual usage
3. **Domain-specific benchmarking**: Different constraint thresholds for different research areas
4. **Methodology clustering**: Group by computational approach rather than just domain
5. **Breakpoint analysis**: Identify constraint regime changes from breakpoint timeline

## Challenges
- **Limited unconstrained data**: May have minimal "true demand" signals to work with
- **Domain expertise required**: Need understanding of typical resource needs by research area
- **Methodology inference**: Difficult to automatically classify research approaches from usage logs
- **Temporal alignment**: Infrastructure changes affect constraint interpretation

## Mitigation Strategies
- **Focus on least constrained periods/groups** as demand indicators
- **Paper-based requirement estimation** to supplement usage data
- **Expert knowledge integration** for domain-specific constraint assessment
- **Conservative extrapolation** acknowledging uncertainty from constraint effects
- **Multi-phase validation**: Cross-validate constraint scores with external benchmarks

## Implementation Specifications
- **Constraint score calculation**: (actual_usage / theoretical_demand) capped at 1.0
- **Domain thresholds**: ML/DL: 0.9, Theory: 0.3, Vision: 0.85, NLP: 0.9
- **Methodology detection**: Pattern analysis of job submissions (batch size, duration, frequency)
- **Quality gates**: Minimum observation period (config: historical_analysis window)

## Integration Testing
- Validate constraint scores against known resource-limited periods
- Cross-reference with infrastructure upgrade impacts
- Sensitivity analysis for threshold parameters