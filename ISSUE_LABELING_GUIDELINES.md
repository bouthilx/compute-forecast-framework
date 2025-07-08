# Issue Labeling and Custom Field Guidelines

## Overview

All issues in the compute-forecast repository must be tagged with both a **Work Type** and a **Domain** to ensure proper categorization and project management. These tags are applied as both GitHub labels and project custom fields.

## Work Type Tags

Each issue must have exactly **one** Work Type tag that describes the primary nature of the work:

### `work:implementation`
**Description**: Building new code, infrastructure, modules, or systems
**Use when**:
- Creating new Python modules or classes
- Building infrastructure components
- Implementing algorithms or data pipelines
- Setting up integration between systems
- Developing new functionality

**Examples**:
- "Implement venue normalization module"
- "Create deduplication pipeline"
- "Build API collection system"

### `work:design`
**Description**: Planning, architecting, or designing systems/methodologies
**Use when**:
- Creating architectural plans
- Designing system workflows
- Planning methodologies or approaches
- Developing templates or frameworks
- Structuring reports or deliverables

**Examples**:
- "Design hierarchical state management system"
- "Plan extraction process methodology"
- "Design report structure"

### `work:execution`
**Description**: Running existing code to generate results, process data, or produce outputs
**Use when**:
- Running analysis scripts
- Executing data extraction
- Processing papers through pipelines
- Generating visualizations from data
- Running validation or tests

**Examples**:
- "Execute benchmark paper extraction"
- "Run growth rate calculations"
- "Generate temporal evolution charts"

### `work:writing`
**Description**: Creating documentation, reports, analysis writeups, or other text deliverables
**Use when**:
- Writing report sections
- Creating documentation
- Preparing analysis summaries
- Writing executive summaries
- Compiling final deliverables

**Examples**:
- "Write suppression analysis section"
- "Create methodology appendix"
- "Prepare final report"

## Domain Tags

Each issue must have exactly **one** Domain tag that describes the primary area of focus:

### `domain:collection`
**Description**: Gathering papers, datasets, or raw data from various sources
**Use when**:
- Fetching papers from APIs
- Collecting datasets
- Gathering venue information
- Retrieving citation data
- Aggregating source materials

**Examples**:
- "Collect papers from NeurIPS 2019-2024"
- "Gather Mila publication data"
- "Retrieve citation counts"

### `domain:extraction`
**Description**: Extracting information from papers (computational requirements, metrics, classifications)
**Use when**:
- Parsing computational requirements
- Extracting GPU hours, parameters
- Identifying benchmarks used
- Extracting domain-specific metrics
- Mining paper metadata

**Examples**:
- "Extract GPU usage from ML papers"
- "Parse training time metrics"
- "Extract NLP-specific metrics"

### `domain:analysis`
**Description**: Analyzing extracted data for patterns, trends, insights, or comparisons
**Use when**:
- Computing growth rates
- Comparing trends
- Generating insights
- Creating visualizations
- Performing statistical analysis

**Examples**:
- "Analyze compute growth trends"
- "Compare Mila vs external institutions"
- "Calculate suppression metrics"

### `domain:testing`
**Description**: Validation, quality assurance, testing infrastructure, or verification activities
**Use when**:
- Creating test suites
- Validating data quality
- Building testing frameworks
- Verifying extraction accuracy
- Quality control processes

**Examples**:
- "Validate extraction accuracy"
- "Test pipeline end-to-end"
- "Create mock data framework"

### `domain:installation`
**Description**: Core system architecture, frameworks, or foundational components
**Use when**:
- Setting up project structure
- Creating core infrastructure
- Building foundational systems
- Establishing architecture
- Setting up monitoring/dashboards

**Examples**:
- "Setup project architecture"
- "Create state management system"
- "Build monitoring dashboard"

## Decision Tree for Tagging

### Work Type Decision:
1. **Am I building something new?** → `work:implementation`
2. **Am I planning/designing how something should work?** → `work:design`
3. **Am I running existing code/scripts?** → `work:execution`
4. **Am I writing documentation/reports?** → `work:writing`

### Domain Decision:
1. **Am I gathering raw data/papers?** → `domain:collection`
2. **Am I parsing/extracting info from papers?** → `domain:extraction`
3. **Am I analyzing/comparing extracted data?** → `domain:analysis`
4. **Am I validating/testing quality?** → `domain:testing`
5. **Am I building core infrastructure?** → `domain:installation`

## Application Process

### For GitHub Issues:

1. **Create the issue** with title and description
2. **Apply labels**:
   ```
   gh issue create --title "Your Title" --body "Description" \
     --label "work:execution,domain:analysis"
   ```
   Or via GitHub UI: Add both labels in the Labels section

### For Project Custom Fields:

1. **Add issue to project** "Orchestrator: Computational Needs Analysis 2025-2027"
2. **Set Work Type field** to match the work: label
3. **Set Work Domain field** to match the domain: label

## Common Patterns

### Implementation + Installation
Core infrastructure building:
- "Setup project architecture"
- "Create monitoring system"

### Implementation + Extraction
Building extraction tools:
- "Create GPU hours extractor"
- "Build paper parser module"

### Execution + Analysis
Running analytical processes:
- "Generate growth rate charts"
- "Compute suppression metrics"

### Writing + Analysis
Documenting analysis results:
- "Write findings section"
- "Create executive summary"

### Design + Testing
Planning validation approaches:
- "Design validation methodology"
- "Plan quality framework"

## Edge Cases

### Visualization Tasks
- **Creating visualization code**: `work:implementation` + `domain:analysis`
- **Running code to generate charts**: `work:execution` + `domain:analysis`

### Testing Infrastructure
- **Building test framework**: `work:implementation` + `domain:testing`
- **Running tests**: `work:execution` + `domain:testing`

### Report Planning
- **Designing report structure**: `work:design` + `domain:analysis`
- **Writing report content**: `work:writing` + `domain:analysis`

## Validation Checklist

Before submitting an issue, verify:
- [ ] Issue has exactly ONE work:* label
- [ ] Issue has exactly ONE domain:* label
- [ ] Labels accurately reflect the primary work and focus
- [ ] If in project, custom fields match the labels
- [ ] Title clearly indicates the task nature

## Examples of Well-Tagged Issues

1. **"Implement citation deduplication algorithm"**
   - `work:implementation` (building new code)
   - `domain:analysis` (processing/analyzing citation data)

2. **"Execute Q4 2024 paper collection from arXiv"**
   - `work:execution` (running collection scripts)
   - `domain:collection` (gathering papers)

3. **"Design suppression metric calculation methodology"**
   - `work:design` (planning approach)
   - `domain:analysis` (focused on analytical methodology)

4. **"Write methodology section for final report"**
   - `work:writing` (creating documentation)
   - `domain:analysis` (documenting analysis approach)

## Quick Reference

| If you're... | Use Work Type | Common Domains |
|-------------|---------------|----------------|
| Building new code | `work:implementation` | Any |
| Planning approach | `work:design` | Any |
| Running scripts | `work:execution` | Collection, Extraction, Analysis, Testing |
| Writing docs | `work:writing` | Analysis (usually) |
| Setting up infra | `work:implementation` | Installation |
| Parsing papers | `work:execution` | Extraction |
| Comparing data | `work:execution` | Analysis |
| Validating results | `work:execution` | Testing |
