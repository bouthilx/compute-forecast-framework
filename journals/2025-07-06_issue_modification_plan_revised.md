# Issue Modification Plan: All Under compute_forecast Package (Revised)

**Date**: 2025-07-06  
**Title**: Revised plan for modifying all issues to place everything under compute_forecast package  
**Purpose**: Ensure all modules are within the compute_forecast Python package, with pipeline as a submodule

## Overview

All 5 issues in milestone "Pipeline Refactoring: Paper vs PDF Collection" (#20) need to be modified to:
1. Place all modules under `package/compute_forecast/`
2. Keep `pipeline` as a submodule under `compute_forecast`
3. Move `core`, `monitoring`, `orchestration`, `quality` under `compute_forecast`
4. Change all `python` commands to `uv run python`

## Key Structure Change

Instead of:
```
package/
├── pipeline/
├── core/
├── monitoring/
├── orchestration/
└── quality/
```

We want:
```
package/
└── compute_forecast/
    ├── pipeline/
    ├── core/
    ├── monitoring/
    ├── orchestration/
    └── quality/
```

## Issue-by-Issue Modifications

### Issue #134: [Refactoring 1/5] Create Structure & Move Core Infrastructure

**Directory Structure Changes:**
- Line 20: `mkdir -p package/pipeline/{metadata_collection,paper_filtering,pdf_acquisition,content_extraction,analysis}`
  → `mkdir -p package/compute_forecast/pipeline/{metadata_collection,paper_filtering,pdf_acquisition,content_extraction,analysis}`
- Lines 21-25: All subdirectory creation under `package/pipeline/` → `package/compute_forecast/pipeline/`
- Lines 28-31: Top-level infrastructure paths:
  - `mkdir -p package/core/{contracts,utils}` → `mkdir -p package/compute_forecast/core/{contracts,utils}`
  - `mkdir -p package/monitoring/...` → `mkdir -p package/compute_forecast/monitoring/...`
  - `mkdir -p package/orchestration/...` → `mkdir -p package/compute_forecast/orchestration/...`
  - `mkdir -p package/quality/validators` → `mkdir -p package/compute_forecast/quality/validators`
- Lines 34-35: Test infrastructure:
  - `mkdir -p package/tests/...` → Keep as is (tests stay at package level)

**Move Commands:**
- Lines 40-41: `mv src/core/* core/` → `mv src/core/* compute_forecast/core/`
- Line 42: `mv src/quality/contracts/* core/contracts/` → `mv src/quality/contracts/* compute_forecast/core/contracts/`
- Line 45: `touch core/utils/__init__.py` → `touch compute_forecast/core/utils/__init__.py`
- Lines 50-58: All monitoring moves to `compute_forecast/monitoring/`
- Lines 64-74: All orchestration moves to `compute_forecast/orchestration/`
- Line 79: `mv src/quality/validators/* quality/validators/` → `mv src/quality/validators/* compute_forecast/quality/validators/`

**Import Test Changes:**
- Lines 132-137: Update imports and use `uv run python`:
  - `python -c "import core.config"` → `uv run python -c "import compute_forecast.core.config"`
  - `python -c "import monitoring.server.dashboard_server"` → `uv run python -c "import compute_forecast.monitoring.server.dashboard_server"`
  - `python -c "import orchestration.core.workflow_coordinator"` → `uv run python -c "import compute_forecast.orchestration.core.workflow_coordinator"`
  - `python -c "import quality.validators.base"` → `uv run python -c "import compute_forecast.quality.validators.base"`

**Directory Verification:**
- Line 96: `tree -d -L 3 package/` → output will show compute_forecast as root
- Line 140: `find core -name "*.py"` → `find compute_forecast/core -name "*.py"`

### Issue #135: [Refactoring 2/5] Migrate Pipeline Stages

**File Movement Commands:**
All occurrences of file moves need to change destination:
- Lines 176-194: `pipeline/metadata_collection/` → `compute_forecast/pipeline/metadata_collection/`
- Lines 196-209: File creation path → `compute_forecast/pipeline/metadata_collection/orchestrator.py`
- Lines 213-217: `pipeline/paper_filtering/` → `compute_forecast/pipeline/paper_filtering/`
- Lines 220-233: File creation path → `compute_forecast/pipeline/paper_filtering/orchestrator.py`
- Lines 238-248: `pipeline/pdf_acquisition/` → `compute_forecast/pipeline/pdf_acquisition/`
- Lines 251-263: File creation path → `compute_forecast/pipeline/pdf_acquisition/orchestrator.py`
- Lines 268-282: `pipeline/content_extraction/` → `compute_forecast/pipeline/content_extraction/`
- Lines 284-295: File creation path → `compute_forecast/pipeline/content_extraction/orchestrator.py`
- Lines 300-301: `pipeline/analysis/` → `compute_forecast/pipeline/analysis/`
- Lines 303-315: File creation path → `compute_forecast/pipeline/analysis/orchestrator.py`

**Import Statement Changes in Orchestrator Templates:**
All orchestrator templates need import updates:
- Metadata collection imports: `from compute_forecast.core.config import CollectionConfig`
- Add `compute_forecast.` prefix to all absolute imports

**Directory Comparison:**
- Lines 324-325: Update comparison paths
- Line 373: `ls -la pipeline/metadata_collection/sources/` → `ls -la compute_forecast/pipeline/metadata_collection/sources/`
- Line 376: `ls -la pipeline/pdf_acquisition/discovery/sources/` → `ls -la compute_forecast/pipeline/pdf_acquisition/discovery/sources/`
- Line 379: `find pipeline/` → `find compute_forecast/pipeline/`
- Line 383: `ls -la pipeline/*/orchestrator.py` → `ls -la compute_forecast/pipeline/*/orchestrator.py`

### Issue #136: [Refactoring 3/5] Update Imports & Configuration

**Import Mapping Script:**
All import mappings in the script need to change (lines 425-468):
```python
IMPORT_MAPPINGS = {
    # Metadata collection
    r'from src\.data\.sources': 'from compute_forecast.pipeline.metadata_collection.sources',
    r'from src\.data\.collectors': 'from compute_forecast.pipeline.metadata_collection.collectors',
    # ... all pipeline imports prefix with compute_forecast.pipeline.
    
    # Core
    r'from src\.core': 'from compute_forecast.core',
    r'from src\.quality\.contracts': 'from compute_forecast.core.contracts',
    
    # Monitoring
    r'from src\.monitoring': 'from compute_forecast.monitoring',
    
    # Orchestration
    r'from src\.orchestration': 'from compute_forecast.orchestration',
    
    # Quality
    r'from src\.quality\.validators': 'from compute_forecast.quality.validators',
    r'from src\.quality': 'from compute_forecast.pipeline.content_extraction.quality',
}
```

**Script Execution:**
- Line 589: `python scripts/update_imports.py` → `uv run python scripts/update_imports.py`

**pyproject.toml Update:**
```toml
[tool.setuptools]
packages = ["compute_forecast"]

[tool.setuptools.package-dir]
"" = "package"

[project.scripts]
compute-forecast = "compute_forecast.orchestration.orchestrators.main_orchestrator:main"
```

**pytest.ini Update:**
```ini
addopts = 
    --cov=compute_forecast
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
pythonpath = package
```

**Import Test Commands:**
- Lines 663-668: All need `compute_forecast.` prefix and `uv run`:
  - `uv run python -c "from compute_forecast.pipeline.metadata_collection.models import Paper"`
  - `uv run python -c "from compute_forecast.pipeline.paper_filtering import computational_filter"`
  - etc.

### Issue #137: [Refactoring 4/5] Implement Orchestrators & Resolve Conflicts

**File Path Comments:**
All orchestrator file paths in comments need updating:
- Line 746: `# compute_forecast/pipeline/metadata_collection/orchestrator.py`
- Line 790: `# compute_forecast/pipeline/paper_filtering/orchestrator.py`
- Line 859: `# compute_forecast/pipeline/pdf_acquisition/orchestrator.py`
- Line 951: `# compute_forecast/pipeline/content_extraction/orchestrator.py`
- Line 1023: `# compute_forecast/pipeline/analysis/orchestrator.py`

**Import Statements in Code Examples:**
All imports need `compute_forecast.` prefix:
- Line 753: `from compute_forecast.core.config import CollectionConfig`
- Line 754: `from compute_forecast.core.logging import get_logger`
- Lines 1098-1102: All pipeline imports need `compute_forecast.pipeline.` prefix
- Line 1104: `from compute_forecast.core.logging import get_logger`
- Line 1105: `from compute_forecast.orchestration.state.state_manager import StateManager`

**Module Comparison Script:**
- Lines 1260-1261: Update paths to include `compute_forecast/`

**Test Commands:**
- Lines 1386-1387: Use `uv run python` with updated imports
- Line 1398: `uv run pytest`

### Issue #138: [Refactoring 5/5] Testing & Documentation

**Test Execution Commands:**
All pytest commands need `uv run`:
- Line 1435: `uv run pytest tests/unit/ -v --cov=compute_forecast`
- Line 1438: `uv run coverage report --fail-under=90`
- Lines 1447-1458: All `uv run pytest`
- Lines 1462-1470: All `uv run pytest`

**Import Fix Examples:**
- Line 1477: `from compute_forecast.pipeline.metadata_collection.models import Paper`
- Line 1482: `@mock.patch('compute_forecast.pipeline.metadata_collection.sources.semantic_scholar.SemanticScholar')`

**Performance Script Imports:**
- Line 1496: `from compute_forecast.orchestration.orchestrators.main_orchestrator import ...`

**Documentation Updates:**
Need to update all paths and imports:
- Lines 1544-1550: Keep structure description but note it's under compute_forecast/
- Line 1565: `from compute_forecast.orchestration.orchestrators.main_orchestrator import ...`
- Lines 1592-1598: Show structure under compute_forecast/
- Lines 1603-1620: All imports need `compute_forecast.` prefix

**Migration Guide Import Table:**
Update all old/new import mappings to include `compute_forecast.` prefix

**Final Verification Script:**
- Lines 1792-1800: Update all directory paths to include `compute_forecast/`
- Lines 1832-1835: Update all import tests with `compute_forecast.` prefix and `uv run`

**Architecture Diagram Script Execution:**
- Use `uv run python scripts/generate_architecture_diagram.py`

## Summary of Changes

### Key Patterns:
1. **Directory creation**: Add `compute_forecast/` prefix to all module paths
2. **File movements**: Add `compute_forecast/` to destination paths
3. **Imports**: Add `compute_forecast.` prefix to all imports
4. **Commands**: `python` → `uv run python`
5. **Package structure**: Everything under `compute_forecast/`, including `pipeline/`

### Import Examples:
- `from pipeline.metadata_collection.models` → `from compute_forecast.pipeline.metadata_collection.models`
- `from core.config` → `from compute_forecast.core.config`
- `from monitoring.server` → `from compute_forecast.monitoring.server`
- `from orchestration.orchestrators` → `from compute_forecast.orchestration.orchestrators`

### Total Modifications:
- Issue #134: ~25 modifications (more path changes)
- Issue #135: ~45 modifications (all paths need compute_forecast/)
- Issue #136: ~60 modifications (all import mappings need update)
- Issue #137: ~30 modifications (all imports need prefix)
- Issue #138: ~70 modifications (extensive documentation updates)

**Total: ~230 modifications across all 5 issues**