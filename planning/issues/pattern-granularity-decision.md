# Pattern Granularity Decision Framework

## Issue
Establish criteria for choosing between 5-8 broad patterns vs. 10-15 specific patterns for usage clustering.

## Interface Contract
```yaml
inputs:
  - name: weighted_usage_data
    format: pandas.DataFrame
    schema: [timestamp, user_id, compute_hours, domain, weight_factor]
    source: data-weighting-strategy
  - name: constraint_scores
    format: dict[str, float]
    schema: {user_id: constraint_score}
    source: constraint-vs-sufficiency-detection
  - name: methodology_clusters
    format: dict[str, str]
    schema: {user_id: methodology_type}
    source: constraint-vs-sufficiency-detection
  - name: collaboration_graph
    format: networkx.Graph
    schema: nodes=authors, edges=collaboration_strength
    source: co-authorship-analysis-depth

outputs:
  - name: cluster_assignments
    format: dict[str, str]
    schema: {user_id: cluster_label}
    consumers: [growth-rate-methodology, co-authorship-analysis-depth]
  - name: cluster_characteristics
    format: dict[str, dict]
    schema: {cluster_label: {size: int, domain_mix: dict, avg_constraint: float}}
    consumers: [growth-rate-methodology, uncertainty-quantification]
  - name: clustering_quality_metrics
    format: dict[str, float]
    schema: {metric_name: score}
    consumers: [uncertainty-quantification]
  - name: optimal_granularity_decision
    format: dict
    schema: {chosen_k: int, rationale: str, evaluation_scores: dict}
    consumers: [uncertainty-quantification]
```

## Dependencies
- **Phase**: 2 (requires constraint detection and weighting outputs)
- **Enables**: growth-rate-methodology (clustering required for growth calculation)
- **Parallel with**: co-authorship-analysis-depth (circular dependency resolved iteratively)

## Context
- Need optimal balance between interpretability and precision
- Statistical significance requirements for reliable projections
- Actionable insights for resource planning
- **Configuration**: Use min_cluster_size, max_clusters, min_clusters from shared config

## Key Questions
1. What minimum sample size per cluster ensures statistical reliability?
2. How to evaluate cluster quality and interpretability?
3. Which granularity provides better growth rate prediction accuracy?
4. What level of detail is most useful for decision-makers?
5. **Integration**: How to incorporate collaboration patterns and constraint scores?

## Evaluation Metrics
- **Statistical**: Silhouette score, within-cluster variance, sample size per cluster
- **Predictive**: Cross-validation accuracy of growth projections
- **Practical**: Interpretability and actionability of patterns
- **Integration**: Consistency with constraint patterns and collaboration networks

## Implementation Plan
- Test both granularities with same dataset
- Compare prediction accuracy using hold-out validation
- Assess interpretability through pattern characterization
- Choose based on composite score across metrics
- **Multi-dimensional clustering**: Incorporate usage patterns, constraints, and collaborations

## Clustering Methodology
- **Feature engineering**: Combine usage patterns, constraint scores, methodology types
- **Iterative refinement**: Initial clustering → collaboration adjustment → final clusters
- **Multi-objective optimization**: Balance statistical quality, predictive power, interpretability
- **Constraint integration**: Weight clustering features by constraint-adjusted importance

## Quality Assessment Framework
- **Statistical validity**:
  - Minimum samples per cluster (config: min_cluster_size = 20)
  - Silhouette score > 0.3
  - Within-cluster sum of squares minimization
- **Predictive accuracy**:
  - Cross-validation with growth rate prediction
  - Hold-out validation accuracy > 0.7
  - Consistent performance across domains
- **Interpretability score**:
  - Clear domain/methodology patterns within clusters
  - Distinguishable cluster characteristics
  - Actionable insights for resource planning

## Decision Algorithm
1. **Candidate evaluation**: Test k=[5,6,7,8,10,12,15] clusters
2. **Multi-metric scoring**: Weighted combination of statistical, predictive, interpretability scores
3. **Constraint consistency**: Verify clustering aligns with constraint patterns
4. **Collaboration coherence**: Check alignment with collaboration-based groupings
5. **Final selection**: Choose k with highest composite score above minimum thresholds

## Integration Specifications
- **Circular dependency resolution**: Iterative refinement with co-authorship analysis
- **Constraint weighting**: Higher weight for less-constrained users in clustering
- **Methodology alignment**: Ensure clusters capture methodological differences
- **Quality gates**: All clusters must meet minimum size and coherence requirements

## Validation Methods
- **Stability testing**: Bootstrap resampling to test cluster stability
- **External validation**: Cross-reference with known research group structures
- **Temporal consistency**: Verify cluster assignments remain stable over time
- **Cross-domain validation**: Test clustering performance across different research domains

## Output Specifications
- **Cluster labels**: Descriptive names based on dominant characteristics
- **Size distribution**: Ensure no clusters below minimum threshold
- **Quality scores**: All metrics used in decision process
- **Decision documentation**: Transparent rationale for chosen granularity

## Error Handling
- **Minimum cluster violations**: Merge or redistribute small clusters
- **Poor quality scores**: Fallback to broader granularity if fine-grained clustering fails
- **Constraint inconsistencies**: Alert for manual review if clustering conflicts with constraint patterns
- **Collaboration misalignment**: Iterate with co-authorship analysis to resolve conflicts
