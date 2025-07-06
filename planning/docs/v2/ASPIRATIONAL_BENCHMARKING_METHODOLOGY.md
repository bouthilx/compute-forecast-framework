# V2 Aspirational Benchmarking Methodology

## Core Approach: High-Impact External Papers as Computational Benchmarks

### Methodology Pivot Rationale
- **Constraint problem**: Both Mila usage data and Mila papers reflect resource limitations
- **Aspirational targets**: Highly-cited external papers represent what Mila researchers aim to achieve
- **Better resource documentation**: Top-tier papers more likely to have detailed computational sections
- **Methodological standards**: Define computational requirements for state-of-the-art research

---

## Phase 1: High-Impact Paper Selection

### Selection Criteria - Dual Benchmark Temporal Analysis

#### Academic Benchmark Papers (2019-2024 Evolution)
- **Citation threshold**: Top academic papers by domain for EACH year (2019-2024)
- **Institution filter**: Universities, academic research labs (not industry)
- **Venue focus**: NeurIPS, ICML, ICLR, academic Nature/Science papers
- **Temporal coverage**: Track computational evolution across 6-year period
- **Purpose**: Analyze how academic computational standards have evolved

#### Industry Benchmark Papers (2019-2024 Evolution)
- **High-impact industry papers**: OpenAI, DeepMind, Meta AI, Google Research by year
- **Breakthrough methodologies**: Track computational paradigm shifts over time
- **Resource transparency**: Industry papers with documented requirements across years
- **Temporal coverage**: Chronicle industry computational scaling 2019-2024
- **Purpose**: Analyze computational frontier evolution and innovation trajectory

### Domain-Specific Selection
- **NLP/LLM**: GPT papers, BERT, T5, PaLM, recent foundation models
- **Computer Vision**: ResNet, EfficientNet, CLIP, diffusion models, DALL-E
- **Reinforcement Learning**: AlphaGo, OpenAI Five, recent policy learning breakthroughs
- **Multimodal**: CLIP, DALL-E, GPT-4, recent multimodal architectures
- **Audio/Speech**: Whisper, recent speech synthesis breakthroughs

### Sample Size per Domain (Temporal Distribution)
- **Academic benchmark**: 1-2 papers per year per domain (2019-2024) = 6-12 papers per domain
- **Industry benchmark**: 1-2 breakthrough papers per year per domain (2019-2024) = 6-12 papers per domain
- **Total**: 12-24 papers per domain across temporal evolution
- **Temporal balance**: Equal representation across years to track evolution patterns

---

## Phase 2: Computational Requirement Extraction

### Extraction Strategy
- **Detailed analysis**: Manual extraction for high-quality data
- **Focus areas**: Training specifications, hyperparameter searches, evaluation protocols
- **Hardware normalization**: Convert to standardized GPU-equivalent units
- **Scale documentation**: Full experimental pipeline, not just final model training

### Key Information to Extract
- **Training compute**: Total GPU-hours for main model training
- **Hyperparameter optimization**: Additional compute for architecture/hyperparameter search
- **Evaluation compute**: Computational cost of comprehensive evaluation
- **Ablation studies**: Additional experiments for paper completeness
- **Reproducibility**: Multiple runs for statistical significance

### Computational Categories
1. **Minimum viable**: Basic replication of core results
2. **Standard research**: Full experimental validation including ablations
3. **Comprehensive study**: Extensive hyperparameter search and analysis
4. **Innovation ready**: Additional compute for novel directions

---

## Phase 3: Mila Trend Analysis & Benchmark Comparison

### Mila Internal Computational Trends (2019-2024)
- **Extract computational data from Mila papers**: Training specifications, hardware usage, experimental scale
- **Temporal trend analysis**: How Mila's computational requirements have evolved
- **Domain-specific growth**: Computational scaling patterns by research area at Mila
- **Research intensity evolution**: Changes in experimental comprehensiveness over time

### Mila vs. Benchmark Gap Analysis
- **Academic gap**: How Mila's computational usage compares to academic benchmark papers
- **Industry gap**: Distance between Mila capabilities and industry breakthrough requirements
- **Trend comparison**: Mila's growth rate vs. external benchmark evolution
- **Competitive positioning**: Where Mila stands relative to academic peers and industry leaders

### Research Group Classification
- **Map Mila groups to domains**: Based on citation patterns and research focus
- **Identify aspirational targets**: Which benchmark papers each group is trying to match/exceed
- **Constraint evidence**: How Mila papers show computational limitations vs. benchmark requirements
- **Research opportunity**: What breakthroughs become possible with benchmark-level compute

---

## Phase 4: Projection Framework

### 2-Year Projection Methodology - Dual Benchmark Framework

#### Academic Competitiveness Projection
```
Academic_Requirement_2027 = Academic_Benchmark_Compute × Mila_Researchers × Research_Activity
```
- **Purpose**: Demonstrate minimum compute needed to remain competitive in academic research
- **Justification**: "Without this, we fall behind peer academic institutions"

#### Innovation Opportunity Projection  
```
Innovation_Requirement_2027 = Industry_Benchmark_Compute × Breakthrough_Factor × Mila_Researchers
```
- **Purpose**: Show computational frontier and potential for breakthrough research
- **Justification**: "With this, we can pursue industry-level innovations"

### Projection Categories
1. **Academic Baseline**: Match computational standards of top academic papers
2. **Academic Leadership**: Exceed typical academic computational investment
3. **Innovation Frontier**: Approach industry-level computational capabilities for breakthrough potential

### Strategic Narrative Framework
- **Academic benchmarks**: "This is what we need to stay competitive"
- **Industry benchmarks**: "This is what becomes possible with adequate resources"
- **Gap analysis**: "Here's what we're missing compared to both academic peers and innovation leaders"

---

## Implementation Advantages

### Addresses Constraint Problem
- **Unconstrained benchmarks**: High-impact papers reflect adequate resource availability
- **Methodological standards**: Define what "normal" research looks like with sufficient compute
- **Aspirational clarity**: Clear targets for what Mila researchers want to achieve

### Practical Benefits
- **Defensible projections**: Based on proven research impact, not speculative scaling
- **Domain expertise**: Leverages existing knowledge of influential papers
- **Communication clarity**: Easy to explain "we need compute to do research like [famous paper]"

### Risk Mitigation
- **Quality control**: Focus on proven methodologies rather than experimental approaches
- **Incremental approach**: Start with replication, then innovation
- **Validation**: Cross-check projections against multiple high-impact benchmarks

---

## Success Metrics

### Data Quality
- **Computational extraction**: Detailed compute requirements from 15-25 landmark papers
- **Domain coverage**: Representative benchmarks across all major Mila research areas
- **Temporal relevance**: Emphasis on 2022-2024 computational standards

### Projection Quality
- **Aspirational alignment**: Projections enable Mila researchers to attempt high-impact methodologies
- **Resource justification**: Clear connection between compute and research capability
- **Competitive positioning**: Projections enable competitive research relative to top institutions

---

## Timeline Allocation (5-7 days)

### Days 1-2: Benchmark Paper Selection
- Identify most cited/influential papers per domain
- Focus on papers with detailed computational documentation
- Validate selection with domain knowledge

### Days 3-4: Computational Requirement Extraction
- Manual extraction of detailed computational requirements
- Normalize across hardware generations and methodologies
- Categorize by research intensity level

### Days 5: Mila Mapping & Projection
- Map Mila research groups to aspirational benchmarks
- Calculate 2-year computational requirements
- Develop conservative/competitive/leadership scenarios

### Days 6-7: Report Generation
- Synthesize findings into compelling resource justification
- Emphasize research opportunities enabled by adequate compute
- Present clear connection between compute and research impact