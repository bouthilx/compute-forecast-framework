# Claude Development Guidelines

## Project Overview

**Goal**: Generate a 3-4 page preliminary report projecting Mila's computational needs for 2025-2027 through evidence-based analysis of research computational requirements.

**Timeline**: 5-7 days total

**Deliverable**: Compelling justification for computational investment based on quantified gaps and suppressed demand

It contains a python package under `package` that serves as the analysis tools based on data extracted from papers over multple years for publications.

The data analysis is presented and described in a report under `report`.

## Strategic Project Goals

### 1. **Demonstrate Computational Gap Through Evidence**
- Quantify how Mila's computational capabilities lag behind both academic peers and industry leaders
- Show temporal evolution: how the gap has been widening from 2019-2024
- Provide concrete examples of research Mila cannot currently pursue

### 2. **Reveal Suppressed Demand**
- Document the hidden cost of computational constraints
- Show what Mila researchers are forced to sacrifice: fewer experiments, smaller models, limited validation
- Quantify the ~68% suppressed demand through comparative analysis

### 3. **Enable Dual Benchmark Defense**
- **Academic Benchmark**: "This is the minimum to stay competitive with peer institutions"
- **Industry Benchmark**: "This is what enables breakthrough innovations"
- Counter the "do different research" argument with evidence from purely academic institutions

### 4. **Project Future Needs with Credibility**
- Use historical trends from both Mila and benchmark institutions
- Show that computational requirements are growing at 52% (Mila) vs 89% (benchmarks) annually
- Demonstrate that without investment, the competitive gap will become insurmountable

## Core Methodology

### Three-Pillar Analysis Framework

#### Pillar 1: Mila Internal Analysis (150-180 papers)
- Extract computational specifications from Mila papers (2019-2024)
- Document explicit mentions of resource constraints
- Analyze experimental scope limitations and methodological compromises

#### Pillar 2: External Benchmark Analysis (300-400 papers)
- **Academic Benchmarks**: MIT, Stanford, CMU papers showing academic computational standards
- **Industry Benchmarks**: OpenAI, DeepMind, Meta AI papers showing innovation frontier
- Temporal analysis: track how computational requirements evolved 2019-2024

#### Pillar 3: Suppressed Demand Quantification
- Compare what Mila did vs. what benchmarks did with adequate resources
- Measure missing experiments, reduced model scales, limited hyperparameter searches
- Calculate composite suppression index showing ~68% unmet computational need

## Implementation Principles

### 1. **Time-Boxed Pragmatism**
- Every issue has hours, not days
- S(2-3h), M(4-6h), L(6-8h) are hard limits
- If it can't be done in the time budget, simplify the approach

### 2. **Research Project, Not Production System**
- This is temporary analysis code for a one-time report
- Prioritize "good enough" over "perfect"
- No need for long-term maintainability or scaling

### 3. **Extend, Don't Rebuild**
- Use existing components where possible
- Minimal modifications to achieve goals
- Avoid architectural overhauls

### 4. **Focus on Evidence Quality**
- Better to extract reliable data from 100 papers than unreliable data from 1000
- Manual validation > complex automation
- Simple statistics > sophisticated ML

### 5. **Report-Driven Development**
- Every component should directly contribute to report sections
- If it doesn't help tell the story, don't build it
- Visualizations and evidence matter more than code elegance

## Technical Guidelines

### Appropriate Technology Choices
- **Simple Python scripts** over complex frameworks
- **Basic pandas/numpy** for data analysis
- **Matplotlib/seaborn** for quick visualizations
- **Standard NLP tools** (spaCy, regex) for text extraction
- **LaTeX** for final report generation

### What NOT to Do
- ❌ Build comprehensive frameworks or libraries
- ❌ Design for extensibility
- ❌ Implement complex architectural patterns
- ❌ Optimize for performance at scale

### What TO Do
- ✅ Write straightforward, readable code
- ✅ Focus on data extraction accuracy
- ✅ Create clear visualizations
- ✅ Document assumptions and limitations
- ✅ Validate results with spot checks

## Project Phases

```
Paper Collection & Extraction Pipeline
├── Collect Mila papers (150-180) and benchmark papers (300-400)
├── Extract computational specifications and constraint indicators
├── Manual validation of extraction quality
└── Build comparative database

Gap Analysis & Suppression Measurement
├── Calculate computational gaps: Mila vs Academic vs Industry
├── Quantify suppressed demand indicators
├── Analyze temporal trends (2019-2024)
└── Statistical validation of findings

Projection & Validation
├── Apply growth models for 2025-2027
├── Create dual benchmark scenarios
├── Quantify uncertainty ranges
└── External validation checks

Report Generation
├── Write compelling narrative with evidence
├── Create impactful visualizations
├── Integrate suppression findings
└── Final review and LaTeX compilation
```

## Success Criteria

1. **Quantified Gaps**: Specific multipliers showing Mila vs benchmark computational differences
2. **Suppressed Demand Evidence**: % suppression index with supporting metrics
3. **Defensible Projections**: Dual benchmark approach that counters expected objections
4. **Compelling Story**: Clear narrative from constraint to opportunity
5. **Actionable Recommendations**: Specific computational investments by domain and timeline

## Key Report Messages

### Opening Hook
"Mila researchers are achieving remarkable results despite operating with 15-27x less computational resources than their peers, but this constraint is becoming unsustainable."

### Core Arguments
1. **Competitive Crisis**: The computational gap with academic peers grew from 6.8x to 26.7x (2019-2024)
2. **Hidden Costs**: 68% of potential research remains unexplored due to resource constraints
3. **Growth Imperative**: Computational needs growing at 89% annually in the field vs Mila's 52%
4. **Innovation Opportunity**: Specific breakthroughs possible with adequate computational investment

### Closing Vision
"With appropriate computational resources, Mila can transition from following breakthroughs to creating them."

## Remember

**This is a focused research project to inform funding decisions, not a software engineering exercise.**

When implementing any issue, ask yourself:
- Does this directly help generate the report? (with the caveat that monitoring tools for long execution processes is helpful)
- Can I complete it within the time budget?
- Am I over-engineering for non-existent requirements?
- Is there a simpler approach that achieves the same goal?

**When in doubt, choose the simpler path, and ask for confirmation**

## Planning and tracking guidelines

### Planning

When creating new issues, follow the guidelines in `ISSUE_LABELING_GUIDELINES.md` for the labeling of the issues.

### Journaling

Keep a journal in `journals/` in markdown format where you detail the analysis requested, how you proceeded and what the outcomes were. Add a timestamp and a title for each important interactions. Use your judgement to squash multiple interactions together in one journal entry if the interactions are iterations on a precise analysis question. When commiting your work, include the contributed journals.


## Package Management
- **Use `uv` for dependency management** (not pip or conda)
- Dependencies are defined in `pyproject.toml` under `[dependency-groups]`
- Install dependencies: `uv sync --group test --group docs`
- Add new dependencies: `uv add <package>` or `uv add --group <group> <package>`
- Add new dependecies of optional plugins: `uv add --extra <plugin>`

## Code Quality & Linting
- **Use `ruff` for linting and formatting** (configured in `pyproject.toml`)
- Run linting: `uv run tox -e lint`
- Auto-format code: `uv run tox -e format`
- Configuration:
  - Line length: 100 characters
  - Python version target: 3.10+
  - Quote style: double quotes

## Testing
- **Use `pytest` for all testing**
- Test structure:
  - `tests/unittest/` - Unit tests for individual components
  - `tests/functional/` - Integration and scenario tests
- **Coverage requirement: 90% minimum**
- Run tests:
  - All tests with coverage: `uv run tox -e all` or `uv run pytest`
  - Unit tests only: `uv run tox -e unit`
  - Functional tests only: `uv run tox -e functional`
  - Quick tests (no coverage): `uv run tox -e quick`
  - Debug mode: `uv run tox -e debug`
- Coverage reports are generated in `htmlcov/index.html`

## Code Organization
[TODO]

## Documentation
- **Use MkDocs for documentation**
- Auto-generate API docs: `python scripts/generate_docs.py`
- Build docs: `uv run tox -e docs`
- Serve docs locally: `uv run tox -e docs-serve`
- Documentation is built to `site/` directory

## Development Workflow
1. **Before making changes**: Run `uv run tox -e lint` to check code quality
2. **After making changes**:
   - Run `uv run pytest` to ensure tests pass with coverage
   - Run `uv run tox -e lint` to verify code quality
3. **For new features**: Add appropriate unit and/or functional tests

## Architecture Guidelines
- Follow the existing modular pattern
- Use composition over inheritance where possible
- Implement proper separation of concerns between engine, entities, world, and scenes
- All classes should have clear, single responsibilities
- Use type hints where beneficial (not enforced but encouraged)

## Package-Specific Guidelines
[TODO]

## Multi-Environment Testing
- Supports Python 3.10-3.10 via tox
- Run across all Python versions: `uv run tox`
- Specific Python version: `uv run tox -e py310`

## Common Commands
```bash
# Install dependencies
uv sync --group test --group docs

# Run all tests with coverage
uv run pytest

# Quick test run
uv run tox -e quick

# Lint and format code
uv run tox -e format

# Generate and build documentation
uv run tox -e docs

# Run specific test file
uv run pytest tests/unittest/test_player.py

# Run with specific coverage target
uv run pytest --cov-fail-under=90
```

## Error Handling
- When tests fail due to coverage, use `uv run tox -e coverage-only` to generate reports without failing
- Use `uv run tox -e debug` for detailed test output when debugging
