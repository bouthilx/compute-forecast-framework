"""
Unit tests for CheckpointManager class.
Tests checkpoint creation, validation, and lifecycle management.
"""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path
from datetime import datetime

from compute_forecast.data.collectors.checkpoint_manager import CheckpointManager
from compute_forecast.data.collectors.state_persistence import StatePersistence
from compute_forecast.data.collectors.state_structures import (
    CheckpointData,
    ErrorContext,
    CheckpointValidationResult,
)
from compute_forecast.data.models import APIHealthStatus, RateLimitStatus

# Add package root to Python path
package_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(package_root))


class TestCheckpointManager:
    """Test CheckpointManager functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def persistence(self, temp_dir):
        """Create StatePersistence instance for testing"""
        return StatePersistence(temp_dir, enable_backups=True)

    @pytest.fixture
    def checkpoint_manager(self, persistence):
        """Create CheckpointManager instance for testing"""
        return CheckpointManager(
            persistence=persistence,
            max_checkpoints_per_session=10,
            checkpoint_cleanup_interval=5,
        )

    def test_checkpoint_manager_initialization(self, persistence):
        """Test CheckpointManager initialization"""
        manager = CheckpointManager(
            persistence=persistence,
            max_checkpoints_per_session=100,
            checkpoint_cleanup_interval=50,
        )

        assert manager.persistence == persistence
        assert manager.max_checkpoints_per_session == 100
        assert manager.checkpoint_cleanup_interval == 50
        assert isinstance(manager._checkpoint_counters, dict)

    def test_create_checkpoint_basic(self, checkpoint_manager):
        """Test basic checkpoint creation"""
        session_id = "test_session_001"

        checkpoint_id = checkpoint_manager.create_checkpoint(
            session_id=session_id,
            checkpoint_type="venue_completed",
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[("ICLR", 2024)],
            venues_not_started=[("NeurIPS", 2024)],
            papers_collected=150,
            papers_by_venue={"CVPR": {2023: 150}},
            last_successful_operation="cvpr_2023_completed",
        )

        assert checkpoint_id is not None
        assert session_id in checkpoint_id
        assert "checkpoint_" in checkpoint_id
        assert checkpoint_manager._checkpoint_counters[session_id] == 1

    def test_create_checkpoint_with_error_context(self, checkpoint_manager):
        """Test checkpoint creation with error context"""
        session_id = "test_session_002"

        error_context = ErrorContext(
            error_type="api_timeout",
            error_message="Request timed out",
            stack_trace="Traceback...",
            venue_context="CVPR",
            year_context=2023,
            retry_count=2,
        )

        checkpoint_id = checkpoint_manager.create_checkpoint(
            session_id=session_id,
            checkpoint_type="error_occurred",
            venues_completed=[],
            venues_in_progress=[("CVPR", 2023)],
            venues_not_started=[("ICLR", 2024)],
            papers_collected=50,
            papers_by_venue={"CVPR": {2023: 50}},
            last_successful_operation="cvpr_2023_partial",
            error_context=error_context,
        )

        assert checkpoint_id is not None

        # Verify error context is saved
        loaded_checkpoint = checkpoint_manager.load_checkpoint(
            session_id, checkpoint_id
        )
        assert loaded_checkpoint is not None
        assert loaded_checkpoint.error_context is not None
        assert loaded_checkpoint.error_context.error_type == "api_timeout"

    def test_create_checkpoint_with_api_status(self, checkpoint_manager):
        """Test checkpoint creation with API health and rate limit status"""
        session_id = "test_session_003"

        api_health = {
            "semantic_scholar": APIHealthStatus(
                api_name="semantic_scholar",
                status="healthy",
                success_rate=0.95,
                avg_response_time_ms=500.0,
                consecutive_errors=0,
            )
        }

        rate_limits = {
            "semantic_scholar": RateLimitStatus(
                api_name="semantic_scholar",
                requests_in_window=45,
                window_capacity=100,
                next_available_slot=datetime.now(),
                current_delay_seconds=1.0,
                health_multiplier=1.0,
            )
        }

        checkpoint_id = checkpoint_manager.create_checkpoint(
            session_id=session_id,
            checkpoint_type="api_call_completed",
            venues_completed=[],
            venues_in_progress=[("CVPR", 2023)],
            venues_not_started=[],
            papers_collected=25,
            papers_by_venue={"CVPR": {2023: 25}},
            last_successful_operation="api_call_successful",
            api_health_status=api_health,
            rate_limit_status=rate_limits,
        )

        assert checkpoint_id is not None

        # Verify API status is saved
        loaded_checkpoint = checkpoint_manager.load_checkpoint(
            session_id, checkpoint_id
        )
        assert loaded_checkpoint is not None
        assert "semantic_scholar" in loaded_checkpoint.api_health_status
        assert "semantic_scholar" in loaded_checkpoint.rate_limit_status

    def test_load_checkpoint(self, checkpoint_manager):
        """Test loading a specific checkpoint"""
        session_id = "test_session_004"

        # Create checkpoint first
        checkpoint_id = checkpoint_manager.create_checkpoint(
            session_id=session_id,
            checkpoint_type="batch_completed",
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[],
            venues_not_started=[("ICLR", 2024)],
            papers_collected=200,
            papers_by_venue={"CVPR": {2023: 200}},
            last_successful_operation="batch_processing_complete",
        )

        # Load the checkpoint
        loaded_checkpoint = checkpoint_manager.load_checkpoint(
            session_id, checkpoint_id
        )

        assert loaded_checkpoint is not None
        assert loaded_checkpoint.checkpoint_id == checkpoint_id
        assert loaded_checkpoint.session_id == session_id
        assert loaded_checkpoint.checkpoint_type == "batch_completed"
        assert loaded_checkpoint.papers_collected == 200
        assert loaded_checkpoint.venues_completed == [("CVPR", 2023)]

    def test_load_nonexistent_checkpoint(self, checkpoint_manager):
        """Test loading a non-existent checkpoint"""
        session_id = "test_session_005"
        fake_checkpoint_id = "nonexistent_checkpoint"

        loaded_checkpoint = checkpoint_manager.load_checkpoint(
            session_id, fake_checkpoint_id
        )

        assert loaded_checkpoint is None

    def test_load_latest_checkpoint(self, checkpoint_manager):
        """Test loading the most recent checkpoint"""
        session_id = "test_session_006"

        # Create multiple checkpoints
        checkpoint_ids = []
        for i in range(3):
            checkpoint_id = checkpoint_manager.create_checkpoint(
                session_id=session_id,
                checkpoint_type="venue_completed",
                venues_completed=[("CVPR", 2023)] if i > 0 else [],
                venues_in_progress=[("ICLR", 2024)] if i < 2 else [],
                venues_not_started=[("NeurIPS", 2024)] if i == 0 else [],
                papers_collected=50 * (i + 1),
                papers_by_venue={"CVPR": {2023: 50 * (i + 1)}} if i > 0 else {},
                last_successful_operation=f"operation_{i}",
            )
            checkpoint_ids.append(checkpoint_id)

        # Load latest checkpoint
        latest_checkpoint = checkpoint_manager.load_latest_checkpoint(session_id)

        assert latest_checkpoint is not None
        assert latest_checkpoint.checkpoint_id == checkpoint_ids[-1]
        assert latest_checkpoint.papers_collected == 150  # Last checkpoint

    def test_load_latest_checkpoint_no_checkpoints(self, checkpoint_manager):
        """Test loading latest checkpoint when none exist"""
        session_id = "empty_session"

        latest_checkpoint = checkpoint_manager.load_latest_checkpoint(session_id)

        assert latest_checkpoint is None

    def test_list_checkpoints(self, checkpoint_manager):
        """Test listing all checkpoints for a session"""
        session_id = "test_session_007"

        # Create multiple checkpoints
        checkpoint_ids = []
        for i in range(3):
            checkpoint_id = checkpoint_manager.create_checkpoint(
                session_id=session_id,
                checkpoint_type="venue_completed",
                venues_completed=[],
                venues_in_progress=[("CVPR", 2023)],
                venues_not_started=[],
                papers_collected=25 * (i + 1),
                papers_by_venue={"CVPR": {2023: 25 * (i + 1)}},
                last_successful_operation=f"operation_{i}",
            )
            checkpoint_ids.append(checkpoint_id)

        # List checkpoints
        checkpoints = checkpoint_manager.list_checkpoints(session_id)

        assert len(checkpoints) == 3
        assert all(isinstance(cp, CheckpointData) for cp in checkpoints)
        assert all(cp.session_id == session_id for cp in checkpoints)

        # Check that all created checkpoint IDs are present
        listed_ids = [cp.checkpoint_id for cp in checkpoints]
        for checkpoint_id in checkpoint_ids:
            assert checkpoint_id in listed_ids

    def test_list_checkpoints_empty_session(self, checkpoint_manager):
        """Test listing checkpoints for session with no checkpoints"""
        session_id = "empty_session"

        checkpoints = checkpoint_manager.list_checkpoints(session_id)

        assert checkpoints == []

    def test_validate_checkpoint(self, checkpoint_manager):
        """Test checkpoint validation"""
        session_id = "test_session_008"

        # Create a valid checkpoint
        checkpoint_id = checkpoint_manager.create_checkpoint(
            session_id=session_id,
            checkpoint_type="venue_completed",
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[],
            venues_not_started=[("ICLR", 2024)],
            papers_collected=100,
            papers_by_venue={"CVPR": {2023: 100}},
            last_successful_operation="venue_completed",
        )

        # Validate the checkpoint
        validation_result = checkpoint_manager.validate_checkpoint(
            session_id, checkpoint_id
        )

        assert isinstance(validation_result, CheckpointValidationResult)
        assert validation_result.checkpoint_id == checkpoint_id
        assert validation_result.is_valid is True
        assert validation_result.integrity_score >= 0.9
        assert validation_result.can_be_used_for_recovery is True
        assert len(validation_result.validation_errors) == 0

    def test_validate_nonexistent_checkpoint(self, checkpoint_manager):
        """Test validation of non-existent checkpoint"""
        session_id = "test_session_009"
        fake_checkpoint_id = "nonexistent_checkpoint"

        validation_result = checkpoint_manager.validate_checkpoint(
            session_id, fake_checkpoint_id
        )

        assert validation_result.is_valid is False
        assert validation_result.integrity_score == 0.0
        assert validation_result.can_be_used_for_recovery is False
        assert len(validation_result.validation_errors) > 0

    def test_cleanup_session_checkpoints(self, checkpoint_manager):
        """Test cleanup of old checkpoints"""
        session_id = "test_session_010"

        # Create many checkpoints
        checkpoint_ids = []
        for i in range(8):
            checkpoint_id = checkpoint_manager.create_checkpoint(
                session_id=session_id,
                checkpoint_type="venue_completed",
                venues_completed=[],
                venues_in_progress=[("CVPR", 2023)],
                venues_not_started=[],
                papers_collected=10 * (i + 1),
                papers_by_venue={"CVPR": {2023: 10 * (i + 1)}},
                last_successful_operation=f"operation_{i}",
            )
            checkpoint_ids.append(checkpoint_id)

        # Verify all checkpoints exist
        checkpoints_before = checkpoint_manager.list_checkpoints(session_id)
        assert len(checkpoints_before) == 8

        # Cleanup, keeping only 3 most recent
        cleaned_count = checkpoint_manager.cleanup_session_checkpoints(
            session_id, keep_latest=3
        )

        assert cleaned_count == 5  # Should remove 5 old checkpoints

        # Verify only 3 checkpoints remain
        checkpoints_after = checkpoint_manager.list_checkpoints(session_id)
        assert len(checkpoints_after) == 3

        # Verify the remaining checkpoints are the most recent ones
        remaining_ids = [cp.checkpoint_id for cp in checkpoints_after]
        for checkpoint_id in checkpoint_ids[-3:]:  # Last 3 created
            assert checkpoint_id in remaining_ids

    def test_automatic_cleanup_on_interval(self, persistence):
        """Test automatic cleanup when checkpoint interval is reached"""
        # Set a small cleanup interval for testing
        manager = CheckpointManager(
            persistence=persistence,
            max_checkpoints_per_session=3,
            checkpoint_cleanup_interval=2,  # Cleanup every 2 checkpoints
        )

        session_id = "test_session_011"

        # Create 6 checkpoints - should trigger cleanup at checkpoint 2, 4, 6
        for i in range(6):
            manager.create_checkpoint(
                session_id=session_id,
                checkpoint_type="venue_completed",
                venues_completed=[],
                venues_in_progress=[("CVPR", 2023)],
                venues_not_started=[],
                papers_collected=10 * (i + 1),
                papers_by_venue={"CVPR": {2023: 10 * (i + 1)}},
                last_successful_operation=f"operation_{i}",
            )

        # Should have triggered automatic cleanup multiple times, keeping max 3 checkpoints
        checkpoints = manager.list_checkpoints(session_id)
        assert len(checkpoints) <= 3

    def test_get_checkpoint_statistics(self, checkpoint_manager):
        """Test getting checkpoint statistics"""
        session_id = "test_session_012"

        # Create checkpoints of different types
        checkpoint_types = ["venue_completed", "batch_completed", "error_occurred"]
        for i, checkpoint_type in enumerate(checkpoint_types):
            checkpoint_manager.create_checkpoint(
                session_id=session_id,
                checkpoint_type=checkpoint_type,
                venues_completed=[],
                venues_in_progress=[("CVPR", 2023)],
                venues_not_started=[],
                papers_collected=10 * (i + 1),
                papers_by_venue={"CVPR": {2023: 10 * (i + 1)}},
                last_successful_operation=f"operation_{i}",
            )

        # Get statistics
        stats = checkpoint_manager.get_checkpoint_statistics(session_id)

        assert stats["total_checkpoints"] == 3
        assert stats["valid_checkpoints"] == 3
        assert stats["corrupted_checkpoints"] == 0
        assert stats["latest_checkpoint"] is not None
        assert stats["earliest_checkpoint"] is not None
        assert len(stats["checkpoint_types"]) == 3
        assert stats["checkpoint_types"]["venue_completed"] == 1
        assert stats["checkpoint_types"]["batch_completed"] == 1
        assert stats["checkpoint_types"]["error_occurred"] == 1

    def test_get_checkpoint_statistics_empty_session(self, checkpoint_manager):
        """Test getting statistics for session with no checkpoints"""
        session_id = "empty_session"

        stats = checkpoint_manager.get_checkpoint_statistics(session_id)

        assert stats["total_checkpoints"] == 0
        assert stats["valid_checkpoints"] == 0
        assert stats["corrupted_checkpoints"] == 0
        assert stats["latest_checkpoint"] is None
        assert stats["earliest_checkpoint"] is None
        assert stats["checkpoint_types"] == {}

    def test_validate_session_checkpoints(self, checkpoint_manager):
        """Test validating all checkpoints for a session"""
        session_id = "test_session_013"

        # Create multiple checkpoints
        for i in range(3):
            checkpoint_manager.create_checkpoint(
                session_id=session_id,
                checkpoint_type="venue_completed",
                venues_completed=[],
                venues_in_progress=[("CVPR", 2023)],
                venues_not_started=[],
                papers_collected=10 * (i + 1),
                papers_by_venue={"CVPR": {2023: 10 * (i + 1)}},
                last_successful_operation=f"operation_{i}",
            )

        # Validate all checkpoints
        validation_results = checkpoint_manager.validate_session_checkpoints(session_id)

        assert len(validation_results) == 3
        assert all(
            result.validation_type == "checkpoint_integrity"
            for result in validation_results
        )
        assert all(
            result.passed for result in validation_results
        )  # All should be valid
        assert all(result.confidence >= 0.9 for result in validation_results)


if __name__ == "__main__":
    pytest.main([__file__])
