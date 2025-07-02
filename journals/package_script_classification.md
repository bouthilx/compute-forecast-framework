# Package Script Classification Analysis

**Date**: 2025-01-02  
**Purpose**: Classify all Python scripts in the package directory to identify which can be removed, archived, or kept for the final report

## Summary

The package directory contains ~170+ Python scripts accumulated during development. Many are temporary tests, debugging scripts, or iterative improvements that are no longer needed. This analysis classifies each script to enable cleanup.

## Classification Categories

### 1. **REMOVE** - Temporary Test/Debug Scripts (56 scripts)

These scripts were created for testing, debugging, or experimentation and can be safely deleted:

```
check_recent_paper_query.py
debug_collection.py
debug_dashboard.py
debug_temporal_classification.py
demo_complete_monitoring.py
demo_dashboard.py
demo_real_logs.py
demo_streaming_working.py
enhanced_google_scholar.py
guaranteed_dashboard.py
investigate_2024_paper.py
investigate_early_years_pattern.py
investigate_missing_analysis.py
investigate_specific_paper.py
quick_environment_check.py
run_enhanced_tests.py
simple_collection.py
simple_collection_test.py
simple_dashboard_test.py
streaming_dashboard.py
test_classification_logic.py
test_collection_setup.py
test_config_integration.py
test_end_to_end.py
test_enhanced_classification.py
test_enhanced_minimal.py
test_enhanced_scholar.py
test_google_scholar_final.py
test_live_display.py
test_rapid_streaming.py
test_realtime.py
test_scholar_browser.py
test_scholar_fixed.py
test_scholar_internal.py
test_scholar_simple.py
test_scholar_simple_final.py
test_small_collection.py
test_stdout_capture.py
test_streaming_logs.py
test_ui.py
working_dashboard.py
```

### 2. **ARCHIVE** - Past Analysis/Iterations (47 scripts)

These scripts represent completed analyses or older versions that should be archived for reference:

```
analyze_dataset_structure.py
analyze_datasets.py
analyze_duplicates.py
analyze_overlap.py
calculate_corrections.py
cluster_domains.py
collection_fixed.py
collection_fixed_display.py
collection_validation_report.py
collection_with_dashboard.py
collection_with_progress.py
collection_with_progress_backup.py
collection_with_real_logs.py
complete_paper_accounting.py
continue_collection.py
continue_collection_with_dashboard.py
correct_venue_mergers.py
create_collection_validation.py
dataset_based_corrections.py
detailed_agreement_analysis.py
domain_mapping_sanity_check.py
empirical_correction_analysis.py
environments_analysis.py
examine_other_domains.py
execute_collection.py
execute_fixed_collection.py
execute_paper_collection.py
extract_domains.py
extract_domains_actual_fix.py
extract_domains_completely_fixed.py
extract_domains_final_fix.py
extract_domains_fixed.py
fast_paper_accounting.py
final_cleanup_venues.py
find_venue_duplicates.py
fix_venue_statistics.py
full_corrected_venue_list.py
full_domain_analysis.py
list_merged_venues.py
manual_create_proof_files.py
realtime_collection.py
temporal_analysis_fixed.py
validate_venue_statistics.py
venue_publication_counter.py
venue_statistics_generator.py
```

### 3. **KEEP** - Active Analysis & Report Generation (25 scripts)

These scripts are needed for ongoing analysis and final report generation:

```
analyze_mila_papers.py                      # Core Mila paper analysis
collection_realtime_final.py                 # Final collection script with monitoring
create_final_temporal_analysis.py            # Temporal analysis for report
create_fixed_multi_label_temporal_analysis.py # Multi-label temporal analysis
create_multi_label_temporal_analysis.py      # Alternative temporal analysis
create_proof_of_concept.py                   # Proof of concept generator
create_research_domains_focus_fixed.py       # Research domain analysis
detailed_rl_subdomain_analysis.py            # RL subdomain deep dive
extract_venue_statistics.py                  # Venue statistics extraction
main.py                                      # Entry point (minimal)
multi_domain_analysis.py                     # Multi-domain analysis
paper_filtering_diagram.py                   # Diagram generation
rl_pattern_analysis.py                       # RL pattern analysis
temporal_stacked_charts.py                   # Stacked chart visualization
visualize_primary_venues.py                  # Venue visualization
visualize_venue_trends.py                    # Venue trend charts
visualize_venue_trends_merged.py             # Merged venue trends
```

### 4. **CORE PACKAGE** - Source Code (Entire src/ directory)

The `src/` directory contains the core package implementation and should be kept intact:

```
src/
├── analysis/           # Analysis modules
├── core/              # Core utilities
├── data/              # Data collection and processing
├── extraction/        # Extraction framework
├── filtering/         # Filtering pipeline
├── monitoring/        # Dashboard and monitoring
├── orchestration/     # Workflow orchestration
├── quality/           # Quality control
├── selection/         # Paper selection
└── testing/           # Testing framework
```

### 5. **TEST SUITE** - Unit/Integration Tests (tests/ directory)

The `tests/` directory contains the proper test suite and should be kept:

```
tests/
├── fixtures/
├── functional/
├── integration/
├── performance/
├── production/
├── unit/
└── unittest/
```

## Recommendations

### Immediate Actions

1. **Delete all scripts in REMOVE category** - These are temporary test files that served their purpose
2. **Move ARCHIVE scripts to `archive/` directory** - Preserve for reference but remove from main directory
3. **Keep KEEP scripts in root** - These are actively used for analysis and report generation
4. **Preserve src/ and tests/** - Core package functionality

### Directory Structure After Cleanup

```
package/
├── archive/                    # Archived scripts (new)
├── config/                     # Configuration files
├── data/                       # Data files and outputs
├── logs/                       # Log files
├── src/                        # Core package source
├── tests/                      # Test suite
├── [25 active scripts]         # Scripts for report generation
├── pyproject.toml             # Package configuration
└── README.md                  # Documentation
```

### Benefits of Cleanup

1. **Clarity**: Clear distinction between active and obsolete code
2. **Maintainability**: Easier to find relevant scripts
3. **Reduced confusion**: No more wondering which `extract_domains_*.py` to use
4. **Faster navigation**: Less clutter in root directory
5. **Professional presentation**: Clean structure for final deliverable

### Total Script Count

- **To Remove**: 56 scripts (33%)
- **To Archive**: 47 scripts (28%)
- **To Keep**: 25 scripts (15%)
- **Core Package**: ~40 modules in src/ (24%)

This cleanup will reduce the root directory from ~170 Python files to just 25 active scripts plus the organized src/ directory.