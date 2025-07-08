# Test Failures Organized by Module

## Unit Test Failures

### 1. Data Module (`tests/unit/data/`)
**Failed Tests: 6**
- `test_venue_collection_engine.py`:
  - `test_api_failure_recovery` - No successful venues when API fails
  - `test_four_to_six_hour_collection_scenario` - API calls estimation incorrect
- `test_venue_normalizer.py`:
  - `test_normalize_venue_name` - Wrong normalization result
  - `test_find_best_match` - Match type incorrect
  - `test_batch_find_matches` - No match found for ICML

### 2. Error Injection Module (`tests/unit/error_injection/`)
**Failed Tests: 9**
- `test_recovery_validator.py`:
  - `test_initialization` - recovery_engine is None
  - `test_validate_recovery_successful` - data loss percentage mismatch
  - `test_validate_recovery_with_data_loss` - data loss percentage mismatch
  - `test_validate_recovery_failed` - data loss percentage mismatch
  - `test_measure_data_integrity` - integrity score mismatch
  - `test_verify_graceful_degradation_healthy` - AttributeError on NoneType
  - `test_verify_graceful_degradation_degraded` - AttributeError on NoneType
  - `test_verify_graceful_degradation_failed` - AttributeError on NoneType
  - `test_recommendations_generation` - No recommendations generated

### 3. Extraction Module (`tests/unit/extraction/`)
**Failed Tests: 4**
- `test_extraction_protocol.py`:
  - `test_phase1_preparation` - time_spent_minutes is 0
  - `test_run_full_protocol` - time_spent_minutes is 0
  - `test_calculate_completeness_score` - score mismatch
  - `test_missing_analyzer_attributes` - Mock object returned instead of float

### 4. Orchestration Module (`tests/unit/orchestration/`)
**Failed/Error Tests: 28**
- `test_enhanced_orchestrator.py`:
  - `test_initialization_default` - GoogleScholarClient call mismatch
  - `test_initialization_with_api_keys` - GoogleScholarClient call mismatch
- `test_enhanced_orchestrator_env.py`:
  - `test_env_vars_override_by_init_params` - GoogleScholarClient not found
  - `test_api_client_initialization_with_env_vars` - GoogleScholarClient not found
- `test_rate_limit_manager.py`:
  - `test_exponential_backoff_for_degraded_apis` - No wait times
  - `test_realistic_collection_scenario` - API calls exceed limit
- `test_state_management.py`:
  - `test_state_manager_initialization` - persistence is None
  - `test_create_session_basic` - session file not created
  - `test_resume_session` - session not found
  - `test_get_session_status` - returns None
  - `test_cleanup_old_sessions` - AttributeError on NoneType
- `test_interruption_recovery_system.py`:
  - **22 ERRORS** - SessionState missing 'RUNNING' attribute

### 5. PDF Discovery Module (`tests/unit/pdf_discovery/`)
**Failed Tests: 1**
- `test_framework.py`:
  - `test_discover_pdfs_with_failures` - Wrong collector name returned

### 6. PDF Storage Module (`tests/unit/pdf_storage/`)
**Failed Tests: 14**
- `test_google_drive_store.py`:
  - **7 tests** - AttributeError: service_account module missing
- `test_pdf_manager.py`:
  - `test_cleanup_cache` - Unexpected keyword argument
  - `test_get_pdf_for_analysis_cached` - requests module missing
  - `test_get_pdf_for_analysis_download` - requests module missing
  - `test_get_statistics` - Statistics count mismatch
  - `test_store_pdf_failure` - Should return False but returns True
  - `test_store_pdf_success` - upload_file not called

### 7. Quality Module (`tests/unit/quality/`)
**Failed Tests: 51**
- `extraction/test_consistency_checker.py`:
  - `test_cross_paper_consistency_high_variation` - Should fail but passes
  - `test_scaling_consistency_violation` - Should fail but passes
  - `test_determine_domain` - Wrong domain detected
- `extraction/test_integrated_validator.py`:
  - `test_validate_extraction_batch` - SVD convergence error
  - `test_outlier_detection_integration` - No outliers detected
  - `test_batch_cache_usage` - SVD convergence error
- `extraction/test_outlier_detection.py`:
  - `test_contextualize_outlier_known_extreme` - Wrong context
  - `test_verify_outlier_corroborating_evidence` - Verification failed
- `test_alert_suppression.py`:
  - **6 tests** - SuppressionRule constructor argument errors
- `test_alert_system.py`:
  - **14 tests** - CollectionProgressMetrics constructor errors
- `test_dashboard_metrics.py`:
  - **10 tests** - Metrics constructor argument errors
- `test_intelligent_alerting_system.py`:
  - **10 tests** - Channel initialization and missing module errors
- `test_metrics_collector.py`:
  - **9 tests** - Missing attributes and methods

### 8. Package Configuration (`tests/unit/`)
**Failed Tests: 3**
- `test_package_configuration.py`:
  - `test_python_version_requirement` - Expected 3.12 only, got >=3.12
  - `test_python_classifiers` - Python 3.13 classifier present
  - `test_current_python_version` - Running on Python 3.13

## Integration Test Failures

### PDF Discovery Integration
**Errors: 10**
- ArXiv collector errors for papers without arXiv IDs (paper_1, 3, 5, 7, 9, 11, 13, 15, 17, 19)

## Issues to Create

### Issue #1: Fix Data Module Test Failures
**Module**: data
**Priority**: High
**Tests to fix**: 6
- Venue collection engine API failure recovery
- Collection time estimation
- Venue normalization logic

### Issue #2: Fix Error Injection Module Test Failures
**Module**: error_injection
**Priority**: Medium
**Tests to fix**: 9
- Recovery validator initialization
- Data loss percentage calculations
- Graceful degradation verification
- Recommendations generation

### Issue #3: Fix Extraction Module Test Failures
**Module**: extraction
**Priority**: Medium
**Tests to fix**: 4
- Time tracking in extraction protocol
- Completeness score calculation
- Mock analyzer attribute handling

### Issue #4: Fix Orchestration Module Test Failures
**Module**: orchestration
**Priority**: Critical
**Tests to fix**: 28
- Enhanced orchestrator initialization
- GoogleScholarClient import issues
- Rate limit manager logic
- State management persistence
- SessionState enum missing attributes (22 errors)

### Issue #5: Fix PDF Discovery Module Test Failures
**Module**: pdf_discovery
**Priority**: Low
**Tests to fix**: 1
- Framework collector identification

### Issue #6: Fix PDF Storage Module Test Failures
**Module**: pdf_storage
**Priority**: High
**Tests to fix**: 14
- Google Drive store service_account import
- PDF manager cache configuration
- Missing requests module
- Store operation return values

### Issue #7: Fix Quality Module Test Failures
**Module**: quality
**Priority**: Critical
**Tests to fix**: 51
- Consistency checker logic
- SVD convergence in validators
- Alert system metric constructors
- Dashboard metrics constructors
- Intelligent alerting channel initialization
- Metrics collector missing methods

### Issue #8: Fix Package Configuration Test Failures
**Module**: package configuration
**Priority**: Low
**Tests to fix**: 3
- Python version constraints
- Classifier configuration
- Test environment Python version

### Issue #9: Fix Integration Test Failures
**Module**: pdf_discovery integration
**Priority**: Medium
**Tests to fix**: 10
- ArXiv collector paper ID handling
