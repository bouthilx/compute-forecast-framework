# Co-authorship Analysis Depth Definition

## Issue
Determine optimal depth and methodology for co-authorship analysis when merging research groups with limited data.

## Interface Contract
```yaml
inputs:
  - name: publication_data
    format: pandas.DataFrame
    schema: [paper_id, authors, venue, year, domain]
    source: milestone-02-extraction-pipeline
  - name: usage_cluster_assignments
    format: dict[str, str]
    schema: {user_id: cluster_label}
    source: pattern-granularity-decision
  - name: constraint_scores
    format: dict[str, float]
    schema: {user_id: constraint_score}
    source: constraint-vs-sufficiency-detection

outputs:
  - name: collaboration_graph
    format: networkx.Graph
    schema: nodes=authors, edges=collaboration_strength
    consumers: [pattern-granularity-decision]
  - name: author_similarity_matrix
    format: numpy.ndarray
    schema: symmetric matrix of collaboration scores
    consumers: [growth-rate-methodology]
  - name: merge_recommendations
    format: dict[str, list]
    schema: {target_cluster: [similar_authors]}
    consumers: [uncertainty-quantification]
```

## Dependencies
- **Phase**: 2 (requires constraint detection output)
- **Blocks**: pattern-granularity-decision (clustering refinement)
- **Parallel with**: None (sequential dependency)

## Context
- Need to merge groups with insufficient historical cluster data
- Co-authorship networks can indicate similar research approaches
- Balance between accuracy and computational complexity
- **Time alignment**: Use 2-year window to match projection horizon (config: collaboration_window)

## Key Questions
1. Direct collaborations only vs. indirect connections (collaborators of collaborators)?
2. **Time window**: 2 years (aligned with projection horizon)
3. How to weight frequent vs. occasional collaborations?
4. Handle cross-domain researchers who span multiple areas?
5. **Integration**: How to combine with constraint-based clustering?

## Proposed Approaches
- **Simple binary**: Direct co-authorship (yes/no) with time decay
- **Weighted network**: Collaboration strength based on publication count and recency
- **Graph-based clustering**: Community detection in collaboration networks
- **Constraint-aware merging**: Prioritize merging groups with similar constraint profiles

## Implementation Considerations
- Computational complexity of network analysis
- Data availability and quality of authorship information
- Interpretability of resulting group mergers
- **Parameter alignment**: Use shared config for time windows and thresholds
- **Quality gates**: Minimum cluster size requirements from config
- **Error handling**: Missing author data, name disambiguation

## Integration Testing
- Mock publication data generator
- Validation against known collaboration patterns
- Sensitivity analysis for collaboration strength thresholds