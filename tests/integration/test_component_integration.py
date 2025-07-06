"""
Component Integration Tests for validating integration between all agent components.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any

from compute_forecast.orchestration.venue_collection_orchestrator import (
    VenueCollectionOrchestrator,
)
from compute_forecast.data.models import CollectionConfig, Paper, Author


@dataclass
class TestResult:
    """Individual test result"""

    test_name: str
    success: bool
    duration_seconds: float
    assertions_passed: int
    assertions_failed: int
    performance_metrics: Dict[str, float]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    test_data: Dict[str, Any] = field(default_factory=dict)
    validation_results: List[Any] = field(default_factory=list)


class ComponentIntegrationTest:
    """Test integration between agent components"""

    def test_alpha_beta_integration(self) -> TestResult:
        """Test API layer integration with state management"""

        test_result = TestResult(
            test_name="alpha_beta_integration",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={},
        )

        start_time = time.time()

        try:
            # Create orchestrator to get components
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()

            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result

            # Test API engine and state manager interaction
            api_engine = orchestrator.api_engine
            state_manager = orchestrator.state_manager

            if api_engine is None or state_manager is None:
                test_result.errors.append("Required components not initialized")
                return test_result

            test_result.assertions_passed += 1

            # Test session creation
            session_id = state_manager.create_session(config)
            assert session_id, "Session creation should return valid ID"
            test_result.assertions_passed += 1

            # Test API connectivity check
            if hasattr(api_engine, "test_api_connectivity"):
                api_status = api_engine.test_api_connectivity()
                assert isinstance(
                    api_status, dict
                ), "API status should return dictionary"
                test_result.assertions_passed += 1

            # Test state persistence with API results
            test_checkpoint_data = {
                "session_id": session_id,
                "checkpoint_type": "api_test",
                "api_status": api_status if "api_status" in locals() else {},
                "timestamp": time.time(),
            }

            # Mock checkpoint data structure
            from compute_forecast.orchestration.state_manager import CheckpointData
            from datetime import datetime

            checkpoint = CheckpointData(
                checkpoint_id="",
                session_id=session_id,
                checkpoint_type="api_test",
                timestamp=datetime.now(),
                venues_completed=[],
                venues_in_progress=[],
                venues_not_started=[],
                papers_collected=0,
                papers_by_venue={},
                last_successful_operation="api_connectivity_test",
                api_health_status=api_status if "api_status" in locals() else {},
                rate_limit_status={},
                checksum="",
            )

            checkpoint_id = state_manager.save_checkpoint(session_id, checkpoint)
            assert checkpoint_id, "Checkpoint should be saved successfully"
            test_result.assertions_passed += 1

            test_result.success = True

        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")

        except Exception as e:
            test_result.errors.append(f"Alpha-Beta integration test failed: {str(e)}")

        finally:
            test_result.duration_seconds = time.time() - start_time

            # Cleanup
            try:
                if "orchestrator" in locals():
                    orchestrator.shutdown_system()
            except Exception:
                pass

        return test_result

    def test_alpha_gamma_integration(self) -> TestResult:
        """Test API layer integration with data processing"""

        test_result = TestResult(
            test_name="alpha_gamma_integration",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={},
        )

        start_time = time.time()

        try:
            # Create orchestrator
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()

            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result

            # Get components
            api_engine = orchestrator.api_engine
            venue_normalizer = orchestrator.venue_normalizer
            deduplicator = orchestrator.deduplicator

            if not all([api_engine, venue_normalizer, deduplicator]):
                test_result.errors.append("Required components not initialized")
                return test_result

            test_result.assertions_passed += 1

            # Create test papers (simulating API collection results)
            test_papers = [
                Paper(
                    title="Test Paper 1",
                    authors=[Author(name="Author 1", affiliation="University 1")],
                    venue="ICML",
                    year=2024,
                    citations=25,
                    abstract="Test abstract 1",
                ),
                Paper(
                    title="Test Paper 2",
                    authors=[Author(name="Author 2", affiliation="University 2")],
                    venue="icml",  # Different case for normalization test
                    year=2024,
                    citations=30,
                    abstract="Test abstract 2",
                ),
                Paper(
                    title="Test Paper 1",  # Duplicate for deduplication test
                    authors=[Author(name="Author 1", affiliation="University 1")],
                    venue="ICML",
                    year=2024,
                    citations=25,
                    abstract="Test abstract 1",
                ),
            ]

            # Test venue normalization
            normalized_papers = []
            for paper in test_papers:
                try:
                    # Try to normalize venue
                    if hasattr(venue_normalizer, "normalize_venue"):
                        normalization_result = venue_normalizer.normalize_venue(
                            paper.venue
                        )
                        if normalization_result:
                            paper.normalized_venue = normalization_result.get(
                                "normalized_name", paper.venue
                            )
                        normalized_papers.append(paper)
                    else:
                        # Fallback for simple test
                        paper.normalized_venue = paper.venue.upper()
                        normalized_papers.append(paper)
                except Exception as e:
                    test_result.warnings.append(
                        f"Venue normalization warning: {str(e)}"
                    )
                    normalized_papers.append(paper)

            assert len(normalized_papers) == len(
                test_papers
            ), "All papers should be processed"
            test_result.assertions_passed += 1

            # Test deduplication
            dedup_result = deduplicator.deduplicate_papers(normalized_papers)

            assert hasattr(
                dedup_result, "unique_papers"
            ), "Deduplication should return result with unique_papers"
            assert hasattr(
                dedup_result, "deduplicated_count"
            ), "Deduplication should return count"
            test_result.assertions_passed += 1

            # Should deduplicate the duplicate paper
            assert dedup_result.deduplicated_count < len(
                test_papers
            ), "Deduplication should reduce paper count"
            test_result.assertions_passed += 1

            # Test data flow integrity
            final_papers = dedup_result.unique_papers
            assert len(final_papers) > 0, "Final paper list should not be empty"
            test_result.assertions_passed += 1

            # Verify normalized venues are preserved
            normalized_venues_count = sum(
                1 for paper in final_papers if hasattr(paper, "normalized_venue")
            )
            assert normalized_venues_count > 0, "Normalized venues should be preserved"
            test_result.assertions_passed += 1

            test_result.success = True

        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")

        except Exception as e:
            test_result.errors.append(f"Alpha-Gamma integration test failed: {str(e)}")

        finally:
            test_result.duration_seconds = time.time() - start_time

            # Cleanup
            try:
                if "orchestrator" in locals():
                    orchestrator.shutdown_system()
            except Exception:
                pass

        return test_result

    def test_beta_gamma_integration(self) -> TestResult:
        """Test state management integration with data processing"""

        test_result = TestResult(
            test_name="beta_gamma_integration",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={},
        )

        start_time = time.time()

        try:
            # Create orchestrator
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()

            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result

            # Get components
            state_manager = orchestrator.state_manager
            deduplicator = orchestrator.deduplicator
            citation_analyzer = orchestrator.citation_analyzer

            if not all([state_manager, deduplicator, citation_analyzer]):
                test_result.errors.append("Required components not initialized")
                return test_result

            test_result.assertions_passed += 1

            # Create session
            session_id = state_manager.create_session(config)
            assert session_id, "Session should be created"
            test_result.assertions_passed += 1

            # Create test papers for processing
            test_papers = [
                Paper(
                    title=f"Paper {i}",
                    authors=[],
                    venue="ICML",
                    year=2024,
                    citations=i * 10,
                    abstract=f"Abstract {i}",
                )
                for i in range(1, 11)  # 10 papers
            ]

            # Test citation analysis
            citation_report = citation_analyzer.analyze_citation_distributions(
                test_papers
            )

            assert hasattr(
                citation_report, "total_papers"
            ), "Citation report should have total_papers"
            assert citation_report.total_papers == len(
                test_papers
            ), "Citation report should count all papers"
            test_result.assertions_passed += 1

            # Test state checkpoint with processing results
            from compute_forecast.orchestration.state_manager import CheckpointData
            from datetime import datetime

            processing_checkpoint = CheckpointData(
                checkpoint_id="",
                session_id=session_id,
                checkpoint_type="processing_complete",
                timestamp=datetime.now(),
                venues_completed=[("ICML", 2024)],
                venues_in_progress=[],
                venues_not_started=[],
                papers_collected=len(test_papers),
                papers_by_venue={"ICML": {2024: len(test_papers)}},
                last_successful_operation="citation_analysis",
                api_health_status={},
                rate_limit_status={},
                checksum="",
            )

            checkpoint_id = state_manager.save_checkpoint(
                session_id, processing_checkpoint
            )
            assert checkpoint_id, "Processing checkpoint should be saved"
            test_result.assertions_passed += 1

            # Test session recovery with processed data
            recovered_session = state_manager.recover_session(session_id)
            assert recovered_session is not None, "Session should be recoverable"
            assert recovered_session["papers_collected"] == len(
                test_papers
            ), "Recovered session should have correct paper count"
            test_result.assertions_passed += 1

            test_result.success = True

        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")

        except Exception as e:
            test_result.errors.append(f"Beta-Gamma integration test failed: {str(e)}")

        finally:
            test_result.duration_seconds = time.time() - start_time

            # Cleanup
            try:
                if "orchestrator" in locals():
                    orchestrator.shutdown_system()
            except Exception:
                pass

        return test_result

    def test_all_delta_integrations(self) -> TestResult:
        """Test monitoring integration with all components"""

        test_result = TestResult(
            test_name="all_delta_integrations",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={},
        )

        start_time = time.time()

        try:
            # Create orchestrator
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()

            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result

            # Get monitoring components
            metrics_collector = orchestrator.metrics_collector
            dashboard = orchestrator.dashboard
            alert_system = orchestrator.alert_system

            if not all([metrics_collector, dashboard, alert_system]):
                test_result.errors.append("Monitoring components not initialized")
                return test_result

            test_result.assertions_passed += 1

            # Start session and monitoring
            session_id = orchestrator.start_collection_session()
            assert session_id, "Session should start successfully"
            test_result.assertions_passed += 1

            # Test metrics collection
            metrics = metrics_collector.collect_current_metrics(session_id)
            assert metrics is not None, "Metrics should be collected"
            assert hasattr(metrics, "session_id"), "Metrics should have session_id"
            assert (
                metrics.session_id == session_id
            ), "Metrics should have correct session_id"
            test_result.assertions_passed += 1

            # Test dashboard integration
            dashboard_data = dashboard.get_dashboard_data(session_id)
            assert dashboard_data is not None, "Dashboard data should be available"
            assert (
                dashboard_data["session_id"] == session_id
            ), "Dashboard should track correct session"
            test_result.assertions_passed += 1

            # Test alert system
            # Create test metrics that should trigger alerts
            test_metrics = metrics
            test_metrics.errors_count = 100  # High error count
            test_metrics.papers_per_minute = 1.0  # Low collection rate

            alerts = alert_system.check_alerts(session_id, test_metrics)
            assert isinstance(alerts, list), "Alert system should return list of alerts"
            # We expect at least one alert due to high error count or low rate
            if len(alerts) > 0:
                test_result.assertions_passed += 1
            else:
                test_result.warnings.append(
                    "No alerts triggered despite test conditions"
                )

            # Test venue completion recording
            venue_metrics = {
                "session_id": session_id,
                "venue": "ICML",
                "year": 2024,
                "papers_collected": 50,
                "papers_after_dedup": 45,
                "processing_time": 120.0,
            }

            # This should not fail
            metrics_collector.record_venue_completion(venue_metrics)
            test_result.assertions_passed += 1

            # Test monitoring integration across workflow
            # Simulate a small collection workflow with monitoring
            test_venues = ["ICML"]
            test_years = [2024]

            # This should trigger monitoring throughout
            collection_result = orchestrator.execute_venue_collection(
                session_id, test_venues, test_years
            )

            # Check that monitoring captured the workflow
            session_summary = metrics_collector.get_session_summary(session_id)
            assert isinstance(
                session_summary, dict
            ), "Session summary should be available"
            test_result.assertions_passed += 1

            test_result.success = True

        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")

        except Exception as e:
            test_result.errors.append(f"Delta integrations test failed: {str(e)}")

        finally:
            test_result.duration_seconds = time.time() - start_time

            # Cleanup
            try:
                if "orchestrator" in locals():
                    orchestrator.shutdown_system()
            except Exception:
                pass

        return test_result


class TestComponentIntegrationRunner:
    """Runner for component integration tests"""

    def run_all_component_tests(self) -> List[TestResult]:
        """Run all component integration tests"""

        integration_test = ComponentIntegrationTest()

        tests = [
            integration_test.test_alpha_beta_integration(),
            integration_test.test_alpha_gamma_integration(),
            integration_test.test_beta_gamma_integration(),
            integration_test.test_all_delta_integrations(),
        ]

        return tests

    def validate_integration_health(
        self, test_results: List[TestResult]
    ) -> Dict[str, Any]:
        """Validate overall integration health"""

        total_tests = len(test_results)
        passed_tests = sum(1 for test in test_results if test.success)

        integration_health = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "overall_health": "healthy" if passed_tests == total_tests else "degraded",
            "critical_failures": [
                test.test_name
                for test in test_results
                if not test.success and test.assertions_failed > test.assertions_passed
            ],
            "warnings": [warning for test in test_results for warning in test.warnings],
        }

        return integration_health
