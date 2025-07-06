# Data Weighting Strategy for Infrastructure Breakpoints

## Issue
How should we weight data differently across infrastructure breakpoints, and why?

## Interface Contract
```yaml
inputs:
  - name: usage_data
    format: pandas.DataFrame
    schema: [timestamp, user_id, compute_hours, domain]
    source: milestone-04-mila-data
  - name: infrastructure_timeline
    format: pandas.DataFrame
    schema: [date, capacity_change, hardware_type, total_capacity]
    source: milestone-04-mila-data

outputs:
  - name: weighted_usage_data
    format: pandas.DataFrame
    schema: [timestamp, user_id, compute_hours, domain, weight_factor]
    consumers: [pattern-granularity-decision, growth-rate-methodology]
  - name: breakpoint_timeline
    format: pandas.DataFrame
    schema: [start_date, end_date, capacity_era, weight_multiplier]
    consumers: [constraint-vs-sufficiency-detection, growth-rate-methodology]
  - name: capacity_normalization_factors
    format: dict[str, float]
    schema: {time_period: normalization_factor}
    consumers: [uncertainty-quantification]
```

## Dependencies
- **Phase**: 1 (independent, can run in parallel)
- **Enables**: constraint-vs-sufficiency-detection, pattern-granularity-decision
- **Parallel with**: external-benchmark-integration, constraint-vs-sufficiency-detection

## Context
- Cluster usage data reflects resource constraints, not actual needs
- Researchers would use 10x more resources if available
- Infrastructure changes create artificial breakpoints in usage patterns
- Need to distinguish between constrained usage vs. true computational requirements
- **Configuration**: Use infrastructure_breakpoint_threshold from shared config (6 months minimum)

## Key Questions
1. Should we weight post-upgrade periods more heavily since they represent less constrained usage?
2. How do we identify when usage plateaus indicate constraint vs. actual need satisfaction?
3. Should we use infrastructure capacity ratios to adjust historical usage data?
4. **Integration**: How to coordinate with constraint detection for consistent weighting?

## Proposed Approaches
- **Constraint-adjusted weighting**: Weight periods by estimated resource availability relative to demand
- **Capacity normalization**: Adjust historical usage by infrastructure capacity changes
- **Breakpoint segmentation**: Analyze trends within infrastructure eras separately
- **Progressive weighting**: Higher weights for more recent, less constrained periods

## Implementation Strategy
- **Breakpoint detection**: Identify capacity changes >20% within breakpoint threshold window
- **Weight calculation**: W = min(current_capacity / baseline_capacity, 3.0) to prevent extreme weights
- **Temporal decay**: Apply exponential decay to older observations (half-life = 1 year)
- **Quality gates**: Minimum data points per era from shared config

## Dependencies Resolution
- Infrastructure timeline data collection
- Understanding of resource allocation policies over time
- Analysis of usage vs. capacity correlations
- **Cross-validation**: Align breakpoints with constraint detection periods

## Integration Specifications
- **Breakpoint alignment**: Coordinate with constraint detection infrastructure timeline
- **Weight normalization**: Ensure total weights sum to reasonable bounds
- **Era definition**: Consistent time period definitions across all consumers
- **Edge case handling**: Partial upgrade periods, maintenance windows

## Validation Methods
- **Historical validation**: Compare weighted vs. unweighted growth predictions against known outcomes
- **Capacity correlation**: Verify weighting factors correlate with actual capacity utilization
- **Cross-era consistency**: Ensure smooth transitions between infrastructure eras
- **Sensitivity analysis**: Test impact of different weighting functions

## Quality Assurance
- Minimum observation periods per infrastructure era
- Outlier detection for extreme capacity changes
- Consistency checks with external infrastructure documentation
- Impact assessment on downstream clustering and growth modeling