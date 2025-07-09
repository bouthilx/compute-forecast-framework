"""Unit tests for InterruptionRecoverySystem."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from compute_forecast.orchestration.recovery_system import (
    InterruptionRecoverySystem,
    RecoveryStrategy,
    InterruptionType,
    RecoveryState,
    RecoveryPlan,
)
from compute_forecast.orchestration.venue_collection_orchestrator import (
    SessionMetadata,
)
from compute_forecast.orchestration.recovery_system import SessionState


class TestInterruptionRecoverySystem:
    """Test cases for InterruptionRecoverySystem."""

    @pytest.fixture
    def mock_checkpoint_manager(self):
        """Create mock checkpoint manager."""
        mock = Mock()
        mock.list_checkpoints.return_value = [
            {
                "checkpoint_id": "ckpt-001",
                "timestamp": datetime.now().isoformat(),
                "checkpoint_type": "periodic",
            },
            {
                "checkpoint_id": "ckpt-002",
                "timestamp": datetime.now().isoformat(),
                "checkpoint_type": "venue_completed",
            },
        ]
        mock.load_checkpoint.return_value = {
            "timestamp": datetime.now().isoformat(),
            "state_data": {
                "completed_venues": ["NeurIPS_2023", "ICML_2023"],
                "workflow_state": {
                    "active_venues": set(),
                    "failed_venues": {"ICLR_2023": "API timeout"},
                },
            },
        }
        return mock

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state persistence manager."""
        mock = Mock()
        mock.load_session_state.return_value = {
            "session_id": "test-session",
            "state": SessionState.RUNNING,
            "progress": 0.5,
        }
        mock.list_session_checkpoints.return_value = ["ckpt-001", "ckpt-002"]
        mock.load_checkpoint.return_value = {
            "timestamp": datetime.now().isoformat(),
            "state_data": {
                "completed_venues": ["NeurIPS_2023", "ICML_2023"],
                "workflow_state": {
                    "active_venues": set(),
                    "failed_venues": {"ICLR_2023": "API timeout"},
                },
            },
        }
        return mock

    @pytest.fixture
    def recovery_system(self, mock_checkpoint_manager, mock_state_manager):
        """Create recovery system instance with mocks."""
        return InterruptionRecoverySystem(
            checkpoint_manager=mock_checkpoint_manager,
            state_manager=mock_state_manager,
            recovery_timeout_seconds=300.0,
            max_recovery_attempts=3,
        )

    @pytest.fixture
    def test_session(self):
        """Create test collection session."""
        from compute_forecast.data.models import CollectionConfig

        session = SessionMetadata(
            session_id="test-session-123",
            created_at=datetime.now(),
            status=SessionState.ERROR.value,
            venues=[
                "NeurIPS_2023",
                "ICML_2023",
                "ICLR_2023",
                "CVPR_2023",
                "ECCV_2023",
                "ICCV_2023",
            ],
            years=[2023],
            config=CollectionConfig(),
        )
        return session

    def test_detect_interruption_type_network_failure(
        self, recovery_system, test_session
    ):
        """Test detection of network failure interruption."""
        error = Exception("Connection timeout: unable to reach API endpoint")
        interruption_type = recovery_system.detect_interruption_type(
            test_session, error
        )
        assert interruption_type == InterruptionType.NETWORK_FAILURE

    def test_detect_interruption_type_api_timeout(self, recovery_system, test_session):
        """Test detection of API timeout interruption."""
        error = Exception("API rate limit exceeded: 429 Too Many Requests")
        interruption_type = recovery_system.detect_interruption_type(
            test_session, error
        )
        assert interruption_type == InterruptionType.API_TIMEOUT

    def test_detect_interruption_type_resource_exhaustion(
        self, recovery_system, test_session
    ):
        """Test detection of resource exhaustion."""
        error = Exception("Out of memory: cannot allocate buffer")
        interruption_type = recovery_system.detect_interruption_type(
            test_session, error
        )
        assert interruption_type == InterruptionType.RESOURCE_EXHAUSTION

    def test_detect_interruption_type_manual_stop(self, recovery_system, test_session):
        """Test detection of manual interruption."""
        error = Exception("Process received SIGTERM signal")
        interruption_type = recovery_system.detect_interruption_type(
            test_session, error
        )
        assert interruption_type == InterruptionType.MANUAL_STOP

    def test_detect_interruption_type_system_crash(self, recovery_system, test_session):
        """Test detection of system crash from session state."""
        test_session.state = SessionState.ERROR
        interruption_type = recovery_system.detect_interruption_type(test_session)
        assert interruption_type == InterruptionType.SYSTEM_CRASH

    def test_create_recovery_plan_network_failure(self, recovery_system, test_session):
        """Test recovery plan creation for network failure."""
        plan = recovery_system.create_recovery_plan(
            test_session, InterruptionType.NETWORK_FAILURE
        )

        assert plan.strategy == RecoveryStrategy.RESUME_FROM_CHECKPOINT
        assert plan.checkpoint_id == "ckpt-002"
        assert len(plan.venues_to_recover) == 4  # 6 total - 2 completed
        assert len(plan.venues_to_skip) == 2  # Already completed
        assert plan.confidence_score > 0.7
        assert len(plan.recovery_steps) > 0

    def test_create_recovery_plan_api_timeout(self, recovery_system, test_session):
        """Test recovery plan creation for API timeout."""
        plan = recovery_system.create_recovery_plan(
            test_session, InterruptionType.API_TIMEOUT
        )

        assert plan.strategy == RecoveryStrategy.SKIP_AND_CONTINUE
        assert plan.confidence_score >= 0.5

    def test_create_recovery_plan_system_crash(self, recovery_system, test_session):
        """Test recovery plan creation for system crash."""
        plan = recovery_system.create_recovery_plan(
            test_session, InterruptionType.SYSTEM_CRASH
        )

        assert plan.strategy == RecoveryStrategy.RESUME_FROM_CHECKPOINT
        assert plan.checkpoint_id is not None

    def test_create_recovery_plan_no_checkpoint(self, recovery_system, test_session):
        """Test recovery plan when no checkpoints exist."""
        recovery_system.checkpoint_manager.list_checkpoints.return_value = []
        recovery_system.state_manager.list_session_checkpoints.return_value = []

        plan = recovery_system.create_recovery_plan(
            test_session, InterruptionType.NETWORK_FAILURE
        )

        assert plan.strategy == RecoveryStrategy.RETRY_FAILED_VENUES
        assert plan.checkpoint_id is None

    def test_execute_recovery_resume_from_checkpoint(
        self, recovery_system, test_session
    ):
        """Test executing recovery from checkpoint."""
        plan = RecoveryPlan(
            strategy=RecoveryStrategy.RESUME_FROM_CHECKPOINT,
            checkpoint_id="ckpt-002",
            venues_to_recover=[("CVPR", 2023), ("ECCV", 2023)],
            venues_to_skip=[("NeurIPS", 2023), ("ICML", 2023)],
            estimated_recovery_time=timedelta(minutes=10),
            confidence_score=0.85,
            recovery_steps=["Step 1", "Step 2"],
        )

        result = recovery_system.execute_recovery(test_session, plan)

        assert result.success is True
        assert "CVPR_2023" in result.recovery_state.recovered_venues
        assert "ECCV_2023" in result.recovery_state.recovered_venues
        assert result.recovery_time.total_seconds() > 0
        assert result.error_message is None

    def test_execute_recovery_retry_failed_venues(self, recovery_system, test_session):
        """Test executing recovery with retry strategy."""
        plan = RecoveryPlan(
            strategy=RecoveryStrategy.RETRY_FAILED_VENUES,
            checkpoint_id=None,
            venues_to_recover=[("ICLR", 2023), ("CVPR", 2023)],
            venues_to_skip=[],
            estimated_recovery_time=timedelta(minutes=5),
            confidence_score=0.75,
            recovery_steps=["Retry step 1", "Retry step 2"],
        )

        result = recovery_system.execute_recovery(test_session, plan)

        assert result.success is True
        assert len(result.recovery_state.recovered_venues) == 2

    def test_execute_recovery_partial(self, recovery_system, test_session):
        """Test partial recovery execution."""
        plan = RecoveryPlan(
            strategy=RecoveryStrategy.PARTIAL_RECOVERY,
            checkpoint_id="ckpt-001",
            venues_to_recover=[("Venue" + str(i), 2023) for i in range(20)],
            venues_to_skip=[],
            estimated_recovery_time=timedelta(minutes=15),
            confidence_score=0.80,
            recovery_steps=["Partial recovery steps"],
        )

        result = recovery_system.execute_recovery(test_session, plan)

        assert result.success is True
        # Partial recovery should limit to 10 venues
        assert len(result.recovery_state.recovered_venues) <= 10

    def test_execute_recovery_failure(self, recovery_system, test_session):
        """Test recovery execution failure."""
        plan = RecoveryPlan(
            strategy=RecoveryStrategy.RESUME_FROM_CHECKPOINT,
            checkpoint_id="invalid-checkpoint",
            venues_to_recover=[("Test", 2023)],
            venues_to_skip=[],
            estimated_recovery_time=timedelta(minutes=5),
            confidence_score=0.5,
            recovery_steps=["Failed step"],
        )

        # Mock checkpoint load failure
        recovery_system.checkpoint_manager.load_checkpoint.side_effect = Exception(
            "Checkpoint not found"
        )

        result = recovery_system.execute_recovery(test_session, plan)

        assert result.success is False
        assert result.error_message is not None
        assert "Checkpoint not found" in result.error_message

    def test_recovery_metrics_tracking(self, recovery_system, test_session):
        """Test recovery metrics are tracked correctly."""
        plan = RecoveryPlan(
            strategy=RecoveryStrategy.SKIP_AND_CONTINUE,
            checkpoint_id=None,
            venues_to_recover=[("Test", 2023)],
            venues_to_skip=[],
            estimated_recovery_time=timedelta(minutes=1),
            confidence_score=0.9,
            recovery_steps=["Skip step"],
        )

        # Execute multiple recoveries
        recovery_system.execute_recovery(test_session, plan)
        recovery_system.execute_recovery(test_session, plan)

        # Check metrics
        metrics = recovery_system.get_recovery_metrics()
        assert metrics["total_recoveries"] == 2
        assert metrics["successful_recoveries"] == 2
        assert metrics["failed_recoveries"] == 0
        assert metrics["average_recovery_time"] > 0

    def test_recovery_state_tracking(self, recovery_system, test_session):
        """Test active recovery state tracking."""
        plan = RecoveryPlan(
            strategy=RecoveryStrategy.RESUME_FROM_CHECKPOINT,
            checkpoint_id="ckpt-001",
            venues_to_recover=[("Test", 2023)],
            venues_to_skip=[],
            estimated_recovery_time=timedelta(minutes=1),
            confidence_score=0.8,
            recovery_steps=["Step"],
        )

        # Start recovery in a thread to test concurrent access
        import threading

        def check_active_recovery():
            # Should see active recovery during execution
            assert test_session.session_id in recovery_system.active_recoveries

        # Mock a delay in recovery execution
        original_resume = recovery_system._resume_from_checkpoint

        def delayed_resume(*args, **kwargs):
            threading.Thread(target=check_active_recovery).start()
            import time

            time.sleep(0.1)
            return original_resume(*args, **kwargs)

        with patch.object(recovery_system, "_resume_from_checkpoint", delayed_resume):
            recovery_system.execute_recovery(test_session, plan)

        # Should be cleaned up after execution
        assert test_session.session_id not in recovery_system.active_recoveries

    def test_validate_recovery_capability_success(self, recovery_system, test_session):
        """Test validation of recovery capability."""
        is_valid, error_msg = recovery_system.validate_recovery_capability(test_session)

        assert is_valid is True
        assert error_msg is None

    def test_validate_recovery_capability_no_checkpoints(
        self, recovery_system, test_session
    ):
        """Test validation when no checkpoints exist."""
        recovery_system.checkpoint_manager.list_checkpoints.return_value = []

        is_valid, error_msg = recovery_system.validate_recovery_capability(test_session)

        assert is_valid is False
        assert "No checkpoints available" in error_msg

    def test_validate_recovery_capability_no_state(self, recovery_system, test_session):
        """Test validation when session state is missing."""
        recovery_system.state_manager.load_session_state.return_value = None

        is_valid, error_msg = recovery_system.validate_recovery_capability(test_session)

        assert is_valid is False
        assert "No persisted session state" in error_msg

    def test_validate_recovery_capability_max_attempts(
        self, recovery_system, test_session
    ):
        """Test validation when max recovery attempts reached."""
        # Add active recovery with max attempts
        recovery_state = RecoveryState(
            session_id=test_session.session_id,
            interruption_time=datetime.now(),
            interruption_type=InterruptionType.NETWORK_FAILURE,
            last_checkpoint_id="ckpt-001",
            recovery_strategy=RecoveryStrategy.RETRY_FAILED_VENUES,
            recovery_attempts=3,
        )
        recovery_system.active_recoveries[test_session.session_id] = recovery_state

        is_valid, error_msg = recovery_system.validate_recovery_capability(test_session)

        assert is_valid is False
        assert "Maximum recovery attempts exceeded" in error_msg

    def test_recovery_plan_generation_steps(self, recovery_system):
        """Test recovery step generation for different strategies."""
        strategies = [
            RecoveryStrategy.RESUME_FROM_CHECKPOINT,
            RecoveryStrategy.RETRY_FAILED_VENUES,
            RecoveryStrategy.PARTIAL_RECOVERY,
            RecoveryStrategy.SKIP_AND_CONTINUE,
            RecoveryStrategy.FULL_RESTART,
        ]

        for strategy in strategies:
            steps = recovery_system._generate_recovery_steps(
                strategy, [("Test", 2023)], {"test": "data"}
            )

            assert len(steps) > 0
            assert all(isinstance(step, str) for step in steps)
            # Check that steps are generated for each strategy
            steps_text = " ".join(steps).lower()
            # Just verify that meaningful steps are generated
            assert len(steps_text) > 50  # Each strategy should have substantial steps

    def test_checkpoint_age_validation(self, recovery_system):
        """Test checkpoint age validation."""
        # Recent checkpoint
        recent_checkpoint = {"timestamp": datetime.now().isoformat()}
        assert recovery_system._is_checkpoint_recent(recent_checkpoint, 24.0) is True

        # Old checkpoint
        old_time = datetime.now() - timedelta(hours=48)
        old_checkpoint = {"timestamp": old_time.isoformat()}
        assert recovery_system._is_checkpoint_recent(old_checkpoint, 24.0) is False

        # Missing timestamp
        invalid_checkpoint = {"data": "test"}
        assert recovery_system._is_checkpoint_recent(invalid_checkpoint) is False

    def test_confidence_score_calculation(self, recovery_system):
        """Test confidence score calculation for different scenarios."""
        checkpoint_data = {"timestamp": datetime.now().isoformat()}

        # High confidence: manual stop with checkpoint resume
        confidence = recovery_system._calculate_recovery_confidence(
            InterruptionType.MANUAL_STOP,
            RecoveryStrategy.SKIP_AND_CONTINUE,
            checkpoint_data,
        )
        assert confidence >= 0.7

        # Low confidence: unknown interruption with full restart
        confidence = recovery_system._calculate_recovery_confidence(
            InterruptionType.UNKNOWN, RecoveryStrategy.FULL_RESTART, None
        )
        assert confidence < 0.5

        # Medium confidence: network failure with retry
        confidence = recovery_system._calculate_recovery_confidence(
            InterruptionType.NETWORK_FAILURE,
            RecoveryStrategy.RETRY_FAILED_VENUES,
            checkpoint_data,
        )
        assert 0.5 <= confidence <= 0.8
