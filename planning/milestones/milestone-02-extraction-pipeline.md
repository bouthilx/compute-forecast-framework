# Milestone 2: Extraction Pipeline Ready

## Objective
Establish standardized methodology for extracting computational requirements from all paper sources with consistent quality and normalization.

## Success Criteria
- ✅ Standardized extraction template for computational requirements
- ✅ Hardware normalization framework (convert to GPU-equivalent units)
- ✅ Data validation methodology established
- ✅ Consistent extraction methodology across all paper sources

## Detailed Tasks

### Extraction Template Development
- **Core fields to extract**:
  - Hardware specifications (GPU types, counts, memory)
  - Training duration (wall-clock time, epochs, iterations)
  - Experimental scale (number of runs, hyperparameter configurations)
  - Dataset characteristics (size, preprocessing compute)
  - Model specifications (parameters, architecture complexity)
  - Additional compute (evaluation, ablations, hyperparameter search)

### Hardware Normalization Framework
- **GPU generation conversion**:
  - Establish conversion factors between GPU generations (K80, P100, V100, A100, H100)
  - Create normalized "GPU-equivalent hours" metric
  - Account for memory capacity differences
  - Document conversion methodology and sources

- **Standardized units**:
  - Primary metric: A100-equivalent GPU-hours
  - Secondary metrics: FLOP estimates where available
  - Memory requirements: Normalized to standard units
  - Training time: Wall-clock hours with hardware context

### Data Validation Methodology
- **Quality control checks**:
  - Extraction completeness scoring
  - Cross-validation between manual and automated extraction
  - Consistency checks across similar papers
  - Outlier detection and verification

- **Confidence scoring**:
  - High confidence: Explicit computational details provided
  - Medium confidence: Partial information requiring inference
  - Low confidence: Minimal information, significant estimation required

### Extraction Process Design
- **Manual extraction protocol**:
  - Systematic search through methodology, experimental, and supplementary sections
  - Standardized extraction forms for consistency
  - Quality review process for extracted data

- **Automated extraction support**:
  - Text pattern recognition for computational statements
  - Keyword-based search for relevant sections
  - Automated unit conversion and standardization

## Deliverables
1. **Extraction template**: Standardized form for computational data collection
2. **Normalization framework**: GPU conversion factors and standardized units
3. **Validation methodology**: Quality control and confidence scoring system
4. **Extraction protocol**: Step-by-step process for consistent data collection
5. **Training materials**: Guidelines for extraction team (if applicable)

## Quality Checks
- **Template completeness**: All relevant computational aspects covered
- **Normalization accuracy**: Conversion factors validated against established sources
- **Validation robustness**: Quality control catches extraction errors
- **Process clarity**: Extraction protocol is unambiguous and reproducible

## Risk Mitigation
- **Inconsistent extraction**: Detailed protocol and quality review process
- **Normalization errors**: Multiple validation sources for conversion factors
- **Missing data**: Tiered extraction approach (explicit → inferred → estimated)
- **Time constraints**: Prioritize high-confidence extractions over complete coverage

## Dependencies
- Completed paper selection (Milestone 1)
- Access to GPU performance benchmarks for normalization
- Extraction tools and templates

## Timeline
- **Duration**: 1 day
- **Completion criteria**: Extraction pipeline ready for immediate deployment on selected papers
