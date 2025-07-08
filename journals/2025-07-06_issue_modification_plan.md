# Issue Modification Plan: Pipeline → Compute Forecast

**Date**: 2025-07-06
**Title**: Plan for modifying all issues in milestone #20 to use compute_forecast package name
**Purpose**: Ensure consistency across all refactoring issues with correct package naming and command execution

## Overview

All 5 issues in milestone "Pipeline Refactoring: Paper vs PDF Collection" (#20) need to be modified to:
1. Change all references from `pipeline/` to `compute_forecast/`
2. Change all `python` commands to `uv run python`

## Issue-by-Issue Modifications

### Issue #134: [Refactoring 1/5] Create Structure & Move Core Infrastructure

**Directory Structure Changes:**
- Line 20: `mkdir -p package/pipeline/{metadata_collection,paper_filtering,pdf_acquisition,content_extraction,analysis}`
  → `mkdir -p package/compute_forecast/{metadata_collection,paper_filtering,pdf_acquisition,content_extraction,analysis}`
- Lines 21-25: All subdirectory creation under `package/pipeline/` → `package/compute_forecast/`

**Import Test Changes:**
- Lines 132-137: All `python -c "import ..."` → `uv run python -c "import ..."`
- Line 142: `python -c "import ..."` → `uv run python -c "import ..."`

**Directory References in Text:**
- Line 8: "Pipeline stages" comment
- Line 96: `tree -d -L 3 package/` command output will show compute_forecast instead
- Line 376-380: Directory listing commands showing `pipeline/` → `compute_forecast/`

### Issue #135: [Refactoring 2/5] Migrate Pipeline Stages

**File Movement Commands:**
All occurrences of file moves need to change destination:
- Lines 176-194: `pipeline/metadata_collection/` → `compute_forecast/metadata_collection/`
- Lines 196-209: File creation in `pipeline/metadata_collection/orchestrator.py` → `compute_forecast/metadata_collection/orchestrator.py`
- Lines 213-217: `pipeline/paper_filtering/` → `compute_forecast/paper_filtering/`
- Lines 220-233: File creation in `pipeline/paper_filtering/orchestrator.py` → `compute_forecast/paper_filtering/orchestrator.py`
- Lines 238-248: `pipeline/pdf_acquisition/` → `compute_forecast/pdf_acquisition/`
- Lines 251-263: File creation in `pipeline/pdf_acquisition/orchestrator.py` → `compute_forecast/pdf_acquisition/orchestrator.py`
- Lines 268-282: `pipeline/content_extraction/` → `compute_forecast/content_extraction/`
- Lines 284-295: File creation in `pipeline/content_extraction/orchestrator.py` → `compute_forecast/content_extraction/orchestrator.py`
- Lines 300-301: `pipeline/analysis/` → `compute_forecast/analysis/`
- Lines 303-315: File creation in `pipeline/analysis/orchestrator.py` → `compute_forecast/analysis/orchestrator.py`

**Import Statement Changes in Orchestrator Templates:**
- Line 224: `from ..metadata_collection.models import Paper` (will work with compute_forecast too)
- Line 254: `from ..metadata_collection.models import Paper` (will work with compute_forecast too)
- All other relative imports in templates will work correctly

**Directory Listing Commands:**
- Lines 322-324: Comparison paths with `pipeline/` → `compute_forecast/`
- Lines 370-380: Directory verification commands
- Line 383: `ls -la pipeline/*/orchestrator.py` → `ls -la compute_forecast/*/orchestrator.py`

### Issue #136: [Refactoring 3/5] Update Imports & Configuration

**Import Mapping Script:**
All import mappings in the script need to change (lines 425-468):
- `'from pipeline.metadata_collection` → `'from compute_forecast.metadata_collection`
- `'from pipeline.paper_filtering` → `'from compute_forecast.paper_filtering`
- `'from pipeline.pdf_acquisition` → `'from compute_forecast.pdf_acquisition`
- `'from pipeline.content_extraction` → `'from compute_forecast.content_extraction`
- `'from pipeline.analysis` → `'from compute_forecast.analysis`

**Script Execution:**
- Line 589: `python scripts/update_imports.py` → `uv run python scripts/update_imports.py`

**pyproject.toml Update:**
- Line 602: packages list includes "pipeline" → should be "compute_forecast"

**Import Test Commands:**
- Lines 663-668: All `python -c` → `uv run python -c`
- Update import paths in test commands from `pipeline.` to `compute_forecast.`

**Other Python Commands:**
- Line 670: `python -m py_compile` → `uv run python -m py_compile`
- Lines 704-705: `pytest` → `uv run pytest`
- Line 708: `python -m compileall` → `uv run python -m compileall`
- Line 711: `python -c` → `uv run python -c`

### Issue #137: [Refactoring 4/5] Implement Orchestrators & Resolve Conflicts

**File Path Comments:**
All orchestrator file paths in comments need updating:
- Line 746: `# pipeline/metadata_collection/orchestrator.py` → `# compute_forecast/metadata_collection/orchestrator.py`
- Line 790: `# pipeline/paper_filtering/orchestrator.py` → `# compute_forecast/paper_filtering/orchestrator.py`
- Line 859: `# pipeline/pdf_acquisition/orchestrator.py` → `# compute_forecast/pdf_acquisition/orchestrator.py`
- Line 951: `# pipeline/content_extraction/orchestrator.py` → `# compute_forecast/content_extraction/orchestrator.py`
- Line 1023: `# pipeline/analysis/orchestrator.py` → `# compute_forecast/analysis/orchestrator.py`

**Import Statements in Code Examples:**
Need to update all imports in the orchestrator implementations:
- Lines 1098-1102: `from pipeline.` → `from compute_forecast.`
- Lines 1260-1261: Module paths in comparison script

**Test Commands:**
- Lines 1386-1387: `python -c` → `uv run python -c`
- Update import paths in test commands
- Line 1390-1395: `python -c` → `uv run python -c`
- Line 1398: `pytest` → `uv run pytest`

### Issue #138: [Refactoring 5/5] Testing & Documentation

**Test Execution Commands:**
- Line 1435: `pytest` → `uv run pytest`
- Line 1438: `coverage report` → `uv run coverage report`
- Lines 1447-1458: All `pytest` → `uv run pytest`
- Lines 1462-1470: All `pytest` → `uv run pytest`

**Performance Testing:**
- Line 1531: `python -X importtime` → `uv run python -X importtime`

**Documentation Updates:**
Need to update all example imports and paths:
- Lines 1544-1550: Pipeline stage descriptions with paths
- Line 1565: Keep `from orchestration.orchestrators.main_orchestrator` (not under pipeline/compute_forecast)
- Lines 1592-1598: Directory structure showing `pipeline/` → `compute_forecast/`
- Lines 1603-1608: Import examples `from pipeline.` → `from compute_forecast.`

**Migration Guide:**
- Lines 1727-1734: Import mapping table needs updating
- Line 1737: `python scripts/update_imports.py` → `uv run python scripts/update_imports.py`
- Line 1744: `pytest tests/` → `uv run pytest tests/`
- Lines 1768-1769: Mock patch paths need updating

**Architecture Diagram Script:**
- Line 1709: Script execution will use `uv run python scripts/generate_architecture_diagram.py`

**Final Verification Script:**
- Lines 1792-1803: Directory paths to check
- Lines 1832-1835: All `python -c` → `uv run python -c`
- Import paths in commands need updating
- Line 1839: `pytest` → `uv run pytest`

**Final Test Commands:**
- Line 1916: `pytest` → `uv run pytest`
- Line 1919: `pytest` → `uv run pytest`
- Line 1925: `pytest` → `uv run pytest`

## Summary Statistics

Total modifications needed per issue:
- Issue #134: ~15 modifications
- Issue #135: ~40 modifications (many file path changes)
- Issue #136: ~55 modifications (import mappings + commands)
- Issue #137: ~20 modifications
- Issue #138: ~65 modifications (many test commands + documentation)

**Total: ~195 modifications across all 5 issues**

## Execution Strategy

1. Create a script to automate the issue updates using `gh issue edit`
2. For each issue:
   - Fetch current body
   - Apply all replacements
   - Update issue body
3. Verify all changes before pushing

## Key Patterns to Replace

1. **Directory paths**: `pipeline/` → `compute_forecast/`
2. **Import statements**: `from pipeline.` → `from compute_forecast.`
3. **Import mapping strings**: `'from pipeline.` → `'from compute_forecast.`
4. **Commands**: `python ` → `uv run python ` (with appropriate context checking)
5. **Test commands**: `pytest ` → `uv run pytest `
6. **pyproject.toml**: Include "compute_forecast" in packages list instead of "pipeline"

## Risks and Mitigation

1. **Risk**: Missing some occurrences due to pattern variations
   - **Mitigation**: Use multiple search patterns and manual review

2. **Risk**: Breaking relative imports
   - **Mitigation**: Relative imports (like `from ..metadata_collection`) don't need changes

3. **Risk**: Changing non-command instances of "python"
   - **Mitigation**: Only replace when "python" is at start of line or after specific markers

4. **Risk**: Documentation becoming inconsistent
   - **Mitigation**: Ensure all examples and text descriptions are updated together

## Next Steps

1. Review this plan for completeness
2. Create automated update script
3. Execute updates on all 5 issues
4. Verify changes in GitHub UI
5. Test that instructions still make sense with new naming
