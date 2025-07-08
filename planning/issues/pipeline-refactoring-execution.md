# Pipeline Refactoring: Clarify Paper Collection vs PDF Collection

## Overview
Refactor the package structure to eliminate confusion between paper metadata collection and PDF acquisition by creating clear pipeline stages and removing the ambiguous "shared" directory.

## Motivation
Current issues:
- Terminology overlap: "collection" used for both metadata and PDFs
- Duplicate source implementations (e.g., semantic_scholar.py in both data/sources/ and pdf_discovery/sources/)
- Unclear workflow integration between Paper and PDFRecord objects
- Overloaded "shared" directory with mixed concerns
- Ambiguous orchestration with merge conflicts

## Refactoring Goals
1. Clear separation of pipeline stages
2. Eliminate terminology confusion
3. Remove duplicate implementations
4. Create purpose-specific top-level directories
5. Maintain ~80% of existing code unchanged

## Detailed Execution Plan

### Phase 1: Create New Directory Structure

#### 1.1 Create Pipeline Stages
```bash
mkdir -p package/pipeline/{metadata_collection,paper_filtering,pdf_acquisition,content_extraction,analysis}
mkdir -p package/pipeline/metadata_collection/{collectors,sources,processors,analysis}
mkdir -p package/pipeline/paper_filtering/selectors
mkdir -p package/pipeline/pdf_acquisition/{discovery,download,storage}
mkdir -p package/pipeline/content_extraction/{parser,templates,validators,quality}
mkdir -p package/pipeline/analysis/{benchmark,classification,computational,mila,venues}
```

#### 1.2 Create Top-Level Infrastructure
```bash
mkdir -p package/core/{contracts,utils}
mkdir -p package/monitoring/{server,alerting,metrics}
mkdir -p package/orchestration/{core,state,recovery,orchestrators}
mkdir -p package/quality/validators
```

#### 1.3 Create Test Infrastructure
```bash
mkdir -p package/tests/infrastructure/{error_injection,frameworks,mock_data}
```

### Phase 2: Move and Rename Modules

#### 2.1 Metadata Collection (from src/data/)
```bash
# Move sources
mv src/data/sources/* pipeline/metadata_collection/sources/
mv src/data/collectors/* pipeline/metadata_collection/collectors/
mv src/data/processors/* pipeline/metadata_collection/processors/
mv src/data/analysis/* pipeline/metadata_collection/analysis/
mv src/data/models.py pipeline/metadata_collection/models.py

# Create orchestrator
echo "# Metadata Collection Orchestrator" > pipeline/metadata_collection/orchestrator.py
```

#### 2.2 Paper Filtering (from src/filtering/)
```bash
mv src/filtering/* pipeline/paper_filtering/
mv src/selection/* pipeline/paper_filtering/selectors/
echo "# Paper Filtering Orchestrator" > pipeline/paper_filtering/orchestrator.py
```

#### 2.3 PDF Acquisition (consolidate PDF modules)
```bash
# Move discovery
mv src/pdf_discovery/* pipeline/pdf_acquisition/discovery/
# Move download
mv src/pdf_download/* pipeline/pdf_acquisition/download/
# Move storage
mv src/pdf_storage/* pipeline/pdf_acquisition/storage/
echo "# PDF Acquisition Orchestrator" > pipeline/pdf_acquisition/orchestrator.py
```

#### 2.4 Content Extraction (consolidate extraction modules)
```bash
# Move parser
mv src/pdf_parser/* pipeline/content_extraction/parser/
# Move extraction templates
mv src/extraction/* pipeline/content_extraction/templates/
# Move extraction validators from quality
mv src/quality/extraction/* pipeline/content_extraction/validators/
# Move quality control
mv src/quality/{metrics.py,quality_analyzer.py,quality_filter.py,quality_monitoring_integration.py,quality_structures.py,reporter.py,threshold_optimizer.py,adaptive_thresholds.py} pipeline/content_extraction/quality/
echo "# Content Extraction Orchestrator" > pipeline/content_extraction/orchestrator.py
```

#### 2.5 Analysis (from src/analysis/)
```bash
mv src/analysis/* pipeline/analysis/
echo "# Analysis Orchestrator" > pipeline/analysis/orchestrator.py
```

#### 2.6 Core Infrastructure
```bash
mv src/core/* core/
mv src/quality/contracts/* core/contracts/
```

#### 2.7 Monitoring System
```bash
mv src/monitoring/{dashboard_server.py,advanced_dashboard_server.py,advanced_analytics_engine.py,dashboard_metrics.py,integration_utils.py} monitoring/server/
mv src/monitoring/static monitoring/server/
mv src/monitoring/templates monitoring/server/
mv src/monitoring/{alert_system.py,alerting_engine.py,intelligent_alerting_system.py,alert_rules.py,alert_structures.py,alert_suppression.py,notification_channels.py} monitoring/alerting/
mv src/monitoring/{metrics_collector.py,monitoring_components.py} monitoring/metrics/
```

#### 2.8 Orchestration System
```bash
mv src/orchestration/{workflow_coordinator.py,component_validator.py,system_initializer.py,data_processors.py} orchestration/core/
mv src/orchestration/{state_manager.py,state_persistence.py} orchestration/state/
mv src/orchestration/{checkpoint_manager.py,recovery_system.py} orchestration/recovery/
mv src/orchestration/{main_orchestrator.py,venue_collection_orchestrator.py} orchestration/orchestrators/
```

#### 2.9 Quality Validators
```bash
mv src/quality/validators/* quality/validators/
```

#### 2.10 Test Infrastructure
```bash
mv src/testing/error_injection/* tests/infrastructure/error_injection/
mv src/testing/integration/* tests/infrastructure/frameworks/
mv src/testing/mock_data/* tests/infrastructure/mock_data/
```

### Phase 3: Update Imports

#### 3.1 Create Import Update Script
```python
# scripts/update_imports.py
import re
from pathlib import Path

IMPORT_MAPPINGS = {
    # Metadata collection
    r'from src\.data\.sources': 'from pipeline.metadata_collection.sources',
    r'from src\.data\.collectors': 'from pipeline.metadata_collection.collectors',
    r'from src\.data\.processors': 'from pipeline.metadata_collection.processors',
    r'from src\.data\.models': 'from pipeline.metadata_collection.models',

    # Paper filtering
    r'from src\.filtering': 'from pipeline.paper_filtering',
    r'from src\.selection': 'from pipeline.paper_filtering.selectors',

    # PDF acquisition
    r'from src\.pdf_discovery': 'from pipeline.pdf_acquisition.discovery',
    r'from src\.pdf_download': 'from pipeline.pdf_acquisition.download',
    r'from src\.pdf_storage': 'from pipeline.pdf_acquisition.storage',

    # Content extraction
    r'from src\.pdf_parser': 'from pipeline.content_extraction.parser',
    r'from src\.extraction': 'from pipeline.content_extraction.templates',
    r'from src\.quality\.extraction': 'from pipeline.content_extraction.validators',

    # Analysis
    r'from src\.analysis': 'from pipeline.analysis',

    # Core
    r'from src\.core': 'from core',
    r'from src\.quality\.contracts': 'from core.contracts',

    # Monitoring
    r'from src\.monitoring': 'from monitoring',

    # Orchestration
    r'from src\.orchestration': 'from orchestration',

    # Quality
    r'from src\.quality\.validators': 'from quality.validators',

    # Testing
    r'from src\.testing': 'from tests.infrastructure',
}

def update_imports(file_path):
    """Update imports in a single file"""
    content = file_path.read_text()

    for old_import, new_import in IMPORT_MAPPINGS.items():
        content = re.sub(old_import, new_import, content)

    file_path.write_text(content)

def main():
    # Update all Python files
    for py_file in Path('package').rglob('*.py'):
        print(f"Updating imports in {py_file}")
        update_imports(py_file)

    # Update test files
    for py_file in Path('tests').rglob('*.py'):
        print(f"Updating imports in {py_file}")
        update_imports(py_file)

if __name__ == '__main__':
    main()
```

#### 3.2 Run Import Updates
```bash
cd package
python scripts/update_imports.py
```

### Phase 4: Update Configuration Files

#### 4.1 Update pyproject.toml
- Update package discovery paths
- Ensure all new directories are included in package data

#### 4.2 Update Test Configurations
- Update pytest.ini for new test paths
- Update coverage configuration

### Phase 5: Create Orchestrators

#### 5.1 Main Pipeline Orchestrator
```python
# orchestration/orchestrators/main_orchestrator.py
from pipeline.metadata_collection.orchestrator import MetadataCollectionOrchestrator
from pipeline.paper_filtering.orchestrator import PaperFilteringOrchestrator
from pipeline.pdf_acquisition.orchestrator import PDFAcquisitionOrchestrator
from pipeline.content_extraction.orchestrator import ContentExtractionOrchestrator
from pipeline.analysis.orchestrator import AnalysisOrchestrator

class ResearchPipelineOrchestrator:
    """Main orchestrator for the complete research pipeline"""

    def __init__(self):
        self.metadata_orchestrator = MetadataCollectionOrchestrator()
        self.filtering_orchestrator = PaperFilteringOrchestrator()
        self.pdf_orchestrator = PDFAcquisitionOrchestrator()
        self.extraction_orchestrator = ContentExtractionOrchestrator()
        self.analysis_orchestrator = AnalysisOrchestrator()

    def run_full_pipeline(self, config):
        """Execute the complete pipeline"""
        # Stage 1: Collect paper metadata
        papers = self.metadata_orchestrator.collect_papers(config)

        # Stage 2: Filter papers
        filtered_papers = self.filtering_orchestrator.filter_papers(papers)

        # Stage 3: Acquire PDFs for filtered papers
        pdf_records = self.pdf_orchestrator.acquire_pdfs(filtered_papers)

        # Stage 4: Extract data from PDFs
        extracted_data = self.extraction_orchestrator.extract_data(pdf_records)

        # Stage 5: Analyze extracted data
        analysis_results = self.analysis_orchestrator.analyze(extracted_data)

        return analysis_results
```

#### 5.2 Create Stage Orchestrators
Create minimal orchestrator interfaces for each stage that wrap existing functionality.

### Phase 6: Handle Special Cases

#### 6.1 Resolve Merge Conflicts
- Review both versions of VenueCollectionOrchestrator
- Determine correct implementation
- Place in orchestration/orchestrators/

#### 6.2 Consolidate Duplicate Sources
- Compare semantic_scholar.py implementations
- Merge functionality if needed
- Remove duplicates

#### 6.3 Create Unified Data Models
```python
# core/models.py
@dataclass
class PaperRecord:
    """Unified model linking all pipeline stages"""
    metadata: PaperMetadata      # From Stage 1
    filter_results: FilterResults # From Stage 2
    pdf_record: Optional[PDFRecord] = None  # From Stage 3
    extracted_data: Optional[ExtractedData] = None  # From Stage 4
    analysis_results: Optional[AnalysisResults] = None  # From Stage 5
```

### Phase 7: Testing

#### 7.1 Unit Test Updates
- Run all unit tests after import updates
- Fix any broken imports
- Verify functionality unchanged

#### 7.2 Integration Tests
```bash
# Test each pipeline stage independently
pytest tests/integration/test_metadata_collection.py
pytest tests/integration/test_paper_filtering.py
pytest tests/integration/test_pdf_acquisition.py
pytest tests/integration/test_content_extraction.py
pytest tests/integration/test_analysis.py

# Test full pipeline
pytest tests/integration/test_full_pipeline.py
```

#### 7.3 Performance Tests
- Ensure no performance regressions
- Test with large datasets

### Phase 8: Documentation Updates

#### 8.1 Update README
- Document new structure
- Update installation instructions
- Add pipeline flow diagram

#### 8.2 Create Architecture Documentation
```markdown
# Architecture Overview

## Pipeline Stages
1. **Metadata Collection**: Gathers paper metadata from academic APIs
2. **Paper Filtering**: Filters papers based on criteria
3. **PDF Acquisition**: Finds and downloads PDF files
4. **Content Extraction**: Extracts data from PDFs
5. **Analysis**: Analyzes extracted data

## Data Flow
PaperMetadata → FilteredPapers → PDFRecords → ExtractedData → AnalysisResults
```

#### 8.3 Update Developer Guidelines
- Update CLAUDE.md with new structure
- Document import conventions
- Add examples

## Review Guidelines

### Pre-Review Checklist
- [ ] All tests pass
- [ ] No import errors
- [ ] Coverage maintained at >90%
- [ ] Documentation updated
- [ ] No duplicate code remains
- [ ] Merge conflicts resolved

### Code Review Focus Areas

#### 1. Import Correctness
- Verify all imports updated correctly
- Check for circular imports
- Ensure no broken references

#### 2. Functionality Preservation
- Confirm no functionality lost
- Test all major workflows
- Verify API compatibility

#### 3. Structure Validation
- Check directory organization matches plan
- Verify no files left in old locations
- Confirm proper module placement

#### 4. Integration Points
- Test pipeline stage connections
- Verify data flow between stages
- Check orchestrator functionality

#### 5. Performance
- Run performance benchmarks
- Compare with pre-refactoring baseline
- Check for memory leaks

### Review Process

1. **Initial Review**: Structure and organization
2. **Detailed Review**: Code changes and imports
3. **Integration Review**: Pipeline functionality
4. **Final Review**: Documentation and tests

### Rollback Plan
If issues discovered:
1. Keep backup of original structure
2. Use git to revert changes if needed
3. Document any issues for future attempt

## Success Criteria

1. **Clear Separation**: Each pipeline stage clearly defined
2. **No Confusion**: Terminology consistent throughout
3. **Clean Organization**: No overloaded directories
4. **Maintained Quality**: All tests pass, coverage maintained
5. **Improved Developer Experience**: Easier to understand and navigate

## Timeline Estimate
- Phase 1-2: 2-3 hours (structure and moves)
- Phase 3-4: 3-4 hours (imports and config)
- Phase 5-6: 2-3 hours (orchestrators and special cases)
- Phase 7: 2-3 hours (testing)
- Phase 8: 1-2 hours (documentation)

**Total**: 10-15 hours

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Broken imports | Automated script + thorough testing |
| Lost functionality | Comprehensive test suite |
| Merge conflicts | Manual review of conflicts |
| Performance regression | Benchmark before/after |
| Missing files | Checklist verification |

## Post-Refactoring Tasks
1. Update CI/CD pipelines
2. Notify team of structure changes
3. Update any external documentation
4. Monitor for issues in first week
5. Create migration guide for open PRs
