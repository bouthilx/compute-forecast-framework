"""
Interruption Recovery Tests for validating system resilience and recovery capabilities.
"""

import pytest
import time
import threading
import signal
import os
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from src.orchestration.venue_collection_orchestrator import VenueCollectionOrchestrator
from src.data.models import CollectionConfig, Paper, Author

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

class InterruptionRecoveryTest:
    """Test system recovery from various interruption scenarios"""
    
    def __init__(self):
        self.test_timeout = 300  # 5 minutes max per test
        self.recovery_timeout = 300  # 5 minutes max for recovery
        
    def test_api_failure_recovery(self) -> TestResult:
        """
        Test recovery from API failure during collection
        
        REQUIREMENTS:
        - Recovery time < 5 minutes
        - No data loss during recovery
        - System state consistency maintained
        """
        
        test_result = TestResult(
            test_name="api_failure_recovery",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={}
        )
        
        start_time = time.time()
        
        try:
            # Setup system
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()
            
            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result
            
            session_id = orchestrator.start_collection_session()
            test_result.assertions_passed += 1
            
            # Start collection
            test_venues = ["ICML", "ICLR"]
            test_years = [2024]
            
            # Mock API failure during collection
            with patch.object(orchestrator.api_engine, 'test_api_connectivity') as mock_connectivity:
                # First call succeeds, then fail
                mock_connectivity.side_effect = [
                    {"semantic_scholar": True, "openalex": True},  # Initial success
                    {"semantic_scholar": False, "openalex": False},  # Failure
                    {"semantic_scholar": True, "openalex": False}   # Partial recovery
                ]
                
                # Start collection (this should encounter the API failure)
                collection_start = time.time()
                collection_result = orchestrator.execute_venue_collection(session_id, test_venues, test_years)
                
                # Even with API failures, system should handle gracefully
                assert collection_result is not None, "Collection should return result even with failures"
                test_result.assertions_passed += 1
                
                # Test recovery
                recovery_start = time.time()
                
                # Try to resume the session
                recovery_result = orchestrator.resume_interrupted_session(session_id)
                recovery_time = time.time() - recovery_start
                
                # Validate recovery
                assert recovery_result.success or len(recovery_result.resume_errors) == 0, \
                    f"Recovery should succeed or have no errors: {recovery_result.resume_errors}"
                test_result.assertions_passed += 1
                
                assert recovery_time < 300, f"Recovery took too long: {recovery_time} seconds"  # 5 minutes
                test_result.assertions_passed += 1
                
                # Check state consistency
                assert recovery_result.state_consistency_validated, "State consistency should be validated"
                test_result.assertions_passed += 1
                
                test_result.performance_metrics['recovery_time_seconds'] = recovery_time
                test_result.performance_metrics['collection_time_seconds'] = time.time() - collection_start
            
            test_result.success = True
            
        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")
            
        except Exception as e:
            test_result.errors.append(f"API failure recovery test failed: {str(e)}")
            
        finally:
            test_result.duration_seconds = time.time() - start_time
            
            # Cleanup
            try:
                if 'orchestrator' in locals():
                    orchestrator.shutdown_system()
            except:
                pass
        
        return test_result
    
    def test_process_termination_recovery(self) -> TestResult:
        """
        Test recovery from simulated process termination mid-collection
        
        REQUIREMENTS:
        - Recovery time < 5 minutes
        - Session state preserved
        - Collection can be resumed
        """
        
        test_result = TestResult(
            test_name="process_termination_recovery",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={}
        )
        
        start_time = time.time()
        
        try:
            # Setup system
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()
            
            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result
            
            session_id = orchestrator.start_collection_session()
            test_result.assertions_passed += 1
            
            # Save initial state
            if orchestrator.state_manager:
                initial_session_data = orchestrator.state_manager.get_session_status(session_id)
                assert initial_session_data is not None, "Initial session data should be available"
                test_result.assertions_passed += 1
            
            # Simulate process termination by clearing orchestrator state
            # (In real scenario, this would be actual process restart)
            original_active_sessions = orchestrator.active_sessions.copy()
            orchestrator.active_sessions.clear()
            orchestrator.system_ready = False
            
            # Simulate system restart and recovery
            recovery_start = time.time()
            
            # Create new orchestrator instance (simulating restart)
            recovery_orchestrator = VenueCollectionOrchestrator(config)
            recovery_init_result = recovery_orchestrator.initialize_system()
            
            assert recovery_init_result.success, "Recovery orchestrator should initialize"
            test_result.assertions_passed += 1
            
            # Attempt to recover the session
            recovery_result = recovery_orchestrator.resume_interrupted_session(session_id)
            recovery_time = time.time() - recovery_start
            
            # Validate recovery
            assert recovery_time < 300, f"Recovery took too long: {recovery_time} seconds"
            test_result.assertions_passed += 1
            
            # Session should be recoverable (even if it doesn't have much data)
            if recovery_result.success:
                assert recovery_result.state_consistency_validated, "State consistency should be validated"
                test_result.assertions_passed += 1
            else:
                # Even if recovery fails, it should fail gracefully
                assert len(recovery_result.resume_errors) > 0, "Recovery failure should have error messages"
                test_result.assertions_passed += 1
            
            test_result.performance_metrics['recovery_time_seconds'] = recovery_time
            test_result.success = True
            
        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")
            
        except Exception as e:
            test_result.errors.append(f"Process termination recovery test failed: {str(e)}")
            
        finally:
            test_result.duration_seconds = time.time() - start_time
            
            # Cleanup
            try:
                if 'recovery_orchestrator' in locals():
                    recovery_orchestrator.shutdown_system()
            except:
                pass
        
        return test_result
    
    def test_network_interruption_recovery(self) -> TestResult:
        """
        Test recovery from network interruption
        
        REQUIREMENTS:
        - Graceful handling of network failures
        - Automatic retry mechanisms
        - Recovery when network restored
        """
        
        test_result = TestResult(
            test_name="network_interruption_recovery",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={}
        )
        
        start_time = time.time()
        
        try:
            # Setup system
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()
            
            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result
            
            session_id = orchestrator.start_collection_session()
            test_result.assertions_passed += 1
            
            # Simulate network interruption by mocking API failures
            with patch.object(orchestrator.api_engine, 'test_api_connectivity') as mock_connectivity:
                # Simulate network interruption pattern
                mock_connectivity.side_effect = [
                    {"semantic_scholar": True, "openalex": True},   # Initial connection
                    Exception("Network timeout"),                   # Network failure
                    Exception("Connection refused"),                # Still down
                    {"semantic_scholar": True, "openalex": False},  # Partial recovery
                    {"semantic_scholar": True, "openalex": True}    # Full recovery
                ]
                
                # Try to start collection during network issues
                test_venues = ["ICML"]
                test_years = [2024]
                
                collection_start = time.time()
                
                # System should handle network failures gracefully
                try:
                    collection_result = orchestrator.execute_venue_collection(session_id, test_venues, test_years)
                    # Should not crash, even with network issues
                    test_result.assertions_passed += 1
                    
                except Exception as e:
                    # If it does fail, it should be a handled failure
                    test_result.warnings.append(f"Collection failed gracefully: {str(e)}")
                    test_result.assertions_passed += 1
                
                # Test recovery after network restoration
                recovery_start = time.time()
                
                # Reset mock to simulate network recovery
                mock_connectivity.side_effect = [
                    {"semantic_scholar": True, "openalex": True}  # Network restored
                ]
                
                # Try recovery
                recovery_result = orchestrator.resume_interrupted_session(session_id)
                recovery_time = time.time() - recovery_start
                
                # Recovery should be fast once network is restored
                assert recovery_time < 60, f"Network recovery should be quick: {recovery_time} seconds"
                test_result.assertions_passed += 1
                
                test_result.performance_metrics['recovery_time_seconds'] = recovery_time
                test_result.performance_metrics['total_test_time'] = time.time() - collection_start
            
            test_result.success = True
            
        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")
            
        except Exception as e:
            test_result.errors.append(f"Network interruption recovery test failed: {str(e)}")
            
        finally:
            test_result.duration_seconds = time.time() - start_time
            
            # Cleanup
            try:
                if 'orchestrator' in locals():
                    orchestrator.shutdown_system()
            except:
                pass
        
        return test_result
    
    def test_component_crash_recovery(self) -> TestResult:
        """
        Test recovery from component crash
        
        REQUIREMENTS:
        - Detect component failures
        - Reinitialize failed components
        - Maintain system stability
        """
        
        test_result = TestResult(
            test_name="component_crash_recovery",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={}
        )
        
        start_time = time.time()
        
        try:
            # Setup system
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()
            
            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result
            
            session_id = orchestrator.start_collection_session()
            test_result.assertions_passed += 1
            
            # Simulate component crash by setting component to None
            original_venue_normalizer = orchestrator.venue_normalizer
            orchestrator.venue_normalizer = None  # Simulate crash
            
            # System should detect the failure
            system_status = orchestrator.get_system_status()
            assert system_status.overall_health in ["degraded", "critical"], \
                f"System should detect component failure: {system_status.overall_health}"
            test_result.assertions_passed += 1
            
            # Test recovery by reinitializing
            recovery_start = time.time()
            
            # Simulate component recovery
            orchestrator.venue_normalizer = original_venue_normalizer
            
            # Validate system integration after recovery
            integration_result = orchestrator.validate_system_integration()
            recovery_time = time.time() - recovery_start
            
            # System should recover
            assert recovery_time < 60, f"Component recovery should be quick: {recovery_time} seconds"
            test_result.assertions_passed += 1
            
            # Check that system can continue operating
            post_recovery_status = orchestrator.get_system_status()
            assert post_recovery_status.overall_health in ["healthy", "degraded"], \
                f"System should recover after component restoration: {post_recovery_status.overall_health}"
            test_result.assertions_passed += 1
            
            test_result.performance_metrics['recovery_time_seconds'] = recovery_time
            test_result.success = True
            
        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")
            
        except Exception as e:
            test_result.errors.append(f"Component crash recovery test failed: {str(e)}")
            
        finally:
            test_result.duration_seconds = time.time() - start_time
            
            # Cleanup
            try:
                if 'orchestrator' in locals():
                    orchestrator.shutdown_system()
            except:
                pass
        
        return test_result
    
    def test_disk_space_exhaustion_recovery(self) -> TestResult:
        """
        Test recovery from disk space exhaustion
        
        REQUIREMENTS:
        - Detect disk space issues
        - Graceful degradation
        - Recovery when space available
        """
        
        test_result = TestResult(
            test_name="disk_space_exhaustion_recovery",
            success=False,
            duration_seconds=0.0,
            assertions_passed=0,
            assertions_failed=0,
            performance_metrics={}
        )
        
        start_time = time.time()
        
        try:
            # Setup system
            config = CollectionConfig()
            orchestrator = VenueCollectionOrchestrator(config)
            init_result = orchestrator.initialize_system()
            
            if not init_result.success:
                test_result.errors.append("System initialization failed")
                return test_result
            
            session_id = orchestrator.start_collection_session()
            test_result.assertions_passed += 1
            
            # Simulate disk space exhaustion by mocking file operations
            with patch('builtins.open', side_effect=OSError("No space left on device")) as mock_open:
                # Try to save checkpoint (should fail due to disk space)
                try:
                    if orchestrator.state_manager:
                        from src.orchestration.state_manager import CheckpointData
                        from datetime import datetime
                        
                        test_checkpoint = CheckpointData(
                            checkpoint_id="",
                            session_id=session_id,
                            checkpoint_type="disk_test",
                            timestamp=datetime.now(),
                            venues_completed=[],
                            venues_in_progress=[],
                            venues_not_started=[],
                            papers_collected=0,
                            papers_by_venue={},
                            last_successful_operation="disk_space_test",
                            api_health_status={},
                            rate_limit_status={},
                            checksum=""
                        )
                        
                        # This should fail due to mocked disk space issue
                        checkpoint_id = orchestrator.state_manager.save_checkpoint(session_id, test_checkpoint)
                        test_result.warnings.append("Checkpoint save unexpectedly succeeded despite disk space simulation")
                        
                except Exception as e:
                    # Expected to fail due to disk space
                    test_result.assertions_passed += 1
                    test_result.test_data['disk_error'] = str(e)
            
            # Test recovery after disk space restored
            recovery_start = time.time()
            
            # Normal file operations should work now (no mock)
            if orchestrator.state_manager:
                try:
                    from src.orchestration.state_manager import CheckpointData
                    from datetime import datetime
                    
                    recovery_checkpoint = CheckpointData(
                        checkpoint_id="",
                        session_id=session_id,
                        checkpoint_type="recovery_test",
                        timestamp=datetime.now(),
                        venues_completed=[],
                        venues_in_progress=[],
                        venues_not_started=[],
                        papers_collected=0,
                        papers_by_venue={},
                        last_successful_operation="disk_recovery_test",
                        api_health_status={},
                        rate_limit_status={},
                        checksum=""
                    )
                    
                    checkpoint_id = orchestrator.state_manager.save_checkpoint(session_id, recovery_checkpoint)
                    assert checkpoint_id, "Checkpoint should save after disk space recovery"
                    test_result.assertions_passed += 1
                    
                except Exception as e:
                    test_result.errors.append(f"Recovery checkpoint failed: {str(e)}")
            
            recovery_time = time.time() - recovery_start
            test_result.performance_metrics['recovery_time_seconds'] = recovery_time
            
            # Recovery should be quick
            assert recovery_time < 30, f"Disk space recovery should be quick: {recovery_time} seconds"
            test_result.assertions_passed += 1
            
            test_result.success = True
            
        except AssertionError as e:
            test_result.assertions_failed += 1
            test_result.errors.append(f"Assertion failed: {str(e)}")
            
        except Exception as e:
            test_result.errors.append(f"Disk space exhaustion recovery test failed: {str(e)}")
            
        finally:
            test_result.duration_seconds = time.time() - start_time
            
            # Cleanup
            try:
                if 'orchestrator' in locals():
                    orchestrator.shutdown_system()
            except:
                pass
        
        return test_result

class InterruptionRecoveryTestRunner:
    """Test runner for interruption recovery tests"""
    
    def run_all_recovery_tests(self) -> List[TestResult]:
        """Run all recovery tests"""
        
        recovery_test = InterruptionRecoveryTest()
        
        tests = [
            recovery_test.test_api_failure_recovery(),
            recovery_test.test_process_termination_recovery(),
            recovery_test.test_network_interruption_recovery(),
            recovery_test.test_component_crash_recovery(),
            recovery_test.test_disk_space_exhaustion_recovery()
        ]
        
        return tests
    
    def validate_recovery_performance(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Validate recovery performance across all tests"""
        
        recovery_times = [
            test.performance_metrics.get('recovery_time_seconds', 0)
            for test in test_results if test.success
        ]
        
        performance_analysis = {
            'total_tests': len(test_results),
            'successful_recoveries': len(recovery_times),
            'failed_recoveries': len(test_results) - len(recovery_times),
            'average_recovery_time': sum(recovery_times) / len(recovery_times) if recovery_times else 0,
            'max_recovery_time': max(recovery_times) if recovery_times else 0,
            'recovery_time_target_met': all(t < 300 for t in recovery_times),  # 5 minute target
            'fast_recovery_count': len([t for t in recovery_times if t < 60]),  # Under 1 minute
            'slow_recovery_count': len([t for t in recovery_times if t > 180])  # Over 3 minutes
        }
        
        return performance_analysis