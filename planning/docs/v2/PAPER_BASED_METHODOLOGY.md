# V2 Paper-Based Computational Requirements Methodology

## Core Approach: Extract True Computational Demand from Research Papers

### Primary Methodology
**Paper-based computational requirement extraction** as the foundation for demand estimation, with usage patterns as optional validation if time permits.

---

## Phase 1: Paper Computational Requirement Extraction

### Data Sources
- **Mila paper corpus 2019-2025**: Focus on papers with computational details
- **Methodology sections**: Extract training specifications, hardware used, duration
- **Experimental sections**: Multiple runs, hyperparameter searches, ablation studies
- **Supplementary materials**: Often contain detailed computational information

### Extraction Strategy
1. **Automated text extraction**: NLP pipeline to identify computational statements
2. **Manual validation**: Spot-check automated extraction quality
3. **Standardization**: Convert to common units (GPU-hours, normalized by hardware generation)

### Key Information to Extract
- **Hardware specifications**: GPU types, counts, memory
- **Training duration**: Wall-clock time, epochs, iterations
- **Experimental scale**: Number of runs, hyperparameter configurations
- **Dataset scale**: Input data size affecting computational requirements
- **Model architecture**: Parameters, layers affecting resource needs

---

## Phase 2: Research Domain Analysis

### Domain Categorization
- **Natural Language Processing**: LLMs, transformers, sequence models
- **Computer Vision**: CNNs, diffusion models, multimodal
- **Reinforcement Learning**: Policy training, environment simulation
- **Machine Learning Theory**: Smaller-scale experimental validation
- **Audio/Speech**: Signal processing, generation models
- **Robotics**: Simulation, control learning

### Domain-Specific Patterns
- **Computational intensity**: GPU-hours per paper by domain
- **Scaling trends**: How requirements change over time per domain
- **Methodology evolution**: Shift from smaller to larger scale experiments

---

## Phase 3: Growth Trend Analysis

### Temporal Analysis
- **Year-over-year growth**: Computational requirements by domain and year
- **Paradigm shifts**: Identify discontinuous jumps (e.g., transformer adoption)
- **Emerging areas**: New computational patterns in recent papers

### Growth Drivers
- **Model scaling**: Larger models requiring more compute
- **Experimental comprehensiveness**: More extensive hyperparameter searches
- **Reproducibility**: Multiple runs for statistical significance
- **New methodologies**: Novel approaches with different computational profiles

---

## Phase 4: Projection Framework

### 2-Year Projection Methodology
1. **Domain-specific growth rates**: Based on paper analysis trends
2. **Research group mapping**: Assign groups to domains based on paper output
3. **Scale adjustment**: Account for difference between "reported" and "ideal" compute
4. **Uncertainty quantification**: Confidence intervals based on data quality

### Projection Calculation
```
Domain_Requirement_2027 = Current_Papers × Growth_Rate × Scale_Multiplier × Group_Size_Growth
```

Where:
- **Current_Papers**: Recent computational requirements from papers
- **Growth_Rate**: Historical trend from paper analysis
- **Scale_Multiplier**: Adjustment for "ideal" vs. "reported" compute (>1.0)
- **Group_Size_Growth**: Expected growth in researchers per domain

---

## Implementation Challenges & Solutions

### Challenge 1: Incomplete Reporting
**Problem**: Papers don't always report computational details
**Solution**: 
- Focus on venues/conferences with better reporting standards
- Use computational details when available, infer patterns for similar work
- Weight extraction by paper impact/citations

### Challenge 2: Hardware Normalization
**Problem**: Different GPU generations across papers
**Solution**:
- Convert all requirements to standardized units (e.g., A100-equivalent hours)
- Use established conversion factors between GPU generations
- Focus on trends rather than absolute numbers

### Challenge 3: Scale Underestimation
**Problem**: Papers may report minimal successful experiments, not comprehensive research
**Solution**:
- Apply scale multipliers based on research methodology
- Use external benchmarks for "typical" research computational needs
- Interview domain experts for scale factors (limited scope)

### Challenge 4: Emerging Research Areas
**Problem**: New areas may not have sufficient historical data
**Solution**:
- Emphasize recent papers more heavily
- Use growth rates from related established domains
- Apply conservative estimates with large uncertainty bounds

---

## Success Metrics

### Data Quality Indicators
- **Extraction coverage**: % of papers with extractable computational information
- **Domain representation**: Computational data across all major research areas
- **Temporal coverage**: Sufficient data points for trend analysis

### Projection Quality
- **Validation against known constraints**: Do projections exceed known resource limitations reasonably?
- **Domain expertise alignment**: Do projections align with expert expectations?
- **Growth rate plausibility**: Are projected growth rates sustainable and realistic?

---

## Timeline Allocation (5-7 days)

### Days 1-2: Paper Analysis Pipeline
- Automated extraction system development
- Manual validation and standardization
- Domain categorization of papers

### Days 3-4: Requirement Analysis
- Extract computational requirements from paper corpus
- Domain-specific trend analysis
- Growth rate calculation

### Days 5: Projection & Validation
- 2-year projections by domain
- External validation where possible
- Uncertainty quantification

### Days 6-7: Report Generation
- Synthesize findings into 3-4 page report
- Focus on paper-based projections
- Include usage data validation if time permits

---

## Optional: Usage Pattern Validation (If Time Permits)
- Compare paper-based projections with usage patterns
- Identify discrepancies between reported and actual usage
- Use as sanity check rather than primary methodology
- Adjust projections if major inconsistencies found