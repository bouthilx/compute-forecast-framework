"""
Checkpoint management for state persistence.
Handles checkpoint creation, validation, and cleanup.
"""

import logging
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import uuid

from .state_structures import (
    CheckpointData,
    CheckpointValidationResult,
    ValidationResult,
)
from .state_persistence import StatePersistence

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoint creation, validation, and lifecycle.
    Ensures checkpoint integrity and provides cleanup capabilities.
    """

    def __init__(
        self,
        persistence: StatePersistence,
        max_checkpoints_per_session: int = 1000,
        checkpoint_cleanup_interval: int = 100,
    ):
        """
        Initialize checkpoint manager.

        Args:
            persistence: StatePersistence instance for file operations
            max_checkpoints_per_session: Maximum checkpoints to keep per session
            checkpoint_cleanup_interval: Cleanup every N checkpoints
        """
        self.persistence = persistence
        self.max_checkpoints_per_session = max_checkpoints_per_session
        self.checkpoint_cleanup_interval = checkpoint_cleanup_interval
        self._lock = threading.RLock()
        self._checkpoint_counters: Dict[str, int] = {}

        logger.info(
            f"CheckpointManager initialized with max_checkpoints={max_checkpoints_per_session}"
        )

    def create_checkpoint(
        self,
        session_id: str,
        checkpoint_type: Literal[
            "venue_completed",
            "batch_completed",
            "api_call_completed",
            "error_occurred",
            "session_started",
        ],
        venues_completed: List[tuple],
        venues_in_progress: List[tuple],
        venues_not_started: List[tuple],
        papers_collected: int,
        papers_by_venue: Dict[str, Dict[int, int]],
        last_successful_operation: str,
        api_health_status: Optional[Dict] = None,
        rate_limit_status: Optional[Dict] = None,
        error_context: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Create a new checkpoint with validation.

        Args:
            session_id: Session identifier
            checkpoint_type: Type of checkpoint
            venues_completed: List of completed venue/year pairs
            venues_in_progress: List of in-progress venue/year pairs
            venues_not_started: List of not-started venue/year pairs
            papers_collected: Total papers collected
            papers_by_venue: Papers by venue and year
            last_successful_operation: Description of last operation
            api_health_status: Current API health status
            rate_limit_status: Current rate limit status
            error_context: Error context if checkpoint_type is "error_occurred"

        Returns:
            Checkpoint ID if successful, None otherwise
        """
        with self._lock:
            try:
                # Generate unique checkpoint ID
                checkpoint_id = self._generate_checkpoint_id(session_id)

                # Create checkpoint data
                checkpoint = CheckpointData(
                    checkpoint_id=checkpoint_id,
                    session_id=session_id,
                    checkpoint_type=checkpoint_type,
                    timestamp=datetime.now(),
                    venues_completed=venues_completed or [],
                    venues_in_progress=venues_in_progress or [],
                    venues_not_started=venues_not_started or [],
                    papers_collected=papers_collected,
                    papers_by_venue=papers_by_venue or {},
                    last_successful_operation=last_successful_operation,
                    api_health_status=api_health_status or {},
                    rate_limit_status=rate_limit_status or {},
                    error_context=error_context,
                )

                # Validate checkpoint data
                if not checkpoint.validate_integrity():
                    logger.error(f"Checkpoint validation failed for {checkpoint_id}")
                    return None

                # Save checkpoint
                checkpoint_path = self._get_checkpoint_path(session_id, checkpoint_id)
                success = self.persistence.save_state_atomic(
                    checkpoint_path, checkpoint, backup_previous=False
                )

                if success:
                    # Update checkpoint counter
                    self._checkpoint_counters[session_id] = (
                        self._checkpoint_counters.get(session_id, 0) + 1
                    )

                    # Cleanup old checkpoints if needed
                    if (
                        self._checkpoint_counters[session_id]
                        % self.checkpoint_cleanup_interval
                        == 0
                    ):
                        self._cleanup_old_checkpoints(session_id)

                    logger.debug(
                        f"Created checkpoint {checkpoint_id} for session {session_id}"
                    )
                    return checkpoint_id
                else:
                    logger.error(f"Failed to save checkpoint {checkpoint_id}")
                    return None

            except Exception as e:
                logger.error(f"Error creating checkpoint for session {session_id}: {e}")
                return None

    def load_checkpoint(
        self, session_id: str, checkpoint_id: str
    ) -> Optional[CheckpointData]:
        """
        Load a specific checkpoint.

        Args:
            session_id: Session identifier
            checkpoint_id: Checkpoint identifier

        Returns:
            CheckpointData if found and valid, None otherwise
        """
        try:
            checkpoint_path = self._get_checkpoint_path(session_id, checkpoint_id)
            checkpoint = self.persistence.load_state(
                checkpoint_path, CheckpointData, validate_integrity=True
            )

            if checkpoint and checkpoint.validate_integrity():
                return checkpoint
            else:
                logger.warning(f"Checkpoint {checkpoint_id} failed validation")
                return None

        except Exception as e:
            logger.error(f"Error loading checkpoint {checkpoint_id}: {e}")
            return None

    def load_latest_checkpoint(self, session_id: str) -> Optional[CheckpointData]:
        """
        Load the most recent valid checkpoint for a session.

        Args:
            session_id: Session identifier

        Returns:
            Most recent valid CheckpointData, or None if no valid checkpoints
        """
        try:
            checkpoints = self.list_checkpoints(session_id)

            if not checkpoints:
                logger.debug(f"No checkpoints found for session {session_id}")
                return None

            # Sort by timestamp (most recent first)
            checkpoints.sort(key=lambda x: x.timestamp, reverse=True)

            # Try to load the most recent valid checkpoint
            for checkpoint in checkpoints:
                if checkpoint.validation_status == "valid":
                    return checkpoint

            logger.warning(f"No valid checkpoints found for session {session_id}")
            return None

        except Exception as e:
            logger.error(
                f"Error loading latest checkpoint for session {session_id}: {e}"
            )
            return None

    def list_checkpoints(self, session_id: str) -> List[CheckpointData]:
        """
        List all checkpoints for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of CheckpointData objects
        """
        try:
            checkpoints_dir = self._get_checkpoints_dir(session_id)
            if not checkpoints_dir.exists():
                return []

            checkpoints = []
            checkpoint_files = list(checkpoints_dir.glob("checkpoint_*.json"))

            for checkpoint_file in checkpoint_files:
                checkpoint = self.persistence.load_state(
                    checkpoint_file,
                    CheckpointData,
                    validate_integrity=False,  # We'll validate after loading
                )

                if checkpoint:
                    # Validate integrity and update status
                    if checkpoint.validate_integrity():
                        checkpoint.validation_status = "valid"
                    else:
                        checkpoint.validation_status = "corrupted"

                    checkpoints.append(checkpoint)

            return checkpoints

        except Exception as e:
            logger.error(f"Error listing checkpoints for session {session_id}: {e}")
            return []

    def validate_checkpoint(
        self, session_id: str, checkpoint_id: str
    ) -> CheckpointValidationResult:
        """
        Validate a specific checkpoint and return detailed results.

        Args:
            session_id: Session identifier
            checkpoint_id: Checkpoint identifier

        Returns:
            Detailed validation result
        """
        try:
            checkpoint = self.load_checkpoint(session_id, checkpoint_id)

            if checkpoint is None:
                return CheckpointValidationResult(
                    checkpoint_id=checkpoint_id,
                    is_valid=False,
                    validation_errors=["Checkpoint could not be loaded"],
                    integrity_score=0.0,
                    can_be_used_for_recovery=False,
                )

            validation_errors = []
            integrity_score = 1.0

            # Data integrity check
            if not checkpoint.validate_integrity():
                validation_errors.append("Checksum validation failed")
                integrity_score -= 0.5

            # Data consistency checks
            total_venues = (
                len(checkpoint.venues_completed)
                + len(checkpoint.venues_in_progress)
                + len(checkpoint.venues_not_started)
            )
            if total_venues == 0:
                validation_errors.append("No venues specified in checkpoint")
                integrity_score -= 0.3

            # Papers count consistency
            papers_sum = sum(
                sum(year_counts.values())
                for year_counts in checkpoint.papers_by_venue.values()
            )
            if abs(papers_sum - checkpoint.papers_collected) > (
                checkpoint.papers_collected * 0.1
            ):
                validation_errors.append("Papers count inconsistency detected")
                integrity_score -= 0.2

            # Session ID consistency
            if checkpoint.session_id != session_id:
                validation_errors.append("Session ID mismatch")
                integrity_score -= 0.4

            is_valid = len(validation_errors) == 0
            can_be_used_for_recovery = integrity_score >= 0.5

            return CheckpointValidationResult(
                checkpoint_id=checkpoint_id,
                is_valid=is_valid,
                validation_errors=validation_errors,
                integrity_score=max(0.0, integrity_score),
                can_be_used_for_recovery=can_be_used_for_recovery,
            )

        except Exception as e:
            logger.error(f"Error validating checkpoint {checkpoint_id}: {e}")
            return CheckpointValidationResult(
                checkpoint_id=checkpoint_id,
                is_valid=False,
                validation_errors=[f"Validation error: {e}"],
                integrity_score=0.0,
                can_be_used_for_recovery=False,
            )

    def cleanup_session_checkpoints(
        self, session_id: str, keep_latest: int = 10
    ) -> int:
        """
        Clean up old checkpoints for a session, keeping the most recent ones.

        Args:
            session_id: Session identifier
            keep_latest: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints cleaned up
        """
        with self._lock:
            try:
                checkpoints = self.list_checkpoints(session_id)

                if len(checkpoints) <= keep_latest:
                    return 0

                # Sort by timestamp (oldest first)
                checkpoints.sort(key=lambda x: x.timestamp)

                # Identify checkpoints to remove (all except the most recent)
                checkpoints_to_remove = checkpoints[:-keep_latest]

                cleaned_count = 0
                for checkpoint in checkpoints_to_remove:
                    checkpoint_path = self._get_checkpoint_path(
                        session_id, checkpoint.checkpoint_id
                    )
                    try:
                        if checkpoint_path.exists():
                            checkpoint_path.unlink()
                            cleaned_count += 1

                        # Also remove metadata file if it exists
                        meta_path = checkpoint_path.with_suffix(
                            f"{checkpoint_path.suffix}.meta"
                        )
                        if meta_path.exists():
                            meta_path.unlink()

                    except Exception as e:
                        logger.warning(
                            f"Failed to remove checkpoint {checkpoint.checkpoint_id}: {e}"
                        )

                logger.info(
                    f"Cleaned up {cleaned_count} old checkpoints for session {session_id}"
                )
                return cleaned_count

            except Exception as e:
                logger.error(
                    f"Error cleaning up checkpoints for session {session_id}: {e}"
                )
                return 0

    def validate_session_checkpoints(self, session_id: str) -> List[ValidationResult]:
        """
        Validate all checkpoints for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of validation results
        """
        results = []
        checkpoints = self.list_checkpoints(session_id)

        for checkpoint in checkpoints:
            validation_result = self.validate_checkpoint(
                session_id, checkpoint.checkpoint_id
            )

            # Convert to ValidationResult format
            result = ValidationResult(
                validation_type="checkpoint_integrity",
                passed=validation_result.is_valid,
                confidence=validation_result.integrity_score,
                details=f"Checkpoint {checkpoint.checkpoint_id}: {'; '.join(validation_result.validation_errors) if validation_result.validation_errors else 'Valid'}",
                recommendations=[
                    "Consider recreating checkpoint"
                    if not validation_result.can_be_used_for_recovery
                    else "Checkpoint usable for recovery"
                ],
            )
            results.append(result)

        return results

    def _generate_checkpoint_id(self, session_id: str) -> str:
        """Generate unique checkpoint ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = str(uuid.uuid4())[:8]
        return f"checkpoint_{session_id}_{timestamp}_{unique_suffix}"

    def _get_checkpoints_dir(self, session_id: str) -> Path:
        """Get checkpoints directory for session"""
        return self.persistence.base_dir / "sessions" / session_id / "checkpoints"

    def _get_checkpoint_path(self, session_id: str, checkpoint_id: str) -> Path:
        """Get full path for checkpoint file"""
        return self._get_checkpoints_dir(session_id) / f"{checkpoint_id}.json"

    def _cleanup_old_checkpoints(self, session_id: str) -> None:
        """Automatic cleanup of old checkpoints"""
        try:
            if self.max_checkpoints_per_session > 0:
                self.cleanup_session_checkpoints(
                    session_id, self.max_checkpoints_per_session
                )
        except Exception as e:
            logger.warning(
                f"Automatic checkpoint cleanup failed for session {session_id}: {e}"
            )

    def get_checkpoint_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics about checkpoints for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with checkpoint statistics
        """
        try:
            checkpoints = self.list_checkpoints(session_id)

            if not checkpoints:
                return {
                    "total_checkpoints": 0,
                    "valid_checkpoints": 0,
                    "corrupted_checkpoints": 0,
                    "latest_checkpoint": None,
                    "earliest_checkpoint": None,
                    "checkpoint_types": {},
                }

            valid_count = sum(1 for c in checkpoints if c.validation_status == "valid")
            corrupted_count = len(checkpoints) - valid_count

            # Sort by timestamp
            checkpoints.sort(key=lambda x: x.timestamp)

            # Count checkpoint types
            checkpoint_types: Dict[str, int] = {}
            for checkpoint in checkpoints:
                checkpoint_types[checkpoint.checkpoint_type] = (
                    checkpoint_types.get(checkpoint.checkpoint_type, 0) + 1
                )

            return {
                "total_checkpoints": len(checkpoints),
                "valid_checkpoints": valid_count,
                "corrupted_checkpoints": corrupted_count,
                "latest_checkpoint": checkpoints[-1].checkpoint_id,
                "earliest_checkpoint": checkpoints[0].checkpoint_id,
                "checkpoint_types": checkpoint_types,
                "timespan_hours": (
                    checkpoints[-1].timestamp - checkpoints[0].timestamp
                ).total_seconds()
                / 3600,
            }

        except Exception as e:
            logger.error(
                f"Error getting checkpoint statistics for session {session_id}: {e}"
            )
            return {"error": str(e)}
