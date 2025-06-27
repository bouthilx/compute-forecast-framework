"""
Main StateManager class for hierarchical state management.
Orchestrates checkpoint management, session lifecycle, and recovery operations.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from .state_structures import (
    CollectionSession, VenueConfig, CheckpointData, RecoveryPlan, SessionResumeResult,
    InterruptionAnalysis, ValidationResult
)
from .state_persistence import StatePersistence
from .checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)


class StateManager:
    """
    Main state management system for paper collection sessions.
    Provides session lifecycle, checkpointing, and recovery capabilities.
    """
    
    def __init__(
        self,
        base_state_dir: Path = Path("data/states"),
        backup_interval_seconds: int = 300,
        max_checkpoints_per_session: int = 1000
    ):
        """
        Initialize StateManager.
        
        Args:
            base_state_dir: Base directory for state storage
            backup_interval_seconds: Interval for automatic backups
            max_checkpoints_per_session: Maximum checkpoints to keep per session
        """
        self.base_state_dir = Path(base_state_dir)
        self.backup_interval_seconds = backup_interval_seconds
        self.max_checkpoints_per_session = max_checkpoints_per_session
        self._lock = threading.RLock()
        self._active_sessions: Dict[str, CollectionSession] = {}
        
        # Initialize components
        self.persistence = StatePersistence(base_state_dir, enable_backups=True)
        self.checkpoint_manager = CheckpointManager(
            persistence=self.persistence,
            max_checkpoints_per_session=max_checkpoints_per_session
        )
        
        # Ensure base directory structure exists
        self._initialize_directory_structure()
        
        logger.info(f"StateManager initialized with base_dir: {self.base_state_dir}")
    
    def create_session(
        self,
        target_venues: List[VenueConfig],
        target_years: List[int],
        collection_config: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """
        Create a new collection session.
        
        Requirements:
        - Must generate unique session ID if not provided
        - Must create session directory structure
        - Must initialize session state file
        - Must be thread-safe
        - Must complete within 1 second
        
        Args:
            target_venues: List of venues to collect from
            target_years: Years to collect papers from
            collection_config: Collection configuration
            session_id: Optional session ID, generated if not provided
            
        Returns:
            Session ID
        """
        with self._lock:
            start_time = time.time()
            
            try:
                # Generate session ID if not provided
                if session_id is None:
                    session_id = self._generate_session_id()
                
                # Check if session already exists
                if session_id in self._active_sessions:
                    raise ValueError(f"Session {session_id} already exists")
                
                # Create session object
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
                
                # Create session directory structure
                session_dir = self._get_session_dir(session_id)
                session_dir.mkdir(parents=True, exist_ok=True)
                (session_dir / "checkpoints").mkdir(exist_ok=True)
                (session_dir / "venues").mkdir(exist_ok=True)
                (session_dir / "recovery").mkdir(exist_ok=True)
                
                # Save session state
                session_file = session_dir / "session.json"
                success = self.persistence.save_state_atomic(session_file, session)
                
                if not success:
                    raise RuntimeError(f"Failed to save session state for {session_id}")
                
                # Add to active sessions
                self._active_sessions[session_id] = session
                
                # Create initial checkpoint
                initial_checkpoint_id = self.checkpoint_manager.create_checkpoint(
                    session_id=session_id,
                    checkpoint_type="session_started",
                    venues_completed=[],
                    venues_in_progress=[],
                    venues_not_started=[(v.venue_name, year) 
                                       for v in target_venues for year in target_years],
                    papers_collected=0,
                    papers_by_venue={},
                    last_successful_operation="session_created"
                )
                
                if initial_checkpoint_id:
                    session.last_checkpoint_id = initial_checkpoint_id
                    session.checkpoint_count = 1
                    # Update session file with checkpoint info
                    self.persistence.save_state_atomic(session_file, session)
                
                duration = time.time() - start_time
                logger.info(f"Created session {session_id} in {duration:.3f}s")
                
                # Check 1-second requirement
                if duration > 1.0:
                    logger.warning(f"Session creation took {duration:.3f}s (>1s requirement)")
                
                return session_id
                
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                raise
    
    def save_checkpoint(
        self,
        session_id: str,
        checkpoint_data: CheckpointData
    ) -> str:
        """
        Save a checkpoint for a session.
        
        Requirements:
        - Must save within 2 seconds
        - Must maintain checkpoint ordering
        - Must handle concurrent checkpoint requests
        - Must validate checkpoint data integrity
        - Must auto-cleanup old checkpoints
        
        Args:
            session_id: Session identifier
            checkpoint_data: Checkpoint data to save
            
        Returns:
            Checkpoint ID if successful
        """
        with self._lock:
            start_time = time.time()
            
            try:
                # Validate session exists
                if session_id not in self._active_sessions:
                    session = self._load_session(session_id)
                    if session is None:
                        raise ValueError(f"Session {session_id} not found")
                    self._active_sessions[session_id] = session
                
                # Save checkpoint using checkpoint manager
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
                
                if checkpoint_id:
                    # Update session with checkpoint info
                    session = self._active_sessions[session_id]
                    session.last_checkpoint_id = checkpoint_id
                    session.checkpoint_count += 1
                    session.last_activity_time = datetime.now()
                    
                    # Update session data from checkpoint
                    session.venues_completed = checkpoint_data.venues_completed
                    session.venues_in_progress = checkpoint_data.venues_in_progress
                    session.total_papers_collected = checkpoint_data.papers_collected
                    session.papers_by_venue = checkpoint_data.papers_by_venue
                    
                    # Save updated session
                    session_file = self._get_session_dir(session_id) / "session.json"
                    self.persistence.save_state_atomic(session_file, session)
                
                duration = time.time() - start_time
                logger.debug(f"Saved checkpoint {checkpoint_id} in {duration:.3f}s")
                
                # Check 2-second requirement
                if duration > 2.0:
                    logger.warning(f"Checkpoint save took {duration:.3f}s (>2s requirement)")
                
                return checkpoint_id
                
            except Exception as e:
                logger.error(f"Failed to save checkpoint for session {session_id}: {e}")
                raise
    
    def load_latest_checkpoint(self, session_id: str) -> Optional[CheckpointData]:
        """
        Load the latest checkpoint for a session.
        
        Requirements:
        - Must validate checkpoint integrity
        - Must handle corrupted checkpoints gracefully
        - Must return None if no valid checkpoints
        - Must complete within 5 seconds
        
        Args:
            session_id: Session identifier
            
        Returns:
            Latest valid checkpoint or None
        """
        start_time = time.time()
        
        try:
            checkpoint = self.checkpoint_manager.load_latest_checkpoint(session_id)
            
            duration = time.time() - start_time
            logger.debug(f"Loaded latest checkpoint for {session_id} in {duration:.3f}s")
            
            # Check 5-second requirement
            if duration > 5.0:
                logger.warning(f"Checkpoint load took {duration:.3f}s (>5s requirement)")
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load latest checkpoint for session {session_id}: {e}")
            return None
    
    def get_recovery_plan(self, session_id: str) -> RecoveryPlan:
        """
        Analyze session and create recovery plan.
        
        Requirements:
        - Must analyze all checkpoints and venue states
        - Must calculate optimal resumption point
        - Must estimate recovery time
        - Must identify data loss (if any)
        
        Args:
            session_id: Session identifier
            
        Returns:
            Recovery plan for the session
        """
        try:
            # This is a simplified recovery plan creation
            # In a full implementation, this would use the RecoveryEngine
            
            # Load session
            session = self._load_session(session_id)
            if session is None:
                raise ValueError(f"Session {session_id} not found")
            
            # Get latest checkpoint
            latest_checkpoint = self.load_latest_checkpoint(session_id)
            
            # Get checkpoint statistics
            checkpoint_stats = self.checkpoint_manager.get_checkpoint_statistics(session_id)
            
            # Create simplified recovery plan
            from .state_structures import InterruptionCause
            
            # Dummy interruption analysis for now
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
            
        except Exception as e:
            logger.error(f"Failed to create recovery plan for session {session_id}: {e}")
            raise
    
    def resume_session(self, session_id: str, recovery_plan: RecoveryPlan) -> SessionResumeResult:
        """
        Resume a session from interruption.
        
        Requirements:
        - Must restore exact previous state
        - Must validate state consistency
        - Must update session metadata
        - Must complete recovery within 5 minutes
        
        Args:
            session_id: Session identifier
            recovery_plan: Recovery plan to execute
            
        Returns:
            Session resume result
        """
        start_time = time.time()
        
        try:
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
            
            # Load session
            session = self._load_session(session_id)
            if session is None:
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
            
            # Save updated session
            session_file = self._get_session_dir(session_id) / "session.json"
            if self.persistence.save_state_atomic(session_file, session):
                result.recovery_steps_executed.append("Updated session state")
            else:
                result.resume_errors.append("Failed to save session state")
            
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
            
            # Check 5-minute requirement
            if result.recovery_duration_seconds > 300:
                logger.warning(f"Recovery took {result.recovery_duration_seconds:.1f}s (>300s requirement)")
            
            logger.info(f"Session {session_id} recovery {'successful' if result.success else 'failed'}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to resume session {session_id}: {e}")
            result.resume_errors.append(f"Recovery error: {e}")
            result.recovery_end_time = datetime.now()
            result.recovery_duration_seconds = time.time() - start_time
            return result
    
    def get_session_status(self, session_id: str) -> Optional[CollectionSession]:
        """
        Get current status of a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object if found, None otherwise
        """
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        
        return self._load_session(session_id)
    
    def list_sessions(self) -> List[str]:
        """
        List all available sessions.
        
        Returns:
            List of session IDs
        """
        try:
            sessions_dir = self.base_state_dir / "sessions"
            if not sessions_dir.exists():
                return []
            
            session_dirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
            return [d.name for d in session_dirs]
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """
        Clean up old sessions and their checkpoints.
        
        Args:
            max_age_days: Maximum age in days before cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            cleaned_count = 0
            
            for session_id in self.list_sessions():
                session = self._load_session(session_id)
                if session and session.last_activity_time < cutoff_time:
                    session_dir = self._get_session_dir(session_id)
                    
                    # Remove from active sessions
                    if session_id in self._active_sessions:
                        del self._active_sessions[session_id]
                    
                    # Remove session directory (includes checkpoints)
                    import shutil
                    shutil.rmtree(session_dir)
                    cleaned_count += 1
                    
            logger.info(f"Cleaned up {cleaned_count} old sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_suffix}"
    
    def _get_session_dir(self, session_id: str) -> Path:
        """Get session directory path"""
        return self.base_state_dir / "sessions" / session_id
    
    def _load_session(self, session_id: str) -> Optional[CollectionSession]:
        """Load session from disk"""
        try:
            session_file = self._get_session_dir(session_id) / "session.json"
            return self.persistence.load_state(session_file, CollectionSession)
        except Exception as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
            return None
    
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
    
    def _initialize_directory_structure(self) -> None:
        """Initialize base directory structure"""
        try:
            self.base_state_dir.mkdir(parents=True, exist_ok=True)
            (self.base_state_dir / "sessions").mkdir(exist_ok=True)
            logger.debug(f"Initialized directory structure at {self.base_state_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize directory structure: {e}")
            raise