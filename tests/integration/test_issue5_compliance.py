"""
Integration tests for Issue #5 compliance - Hierarchical State Management System.

Tests the exact interface contract and requirements specified in Issue #5.
"""

import pytest
import tempfile
import time
from pathlib import Path
from datetime import datetime

from compute_forecast.data.collectors.state_management import StateManager
from compute_forecast.data.collectors.recovery_engine import RecoveryEngine
from compute_forecast.data.collectors.state_persistence import StatePersistence
from compute_forecast.data.collectors.state_structures import (
    CheckpointData,
    ErrorContext,
)
from compute_forecast.core.config import CollectionConfig


class TestIssue5StateManager:
    """Test StateManager class compliance with Issue #5 exact interface"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_manager = StateManager(
            base_state_dir=self.temp_dir / "states",
            backup_interval_seconds=300,
            max_checkpoints_per_session=1000,
        )
        self.collection_config = CollectionConfig(
            papers_per_domain_year=50,
            total_target_min=1000,
            total_target_max=5000,
            citation_threshold_base=10,
        )

    def test_create_session_exact_interface(self):
        """Test create_session with exact Issue #5 interface"""
        start_time = time.time()

        # Test with exact parameters from Issue #5
        session_id = self.state_manager.create_session(
            session_config=self.collection_config,
            session_id=None,  # Should generate unique ID
        )

        duration = time.time() - start_time

        # Verify requirements
        assert session_id is not None
        assert isinstance(session_id, str)
        assert session_id.startswith("session_")
        assert (
            duration < 1.0
        ), f"Session creation took {duration:.3f}s (>1s requirement)"

        # Verify directory structure created
        session_dir = self.temp_dir / "states" / "sessions" / session_id
        assert session_dir.exists()
        assert (session_dir / "checkpoints").exists()
        assert (session_dir / "venues").exists()
        assert (session_dir / "recovery").exists()

        # Verify session files created
        assert (session_dir / "session_config.json").exists()
        assert (session_dir / "session_status.json").exists()

    def test_create_session_with_provided_id(self):
        """Test create_session with user-provided session ID"""
        custom_id = "test_session_123"

        session_id = self.state_manager.create_session(
            session_config=self.collection_config, session_id=custom_id
        )

        assert session_id == custom_id

        # Verify cannot create duplicate
        with pytest.raises(ValueError, match="already exists"):
            self.state_manager.create_session(
                session_config=self.collection_config, session_id=custom_id
            )

    def test_save_checkpoint_exact_interface(self):
        """Test save_checkpoint with exact Issue #5 requirements"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023)],
            venues_in_progress=[("NeurIPS", 2023)],
            venues_not_started=[("ICLR", 2023)],
            papers_collected=100,
            papers_by_venue={"ICML": {2023: 100}},
            last_successful_operation="venue_collection_completed",
            api_health_status={},
            rate_limit_status={},
        )

        start_time = time.time()
        checkpoint_id = self.state_manager.save_checkpoint(session_id, checkpoint_data)
        duration = time.time() - start_time

        # Verify requirements
        assert checkpoint_id is not None
        assert isinstance(checkpoint_id, str)
        assert duration < 2.0, f"Checkpoint save took {duration:.3f}s (>2s requirement)"

        # Verify checkpoint file created
        session_dir = self.temp_dir / "states" / "sessions" / session_id
        checkpoint_file = session_dir / "checkpoints" / f"{checkpoint_id}.json"
        assert checkpoint_file.exists()

    def test_load_latest_checkpoint_exact_interface(self):
        """Test load_latest_checkpoint with exact Issue #5 requirements"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        # Save a checkpoint first
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023)],
            venues_in_progress=[],
            venues_not_started=[],
            papers_collected=50,
            papers_by_venue={"ICML": {2023: 50}},
            last_successful_operation="test_operation",
            api_health_status={},
            rate_limit_status={},
        )

        self.state_manager.save_checkpoint(session_id, checkpoint_data)

        # Test loading
        start_time = time.time()
        loaded_checkpoint = self.state_manager.load_latest_checkpoint(session_id)
        duration = time.time() - start_time

        # Verify requirements
        assert loaded_checkpoint is not None
        assert duration < 5.0, f"Checkpoint load took {duration:.3f}s (>5s requirement)"
        assert loaded_checkpoint.session_id == session_id
        assert loaded_checkpoint.papers_collected == 50

        # Test graceful handling of corrupted checkpoints
        # (Note: Would need to implement checkpoint corruption simulation)

        # Test no checkpoints case - new sessions have initial checkpoint, so this is expected
        new_session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )
        initial_checkpoint = self.state_manager.load_latest_checkpoint(new_session_id)
        assert initial_checkpoint is not None  # Initial session checkpoint should exist
        assert initial_checkpoint.checkpoint_type == "session_started"

    def test_get_recovery_plan_exact_interface(self):
        """Test get_recovery_plan with exact Issue #5 requirements"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        # Save a checkpoint
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023)],
            venues_in_progress=[("NeurIPS", 2023)],
            venues_not_started=[("ICLR", 2023)],
            papers_collected=100,
            papers_by_venue={"ICML": {2023: 100}},
            last_successful_operation="venue_completed",
            api_health_status={},
            rate_limit_status={},
        )

        self.state_manager.save_checkpoint(session_id, checkpoint_data)

        # Get recovery plan
        recovery_plan = self.state_manager.get_recovery_plan(session_id)

        # Verify requirements
        assert recovery_plan is not None
        assert recovery_plan.session_id == session_id
        assert recovery_plan.resumption_strategy in [
            "from_last_checkpoint",
            "from_venue_start",
            "partial_restart",
            "full_restart",
        ]
        assert 0.0 <= recovery_plan.recovery_confidence <= 1.0
        assert recovery_plan.estimated_recovery_time_minutes > 0
        assert isinstance(recovery_plan.recommended_validation_steps, list)

    def test_resume_session_exact_interface(self):
        """Test resume_session with exact Issue #5 requirements"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        # Save a checkpoint
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023)],
            venues_in_progress=[("NeurIPS", 2023)],
            venues_not_started=[("ICLR", 2023)],
            papers_collected=100,
            papers_by_venue={"ICML": {2023: 100}},
            last_successful_operation="venue_completed",
            api_health_status={},
            rate_limit_status={},
        )

        self.state_manager.save_checkpoint(session_id, checkpoint_data)

        # Get recovery plan
        recovery_plan = self.state_manager.get_recovery_plan(session_id)

        # Test resume
        start_time = time.time()
        result = self.state_manager.resume_session(session_id, recovery_plan)
        duration = time.time() - start_time

        # Verify requirements
        assert result is not None
        assert result.session_id == session_id
        assert result.plan_id == recovery_plan.plan_id
        assert isinstance(result.success, bool)
        assert (
            duration < 300.0
        ), f"Session recovery took {duration:.1f}s (>300s requirement)"
        assert (
            abs(result.recovery_duration_seconds - duration) < 0.001
        )  # Allow small timing differences
        assert isinstance(result.state_consistency_validated, bool)
        assert isinstance(result.recovery_steps_executed, list)


class TestIssue5RecoveryEngine:
    """Test RecoveryEngine class compliance with Issue #5 exact interface"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_manager = StateManager(base_state_dir=self.temp_dir / "states")
        self.recovery_engine = RecoveryEngine(self.state_manager)
        self.collection_config = CollectionConfig(
            papers_per_domain_year=50,
            total_target_min=1000,
            total_target_max=5000,
            citation_threshold_base=10,
        )

    def test_analyze_interruption_exact_interface(self):
        """Test analyze_interruption with exact Issue #5 requirements"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        # Create an interruption scenario with error
        error_checkpoint = CheckpointData(
            checkpoint_id="error_checkpoint",
            session_id=session_id,
            checkpoint_type="error_occurred",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023)],
            venues_in_progress=[("NeurIPS", 2023)],
            venues_not_started=[("ICLR", 2023)],
            papers_collected=50,
            papers_by_venue={"ICML": {2023: 50}},
            last_successful_operation="api_call_failed",
            api_health_status={},
            rate_limit_status={},
            error_context=ErrorContext(
                error_type="api_failure",
                error_message="API timeout",
                stack_trace="test stack trace",
                venue_context="NeurIPS",
                year_context=2023,
            ),
        )

        self.state_manager.save_checkpoint(session_id, error_checkpoint)

        # Test analysis
        start_time = time.time()
        analysis = self.recovery_engine.analyze_interruption(session_id)
        duration = time.time() - start_time

        # Verify requirements
        assert analysis is not None
        assert analysis.session_id == session_id
        assert duration < 120.0, f"Analysis took {duration:.1f}s (>120s requirement)"
        assert analysis.interruption_cause is not None
        assert analysis.recovery_complexity in [
            "trivial",
            "simple",
            "complex",
            "problematic",
        ]
        assert isinstance(analysis.valid_checkpoints, list)
        assert isinstance(analysis.corrupted_checkpoints, list)

    def test_create_recovery_plan_exact_interface(self):
        """Test create_recovery_plan with exact Issue #5 requirements"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        # Create checkpoint and analysis
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023)],
            venues_in_progress=[("NeurIPS", 2023)],
            venues_not_started=[("ICLR", 2023)],
            papers_collected=100,
            papers_by_venue={"ICML": {2023: 100}},
            last_successful_operation="venue_completed",
            api_health_status={},
            rate_limit_status={},
        )

        self.state_manager.save_checkpoint(session_id, checkpoint_data)

        # Get analysis
        analysis = self.recovery_engine.analyze_interruption(session_id)

        # Test recovery plan creation
        recovery_plan = self.recovery_engine.create_recovery_plan(session_id, analysis)

        # Verify requirements
        assert recovery_plan is not None
        assert recovery_plan.session_id == session_id
        assert recovery_plan.based_on_analysis == analysis
        assert recovery_plan.resumption_strategy in [
            "from_last_checkpoint",
            "from_venue_start",
            "partial_restart",
            "full_restart",
        ]
        assert 0.0 <= recovery_plan.confidence_score <= 1.0
        assert isinstance(recovery_plan.venues_to_skip, list)
        assert isinstance(recovery_plan.venues_to_resume, list)
        assert isinstance(recovery_plan.venues_to_restart, list)
        assert isinstance(recovery_plan.venues_to_validate, list)
        assert recovery_plan.estimated_recovery_time_minutes > 0
        assert recovery_plan.data_loss_estimate >= 0


class TestIssue5StatePersistence:
    """Test StatePersistence class compliance with Issue #5 exact interface"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_persistence = StatePersistence(self.temp_dir, enable_backups=True)

    def test_save_state_atomic_exact_interface(self):
        """Test save_state_atomic with exact Issue #5 requirements"""
        test_file = self.temp_dir / "test_state.json"

        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id="test_session",
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023)],
            venues_in_progress=[],
            venues_not_started=[],
            papers_collected=50,
            papers_by_venue={"ICML": {2023: 50}},
            last_successful_operation="test_operation",
            api_health_status={},
            rate_limit_status={},
        )

        # Test atomic save
        start_time = time.time()
        success = self.state_persistence.save_state_atomic(
            file_path=test_file, data=checkpoint_data, backup_previous=True
        )
        duration = time.time() - start_time

        # Verify requirements
        assert success is True
        assert duration < 2.0, f"Atomic save took {duration:.3f}s (>2s requirement)"
        assert test_file.exists()

        # Verify atomic operation (no partial writes)
        loaded_data = self.state_persistence.load_state(
            test_file, CheckpointData, validate_integrity=True
        )
        assert loaded_data is not None
        assert loaded_data.session_id == "test_session"

        # Test backup creation when overwriting
        modified_checkpoint = CheckpointData(
            checkpoint_id="modified_checkpoint",
            session_id="test_session",
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023), ("NeurIPS", 2023)],
            venues_in_progress=[],
            venues_not_started=[],
            papers_collected=100,
            papers_by_venue={"ICML": {2023: 50}, "NeurIPS": {2023: 50}},
            last_successful_operation="modified_operation",
            api_health_status={},
            rate_limit_status={},
        )

        # Save with backup
        success = self.state_persistence.save_state_atomic(
            file_path=test_file, data=modified_checkpoint, backup_previous=True
        )

        assert success is True
        backup_file = test_file.with_suffix(f"{test_file.suffix}.backup")
        assert backup_file.exists()


class TestIssue5PerformanceRequirements:
    """Test performance requirements specified in Issue #5"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_manager = StateManager(base_state_dir=self.temp_dir / "states")
        self.collection_config = CollectionConfig(
            papers_per_domain_year=50,
            total_target_min=1000,
            total_target_max=5000,
            citation_threshold_base=10,
        )

    def test_checkpoint_creation_2_second_requirement(self):
        """Test checkpoint creation within 2 seconds"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        checkpoint_data = CheckpointData(
            checkpoint_id="perf_test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023)],
            venues_in_progress=[("NeurIPS", 2023)],
            venues_not_started=[("ICLR", 2023)],
            papers_collected=100,
            papers_by_venue={"ICML": {2023: 100}},
            last_successful_operation="performance_test",
            api_health_status={},
            rate_limit_status={},
        )

        # Test multiple checkpoint saves
        for i in range(5):
            start_time = time.time()
            checkpoint_id = self.state_manager.save_checkpoint(
                session_id, checkpoint_data
            )
            duration = time.time() - start_time

            assert (
                duration < 2.0
            ), f"Checkpoint {i} save took {duration:.3f}s (>2s requirement)"
            assert checkpoint_id is not None

    def test_state_loading_5_second_requirement(self):
        """Test state loading within 5 seconds"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        # Create several checkpoints
        for i in range(10):
            checkpoint_data = CheckpointData(
                checkpoint_id=f"load_test_checkpoint_{i}",
                session_id=session_id,
                checkpoint_type="venue_completed",
                timestamp=datetime.now(),
                venues_completed=[("ICML", 2023)],
                venues_in_progress=[("NeurIPS", 2023)],
                venues_not_started=[("ICLR", 2023)],
                papers_collected=i * 10,
                papers_by_venue={"ICML": {2023: i * 10}},
                last_successful_operation=f"load_test_{i}",
                api_health_status={},
                rate_limit_status={},
            )
            self.state_manager.save_checkpoint(session_id, checkpoint_data)

        # Test loading performance
        for i in range(5):
            start_time = time.time()
            checkpoint = self.state_manager.load_latest_checkpoint(session_id)
            duration = time.time() - start_time

            assert (
                duration < 5.0
            ), f"Checkpoint load {i} took {duration:.3f}s (>5s requirement)"
            assert checkpoint is not None

    def test_recovery_5_minute_requirement(self):
        """Test full recovery within 5 minutes"""
        session_id = self.state_manager.create_session(
            session_config=self.collection_config
        )

        # Create complex recovery scenario
        checkpoint_data = CheckpointData(
            checkpoint_id="recovery_test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("ICML", 2023), ("NeurIPS", 2023)],
            venues_in_progress=[("ICLR", 2023)],
            venues_not_started=[("AAAI", 2023), ("IJCAI", 2023)],
            papers_collected=150,
            papers_by_venue={"ICML": {2023: 75}, "NeurIPS": {2023: 75}},
            last_successful_operation="complex_recovery_test",
            api_health_status={},
            rate_limit_status={},
        )

        self.state_manager.save_checkpoint(session_id, checkpoint_data)

        # Test recovery performance
        recovery_plan = self.state_manager.get_recovery_plan(session_id)

        start_time = time.time()
        result = self.state_manager.resume_session(session_id, recovery_plan)
        duration = time.time() - start_time

        assert duration < 300.0, f"Recovery took {duration:.1f}s (>300s requirement)"
        assert result.success is True
        assert (
            abs(result.recovery_duration_seconds - duration) < 0.001
        )  # Allow small timing differences
