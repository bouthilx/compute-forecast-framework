# Compute Forecast Package Structure After Refactoring

**Date**: 2025-07-06  
**Title**: Complete structure of compute_forecast package after refactoring  
**Purpose**: Document the full tree structure (depth 3) of the refactored package

## Package Structure

```
package/
├── compute_forecast/
│   ├── __init__.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── metadata_collection/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   ├── models.py
│   │   │   ├── collectors/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_collector.py
│   │   │   │   ├── collection_executor.py
│   │   │   │   ├── enhanced_orchestrator.py
│   │   │   │   └── ... (other collectors)
│   │   │   ├── sources/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── arxiv.py
│   │   │   │   ├── crossref.py
│   │   │   │   ├── openai.py
│   │   │   │   ├── semantic_scholar.py
│   │   │   │   └── ... (other sources)
│   │   │   ├── processors/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── data_processor.py
│   │   │   │   ├── deduplication.py
│   │   │   │   └── ... (other processors)
│   │   │   └── analysis/
│   │   │       ├── __init__.py
│   │   │       ├── collection_analyzer.py
│   │   │       └── ... (other analysis)
│   │   ├── paper_filtering/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   ├── authorship_classifier.py
│   │   │   ├── computational_filter.py
│   │   │   ├── venue_relevance_scorer.py
│   │   │   ├── selectors/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── domain_selector.py
│   │   │   │   ├── keyword_selector.py
│   │   │   │   └── ... (other selectors)
│   │   │   └── ... (other filtering modules)
│   │   ├── pdf_acquisition/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   ├── discovery/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── core/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── framework.py
│   │   │   │   │   └── ... (discovery core)
│   │   │   │   ├── sources/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── arxiv_collector.py
│   │   │   │   │   ├── semantic_scholar_collector.py
│   │   │   │   │   └── ... (other collectors)
│   │   │   │   └── strategies/
│   │   │   │       ├── __init__.py
│   │   │   │       └── ... (discovery strategies)
│   │   │   ├── download/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── downloader.py
│   │   │   │   ├── rate_limiter.py
│   │   │   │   └── ... (download utilities)
│   │   │   └── storage/
│   │   │       ├── __init__.py
│   │   │       ├── pdf_manager.py
│   │   │       ├── storage_backend.py
│   │   │       └── ... (storage utilities)
│   │   ├── content_extraction/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   ├── parser/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── core/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── processor.py
│   │   │   │   │   └── ... (parser core)
│   │   │   │   └── ... (parser modules)
│   │   │   ├── templates/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── template_engine.py
│   │   │   │   ├── computational_template.py
│   │   │   │   └── ... (extraction templates)
│   │   │   ├── validators/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── extraction_validator.py
│   │   │   │   └── ... (validators)
│   │   │   └── quality/
│   │   │       ├── __init__.py
│   │   │       ├── metrics.py
│   │   │       ├── quality_analyzer.py
│   │   │       ├── quality_filter.py
│   │   │       ├── quality_monitoring_integration.py
│   │   │       ├── quality_structures.py
│   │   │       ├── reporter.py
│   │   │       ├── threshold_optimizer.py
│   │   │       ├── adaptive_thresholds.py
│   │   │       └── ... (quality modules)
│   │   └── analysis/
│   │       ├── __init__.py
│   │       ├── orchestrator.py
│   │       ├── base.py
│   │       ├── benchmark/
│   │       │   ├── __init__.py
│   │       │   ├── extractor.py
│   │       │   └── ... (benchmark analysis)
│   │       ├── classification/
│   │       │   ├── __init__.py
│   │       │   └── ... (classification)
│   │       ├── computational/
│   │       │   ├── __init__.py
│   │       │   ├── analyzer.py
│   │       │   └── ... (computational analysis)
│   │       ├── mila/
│   │       │   ├── __init__.py
│   │       │   └── ... (Mila-specific analysis)
│   │       └── venues/
│   │           ├── __init__.py
│   │           ├── venue_analyzer.py
│   │           └── ... (venue analysis)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   ├── contracts/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── data_contracts.py
│   │   │   └── ... (other contracts)
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── ... (utility modules)
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── server/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard_server.py
│   │   │   ├── advanced_dashboard_server.py
│   │   │   ├── advanced_analytics_engine.py
│   │   │   ├── dashboard_metrics.py
│   │   │   ├── integration_utils.py
│   │   │   ├── static/
│   │   │   │   ├── css/
│   │   │   │   └── js/
│   │   │   └── templates/
│   │   │       └── ... (HTML templates)
│   │   ├── alerting/
│   │   │   ├── __init__.py
│   │   │   ├── alert_system.py
│   │   │   ├── alerting_engine.py
│   │   │   ├── intelligent_alerting_system.py
│   │   │   ├── alert_rules.py
│   │   │   ├── alert_structures.py
│   │   │   ├── alert_suppression.py
│   │   │   ├── notification_channels.py
│   │   │   └── ... (alerting modules)
│   │   └── metrics/
│   │       ├── __init__.py
│   │       ├── metrics_collector.py
│   │       ├── monitoring_components.py
│   │       └── ... (metrics modules)
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── workflow_coordinator.py
│   │   │   ├── component_validator.py
│   │   │   ├── system_initializer.py
│   │   │   ├── data_processors.py
│   │   │   └── ... (core orchestration)
│   │   ├── state/
│   │   │   ├── __init__.py
│   │   │   ├── state_manager.py
│   │   │   ├── state_persistence.py
│   │   │   └── ... (state management)
│   │   ├── recovery/
│   │   │   ├── __init__.py
│   │   │   ├── checkpoint_manager.py
│   │   │   ├── recovery_system.py
│   │   │   └── ... (recovery modules)
│   │   └── orchestrators/
│   │       ├── __init__.py
│   │       ├── main_orchestrator.py
│   │       ├── venue_collection_orchestrator.py
│   │       └── ... (other orchestrators)
│   └── quality/
│       ├── __init__.py
│       └── validators/
│           ├── __init__.py
│           ├── base.py
│           ├── schema_validator.py
│           └── ... (generic validators)
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   └── ... (unit tests)
│   ├── integration/
│   │   └── ... (integration tests)
│   ├── performance/
│   │   └── ... (performance tests)
│   └── infrastructure/
│       ├── __init__.py
│       ├── error_injection/
│       │   ├── __init__.py
│       │   ├── component_handlers/
│       │   └── scenarios/
│       ├── frameworks/
│       │   ├── __init__.py
│       │   └── test_scenarios/
│       └── mock_data/
│           ├── __init__.py
│           └── ... (mock data)
├── scripts/
│   ├── update_imports.py
│   ├── consolidate_sources.py
│   ├── validate_performance.py
│   ├── generate_architecture_diagram.py
│   └── final_verification.sh
├── docs/
│   └── ... (documentation)
├── pyproject.toml
├── pytest.ini
├── README.md
└── CLAUDE.md
```

## Key Points About This Structure

1. **Everything under compute_forecast**: All Python modules are now under the `compute_forecast` package, making it a proper Python package.

2. **Pipeline as submodule**: The `pipeline` module is preserved but placed under `compute_forecast`, maintaining the clear separation of pipeline stages.

3. **Infrastructure at package level**: Core infrastructure (`core`, `monitoring`, `orchestration`, `quality`) is at the same level as `pipeline` under `compute_forecast`.

4. **Tests remain separate**: Tests stay at the package root level, not inside `compute_forecast`, following Python best practices.

5. **Scripts and docs**: Non-Python files (scripts, docs) remain at the package root level.

## Import Examples After Refactoring

```python
# Pipeline imports
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.paper_filtering.computational_filter import ComputationalFilter
from compute_forecast.pipeline.pdf_acquisition.discovery.core.framework import PDFDiscoveryFramework
from compute_forecast.pipeline.content_extraction.parser.core.processor import PDFProcessor
from compute_forecast.pipeline.analysis.computational.analyzer import ComputationalAnalyzer

# Infrastructure imports
from compute_forecast.core.config import Config
from compute_forecast.core.logging import get_logger
from compute_forecast.monitoring.server.dashboard_server import DashboardServer
from compute_forecast.orchestration.orchestrators.main_orchestrator import ResearchPipelineOrchestrator
from compute_forecast.quality.validators.base import BaseValidator

# Relative imports within a module (e.g., within pipeline.paper_filtering)
from ..metadata_collection.models import Paper  # Works as before
from .computational_filter import ComputationalFilter  # Works as before
```

## Benefits of This Structure

1. **Clear package boundary**: Everything is contained within `compute_forecast`, making it easy to install and distribute.

2. **Logical organization**: Pipeline stages are clearly separated from infrastructure components.

3. **No namespace pollution**: Installing the package only adds `compute_forecast` to the Python namespace.

4. **Easy imports**: All imports start with `compute_forecast.`, making it clear where modules come from.

5. **Maintains separation**: The refactoring goals are preserved - pipeline stages are distinct and the flow is clear.