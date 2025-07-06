# V2 Methodology - Clarifications and Decisions

## Project Scope
- **Timeline**: 2-year projection (instead of 5-year from v1)
- **Deliverable**: 3-4 page preliminary report by end of week
- **Approach**: Data-driven analysis minimizing professor/student involvement

## Data Sources Available
1. **Cluster usage data**: Job-level with requested resources + actual usage
2. **Paper corpus**: Mila researchers 2019-2025 for research trends/domains analysis  
3. **Research group data**: Group compositions and student counts
4. **External benchmarks**: Data from other research labs (papers + surveys)

## Methodology: Pattern-Based Clustering (4-5 day timeline)

### Core Approach
- Focus on **usage patterns across research groups** rather than individual researchers
- Cluster based on computational patterns, not just research sub-domains
- Cross-validate patterns with research domain trends from paper analysis

### Key Hypothesis
Many research sub-domains share similar computational usage patterns, making pattern-based clustering more effective than domain-specific analysis.

## Analysis Strategy

### Phase 1: Usage Pattern Discovery
- Cluster researchers/groups by computational usage patterns from cluster data
- Identify pattern characteristics: GPU count, memory usage, job duration, frequency
- Correlate patterns with research domains from paper analysis

### Phase 2: Trend Analysis  
- Analyze historical growth in each usage pattern cluster
- Apply both **historical trend extrapolation** and **research domain shift** considerations
- Use paper trends to validate and adjust usage pattern projections

### Phase 3: External Validation
- Compare patterns and growth rates with external lab data
- Adjust projections based on external benchmarks

## Output Requirements

### Primary Goal
Demonstrate potential achievements with additional compute resources and justify need for these resources.

### Report Structure
1. **Aggregate projections**: Total resource needs for 2-year horizon
2. **Domain decomposition**: Breakdown by research domains
3. **Uncertainty analysis**: Confidence intervals and risk assessment

### Estimation Philosophy
- Expect to **underestimate needs** (conservative approach acceptable)
- Include uncertainty ranges for decision-making flexibility

## Risk Management
- **Data quality issues**: Plan backup approaches if correlations fail
- **Confidence intervals**: Essential for all projections
- **Validation methods**: Cross-reference multiple data sources

## Finalized Decisions

### Data Integration Strategies
- **Groups with limited data**: Merge with similar groups based on research domains and co-authorship networks
- **External benchmarks**: Include broader range of institutions for comprehensive context
- **Pattern granularity**: Test both 5-8 broad patterns and 10-15 specific patterns to determine optimal approach

## Open Questions for Implementation
1. **Data weighting**: Should recent trends be weighted more heavily? (Requires further consideration of weighting methodology)
2. **Minimum sample size**: What's the threshold for reliable pattern cluster projections?
3. **Co-authorship analysis**: How deep should we analyze collaboration networks for group merging?