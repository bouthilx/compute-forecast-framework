"""
Unit tests for state management data structures.
Following TDD approach - tests written before implementation.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path

import sys

# Add package root to Python path
package_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(package_root))

from compute_forecast.data.collectors.state_structures import (
    CheckpointData,
    ErrorContext,
    InterruptionAnalysis,
    InterruptionCause,
    RecoveryPlan,
    CollectionSession,
    VenueConfig,
    IntegrityCheckResult,
)


class TestCheckpointData:
    """Test CheckpointData structure and methods"""

    def test_checkpoint_creation(self):
        """Test basic checkpoint creation"""
        checkpoint = CheckpointData(
            checkpoint_id="chk_001",
            session_id="session_123",
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[("ICLR", 2024)],
            venues_not_started=[("NeurIPS", 2024)],
            papers_collected=150,
            papers_by_venue={"CVPR": {2023: 150}},
            last_successful_operation="venue_cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={},
        )

        assert checkpoint.checkpoint_id == "chk_001"
        assert checkpoint.session_id == "session_123"
        assert checkpoint.checkpoint_type == "venue_completed"
        assert checkpoint.papers_collected == 150
        assert checkpoint.venues_completed == [("CVPR", 2023)]

    def test_checksum_calculation(self):
        """Test automatic checksum calculation"""
        checkpoint = CheckpointData(
            checkpoint_id="chk_001",
            session_id="session_123",
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[],
            venues_not_started=[],
            papers_collected=150,
            papers_by_venue={"CVPR": {2023: 150}},
            last_successful_operation="venue_cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={},
        )

        # Checksum should be automatically calculated
        assert checkpoint.checksum != ""
        assert len(checkpoint.checksum) == 64  # SHA256 hex length

    def test_checksum_validation(self):
        """Test checksum validation for data integrity"""
        checkpoint = CheckpointData(
            checkpoint_id="chk_001",
            session_id="session_123",
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[],
            venues_not_started=[],
            papers_collected=150,
            papers_by_venue={"CVPR": {2023: 150}},
            last_successful_operation="venue_cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={},
        )

        # Initially valid
        assert checkpoint.validate_integrity() is True

        # Manually corrupt data
        checkpoint.papers_collected = 999
        assert checkpoint.validate_integrity() is False

        # Recalculate checksum
        checkpoint.checksum = checkpoint.calculate_checksum()
        assert checkpoint.validate_integrity() is True

    def test_checkpoint_serialization(self):
        """Test checkpoint serialization to/from dict"""
        timestamp = datetime.now()
        checkpoint = CheckpointData(
            checkpoint_id="chk_001",
            session_id="session_123",
            checkpoint_type="venue_completed",
            timestamp=timestamp,
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[],
            venues_not_started=[],
            papers_collected=150,
            papers_by_venue={"CVPR": {2023: 150}},
            last_successful_operation="venue_cvpr_2023_completed",
            api_health_status={},
            rate_limit_status={},
        )

        # Convert to dict
        checkpoint_dict = checkpoint.to_dict()

        # Verify structure
        assert checkpoint_dict["checkpoint_id"] == "chk_001"
        assert checkpoint_dict["session_id"] == "session_123"
        assert checkpoint_dict["timestamp"] == timestamp.isoformat()
        assert checkpoint_dict["papers_collected"] == 150

        # Should be JSON serializable
        json_str = json.dumps(checkpoint_dict)
        assert len(json_str) > 0


class TestErrorContext:
    """Test ErrorContext structure"""

    def test_error_context_creation(self):
        """Test creating error context"""
        error = ErrorContext(
            error_type="api_timeout",
            error_message="Request timed out after 30 seconds",
            stack_trace="Traceback...",
            venue_context="CVPR",
            year_context=2023,
            api_context="semantic_scholar",
            retry_count=2,
        )

        assert error.error_type == "api_timeout"
        assert error.venue_context == "CVPR"
        assert error.year_context == 2023
        assert error.retry_count == 2
        assert isinstance(error.timestamp, datetime)


class TestCollectionSession:
    """Test CollectionSession structure"""

    def test_session_creation(self):
        """Test creating a collection session"""
        venue_configs = [
            VenueConfig(
                venue_name="CVPR", target_years=[2023, 2024], max_papers_per_year=50
            ),
            VenueConfig(
                venue_name="ICLR", target_years=[2023, 2024], max_papers_per_year=40
            ),
        ]

        session = CollectionSession(
            session_id="session_123",
            creation_time=datetime.now(),
            last_activity_time=datetime.now(),
            status="active",
            target_venues=venue_configs,
            target_years=[2023, 2024],
            collection_config={"max_retries": 3},
            venues_completed=[],
            venues_in_progress=[("CVPR", 2023)],
            venues_failed=[],
        )

        assert session.session_id == "session_123"
        assert session.status == "active"
        assert len(session.target_venues) == 2
        assert session.venues_in_progress == [("CVPR", 2023)]
        assert session.total_papers_collected == 0  # Default value

    def test_venue_config(self):
        """Test VenueConfig structure"""
        venue = VenueConfig(
            venue_name="NeurIPS",
            target_years=[2022, 2023, 2024],
            max_papers_per_year=100,
            priority=1,
        )

        assert venue.venue_name == "NeurIPS"
        assert venue.target_years == [2022, 2023, 2024]
        assert venue.max_papers_per_year == 100
        assert venue.priority == 1


class TestInterruptionAnalysis:
    """Test InterruptionAnalysis structure"""

    def test_interruption_analysis_creation(self):
        """Test creating interruption analysis"""
        cause = InterruptionCause(
            cause_type="process_killed",
            confidence=0.9,
            evidence=["Process terminated signal received"],
            recovery_implications=["Need to check last checkpoint"],
        )

        analysis = InterruptionAnalysis(
            session_id="session_123",
            analysis_timestamp=datetime.now(),
            interruption_time=datetime.now() - timedelta(minutes=5),
            last_successful_operation="venue_cvpr_2023_batch_completed",
            last_checkpoint_id="chk_042",
            venues_definitely_completed=[("CVPR", 2023)],
            venues_possibly_incomplete=[("ICLR", 2024)],
            venues_unknown_status=[],
            venues_not_started=[("NeurIPS", 2024)],
            corrupted_checkpoints=[],
            missing_checkpoints=[],
            data_files_found=[Path("data/cvpr_2023.json")],
            data_files_corrupted=[],
            valid_checkpoints=["chk_041", "chk_042"],
            recovery_complexity="simple",
            blocking_issues=[],
            estimated_papers_collected=150,
            estimated_papers_lost=0,
            interruption_cause=cause,
            system_state_at_interruption={"memory_usage": "75%"},
        )

        assert analysis.session_id == "session_123"
        assert analysis.recovery_complexity == "simple"
        assert analysis.estimated_papers_collected == 150
        assert analysis.interruption_cause.cause_type == "process_killed"
        assert len(analysis.valid_checkpoints) == 2


class TestRecoveryPlan:
    """Test RecoveryPlan structure"""

    def test_recovery_plan_creation(self):
        """Test creating a recovery plan"""
        # Create dummy interruption analysis first
        cause = InterruptionCause(
            cause_type="process_killed",
            confidence=0.9,
            evidence=["Process terminated"],
            recovery_implications=["Check checkpoints"],
        )

        analysis = InterruptionAnalysis(
            session_id="session_123",
            analysis_timestamp=datetime.now(),
            interruption_time=datetime.now(),
            last_successful_operation="venue_completed",
            last_checkpoint_id="chk_042",
            venues_definitely_completed=[("CVPR", 2023)],
            venues_possibly_incomplete=[("ICLR", 2024)],
            venues_unknown_status=[],
            venues_not_started=[("NeurIPS", 2024)],
            corrupted_checkpoints=[],
            missing_checkpoints=[],
            data_files_found=[],
            data_files_corrupted=[],
            valid_checkpoints=["chk_042"],
            recovery_complexity="simple",
            blocking_issues=[],
            estimated_papers_collected=150,
            estimated_papers_lost=0,
            interruption_cause=cause,
            system_state_at_interruption={},
        )

        plan = RecoveryPlan(
            session_id="session_123",
            plan_id="recovery_001",
            created_at=datetime.now(),
            based_on_analysis=analysis,
            resumption_strategy="from_last_checkpoint",
            optimal_checkpoint_id="chk_042",
            venues_to_skip=[("CVPR", 2023)],
            venues_to_resume=[("ICLR", 2024)],
            venues_to_restart=[],
            venues_to_validate=[],
            checkpoints_to_restore=["chk_042"],
            data_files_to_recover=[],
            corrupted_data_to_discard=[],
            estimated_recovery_time_minutes=2.5,
            estimated_papers_to_recover=50,
            data_loss_estimate=0,
            confidence_score=0.95,
            recovery_confidence=0.9,
            recommended_validation_steps=["Verify checkpoint integrity"],
            risk_assessment=["Low risk - clean checkpoint available"],
        )

        assert plan.session_id == "session_123"
        assert plan.resumption_strategy == "from_last_checkpoint"
        assert plan.estimated_recovery_time_minutes == 2.5
        assert plan.confidence_score == 0.95
        assert len(plan.venues_to_skip) == 1


# DataIntegrityAssessment class no longer exists in state_structures
# class TestDataIntegrityAssessment:
#     """Test DataIntegrityAssessment structure"""

#     def test_data_integrity_assessment(self):
#         """Test creating data integrity assessment"""
#         assessment = DataIntegrityAssessment(
#             session_id="session_123",
#             assessment_time=datetime.now(),
#             total_data_files=10,
#             valid_data_files=9,
#             corrupted_data_files=1,
#             missing_data_files=0,
#             total_checkpoints=50,
#             valid_checkpoints=48,
#             corrupted_checkpoints=2,
#             venue_data_consistency={"CVPR": True, "ICLR": False},
#             paper_count_consistency=True,
#             timestamp_consistency=True,
#             data_loss_severity="minimal",
#             recovery_feasibility="simple",
#             estimated_recovery_time_minutes=3.0,
#         )
#
#         assert assessment.session_id == "session_123"
#         assert assessment.total_data_files == 10
#         assert assessment.valid_data_files == 9
#         assert assessment.data_loss_severity == "minimal"
#         assert assessment.recovery_feasibility == "simple"
#         assert assessment.venue_data_consistency["CVPR"] is True
#         assert assessment.venue_data_consistency["ICLR"] is False


class TestIntegrityCheckResult:
    """Test IntegrityCheckResult structure"""

    def test_integrity_check_result(self):
        """Test creating integrity check result"""
        result = IntegrityCheckResult(
            file_path=Path("data/cvpr_2023.json"),
            integrity_status="valid",
            checksum_valid=True,
            size_expected=1024,
            size_actual=1024,
            last_modified=datetime.now(),
            recovery_action=None,
        )

        assert result.file_path == Path("data/cvpr_2023.json")
        assert result.integrity_status == "valid"
        assert result.checksum_valid is True
        assert result.size_expected == result.size_actual
        assert result.recovery_action is None


if __name__ == "__main__":
    pytest.main([__file__])
