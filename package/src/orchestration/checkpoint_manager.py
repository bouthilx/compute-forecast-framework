"""
Checkpoint Manager - Handles checkpoint creation, validation and recovery
Implements intelligent checkpointing with automatic recovery point generation.
"""

import threading
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from src.data.collectors.state_structures import (
    CheckpointData, CollectionSession, ErrorContext, 
    CheckpointValidationResult, VenueConfig
)
from src.data.models import APIHealthStatus, RateLimitStatus
from .state_persistence import StatePersistenceManager

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoint creation, validation, and recovery for collection sessions
    
    REQUIREMENTS:
    - Automatic checkpoint creation at key collection milestones
    - Checkpoint validation and integrity verification
    - Recovery point recommendations
    - Thread-safe operations
    """
    
    def __init__(self, persistence_manager: StatePersistenceManager):
        self.persistence = persistence_manager
        self._session_locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()
    
    def _get_session_lock(self, session_id: str) -> threading.RLock:
        """Get or create lock for session"""
        with self._global_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = threading.RLock()
            return self._session_locks[session_id]
    
    def create_checkpoint(
        self, 
        session: CollectionSession,
        checkpoint_type: str,
        venues_completed: List[tuple],
        venues_in_progress: List[tuple],
        venues_not_started: List[tuple],
        papers_by_venue: Dict[str, Dict[int, int]],
        api_health_status: Dict[str, APIHealthStatus],
        rate_limit_status: Dict[str, RateLimitStatus],
        last_operation: str,
        error_context: Optional[ErrorContext] = None
    ) -> Optional[CheckpointData]:
        """
        Create a new checkpoint for the session
        
        Args:
            session: Current collection session
            checkpoint_type: Type of checkpoint being created
            venues_completed: List of (venue, year) tuples completed
            venues_in_progress: List of (venue, year) tuples in progress
            venues_not_started: List of (venue, year) tuples not started
            papers_by_venue: Paper counts by venue and year
            api_health_status: Current API health statuses
            rate_limit_status: Current rate limit statuses
            last_operation: Description of last successful operation
            error_context: Error context if checkpoint created due to error
        
        Returns:
            CheckpointData if successful, None otherwise
        """
        session_lock = self._get_session_lock(session.session_id)
        with session_lock:
            try:
                checkpoint_id = f"{session.session_id}_{checkpoint_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                
                # Calculate total papers collected
                total_papers = sum(
                    sum(year_counts.values()) 
                    for year_counts in papers_by_venue.values()
                )
                
                # Create checkpoint
                checkpoint = CheckpointData(
                    checkpoint_id=checkpoint_id,
                    session_id=session.session_id,
                    checkpoint_type=checkpoint_type,
                    timestamp=datetime.now(),
                    venues_completed=venues_completed,
                    venues_in_progress=venues_in_progress,
                    venues_not_started=venues_not_started,
                    papers_collected=total_papers,
                    papers_by_venue=papers_by_venue,
                    last_successful_operation=last_operation,
                    api_health_status=api_health_status,
                    rate_limit_status=rate_limit_status,
                    error_context=error_context
                )
                
                # Save checkpoint
                if self.persistence.save_checkpoint(checkpoint):
                    # Update session with latest checkpoint
                    session.last_checkpoint_id = checkpoint_id
                    session.checkpoint_count += 1
                    session.last_activity_time = datetime.now()
                    
                    # Save updated session state
                    self.persistence.save_session_state(session)
                    
                    logger.info(f"Created checkpoint {checkpoint_id} for session {session.session_id}")
                    return checkpoint
                else:
                    logger.error(f"Failed to save checkpoint {checkpoint_id}")
                    return None
                
            except Exception as e:
                logger.error(f"Failed to create checkpoint for session {session.session_id}: {e}")
                return None
    
    def create_venue_completion_checkpoint(
        self,
        session: CollectionSession,
        completed_venue: str,
        completed_year: int,
        papers_collected: int,
        collection_metadata: Dict[str, Any],
        api_health_status: Dict[str, APIHealthStatus],
        rate_limit_status: Dict[str, RateLimitStatus]
    ) -> Optional[CheckpointData]:
        """
        Create checkpoint when a venue collection is completed
        
        Returns:
            CheckpointData if successful, None otherwise
        """
        # Build venue lists from session state
        venues_completed = session.venues_completed.copy()
        venues_completed.append((completed_venue, completed_year))
        
        venues_in_progress = [
            (v, y) for (v, y) in session.venues_in_progress 
            if not (v == completed_venue and y == completed_year)
        ]
        
        # Calculate remaining venues
        all_target_venues = set()
        for venue_config in session.target_venues:
            for year in venue_config.target_years:
                all_target_venues.add((venue_config.venue_name, year))
        
        venues_not_started = [
            (v, y) for (v, y) in all_target_venues
            if (v, y) not in venues_completed and (v, y) not in venues_in_progress
        ]
        
        # Update papers by venue
        papers_by_venue = session.papers_by_venue.copy()
        if completed_venue not in papers_by_venue:
            papers_by_venue[completed_venue] = {}
        papers_by_venue[completed_venue][completed_year] = papers_collected
        
        return self.create_checkpoint(
            session=session,
            checkpoint_type="venue_completed",
            venues_completed=venues_completed,
            venues_in_progress=venues_in_progress,
            venues_not_started=venues_not_started,
            papers_by_venue=papers_by_venue,
            api_health_status=api_health_status,
            rate_limit_status=rate_limit_status,
            last_operation=f"Completed collection for {completed_venue} {completed_year}: {papers_collected} papers"
        )
    
    def create_error_checkpoint(
        self,
        session: CollectionSession,
        error_context: ErrorContext,
        api_health_status: Dict[str, APIHealthStatus],
        rate_limit_status: Dict[str, RateLimitStatus]
    ) -> Optional[CheckpointData]:
        """
        Create checkpoint when an error occurs
        
        Returns:
            CheckpointData if successful, None otherwise
        """
        return self.create_checkpoint(
            session=session,
            checkpoint_type="error_occurred",
            venues_completed=session.venues_completed,
            venues_in_progress=session.venues_in_progress,
            venues_not_started=[],  # Calculate from target venues
            papers_by_venue=session.papers_by_venue,
            api_health_status=api_health_status,
            rate_limit_status=rate_limit_status,
            last_operation=f"Error occurred: {error_context.error_type}",
            error_context=error_context
        )
    
    def create_session_start_checkpoint(
        self,
        session: CollectionSession,
        api_health_status: Dict[str, APIHealthStatus],
        rate_limit_status: Dict[str, RateLimitStatus]
    ) -> Optional[CheckpointData]:
        """
        Create initial checkpoint when session starts
        
        Returns:
            CheckpointData if successful, None otherwise
        """
        # Calculate all target venues
        all_target_venues = []
        for venue_config in session.target_venues:
            for year in venue_config.target_years:
                all_target_venues.append((venue_config.venue_name, year))
        
        return self.create_checkpoint(
            session=session,
            checkpoint_type="session_started",
            venues_completed=[],
            venues_in_progress=[],
            venues_not_started=all_target_venues,
            papers_by_venue={},
            api_health_status=api_health_status,
            rate_limit_status=rate_limit_status,
            last_operation="Session initialization completed"
        )
    
    def validate_checkpoint_chain(self, session_id: str) -> List[CheckpointValidationResult]:
        """
        Validate the entire chain of checkpoints for a session
        
        Returns:
            List of validation results, one per checkpoint
        """
        return self.persistence.validate_checkpoints(session_id)
    
    def find_best_recovery_checkpoint(self, session_id: str) -> Optional[CheckpointData]:
        """
        Find the best checkpoint to use for recovery
        
        Returns:
            Best CheckpointData for recovery, or None if none suitable
        """
        try:
            validation_results = self.validate_checkpoint_chain(session_id)
            
            # Filter to checkpoints that can be used for recovery
            recovery_candidates = [
                result for result in validation_results
                if result.can_be_used_for_recovery and result.integrity_score >= 0.8
            ]
            
            if not recovery_candidates:
                logger.warning(f"No suitable recovery checkpoints found for session {session_id}")
                return None
            
            # Sort by integrity score and find the most recent high-quality checkpoint
            recovery_candidates.sort(key=lambda x: x.integrity_score, reverse=True)
            best_checkpoint_id = recovery_candidates[0].checkpoint_id
            
            # Load and return the best checkpoint
            checkpoint = self.persistence.load_checkpoint(best_checkpoint_id)
            if checkpoint and checkpoint.validate_integrity():
                logger.info(f"Best recovery checkpoint for {session_id}: {best_checkpoint_id}")
                return checkpoint
            else:
                logger.error(f"Failed to load or validate best recovery checkpoint {best_checkpoint_id}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to find best recovery checkpoint for session {session_id}: {e}")
            return None
    
    def get_checkpoint_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary of all checkpoints for a session
        
        Returns:
            Dictionary with checkpoint statistics and status
        """
        try:
            checkpoint_ids = self.persistence.list_session_checkpoints(session_id)
            validation_results = self.validate_checkpoint_chain(session_id)
            
            # Calculate statistics
            total_checkpoints = len(checkpoint_ids)
            valid_checkpoints = sum(1 for result in validation_results if result.is_valid)
            recoverable_checkpoints = sum(1 for result in validation_results if result.can_be_used_for_recovery)
            
            # Find checkpoint types
            checkpoint_types = {}
            for checkpoint_id in checkpoint_ids:
                checkpoint = self.persistence.load_checkpoint(checkpoint_id)
                if checkpoint:
                    checkpoint_type = checkpoint.checkpoint_type
                    checkpoint_types[checkpoint_type] = checkpoint_types.get(checkpoint_type, 0) + 1
            
            # Calculate average integrity score
            avg_integrity = 0.0
            if validation_results:
                avg_integrity = sum(result.integrity_score for result in validation_results) / len(validation_results)
            
            return {
                'session_id': session_id,
                'total_checkpoints': total_checkpoints,
                'valid_checkpoints': valid_checkpoints,
                'recoverable_checkpoints': recoverable_checkpoints,
                'checkpoint_types': checkpoint_types,
                'average_integrity_score': avg_integrity,
                'has_recovery_options': recoverable_checkpoints > 0,
                'latest_checkpoint': checkpoint_ids[-1] if checkpoint_ids else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get checkpoint summary for session {session_id}: {e}")
            return {
                'session_id': session_id,
                'error': str(e),
                'has_recovery_options': False
            }
    
    def cleanup_old_checkpoints(self, session_id: str, keep_count: int = 10) -> int:
        """
        Clean up old checkpoints, keeping only the most recent ones
        
        Args:
            session_id: Session to clean up
            keep_count: Number of recent checkpoints to keep
        
        Returns:
            Number of checkpoints removed
        """
        try:
            checkpoint_ids = self.persistence.list_session_checkpoints(session_id)
            
            if len(checkpoint_ids) <= keep_count:
                return 0
            
            # Remove oldest checkpoints
            checkpoints_to_remove = checkpoint_ids[:-keep_count]
            removed_count = 0
            
            for checkpoint_id in checkpoints_to_remove:
                checkpoint_file = self.persistence.checkpoints_dir / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()
                    removed_count += 1
            
            logger.info(f"Cleaned up {removed_count} old checkpoints for session {session_id}")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints for session {session_id}: {e}")
            return 0