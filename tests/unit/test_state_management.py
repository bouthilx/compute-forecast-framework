"""
Unit tests for StateManager class.
Tests session lifecycle, checkpointing, and recovery functionality.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta

import sys

# Add package root to Python path
package_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(package_root))

from compute_forecast.data.collectors.state_management import StateManager
from compute_forecast.data.collectors.state_structures import (
    VenueConfig,
    CheckpointData,
    RecoveryPlan,
    SessionResumeResult,
)


class TestStateManager:
    """Test StateManager functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def state_manager(self, temp_dir):
        """Create StateManager instance for testing"""
        return StateManager(
            base_state_dir=temp_dir,
            backup_interval_seconds=300,
            max_checkpoints_per_session=100,
        )

    @pytest.fixture
    def sample_venues(self):
        """Create sample venue configurations"""
        return [
            VenueConfig(
                venue_name="CVPR", target_years=[2023, 2024], max_papers_per_year=50
            ),
            VenueConfig(
                venue_name="ICLR", target_years=[2023, 2024], max_papers_per_year=40
            ),
        ]

    @pytest.fixture
    def sample_config(self):
        """Create sample collection configuration"""
        return {
            "max_retries": 3,
            "timeout_seconds": 300,
            "api_priority": ["semantic_scholar", "openalex"],
        }

    def test_state_manager_initialization(self, temp_dir):
        """Test StateManager initialization"""
        manager = StateManager(
            base_state_dir=temp_dir,
            backup_interval_seconds=600,
            max_checkpoints_per_session=50,
        )

        assert manager.base_state_dir == temp_dir
        assert manager.backup_interval_seconds == 600
        assert manager.max_checkpoints_per_session == 50
        assert isinstance(manager._active_sessions, dict)
        assert manager.persistence is not None
        assert manager.checkpoint_manager is not None

        # Check directory structure is created
        assert (temp_dir / "sessions").exists()

    def test_create_session_basic(self, state_manager, sample_venues, sample_config):
        """Test basic session creation"""
        target_years = [2023, 2024]

        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=target_years,
            collection_config=sample_config,
        )

        assert session_id is not None
        assert "session_" in session_id
        assert session_id in state_manager._active_sessions

        # Verify session structure
        session = state_manager._active_sessions[session_id]
        assert session.session_id == session_id
        assert session.status == "active"
        assert len(session.target_venues) == 2
        assert session.target_years == target_years
        assert session.total_papers_collected == 0

        # Verify session directory is created
        session_dir = state_manager._get_session_dir(session_id)
        assert session_dir.exists()
        assert (session_dir / "checkpoints").exists()
        assert (session_dir / "venues").exists()
        assert (session_dir / "recovery").exists()
        assert (session_dir / "session.json").exists()

    def test_create_session_with_custom_id(
        self, state_manager, sample_venues, sample_config
    ):
        """Test session creation with custom ID"""
        custom_id = "custom_session_001"

        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023],
            collection_config=sample_config,
            session_id=custom_id,
        )

        assert session_id == custom_id
        assert custom_id in state_manager._active_sessions

    def test_create_session_duplicate_id(
        self, state_manager, sample_venues, sample_config
    ):
        """Test creating session with duplicate ID raises error"""
        session_id = "duplicate_session"

        # Create first session
        state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023],
            collection_config=sample_config,
            session_id=session_id,
        )

        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            state_manager.create_session(
                target_venues=sample_venues,
                target_years=[2023],
                collection_config=sample_config,
                session_id=session_id,
            )

    def test_save_checkpoint(self, state_manager, sample_venues, sample_config):
        """Test saving checkpoint"""
        # Create session
        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023, 2024],
            collection_config=sample_config,
        )

        # Create checkpoint data
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[("ICLR", 2024)],
            venues_not_started=[("CVPR", 2024)],
            papers_collected=100,
            papers_by_venue={"CVPR": {2023: 100}},
            last_successful_operation="cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={},
        )

        # Save checkpoint
        checkpoint_id = state_manager.save_checkpoint(session_id, checkpoint_data)

        assert checkpoint_id is not None

        # Verify session is updated
        session = state_manager._active_sessions[session_id]
        assert session.last_checkpoint_id == checkpoint_id
        assert session.checkpoint_count == 2  # Initial + this one
        assert session.total_papers_collected == 100
        assert session.venues_completed == [("CVPR", 2023)]

    def test_load_latest_checkpoint(self, state_manager, sample_venues, sample_config):
        """Test loading latest checkpoint"""
        # Create session
        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023],
            collection_config=sample_config,
        )

        # Create and save checkpoint
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[],
            venues_not_started=[],
            papers_collected=75,
            papers_by_venue={"CVPR": {2023: 75}},
            last_successful_operation="cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={},
        )

        state_manager.save_checkpoint(session_id, checkpoint_data)

        # Load latest checkpoint
        latest_checkpoint = state_manager.load_latest_checkpoint(session_id)

        assert latest_checkpoint is not None
        assert latest_checkpoint.session_id == session_id
        assert latest_checkpoint.papers_collected == 75
        assert latest_checkpoint.venues_completed == [("CVPR", 2023)]

    def test_load_latest_checkpoint_nonexistent_session(self, state_manager):
        """Test loading checkpoint for non-existent session"""
        checkpoint = state_manager.load_latest_checkpoint("nonexistent_session")
        assert checkpoint is None

    def test_get_recovery_plan(self, state_manager, sample_venues, sample_config):
        """Test creating recovery plan"""
        # Create session
        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023, 2024],
            collection_config=sample_config,
        )

        # Create checkpoint
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[("ICLR", 2024)],
            venues_not_started=[("CVPR", 2024)],
            papers_collected=50,
            papers_by_venue={"CVPR": {2023: 50}},
            last_successful_operation="cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={},
        )

        state_manager.save_checkpoint(session_id, checkpoint_data)

        # Get recovery plan
        recovery_plan = state_manager.get_recovery_plan(session_id)

        assert isinstance(recovery_plan, RecoveryPlan)
        assert recovery_plan.session_id == session_id
        assert recovery_plan.resumption_strategy == "from_last_checkpoint"
        assert recovery_plan.estimated_recovery_time_minutes <= 5.0
        assert recovery_plan.confidence_score > 0.5

    def test_resume_session(self, state_manager, sample_venues, sample_config):
        """Test session resumption"""
        # Create session
        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023, 2024],
            collection_config=sample_config,
        )

        # Create checkpoint
        checkpoint_data = CheckpointData(
            checkpoint_id="test_checkpoint",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[("ICLR", 2024)],
            venues_not_started=[("CVPR", 2024)],
            papers_collected=75,
            papers_by_venue={"CVPR": {2023: 75}},
            last_successful_operation="cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={},
        )

        checkpoint_id = state_manager.save_checkpoint(session_id, checkpoint_data)

        # Get recovery plan
        recovery_plan = state_manager.get_recovery_plan(session_id)

        # Remove from active sessions to simulate interruption
        del state_manager._active_sessions[session_id]

        # Resume session
        resume_result = state_manager.resume_session(session_id, recovery_plan)

        assert isinstance(resume_result, SessionResumeResult)
        assert resume_result.success is True
        assert resume_result.session_id == session_id
        assert resume_result.checkpoints_recovered == 1
        assert resume_result.papers_recovered == 75
        assert resume_result.ready_for_continuation is True

        # Verify session is restored
        assert session_id in state_manager._active_sessions
        session = state_manager._active_sessions[session_id]
        assert session.status == "active"
        assert session.total_papers_collected == 75

    def test_get_session_status(self, state_manager, sample_venues, sample_config):
        """Test getting session status"""
        # Create session
        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023],
            collection_config=sample_config,
        )

        # Get status from active sessions
        session = state_manager.get_session_status(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.status == "active"

        # Remove from active and test loading from disk
        del state_manager._active_sessions[session_id]

        session = state_manager.get_session_status(session_id)
        assert session is not None
        assert session.session_id == session_id

    def test_get_session_status_nonexistent(self, state_manager):
        """Test getting status for non-existent session"""
        session = state_manager.get_session_status("nonexistent_session")
        assert session is None

    def test_list_sessions(self, state_manager, sample_venues, sample_config):
        """Test listing sessions"""
        # Initially no sessions
        sessions = state_manager.list_sessions()
        assert len(sessions) == 0

        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_id = state_manager.create_session(
                target_venues=sample_venues,
                target_years=[2023],
                collection_config=sample_config,
            )
            session_ids.append(session_id)

        # List sessions
        sessions = state_manager.list_sessions()
        assert len(sessions) == 3

        for session_id in session_ids:
            assert session_id in sessions

    def test_cleanup_old_sessions(self, state_manager, sample_venues, sample_config):
        """Test cleanup of old sessions"""
        # Create a session
        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023],
            collection_config=sample_config,
        )

        # Modify session to be old
        session = state_manager._active_sessions[session_id]
        session.last_activity_time = datetime.now() - timedelta(days=35)

        # Save modified session
        session_file = state_manager._get_session_dir(session_id) / "session.json"
        state_manager.persistence.save_state_atomic(session_file, session)

        # Cleanup sessions older than 30 days
        cleaned_count = state_manager.cleanup_old_sessions(max_age_days=30)

        assert cleaned_count == 1
        assert session_id not in state_manager._active_sessions
        assert not state_manager._get_session_dir(session_id).exists()

    def test_performance_requirements(
        self, state_manager, sample_venues, sample_config
    ):
        """Test that operations meet performance requirements"""
        # Test session creation < 1 second
        start_time = time.time()
        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023],
            collection_config=sample_config,
        )
        creation_time = time.time() - start_time
        assert creation_time < 1.0

        # Test checkpoint save < 2 seconds
        checkpoint_data = CheckpointData(
            checkpoint_id="perf_test",
            session_id=session_id,
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[],
            venues_not_started=[],
            papers_collected=50,
            papers_by_venue={"CVPR": {2023: 50}},
            last_successful_operation="performance_test",
            api_health_status={},
            rate_limit_status={},
        )

        start_time = time.time()
        state_manager.save_checkpoint(session_id, checkpoint_data)
        save_time = time.time() - start_time
        assert save_time < 2.0

        # Test checkpoint load < 5 seconds
        start_time = time.time()
        state_manager.load_latest_checkpoint(session_id)
        load_time = time.time() - start_time
        assert load_time < 5.0

    def test_concurrent_operations(self, state_manager, sample_venues, sample_config):
        """Test thread safety of concurrent operations"""
        import threading

        results = []

        def create_session(index):
            try:
                session_id = state_manager.create_session(
                    target_venues=sample_venues,
                    target_years=[2023],
                    collection_config=sample_config,
                    session_id=f"concurrent_session_{index}",
                )
                results.append(session_id)
            except Exception as e:
                results.append(f"Error: {e}")

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_session, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all sessions were created successfully
        assert len(results) == 3
        for result in results:
            assert "concurrent_session_" in result
            assert not result.startswith("Error:")

    def test_session_validation(self, state_manager, sample_venues, sample_config):
        """Test session state validation"""
        # Create session
        session_id = state_manager.create_session(
            target_venues=sample_venues,
            target_years=[2023, 2024],
            collection_config=sample_config,
        )

        # Get session and validate
        session = state_manager._active_sessions[session_id]
        validation_results = state_manager._validate_session_state(session)

        assert len(validation_results) >= 2
        assert all(isinstance(result.passed, bool) for result in validation_results)
        assert all(
            isinstance(result.confidence, float) for result in validation_results
        )
        assert all(0.0 <= result.confidence <= 1.0 for result in validation_results)


if __name__ == "__main__":
    pytest.main([__file__])
