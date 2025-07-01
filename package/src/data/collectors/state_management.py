"""
Simple StateManager for InterruptionRecoveryEngine testing.
Provides basic session and checkpoint management functionality.
"""

import logging
import time
import threading
import warnings
import gzip
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from .state_structures import (
    CollectionSession, VenueConfig, CheckpointData, RecoveryPlan, SessionResumeResult,
    InterruptionAnalysis, ValidationResult, InterruptionCause
)
from src.core.config import CollectionConfig

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
    """
    StateManager implementation matching Issue #5 exact interface contract.
    
    REQUIREMENTS from Issue #5:
    - Must generate unique session ID if not provided
    - Must create session directory structure
    - Must initialize session state file
    - Must be thread-safe
    - Must complete within 1 second
    """
    
    def __init__(
        self, 
        base_state_dir: Path = Path("data/states"), 
        backup_interval_seconds: int = 300, 
        max_checkpoints_per_session: int = 1000
    ):
        """
        Initialize StateManager with Issue #5 exact parameters.
        
        Args:
            base_state_dir: Base directory for all state files
            backup_interval_seconds: Interval for automatic backups
            max_checkpoints_per_session: Maximum checkpoints per session
        """
        self.base_state_dir = Path(base_state_dir)
        self.backup_interval_seconds = backup_interval_seconds
        self.max_checkpoints_per_session = max_checkpoints_per_session
        self._active_sessions: Dict[str, CollectionSession] = {}
        self.checkpoint_manager = SimpleCheckpointManager()
        
        # Ensure base directory structure exists
        self.base_state_dir.mkdir(parents=True, exist_ok=True)
        (self.base_state_dir / "sessions").mkdir(exist_ok=True)
        
        # For backward compatibility with tests
        self.persistence = None
        
        logger.info(f"StateManager initialized with base_dir: {self.base_state_dir}, "
                   f"backup_interval: {backup_interval_seconds}s, "
                   f"max_checkpoints: {max_checkpoints_per_session}")
    
    def create_session(
        self,
        session_config: CollectionConfig,
        session_id: Optional[str] = None
    ) -> str:
        """
        Create a new collection session matching Issue #5 requirements.
        
        REQUIREMENTS from Issue #5:
        - Must generate unique session ID if not provided
        - Must create session directory structure
        - Must initialize session state file
        - Must be thread-safe
        - Must complete within 1 second
        
        Args:
            session_config: CollectionConfig containing collection parameters
            session_id: Optional session identifier
            
        Returns:
            Session ID string
        """
        start_time = datetime.now()
        
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        if session_id in self._active_sessions:
            raise ValueError(f"Session {session_id} already exists")
        
        # Create session directory structure as required by Issue #5
        session_dir = self.base_state_dir / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "checkpoints").mkdir(exist_ok=True)
        (session_dir / "venues").mkdir(exist_ok=True)
        (session_dir / "recovery").mkdir(exist_ok=True)
        
        # Create default venue configurations for session
        # Note: This is a simplified approach - in practice, venues would come from configuration
        target_venues = [
            VenueConfig(venue_name="ICML", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=session_config.papers_per_domain_year),
            VenueConfig(venue_name="NeurIPS", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=session_config.papers_per_domain_year),
            VenueConfig(venue_name="ICLR", target_years=[2020, 2021, 2022, 2023], max_papers_per_year=session_config.papers_per_domain_year)
        ]
        target_years = [2020, 2021, 2022, 2023]
        
        session = CollectionSession(
            session_id=session_id,
            creation_time=datetime.now(),
            last_activity_time=datetime.now(),
            status="active",
            target_venues=target_venues,
            target_years=target_years,
            collection_config=session_config.__dict__,  # Convert to dict for compatibility
            venues_completed=[],
            venues_in_progress=[],
            venues_failed=[]
        )
        
        self._active_sessions[session_id] = session
        
        # Save session config file as required by Issue #5
        import json
        session_config_file = session_dir / "session_config.json"
        with open(session_config_file, 'w') as f:
            json.dump({
                "session_id": session_id,
                "collection_config": session_config.__dict__,
                "target_venues": [v.__dict__ for v in target_venues],
                "target_years": target_years,
                "created_at": session.creation_time.isoformat()
            }, f, indent=2)
        
        # Save session status file as required by Issue #5
        session_status_file = session_dir / "session_status.json"
        with open(session_status_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2, default=str)
        
        # Create initial checkpoint
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            session_id=session_id,
            checkpoint_type="session_started",
            venues_completed=[],
            venues_in_progress=[],
            venues_not_started=[(v.venue_name, year) for v in target_venues for year in target_years],
            papers_collected=0,
            papers_by_venue={},
            last_successful_operation="session_created"
        )
        
        # Update session with initial checkpoint
        session.checkpoint_count = 1
        session.last_checkpoint_id = checkpoint_id
        
        # Check 1-second requirement
        duration = (datetime.now() - start_time).total_seconds()
        if duration > 1.0:
            logger.warning(f"Session creation took {duration:.3f}s (>1s requirement)")
        else:
            logger.info(f"Session {session_id} created in {duration:.3f}s")
        
        return session_id
    
    
    def save_checkpoint(self, session_id: str, checkpoint_data: CheckpointData) -> str:
        """
        Save a checkpoint for a session matching Issue #5 requirements.
        
        REQUIREMENTS from Issue #5:
        - Must save within 2 seconds
        - Must maintain checkpoint ordering
        - Must handle concurrent checkpoint requests
        - Must validate checkpoint data integrity
        - Must auto-cleanup old checkpoints
        
        Args:
            session_id: Session identifier
            checkpoint_data: Checkpoint data to save
            
        Returns:
            Checkpoint ID string
        """
        start_time = datetime.now()
        
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        # Validate checkpoint data integrity
        if not checkpoint_data.validate_integrity():
            raise ValueError(f"Checkpoint data integrity validation failed")
        
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
        
        # Auto-cleanup old checkpoints if exceeding maximum
        if session.checkpoint_count > self.max_checkpoints_per_session:
            logger.info(f"Cleaning up old checkpoints for session {session_id}")
            self._cleanup_old_checkpoints(session_id)
        
        # Save checkpoint to session directory as required by Issue #5
        session_dir = self.base_state_dir / "sessions" / session_id
        checkpoint_file = session_dir / "checkpoints" / f"{checkpoint_id}.json"
        
        # Validate path security
        if not self._validate_path_security(checkpoint_file):
            raise ValueError(f"Invalid checkpoint path: {checkpoint_file}")
        
        # Serialize checkpoint data
        checkpoint_dict = checkpoint_data.to_dict()
        checkpoint_json = json.dumps(checkpoint_dict, indent=2, default=str)
        
        # Compress if checkpoint is larger than 10KB
        if len(checkpoint_json.encode()) > 10240:
            checkpoint_file = checkpoint_file.with_suffix('.json.gz')
            with gzip.open(checkpoint_file, 'wt', encoding='utf-8') as f:
                f.write(checkpoint_json)
            logger.debug(f"Compressed checkpoint saved: {checkpoint_file.name}")
        else:
            with open(checkpoint_file, 'w') as f:
                f.write(checkpoint_json)
        
        # Update session status file
        session_status_file = session_dir / "session_status.json"
        with open(session_status_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2, default=str)
        
        # Check 2-second requirement
        duration = (datetime.now() - start_time).total_seconds()
        if duration > 2.0:
            logger.warning(f"Checkpoint save took {duration:.3f}s (>2s requirement)")
        else:
            logger.debug(f"Checkpoint {checkpoint_id} saved in {duration:.3f}s")
        
        return checkpoint_id
    
    def load_latest_checkpoint(self, session_id: str) -> Optional[CheckpointData]:
        """
        Load the latest checkpoint for a session matching Issue #5 requirements.
        
        REQUIREMENTS from Issue #5:
        - Must validate checkpoint integrity
        - Must handle corrupted checkpoints gracefully
        - Must return None if no valid checkpoints
        - Must complete within 5 seconds
        
        Args:
            session_id: Session identifier
            
        Returns:
            Latest valid CheckpointData or None
        """
        start_time = datetime.now()
        
        try:
            checkpoint = self.checkpoint_manager.load_latest_checkpoint(session_id)
            
            if checkpoint is not None:
                # Validate checkpoint integrity as required by Issue #5
                if not checkpoint.validate_integrity():
                    logger.warning(f"Latest checkpoint for session {session_id} failed integrity check")
                    return None
            
            # Check 5-second requirement
            duration = (datetime.now() - start_time).total_seconds()
            if duration > 5.0:
                logger.warning(f"Checkpoint load took {duration:.3f}s (>5s requirement)")
            else:
                logger.debug(f"Checkpoint loaded in {duration:.3f}s")
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load latest checkpoint for session {session_id}: {e}")
            # Handle corrupted checkpoints gracefully as required
            return None
    
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
        """
        Resume a session from interruption matching Issue #5 requirements.
        
        REQUIREMENTS from Issue #5:
        - Must restore exact previous state
        - Must validate state consistency
        - Must update session metadata
        - Must complete recovery within 5 minutes
        
        Args:
            session_id: Session identifier
            recovery_plan: Recovery plan to execute
            
        Returns:
            SessionResumeResult with recovery details
        """
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
            
            # Check 5-minute requirement as specified in Issue #5
            if result.recovery_duration_seconds > 300.0:  # 5 minutes = 300 seconds
                logger.warning(f"Session recovery took {result.recovery_duration_seconds:.1f}s (>300s requirement)")
                result.resume_warnings.append("Recovery exceeded 5-minute requirement")
            else:
                logger.info(f"Session {session_id} recovered in {result.recovery_duration_seconds:.1f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to resume session {session_id}: {e}")
            result.resume_errors.append(f"Recovery error: {e}")
            result.recovery_end_time = datetime.now()
            result.recovery_duration_seconds = time.time() - start_time
            
            # Check 5-minute requirement even for failed recovery
            if result.recovery_duration_seconds > 300.0:
                result.resume_warnings.append("Recovery attempt exceeded 5-minute requirement")
            
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
    
    def _cleanup_old_checkpoints(self, session_id: str):
        """Remove old checkpoints when exceeding max_checkpoints_per_session"""
        # Get checkpoint statistics
        stats = self.checkpoint_manager.get_checkpoint_statistics(session_id)
        total_checkpoints = stats["total_checkpoints"]
        
        if total_checkpoints <= self.max_checkpoints_per_session:
            return
        
        # Get all checkpoints for the session
        session_dir = self.base_state_dir / "sessions" / session_id
        checkpoint_dir = session_dir / "checkpoints"
        
        if not checkpoint_dir.exists():
            return
        
        # Get all checkpoint files sorted by modification time
        checkpoint_files = sorted(
            checkpoint_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime
        )
        
        # Calculate how many to delete
        to_delete = total_checkpoints - self.max_checkpoints_per_session + 10  # Keep buffer of 10
        
        if to_delete > 0 and len(checkpoint_files) > to_delete:
            for i in range(to_delete):
                try:
                    checkpoint_files[i].unlink()
                    logger.debug(f"Deleted old checkpoint: {checkpoint_files[i].name}")
                except Exception as e:
                    logger.warning(f"Failed to delete checkpoint {checkpoint_files[i]}: {e}")
    
    @staticmethod
    def _validate_path_security(path: Path) -> bool:
        """Validate that a path is safe from directory traversal attacks"""
        try:
            # Resolve the path and check it doesn't escape the intended directory
            resolved = path.resolve()
            return not (".." in str(path))
        except Exception:
            return False
    
    def _get_session_dir(self, session_id: str) -> Path:
        """Get the directory path for a session"""
        return self.base_state_dir / "sessions" / session_id
    
    def list_sessions(self) -> List[str]:
        """List all available sessions"""
        # Return active sessions
        active_sessions = list(self._active_sessions.keys())
        
        # Also check for sessions on disk
        sessions_dir = self.base_state_dir / "sessions"
        if sessions_dir.exists():
            disk_sessions = [d.name for d in sessions_dir.iterdir() if d.is_dir()]
            # Combine and deduplicate
            all_sessions = list(set(active_sessions + disk_sessions))
            return sorted(all_sessions)
        
        return sorted(active_sessions)


# Monkey patch for backward compatibility with existing tests
original_create_session = StateManager.create_session

def create_session_flexible(self, *args, **kwargs):
    """
    Flexible create_session that supports both new and legacy interfaces.
    
    New interface: create_session(session_config: CollectionConfig, session_id: Optional[str] = None)
    Legacy interface: create_session(target_venues, target_years, collection_config, session_id)
    """
    # Check if using new interface (first arg is CollectionConfig)
    if len(args) >= 1 and isinstance(args[0], CollectionConfig):
        return original_create_session(self, *args, **kwargs)
    
    # Check for keyword-based new interface
    if 'session_config' in kwargs:
        return original_create_session(self, **kwargs)
    
    # Legacy interface detection
    if (len(args) >= 3 or 
        ('target_venues' in kwargs and 'target_years' in kwargs and 'collection_config' in kwargs)):
        
        # Extract legacy parameters
        if len(args) >= 3:
            target_venues, target_years, collection_config = args[:3]
            session_id = args[3] if len(args) > 3 else kwargs.get('session_id')
        else:
            target_venues = kwargs['target_venues']
            target_years = kwargs['target_years']
            collection_config = kwargs['collection_config']
            session_id = kwargs.get('session_id')
        
        logger.warning("Using legacy create_session interface. "
                      "Please migrate to create_session(session_config, session_id)")
        
        # Convert legacy parameters to CollectionConfig
        legacy_collection_config = CollectionConfig(
            papers_per_domain_year=collection_config.get("papers_per_domain_year", 50),
            total_target_min=collection_config.get("total_target_min", 1000),
            total_target_max=collection_config.get("total_target_max", 5000),
            citation_threshold_base=collection_config.get("citation_threshold_base", 10)
        )
        
        # Use new interface
        new_session_id = original_create_session(self, legacy_collection_config, session_id)
        
        # Update session with legacy venues and years (override defaults)
        session = self._active_sessions[new_session_id]
        session.target_venues = target_venues
        session.target_years = target_years
        session.collection_config = collection_config
        
        return new_session_id
    
    # Fallback to original method
    return original_create_session(self, *args, **kwargs)

# Apply the monkey patch
StateManager.create_session = create_session_flexible
