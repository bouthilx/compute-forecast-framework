# V2 Methodology - Unclear Aspects for Elaboration

## 1. Data Weighting Strategy

### Core Question
How should we weight recent vs. historical data in our analysis?

### Key Considerations
- **Temporal relevance**: Should 2023-2025 data have more influence due to evolving research methods?
- **Infrastructure changes**: How do we handle major infrastructure changes (new clusters, GPU upgrades)?
- **External disruptions**: What about COVID-19 impacts on 2020-2021 usage patterns?
- **Research evolution**: How do we account for shifts in computational requirements as research matures?

### Potential Approaches
- Equal weighting across all years
- Exponential decay weighting (more recent = higher weight)
- Segmented approach (pre/post major infrastructure changes)
- Adaptive weighting based on research domain maturity

---

## 2. Co-authorship Analysis Depth

### Core Question
How extensively should we analyze collaboration networks for group consolidation?

### Key Considerations
- **Connection depth**: Direct co-authorships only, or include indirect connections (collaborators of collaborators)?
- **Time window**: What timeframe for co-authorship relevance (last 2-3 years vs. all-time)?
- **Collaboration strength**: How to weight frequent vs. occasional collaborations?
- **Cross-domain collaborations**: How to handle researchers spanning multiple domains?

### Potential Approaches
- Simple direct co-authorship (binary: yes/no)
- Weighted by number of shared publications
- Network analysis with centrality measures
- Time-decayed collaboration strength

---

## 3. Pattern Granularity Decision Framework

### Core Question
What criteria determine whether 5-8 or 10-15 clusters is optimal?

### Key Considerations
- **Statistical significance**: Minimum sample size thresholds for each cluster?
- **Interpretability**: Can we meaningfully characterize and explain each pattern?
- **Predictive power**: Which granularity gives better projection accuracy?
- **Actionability**: What level of detail is useful for resource planning?

### Evaluation Metrics
- Silhouette score for cluster quality
- Minimum researchers per cluster (e.g., >20 for statistical reliability)
- Variance explained by clustering
- Cross-validation of growth rate predictions

---

## 4. External Benchmark Integration

### Core Question
How should we incorporate broader institutional data into our analysis?

### Key Considerations
- **Hardware normalization**: How to account for different hardware/infrastructure across institutions?
- **Research focus alignment**: How to adjust for different research priorities and domains?
- **Scale differences**: How to compare institutions of different sizes?
- **Data quality variance**: How to handle varying data quality/completeness?

### Integration Strategies
- Normalize by FTE researchers or publication count
- Focus on growth rates rather than absolute numbers
- Weight by research domain overlap with Mila
- Use as validation rather than direct comparison

---

## 5. Growth Rate Methodology

### Core Question
How do we calculate and apply growth rates for 2-year projections?

### Key Considerations
- **Growth model**: Linear vs. exponential vs. logistic growth assumptions?
- **Granularity**: Domain-specific vs. pattern-specific vs. hybrid growth rates?
- **Discontinuities**: How to handle new research areas or breakthrough technologies?
- **Saturation effects**: Are there natural limits to computational growth?

### Methodological Options
- Simple linear regression on historical usage
- Exponential smoothing with trend
- Segmented growth rates by research maturity
- Ensemble of multiple growth models

---

## 6. Uncertainty Quantification

### Core Question
How do we properly quantify and communicate uncertainty in our projections?

### Key Considerations
- **Confidence intervals**: What statistical methods for uncertainty bounds?
- **Scenario analysis**: Best/worst case scenarios vs. probabilistic ranges?
- **Compounding uncertainty**: How do clustering + growth + external factors combine?
- **Communication**: How to present uncertainty to decision-makers?

### Approaches
- Bootstrap resampling for confidence intervals
- Monte Carlo simulation for scenario analysis
- Sensitivity analysis for key parameters
- Multiple projection scenarios (conservative/optimistic/realistic)

---

## Next Steps
Elaborate on each aspect in detail, starting with the most critical for methodology success.
