"""
Simple StateManager for InterruptionRecoveryEngine testing.
Provides basic session and checkpoint management functionality.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from .state_structures import (
    CollectionSession, VenueConfig, CheckpointData, RecoveryPlan, SessionResumeResult,
    InterruptionAnalysis, ValidationResult, InterruptionCause
)

logger = logging.getLogger(__name__)


class SimpleCheckpointManager:
    """Simplified checkpoint manager for testing"""
    
    def __init__(self):
        self._checkpoints: Dict[str, Dict[str, CheckpointData]] = {}  # session_id -> checkpoint_id -> checkpoint
    
    def create_checkpoint(
        self,
        session_id: str,
        checkpoint_type: str,
        venues_completed: List[tuple],
        venues_in_progress: List[tuple],
        venues_not_started: List[tuple],
        papers_collected: int,
        papers_by_venue: Dict[str, Dict[int, int]],
        last_successful_operation: str,
        api_health_status: Dict = None,
        rate_limit_status: Dict = None,
        error_context=None
    ) -> Optional[str]:
        """Create a new checkpoint"""
        checkpoint_id = f"{session_id}_checkpoint_{int(time.time())}"
        
        checkpoint = CheckpointData(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            checkpoint_type=checkpoint_type,
            timestamp=datetime.now(),
            venues_completed=venues_completed,
            venues_in_progress=venues_in_progress,
            venues_not_started=venues_not_started,
            papers_collected=papers_collected,
            papers_by_venue=papers_by_venue,
            last_successful_operation=last_successful_operation,
            api_health_status=api_health_status or {},
            rate_limit_status=rate_limit_status or {},
            error_context=error_context
        )
        
        if session_id not in self._checkpoints:
            self._checkpoints[session_id] = {}
        
        self._checkpoints[session_id][checkpoint_id] = checkpoint
        return checkpoint_id
    
    def load_checkpoint(self, session_id: str, checkpoint_id: str) -> Optional[CheckpointData]:
        """Load a specific checkpoint"""
        return self._checkpoints.get(session_id, {}).get(checkpoint_id)
    
    def load_latest_checkpoint(self, session_id: str) -> Optional[CheckpointData]:
        """Load the latest checkpoint for a session"""
        session_checkpoints = self._checkpoints.get(session_id, {})
        if not session_checkpoints:
            return None
        
        # Return the most recent checkpoint
        latest_checkpoint = max(session_checkpoints.values(), key=lambda cp: cp.timestamp)
        return latest_checkpoint
    
    def validate_checkpoint(self, session_id: str, checkpoint_id: str):
        """Validate a checkpoint"""
        from .state_structures import CheckpointValidationResult
        
        checkpoint = self.load_checkpoint(session_id, checkpoint_id)
        if not checkpoint:
            return CheckpointValidationResult(
                checkpoint_id=checkpoint_id,
                is_valid=False,
                validation_errors=["Checkpoint not found"],
                integrity_score=0.0,
                can_be_used_for_recovery=False
            )
        
        is_valid = checkpoint.validate_integrity()
        return CheckpointValidationResult(
            checkpoint_id=checkpoint_id,
            is_valid=is_valid,
            validation_errors=[] if is_valid else ["Integrity check failed"],
            integrity_score=1.0 if is_valid else 0.0,
            can_be_used_for_recovery=is_valid
        )
    
    def get_checkpoint_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get checkpoint statistics for a session"""
        session_checkpoints = self._checkpoints.get(session_id, {})
        
        if not session_checkpoints:
            return {
                "total_checkpoints": 0,
                "valid_checkpoints": 0,
                "corrupted_checkpoints": 0,
                "latest_checkpoint": None,
                "earliest_checkpoint": None,
                "checkpoint_types": {}
            }
        
        checkpoints = list(session_checkpoints.values())
        valid_count = sum(1 for cp in checkpoints if cp.validate_integrity())
        
        latest = max(checkpoints, key=lambda cp: cp.timestamp)
        earliest = min(checkpoints, key=lambda cp: cp.timestamp)
        
        # Count checkpoint types
        type_counts = {}
        for cp in checkpoints:
            type_counts[cp.checkpoint_type] = type_counts.get(cp.checkpoint_type, 0) + 1
        
        return {
            "total_checkpoints": len(checkpoints),
            "valid_checkpoints": valid_count,
            "corrupted_checkpoints": len(checkpoints) - valid_count,
            "latest_checkpoint": latest.checkpoint_id,
            "earliest_checkpoint": earliest.checkpoint_id,
            "checkpoint_types": type_counts
        }


class StateManager:
    """Simplified StateManager for testing InterruptionRecoveryEngine"""
    
    def __init__(self, base_state_dir: Path = Path("test_states"), **kwargs):
        self.base_state_dir = Path(base_state_dir)
        self._active_sessions: Dict[str, CollectionSession] = {}
        self.checkpoint_manager = SimpleCheckpointManager()
        
        # Ensure directory exists
        self.base_state_dir.mkdir(parents=True, exist_ok=True)
    
    def create_session(
        self,
        target_venues: List[VenueConfig],
        target_years: List[int],
        collection_config: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """Create a new collection session"""
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        if session_id in self._active_sessions:
            raise ValueError(f"Session {session_id} already exists")
        
        session = CollectionSession(
            session_id=session_id,
            creation_time=datetime.now(),
            last_activity_time=datetime.now(),
            status="active",
            target_venues=target_venues,
            target_years=target_years,
            collection_config=collection_config,
            venues_completed=[],
            venues_in_progress=[],
            venues_failed=[]
        )
        
        self._active_sessions[session_id] = session
        
        # Create initial checkpoint
        self.checkpoint_manager.create_checkpoint(
            session_id=session_id,
            checkpoint_type="session_started",
            venues_completed=[],
            venues_in_progress=[],
            venues_not_started=[(v.venue_name, year) for v in target_venues for year in target_years],
            papers_collected=0,
            papers_by_venue={},
            last_successful_operation="session_created"
        )
        
        return session_id
    
    def save_checkpoint(self, session_id: str, checkpoint_data: CheckpointData) -> str:
        """Save a checkpoint for a session"""
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            session_id=checkpoint_data.session_id,
            checkpoint_type=checkpoint_data.checkpoint_type,
            venues_completed=checkpoint_data.venues_completed,
            venues_in_progress=checkpoint_data.venues_in_progress,
            venues_not_started=checkpoint_data.venues_not_started,
            papers_collected=checkpoint_data.papers_collected,
            papers_by_venue=checkpoint_data.papers_by_venue,
            last_successful_operation=checkpoint_data.last_successful_operation,
            api_health_status=checkpoint_data.api_health_status,
            rate_limit_status=checkpoint_data.rate_limit_status,
            error_context=checkpoint_data.error_context
        )
        
        # Update session
        session = self._active_sessions[session_id]
        session.last_checkpoint_id = checkpoint_id
        session.checkpoint_count += 1
        session.last_activity_time = datetime.now()
        session.venues_completed = checkpoint_data.venues_completed
        session.venues_in_progress = checkpoint_data.venues_in_progress
        session.total_papers_collected = checkpoint_data.papers_collected
        session.papers_by_venue = checkpoint_data.papers_by_venue
        
        return checkpoint_id
    
    def load_latest_checkpoint(self, session_id: str) -> Optional[CheckpointData]:
        """Load the latest checkpoint for a session"""
        return self.checkpoint_manager.load_latest_checkpoint(session_id)
    
    def get_recovery_plan(self, session_id: str) -> RecoveryPlan:
        """Generate a recovery plan for a session"""
        session = self.get_session_status(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        latest_checkpoint = self.load_latest_checkpoint(session_id)
        
        # Create simplified interruption analysis
        interruption_analysis = InterruptionAnalysis(
            session_id=session_id,
            analysis_timestamp=datetime.now(),
            interruption_time=session.last_activity_time,
            last_successful_operation=latest_checkpoint.last_successful_operation if latest_checkpoint else "unknown",
            last_checkpoint_id=latest_checkpoint.checkpoint_id if latest_checkpoint else "",
            venues_definitely_completed=session.venues_completed,
            venues_possibly_incomplete=session.venues_in_progress,
            venues_unknown_status=[],
            venues_not_started=[],
            corrupted_checkpoints=[],
            missing_checkpoints=[],
            data_files_found=[],
            data_files_corrupted=[],
            valid_checkpoints=[latest_checkpoint.checkpoint_id] if latest_checkpoint else [],
            recovery_complexity="simple" if latest_checkpoint else "complex",
            blocking_issues=[],
            estimated_papers_collected=session.total_papers_collected,
            estimated_papers_lost=0,
            interruption_cause=InterruptionCause(
                cause_type="unknown",
                confidence=0.5,
                evidence=[],
                recovery_implications=[]
            ),
            system_state_at_interruption={}
        )
        
        recovery_plan = RecoveryPlan(
            session_id=session_id,
            plan_id=f"recovery_{session_id}_{int(time.time())}",
            created_at=datetime.now(),
            based_on_analysis=interruption_analysis,
            resumption_strategy="from_last_checkpoint" if latest_checkpoint else "full_restart",
            optimal_checkpoint_id=latest_checkpoint.checkpoint_id if latest_checkpoint else None,
            venues_to_skip=session.venues_completed,
            venues_to_resume=session.venues_in_progress,
            venues_to_restart=[],
            venues_to_validate=[],
            checkpoints_to_restore=[latest_checkpoint.checkpoint_id] if latest_checkpoint else [],
            data_files_to_recover=[],
            corrupted_data_to_discard=[],
            estimated_recovery_time_minutes=2.0 if latest_checkpoint else 10.0,
            estimated_papers_to_recover=len(session.venues_in_progress) * 50,
            data_loss_estimate=0,
            confidence_score=0.9 if latest_checkpoint else 0.6,
            recovery_confidence=0.95 if latest_checkpoint else 0.7,
            recommended_validation_steps=["Verify checkpoint integrity"],
            risk_assessment=["Low risk"] if latest_checkpoint else ["Medium risk - no checkpoints"]
        )
        
        return recovery_plan
    
    def resume_session(self, session_id: str, recovery_plan: RecoveryPlan) -> SessionResumeResult:
        """Resume a session from interruption"""
        start_time = time.time()
        
        result = SessionResumeResult(
            session_id=session_id,
            plan_id=recovery_plan.plan_id,
            success=False,
            recovery_start_time=datetime.fromtimestamp(start_time),
            recovery_end_time=datetime.fromtimestamp(start_time),
            recovery_duration_seconds=0.0,
            checkpoints_recovered=0,
            papers_recovered=0,
            venues_recovered=0,
            data_files_recovered=0,
            recovery_steps_executed=[],
            recovery_steps_failed=[],
            data_integrity_checks=[],
            state_consistency_validated=False,
            checkpoint_validation_results=[]
        )
        
        try:
            # Load or get session
            session = self.get_session_status(session_id)
            if not session:
                result.resume_errors.append(f"Session {session_id} not found")
                return result
            
            # Restore from checkpoint if available
            if recovery_plan.optimal_checkpoint_id:
                checkpoint = self.checkpoint_manager.load_checkpoint(
                    session_id, recovery_plan.optimal_checkpoint_id
                )
                
                if checkpoint:
                    # Restore session state from checkpoint
                    session.venues_completed = checkpoint.venues_completed
                    session.venues_in_progress = checkpoint.venues_in_progress
                    session.total_papers_collected = checkpoint.papers_collected
                    session.papers_by_venue = checkpoint.papers_by_venue
                    session.last_checkpoint_id = checkpoint.checkpoint_id
                    session.status = "active"
                    session.last_activity_time = datetime.now()
                    
                    result.checkpoints_recovered = 1
                    result.papers_recovered = checkpoint.papers_collected
                    result.venues_recovered = len(checkpoint.venues_completed) + len(checkpoint.venues_in_progress)
                    result.recovery_steps_executed.append("Restored from checkpoint")
                else:
                    result.resume_errors.append("Failed to load checkpoint")
            
            # Add session to active sessions
            self._active_sessions[session_id] = session
            result.session_state_after_recovery = session
            
            # Validate consistency
            validation_results = self._validate_session_state(session)
            result.state_consistency_validated = all(v.passed for v in validation_results)
            
            # Update result
            result.success = len(result.resume_errors) == 0
            result.ready_for_continuation = result.success and result.state_consistency_validated
            
            end_time = time.time()
            result.recovery_end_time = datetime.fromtimestamp(end_time)
            result.recovery_duration_seconds = end_time - start_time
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to resume session {session_id}: {e}")
            result.resume_errors.append(f"Recovery error: {e}")
            result.recovery_end_time = datetime.now()
            result.recovery_duration_seconds = time.time() - start_time
            return result
    
    def get_session_status(self, session_id: str) -> Optional[CollectionSession]:
        """Get current status of a session"""
        return self._active_sessions.get(session_id)
    
    def _validate_session_state(self, session: CollectionSession) -> List[ValidationResult]:
        """Validate session state consistency"""
        results = []
        
        # Check venue state consistency
        all_venues = set(session.venues_completed + session.venues_in_progress + session.venues_failed)
        expected_venues = set((v.venue_name, year) for v in session.target_venues for year in session.target_years)
        
        venue_consistency = len(all_venues - expected_venues) == 0
        results.append(ValidationResult(
            validation_type="venue_consistency",
            passed=venue_consistency,
            confidence=1.0 if venue_consistency else 0.0,
            details="All venues match configuration" if venue_consistency else "Venue mismatch detected",
            recommendations=[] if venue_consistency else ["Review venue configuration"]
        ))
        
        # Check papers count consistency
        papers_sum = sum(sum(year_counts.values()) for year_counts in session.papers_by_venue.values())
        papers_consistency = abs(papers_sum - session.total_papers_collected) <= (session.total_papers_collected * 0.1)
        results.append(ValidationResult(
            validation_type="papers_count_consistency",
            passed=papers_consistency,
            confidence=0.9 if papers_consistency else 0.3,
            details=f"Papers count: {session.total_papers_collected}, Sum: {papers_sum}",
            recommendations=[] if papers_consistency else ["Recalculate paper counts"]
        ))
        
        return results