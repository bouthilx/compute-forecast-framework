# Pipeline Refactoring: Complete Structure

**Date**: 2025-07-03
**Title**: Complete Refactored Package Structure
**Purpose**: Document the entire proposed refactoring of the package/ directory to clarify the distinction between paper collection and PDF collection

## Overview

This refactoring reorganizes the codebase to create clear pipeline stages:
1. **Metadata Collection** - Collect paper metadata from APIs
2. **Paper Filtering** - Filter papers based on criteria
3. **PDF Acquisition** - Find and download PDF files
4. **Content Extraction** - Extract data from PDFs
5. **Analysis** - Analyze extracted data

## Major Organizational Changes

### Removed `shared/` Directory
Instead of a catch-all `shared/` directory, the refactoring creates purpose-specific top-level directories:

1. **`core/`** - Only truly cross-cutting infrastructure (config, exceptions, logging, contracts)
2. **`monitoring/`** - Standalone monitoring system with web dashboard and alerting
3. **`orchestration/`** - Pipeline coordination and state management
4. **`quality/`** - Generic quality validators used across stages

### Stage-Specific Organization
- **Selection logic** moved to `pipeline/paper_filtering/selectors/`
- **Extraction validators** moved to `pipeline/content_extraction/validators/`
- **Quality control for extraction** moved to `pipeline/content_extraction/quality/`

### Test Infrastructure
- Testing utilities moved to `tests/infrastructure/` to keep test code together

## Complete Directory Structure

```
package/
├── pyproject.toml
├── pytest.ini
├── uv.lock
├── README.md
├── CLAUDE.md
├── CLAUDE.local.md
├── DASHBOARD_PROGRESS.md
├── FINDINGS.md
├── GOOGLE_SCHOLAR_DEBUG_SUMMARY.md
├── SEMANTIC_SCHOLAR_DEBUG_REPORT.md
├── STRATEGIC_VENUE_COLLECTION_SUMMARY.md
├── WORKER7_HANDOFF.md
│
├── config/
│   ├── keywords.yaml
│   ├── organizations.yaml
│   ├── organizations_enhanced.yaml
│   ├── settings.yaml
│   └── venues.yaml
│
├── data/
│   ├── benchmarks/
│   ├── cache/
│   ├── processed/
│   ├── raw/
│   ├── states/
│   │   └── README.md
│   ├── breakthrough_keywords.json
│   ├── collection_statistics.json
│   ├── collection_validation_report.json
│   ├── domain_progress_0.json
│   ├── enhanced_collection_statistics.json
│   ├── failed_searches.json
│   ├── high_impact_authors.json
│   ├── manual_venue_corrections.json
│   ├── mila_computational_requirements.csv
│   ├── mila_computational_requirements.json
│   ├── mila_selected_papers.json
│   ├── mila_selection_summary.json
│   ├── mila_venue_statistics.json
│   ├── progress_0_2020.json
│   ├── progress_0_2022.json
│   ├── progress_0_2024.json
│   ├── raw_collected_papers.json
│   ├── simple_collected_papers.json
│   ├── simple_collection_stats.json
│   └── strategic_venue_collection.json
│
├── logs/
│   ├── collection_execution.log
│   ├── fixed_collection.log
│   └── proof_of_concept.log
│
├── reports/
│   └── mila_extraction_summary.md
│
├── scripts/
│   ├── analyze_mila_papers_detailed.py
│   ├── check_paper_abstracts.py
│   ├── create_drive_folder.py
│   ├── extract_mila_computational_requirements.py
│   ├── migrate_pdfs_to_drive.py
│   ├── select_mila_papers.py
│   ├── setup_google_drive.py
│   └── test_google_drive_config.py
│
├── examples/
│   ├── computational_filtering_usage.py
│   └── quality_system_demo.py
│
├── pipeline/
│   ├── __init__.py
│   │
│   ├── metadata_collection/     # Stage 1: Collect paper metadata from APIs
│   │   ├── __init__.py
│   │   ├── collectors/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── api_health_monitor.py
│   │   │   ├── api_integration_layer.py
│   │   │   ├── checkpoint_manager.py
│   │   │   ├── citation_collector.py
│   │   │   ├── collection_executor.py
│   │   │   ├── domain_collector.py
│   │   │   ├── enhanced_orchestrator.py
│   │   │   ├── enhanced_orchestrator_streaming.py
│   │   │   ├── interruption_recovery.py
│   │   │   ├── rate_limit_manager.py
│   │   │   ├── recovery_engine.py
│   │   │   ├── state_management.py
│   │   │   ├── state_persistence.py
│   │   │   └── state_structures.py
│   │   ├── sources/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── enhanced_crossref.py
│   │   │   ├── enhanced_openalex.py
│   │   │   ├── enhanced_semantic_scholar.py
│   │   │   ├── google_scholar.py
│   │   │   ├── openalex.py
│   │   │   └── semantic_scholar.py
│   │   ├── processors/
│   │   │   ├── __init__.py
│   │   │   ├── adaptive_threshold_calculator.py
│   │   │   ├── breakthrough_detector.py
│   │   │   ├── citation_analyzer.py
│   │   │   ├── citation_config.py
│   │   │   ├── citation_statistics.py
│   │   │   ├── fuzzy_venue_matcher.py
│   │   │   ├── venue_mapping_loader.py
│   │   │   └── venue_normalizer.py
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   └── statistical_analyzer.py
│   │   ├── models.py
│   │   └── orchestrator.py
│   │
│   ├── paper_filtering/         # Stage 2: Filter papers based on criteria
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── authorship_classifier.py
│   │   ├── computational_analyzer.py
│   │   ├── computational_filter.py
│   │   ├── pipeline_integration.py
│   │   ├── venue_relevance_scorer.py
│   │   ├── selectors/          # Selection criteria
│   │   │   └── __init__.py
│   │   └── orchestrator.py
│   │
│   ├── pdf_acquisition/         # Stage 3: Find and download PDFs
│   │   ├── __init__.py
│   │   ├── discovery/
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── collectors.py
│   │   │   │   ├── framework.py
│   │   │   │   └── models.py
│   │   │   ├── sources/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── aaai_collector.py
│   │   │   │   ├── acl_anthology_collector.py
│   │   │   │   ├── arxiv_collector.py
│   │   │   │   ├── core_collector.py
│   │   │   │   ├── cvf_collector.py
│   │   │   │   ├── doi_resolver_collector.py
│   │   │   │   ├── hal_collector.py
│   │   │   │   ├── ieee_xplore_collector.py
│   │   │   │   ├── jmlr_collector.py
│   │   │   │   ├── nature_collector.py
│   │   │   │   ├── openalex_collector.py
│   │   │   │   ├── openreview_collector.py
│   │   │   │   ├── pmlr_collector.py
│   │   │   │   ├── pubmed_central_collector.py
│   │   │   │   ├── semantic_scholar_collector.py
│   │   │   │   ├── unpaywall_client.py
│   │   │   │   ├── venue_mappings.py
│   │   │   │   └── data/
│   │   │   │       └── pmlr_volumes.json
│   │   │   ├── deduplication/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine.py
│   │   │   │   ├── matchers.py
│   │   │   │   └── version_manager.py
│   │   │   └── utils/
│   │   │       ├── __init__.py
│   │   │       ├── exceptions.py
│   │   │       └── rate_limiter.py
│   │   ├── download/
│   │   │   ├── __init__.py
│   │   │   ├── cache_manager.py
│   │   │   └── downloader.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── discovery_integration.py
│   │   │   ├── google_drive_store.py
│   │   │   └── pdf_manager.py
│   │   └── orchestrator.py
│   │
│   ├── content_extraction/      # Stage 4: Extract data from PDFs
│   │   ├── __init__.py
│   │   ├── parser/
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_extractor.py
│   │   │   │   ├── cost_tracker.py
│   │   │   │   ├── processor.py
│   │   │   │   └── validation.py
│   │   ├── templates/
│   │   │   ├── __init__.py
│   │   │   ├── coverage_reporter.py
│   │   │   ├── default_templates.py
│   │   │   ├── normalization_engine.py
│   │   │   ├── suppression_templates.py
│   │   │   ├── template_engine.py
│   │   │   └── validation_rules.py
│   │   ├── validators/          # Extraction-specific validation
│   │   │   ├── __init__.py
│   │   │   ├── consistency_checker.py
│   │   │   ├── cross_validation.py
│   │   │   ├── extraction_validator.py
│   │   │   ├── integrated_validator.py
│   │   │   ├── outlier_detection.py
│   │   │   └── validation_rules.yaml
│   │   ├── quality/             # Quality control for extraction
│   │   │   ├── __init__.py
│   │   │   ├── metrics.py
│   │   │   ├── quality_analyzer.py
│   │   │   ├── quality_filter.py
│   │   │   ├── quality_monitoring_integration.py
│   │   │   ├── quality_structures.py
│   │   │   ├── reporter.py
│   │   │   ├── threshold_optimizer.py
│   │   │   └── adaptive_thresholds.py
│   │   └── orchestrator.py
│   │
│   └── analysis/                # Stage 5: Analyze extracted data
│       ├── __init__.py
│       ├── base.py
│       ├── benchmark/
│       │   ├── __init__.py
│       │   ├── domain_extractors.py
│       │   ├── export.py
│       │   ├── extractor.py
│       │   ├── models.py
│       │   ├── quality_assurance.py
│       │   └── workflow_manager.py
│       ├── classification/
│       │   ├── __init__.py
│       │   ├── affiliation_parser.py
│       │   ├── enhanced_affiliation_parser.py
│       │   ├── enhanced_organizations.py
│       │   ├── enhanced_validator.py
│       │   ├── organizations.py
│       │   ├── paper_classifier.py
│       │   └── validator.py
│       ├── computational/
│       │   ├── __init__.py
│       │   ├── analyzer.py
│       │   ├── experimental_detector.py
│       │   ├── extraction_forms.py
│       │   ├── extraction_patterns.py
│       │   ├── extraction_protocol.py
│       │   ├── extraction_workflow.py
│       │   ├── filter.py
│       │   ├── filter_tests.py
│       │   ├── keywords.py
│       │   ├── pattern_tests.py
│       │   └── quality_control.py
│       ├── mila/
│       │   ├── __init__.py
│       │   └── paper_selector.py
│       ├── venues/
│       │   ├── __init__.py
│       │   ├── collection_strategy.py
│       │   ├── venue_analyzer.py
│       │   ├── venue_database.py
│       │   ├── venue_scoring.py
│       │   └── venue_strategist.py
│       └── orchestrator.py
│
├── core/                        # True infrastructure only
│   ├── __init__.py
│   ├── config.py
│   ├── exceptions.py
│   ├── logging.py
│   ├── contracts/              # Data contracts used everywhere
│   │   ├── __init__.py
│   │   ├── analysis_contracts.py
│   │   ├── base_contracts.py
│   │   ├── contract_tests.py
│   │   └── pipeline_validator.py
│   └── utils/                  # Generic utilities
│       └── __init__.py
│
├── monitoring/                  # Standalone monitoring system
│   ├── __init__.py
│   ├── server/                 # Web dashboard
│   │   ├── __init__.py
│   │   ├── dashboard_server.py
│   │   ├── advanced_dashboard_server.py
│   │   ├── advanced_analytics_engine.py
│   │   ├── dashboard_metrics.py
│   │   ├── integration_utils.py
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   └── dashboard.css
│   │   │   └── js/
│   │   │       └── dashboard.js
│   │   └── templates/
│   │       ├── analytics_dashboard.html
│   │       └── dashboard.html
│   ├── alerting/              # Notifications
│   │   ├── __init__.py
│   │   ├── alert_system.py
│   │   ├── alerting_engine.py
│   │   ├── intelligent_alerting_system.py
│   │   ├── alert_rules.py
│   │   ├── alert_structures.py
│   │   ├── alert_suppression.py
│   │   └── notification_channels.py
│   └── metrics/               # Metric collection
│       ├── __init__.py
│       ├── metrics_collector.py
│       └── monitoring_components.py
│
├── orchestration/              # Pipeline coordination
│   ├── __init__.py
│   ├── core/                  # Base orchestration classes
│   │   ├── __init__.py
│   │   ├── workflow_coordinator.py
│   │   ├── component_validator.py
│   │   ├── system_initializer.py
│   │   └── data_processors.py
│   ├── state/                 # State management
│   │   ├── __init__.py
│   │   ├── state_manager.py
│   │   └── state_persistence.py
│   ├── recovery/              # Checkpoint & recovery
│   │   ├── __init__.py
│   │   ├── checkpoint_manager.py
│   │   └── recovery_system.py
│   └── orchestrators/         # Specific orchestrators
│       ├── __init__.py
│       ├── main_orchestrator.py
│       └── venue_collection_orchestrator.py
│
├── quality/                    # Generic quality validation
│   ├── __init__.py
│   └── validators/
│       ├── __init__.py
│       ├── base.py
│       ├── citation_validator.py
│       └── sanity_checker.py
│
├── main.py
├── analyze_mila_papers.py
├── analyze_paperoni_dataset.py
├── collection_realtime_final.py
├── create_final_temporal_analysis.py
├── create_fixed_multi_label_temporal_analysis.py
├── create_multi_label_temporal_analysis.py
├── create_proof_of_concept.py
├── create_research_domains_focus_fixed.py
├── detailed_rl_subdomain_analysis.py
├── extract_venue_statistics.py
├── multi_domain_analysis.py
├── paper_filtering_diagram.py
├── rl_pattern_analysis.py
├── temporal_stacked_charts.py
├── test_google_scholar_init.py
├── visualize_primary_venues.py
├── visualize_venue_trends.py
├── visualize_venue_trends_merged.py
│
├── tests/
│   ├── fixtures/
│   ├── functional/
│   │   └── test_extraction_integration.py
│   ├── infrastructure/          # Testing utilities
│   │   ├── __init__.py
│   │   ├── error_injection/
│   │   │   ├── __init__.py
│   │   │   ├── component_handlers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analyzer_errors.py
│   │   │   │   ├── collector_errors.py
│   │   │   │   └── reporter_errors.py
│   │   │   ├── injection_framework.py
│   │   │   ├── recovery_validator.py
│   │   │   └── scenarios/
│   │   │       ├── __init__.py
│   │   │       ├── api_failures.py
│   │   │       ├── data_corruption.py
│   │   │       └── resource_exhaustion.py
│   │   ├── frameworks/
│   │   │   ├── __init__.py
│   │   │   ├── performance_monitor.py
│   │   │   ├── phase_validators.py
│   │   │   ├── pipeline_test_framework.py
│   │   │   └── test_scenarios/
│   │   │       ├── __init__.py
│   │   │       ├── error_recovery.py
│   │   │       ├── large_scale.py
│   │   │       ├── normal_flow.py
│   │   │       ├── performance_regression.py
│   │   │       └── test_runner.py
│   │   └── mock_data/
│   │       ├── README.md
│   │       ├── __init__.py
│   │       ├── configs.py
│   │       ├── examples.py
│   │       └── generators.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── data/
│   │   │   └── processors/
│   │   │       └── test_citation_analysis_integration.py
│   │   ├── pdf_discovery/
│   │   │   ├── test_aaai_integration.py
│   │   │   ├── test_acl_anthology_integration.py
│   │   │   ├── test_core_hal_integration.py
│   │   │   ├── test_cvf_integration.py
│   │   │   ├── test_ieee_integration.py
│   │   │   ├── test_jmlr_integration.py
│   │   │   ├── test_nature_integration.py
│   │   │   ├── test_openalex_integration.py
│   │   │   ├── test_pdf_discovery_integration.py
│   │   │   ├── test_pmlr_integration.py
│   │   │   ├── test_pubmed_central_integration.py
│   │   │   └── test_semantic_scholar_integration.py
│   │   ├── pdf_download/
│   │   │   └── test_pdf_download_integration.py
│   │   ├── test_all_sources_integration.py
│   │   ├── test_analysis_pipeline_integration.py
│   │   ├── test_component_integration.py
│   │   ├── test_contract_validation_integration.py
│   │   ├── test_dashboard_alerting_integration.py
│   │   ├── test_error_injection_demo.py
│   │   ├── test_error_injection_integration.py
│   │   ├── test_full_collection_pipeline.py
│   │   ├── test_interruption_recovery.py
│   │   ├── test_issue5_compliance.py
│   │   ├── test_orchestrator_integration.py
│   │   └── test_orchestrator_performance.py
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── data/
│   │   │   └── processors/
│   │   │       └── test_citation_analysis_performance.py
│   │   ├── test_collection_performance.py
│   │   └── test_scalability.py
│   ├── production/
│   │   ├── __init__.py
│   │   └── test_production_readiness.py
│   ├── unit/
│   │   ├── error_injection/
│   │   │   ├── test_component_handlers.py
│   │   │   ├── test_component_handlers_simple.py
│   │   │   ├── test_injection_framework.py
│   │   │   ├── test_recovery_validator.py
│   │   │   ├── test_recovery_validator_fixed.py
│   │   │   ├── test_recovery_validator_simple.py
│   │   │   └── test_scenarios.py
│   │   ├── pdf_discovery/
│   │   │   ├── deduplication/
│   │   │   │   ├── test_engine.py
│   │   │   │   ├── test_matchers.py
│   │   │   │   ├── test_performance.py
│   │   │   │   └── test_version_manager.py
│   │   │   ├── sources/
│   │   │   │   ├── test_aaai_collector.py
│   │   │   │   ├── test_acl_anthology_collector.py
│   │   │   │   ├── test_core_collector.py
│   │   │   │   ├── test_hal_collector.py
│   │   │   │   ├── test_jmlr_collector.py
│   │   │   │   ├── test_openalex_collector.py
│   │   │   │   ├── test_pmlr_collector.py
│   │   │   │   └── test_pubmed_central_collector.py
│   │   │   ├── test_arxiv_collector.py
│   │   │   ├── test_collectors.py
│   │   │   ├── test_collectors_additional.py
│   │   │   ├── test_crossref_doi_lookup.py
│   │   │   ├── test_cvf_collector.py
│   │   │   ├── test_doi_resolver_collector.py
│   │   │   ├── test_doi_resolver_integration.py
│   │   │   ├── test_exceptions.py
│   │   │   ├── test_framework.py
│   │   │   ├── test_framework_integration.py
│   │   │   ├── test_framework_simple.py
│   │   │   ├── test_ieee_xplore_collector.py
│   │   │   ├── test_models.py
│   │   │   ├── test_models_additional.py
│   │   │   ├── test_nature_collector.py
│   │   │   ├── test_openreview_collector.py
│   │   │   ├── test_rate_limiter.py
│   │   │   ├── test_semantic_scholar_collector.py
│   │   │   ├── test_semantic_scholar_improvements.py
│   │   │   └── test_unpaywall_client.py
│   │   ├── pdf_download/
│   │   │   ├── test_cache_manager.py
│   │   │   └── test_downloader.py
│   │   ├── pdf_parser/
│   │   │   ├── __init__.py
│   │   │   ├── test_base_extractor.py
│   │   │   ├── test_cost_tracker.py
│   │   │   ├── test_integration.py
│   │   │   ├── test_processor.py
│   │   │   └── test_validation.py
│   │   ├── pdf_storage/
│   │   │   ├── __init__.py
│   │   │   ├── test_google_drive_store.py
│   │   │   └── test_pdf_manager.py
│   │   ├── test_adaptive_quality_thresholds.py
│   │   ├── test_checkpoint_manager.py
│   │   ├── test_computational_filtering.py
│   │   ├── test_enhanced_orchestrator.py
│   │   ├── test_enhanced_orchestrator_env.py
│   │   ├── test_google_scholar.py
│   │   ├── test_intelligent_alerting_system.py
│   │   ├── test_interruption_recovery.py
│   │   ├── test_interruption_recovery_system.py
│   │   ├── test_mila_paper_selector.py
│   │   ├── test_state_management.py
│   │   ├── test_state_persistence.py
│   │   ├── test_state_structures.py
│   │   ├── test_suppression_templates.py
│   │   └── test_venue_collection_orchestrator.py
│   └── unittest/
│       ├── analysis/
│       │   └── benchmark/
│       │       ├── __init__.py
│       │       ├── test_domain_extractors.py
│       │       ├── test_extractor.py
│       │       ├── test_models.py
│       │       ├── test_quality_assurance.py
│       │       └── test_workflow_manager.py
│       ├── data/
│       │   └── processors/
│       │       ├── test_adaptive_threshold_calculator.py
│       │       ├── test_breakthrough_detector.py
│       │       ├── test_citation_analyzer.py
│       │       └── test_citation_analyzer_edge_cases.py
│       ├── extraction/
│       │   ├── test_coverage_reporter.py
│       │   ├── test_default_templates.py
│       │   ├── test_extraction_engine.py
│       │   ├── test_integration.py
│       │   ├── test_normalization_engine.py
│       │   ├── test_template_engine.py
│       │   └── test_validation_rules.py
│       ├── quality/
│       │   ├── contracts/
│       │   │   ├── __init__.py
│       │   │   ├── test_analysis_contracts.py
│       │   │   ├── test_base_contracts.py
│       │   │   └── test_pipeline_validator.py
│       │   └── extraction/
│       │       ├── __init__.py
│       │       ├── test_consistency_checker.py
│       │       ├── test_cross_validation.py
│       │       ├── test_extraction_validator.py
│       │       ├── test_helpers.py
│       │       ├── test_integrated_validator.py
│       │       └── test_outlier_detection.py
│       ├── test_alert_suppression.py
│       ├── test_alert_system.py
│       ├── test_api_health_monitor.py
│       ├── test_dashboard_metrics.py
│       ├── test_enhanced_affiliation_parser.py
│       ├── test_enhanced_api_clients.py
│       ├── test_enhanced_organizations.py
│       ├── test_extraction_forms.py
│       ├── test_extraction_patterns.py
│       ├── test_extraction_protocol.py
│       ├── test_extraction_workflow.py
│       ├── test_integration_workflow.py
│       ├── test_metrics_collector.py
│       ├── test_quality_control.py
│       ├── test_rate_limit_manager.py
│       ├── test_venue_collection_engine.py
│       ├── test_venue_normalizer.py
│       └── testing/
│           ├── __init__.py
│           ├── integration/
│           │   ├── test_performance_monitor.py
│           │   ├── test_phase_validators.py
│           │   └── test_pipeline_test_framework.py
│           └── mock_data/
│               ├── __init__.py
│               ├── test_configs.py
│               └── test_generators.py
│
├── archive/
│   ├── analyze_dataset_structure.py
│   ├── analyze_datasets.py
│   ├── analyze_duplicates.py
│   ├── analyze_overlap.py
│   ├── calculate_corrections.py
│   ├── cluster_domains.py
│   ├── collection_fixed.py
│   ├── collection_fixed_display.py
│   ├── collection_validation_report.py
│   ├── collection_with_dashboard.py
│   ├── collection_with_progress.py
│   ├── collection_with_progress_backup.py
│   ├── collection_with_real_logs.py
│   ├── complete_paper_accounting.py
│   ├── continue_collection.py
│   ├── continue_collection_with_dashboard.py
│   ├── correct_venue_mergers.py
│   ├── create_collection_validation.py
│   ├── dataset_based_corrections.py
│   ├── detailed_agreement_analysis.py
│   ├── domain_mapping_sanity_check.py
│   ├── empirical_correction_analysis.py
│   ├── environments_analysis.py
│   ├── examine_other_domains.py
│   ├── execute_collection.py
│   ├── execute_fixed_collection.py
│   ├── execute_paper_collection.py
│   ├── extract_domains.py
│   ├── extract_domains_actual_fix.py
│   ├── extract_domains_completely_fixed.py
│   ├── extract_domains_final_fix.py
│   ├── extract_domains_fixed.py
│   ├── fast_paper_accounting.py
│   ├── final_cleanup_venues.py
│   ├── find_venue_duplicates.py
│   ├── fix_venue_statistics.py
│   ├── full_corrected_venue_list.py
│   ├── full_domain_analysis.py
│   ├── list_merged_venues.py
│   ├── manual_create_proof_files.py
│   ├── realtime_collection.py
│   ├── temporal_analysis_fixed.py
│   ├── validate_venue_statistics.py
│   └── venue_publication_counter.py
│
├── journals/
│   ├── 2025-07-01_dependency_analysis_25_open_issues.md
│   ├── 2025-07-01_final_issue_prioritization.md
│   ├── 2025-07-01_issue42_pipeline_testing_analysis.md
│   ├── 2025-07-01_issue_28_extraction_template_analysis.md
│   ├── 2025-07-01_issue_30_completion.md
│   ├── 2025-07-01_issue_30_planning.md
│   ├── 2025-07-01_issue_30_revised_planning.md
│   ├── 2025-07-01_issue_42_analysis.md
│   ├── 2025-07-01_issue_46_readiness_assessment.md
│   ├── 2025-07-01_issue_readiness_assessment.md
│   ├── 2025-07-01_open_issues_prioritization.md
│   ├── 2025-07-02_issue_79_arxiv_collector_implementation.md
│   ├── 2025-07-02_issue_89_pdf_downloader_planning.md
│   ├── 2025-07-02_issue_93_jmlr_collector_completion.md
│   ├── 2025-07-02_issue_93_jmlr_collector_planning.md
│   ├── adaptive_threshold_engine_analysis.md
│   ├── analysis_log.md
│   ├── cleanup_comparison_report.md
│   ├── cvf_implementation_complete.md
│   ├── cvf_scraper_planning.md
│   ├── error_propagation_recovery_testing.md
│   ├── extraction_validation_architecture_design.md
│   ├── implementation_order_analysis.md
│   ├── infrastructure_analysis_closed_issues.md
│   ├── issue-29-analysis.md
│   ├── issue-29-execution-analysis.md
│   ├── issue-tagging-report.md
│   ├── issue_29_analysis.md
│   ├── issue_44_analysis.md
│   ├── issue_44_organization_classification.md
│   ├── issue_46_context_analysis.md
│   ├── issue_46_planning.md
│   ├── issue_74_comprehensive_pdf_acquisition_plan.md
│   ├── issue_74_comprehensive_pdf_acquisition_strategy.md
│   ├── issue_74_pdf_acquisition_implementation_plan.md
│   ├── issue_74_pdf_acquisition_summary.md
│   ├── issue_74_pdf_extraction_analysis.md
│   ├── issue_74_pdf_infrastructure_plan.md
│   ├── issue_74_summary.md
│   ├── issue_77_pdf_discovery_framework_implementation.md
│   ├── issue_80_openreview_integration.md
│   ├── issue_86_openalex_pdf_implementation.md
│   ├── issue_86_openalex_pdf_implementation_plan.md
│   ├── issue_88_aaai_collector_implementation.md
│   ├── issue_115_google_drive_storage.md
│   ├── issue_tagging_analysis.md
│   ├── package_script_classification.md
│   ├── pdf_discovery_github_issues.md
│   ├── pdf_discovery_implementation_breakdown.md
│   ├── pdf_download_parsing_simplified_plan.md
│   ├── pdf_handling_limitations_analysis.md
│   ├── pdf_infrastructure_comprehensive_coverage.md
│   ├── pdf_infrastructure_comprehensive_plan.md
│   ├── pdf_infrastructure_consolidated_plan.md
│   ├── pdf_infrastructure_focused_sources.md
│   ├── pdf_infrastructure_issue_creation.md
│   ├── pdf_parsing_final_implementation.md
│   ├── pdf_parsing_optimized_implementation.md
│   ├── pdf_storage_design.md
│   ├── pr_55_review.md
│   ├── pr_68_benchmark_extraction_analysis.md
│   └── url_field_analysis.md
│
├── debug_plans/
│   ├── worker2_google_scholar_debug.md
│   └── worker3_semantic_scholar_debug.md
│
├── status/
│   ├── worker0-overall.json
│   ├── worker0-structure.json
│   ├── worker1-citation-collector.json
│   ├── worker1-google-scholar.json
│   ├── worker1-openalex.json
│   ├── worker1-overall.json
│   ├── worker1-semantic-scholar.json
│   ├── worker2-classification.json
│   ├── worker2-google-scholar-debug.json
│   ├── worker2-organizations.json
│   ├── worker2-overall.json
│   ├── worker2-parsing.json
│   ├── worker2-validation.json
│   ├── worker3-mila-venues.json
│   ├── worker3-overall.json
│   ├── worker3-scoring.json
│   ├── worker3-strategy.json
│   ├── worker3-venue-database.json
│   ├── worker4-analyzer.json
│   ├── worker4-bug-fixes.json
│   ├── worker4-experimental.json
│   ├── worker4-filter-bug-fix.json
│   ├── worker4-filtering.json
│   ├── worker4-keywords.json
│   ├── worker4-overall.json
│   ├── worker5-citation-validation.json
│   ├── worker5-overall.json
│   ├── worker5-quality-metrics.json
│   ├── worker5-reporting.json
│   ├── worker5-sanity-checks.json
│   ├── worker6-final-assessment.json
│   ├── worker6-final-completion.json
│   ├── worker6-overall.json
│   ├── worker6-production-ready.json
│   ├── worker6-setup.json
│   └── worker6-validation.json
│
├── milestones/
│   ├── milestone-00-integration-testing.md
│   ├── milestone-01-author-affiliation-filter.md
│   ├── milestone-01-detailed-implementation.md
│   ├── milestone-01-implementation-code.md
│   ├── milestone-01-implementation-plan.md
│   ├── milestone-01-next-steps.md
│   ├── milestone-01-paper-selection.md
│   ├── milestone-01-sanity-check-lists.md
│   ├── milestone-02-extraction-pipeline.md
│   ├── milestone-03-benchmark-data.md
│   ├── milestone-04-mila-data.md
│   ├── milestone-05-temporal-trends.md
│   ├── milestone-06-gap-analysis.md
│   ├── milestone-07-trajectory-comparison.md
│   ├── milestone-08-research-group-mapping.md
│   ├── milestone-09-projections.md
│   ├── milestone-10-validation.md
│   ├── milestone-11-strategic-narrative.md
│   ├── milestone-12-data-visualization.md
│   ├── milestone-13-draft-report.md
│   ├── milestone-14-final-deliverable.md
│   └── milestone1/
│       ├── orchestration.md
│       ├── worker0-architecture-setup.md
│       ├── worker1-citation-infrastructure.md
│       ├── worker2-organization-classification.md
│       ├── worker3-venue-analysis.md
│       ├── worker4-computational-content.md
│       ├── worker5-quality-control.md
│       ├── worker6-paper-collection.md
│       └── worker7-final-selection.md
│
└── JSON and analysis files:
    ├── all_domains_actual_fix.json
    ├── all_domains_completely_fixed.json
    ├── all_domains_final_fix.json
    ├── all_domains_fixed.json
    ├── all_domains_full.json
    ├── all_research_domains_temporal_analysis_FIXED.png
    ├── complete_corrected_venue_list.json
    ├── complete_merged_venue_list.json
    ├── corrected_venue_mergers.json
    ├── correction_factors.json
    ├── critical_agreement_analysis.json
    ├── dataset_based_corrections_results.json
    ├── dataset_corrections_comparison.png
    ├── dataset_domain_comparison.json
    ├── detailed_rl_subdomain_analysis.json
    ├── domain_clusters.json
    ├── domain_extraction_raw.csv
    ├── domain_extraction_raw.json
    ├── domain_mapping_sanity_check_results.json
    ├── empirical_correction_analysis.json
    ├── final_corrected_domain_stats.json
    ├── main_research_domains_temporal_analysis_FIXED.png
    ├── mila_domain_taxonomy.json
    ├── overlap_analysis.json
    ├── paper_classification_temporal_analysis.png
    ├── paper_classification_temporal_analysis_COMPLETE.png
    ├── paper_classification_temporal_analysis_FIXED.png
    ├── paper_classification_temporal_analysis_MULTI_LABEL.png
    ├── research_domains_temporal_analysis.png
    ├── research_domains_temporal_analysis_COMPLETE.png
    ├── research_domains_temporal_analysis_FIXED.png
    ├── research_domains_temporal_analysis_MULTI_LABEL.png
    ├── research_papers_comparison_original_vs_fixed.png
    ├── rl_pattern_analysis.json
    ├── temporal_analysis_data.json
    ├── temporal_analysis_data_COMPLETE.json
    ├── temporal_analysis_data_FIXED.json
    ├── temporal_analysis_data_FIXED_MULTI_LABEL.json
    ├── temporal_analysis_data_MULTI_LABEL.json
    ├── venue_duplicate_mapping.json
    ├── venue_trends_heatmap.png
    ├── venue_trends_line_plot.png
    ├── venue_trends_merged_heatmap.png
    ├── venue_trends_merged_line_plot.png
    ├── venue_statistics_generator.py
    └── worker6_venue_mapping.json
```

## Key Benefits of This Refactoring

1. **Clear Pipeline Stages**: The five stages are explicitly separated and named according to their function
2. **Eliminates Confusion**: "Paper collection" becomes "metadata collection", "PDF collection" becomes "PDF acquisition"
3. **Consolidated PDF Handling**: All PDF-related operations (discovery, download, storage) are in one logical unit
4. **Better Infrastructure Organization**:
   - Core infrastructure in `core/` (only truly generic utilities)
   - Monitoring elevated to top-level system
   - Orchestration as standalone coordination system
   - Quality validation split between generic and stage-specific
5. **Minimal Disruption**: ~80% of the codebase remains untouched (config, data, tests, utilities)
6. **Better Organization**: Each pipeline stage has its own orchestrator for independent operation
7. **Explicit Data Flow**: The pipeline stages clearly show the flow from metadata → filtering → PDFs → extraction → analysis
8. **No Overloaded "Shared" Directory**: Each component has a clear home based on its purpose

## Migration Path

1. **Phase 1**: Create new directory structure
2. **Phase 2**: Move modules to new locations with updated imports
3. **Phase 3**: Create stage orchestrators and main pipeline orchestrator
4. **Phase 4**: Update tests to match new structure
5. **Phase 5**: Integration testing of the complete pipeline

This refactoring maintains all existing functionality while providing much clearer organization and separation of concerns.
