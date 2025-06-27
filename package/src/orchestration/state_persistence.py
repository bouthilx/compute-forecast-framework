"""
State Persistence Manager - Handles session state persistence and recovery
Implements robust state management with checkpoint validation and recovery.
"""

import json
import threading
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

from src.data.collectors.state_structures import (
    CollectionSession, CheckpointData, InterruptionAnalysis, 
    RecoveryPlan, IntegrityCheckResult, CheckpointValidationResult
)

logger = logging.getLogger(__name__)


class StatePersistenceManager:
    """
    Manages persistent state for collection sessions with validation and recovery
    
    REQUIREMENTS:
    - Thread-safe operations for concurrent access
    - Automatic checkpoint validation and integrity checks
    - Recovery plan generation for interrupted sessions
    - State consistency verification
    """
    
    def __init__(self, state_dir: Path = Path("data/state")):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions_dir = self.state_dir / "sessions"
        self.checkpoints_dir = self.state_dir / "checkpoints"
        self.recovery_dir = self.state_dir / "recovery"
        
        for dir_path in [self.sessions_dir, self.checkpoints_dir, self.recovery_dir]:
            dir_path.mkdir(exist_ok=True)
        
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()
    
    def _get_session_lock(self, session_id: str) -> threading.RLock:
        """Get or create lock for session"""
        with self._global_lock:
            if session_id not in self._locks:
                self._locks[session_id] = threading.RLock()
            return self._locks[session_id]
    
    def save_session_state(self, session: CollectionSession) -> bool:
        """
        Save session state to persistent storage
        
        Returns:
            bool: True if save was successful, False otherwise
        """
        session_lock = self._get_session_lock(session.session_id)
        with session_lock:
            try:
                session_file = self.sessions_dir / f"{session.session_id}.json"
                
                # Update last activity time
                session.last_activity_time = datetime.now()
                
                # Convert to dictionary and save
                session_data = session.to_dict()
                
                # Atomic write using temporary file
                temp_file = session_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(session_data, f, indent=2, default=str)
                
                # Move to final location
                temp_file.rename(session_file)
                
                logger.info(f"Saved session state: {session.session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save session {session.session_id}: {e}")
                return False
    
    def load_session_state(self, session_id: str) -> Optional[CollectionSession]:
        """
        Load session state from persistent storage
        
        Returns:
            CollectionSession if found and valid, None otherwise
        """
        session_lock = self._get_session_lock(session_id)
        with session_lock:
            try:
                session_file = self.sessions_dir / f"{session_id}.json"
                
                if not session_file.exists():
                    logger.warning(f"Session file not found: {session_id}")
                    return None
                
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                # Validate and convert back to CollectionSession
                session = CollectionSession.from_dict(session_data)
                
                logger.info(f"Loaded session state: {session_id}")
                return session
                
            except Exception as e:
                logger.error(f"Failed to load session {session_id}: {e}")
                return None
    
    def save_checkpoint(self, checkpoint: CheckpointData) -> bool:
        """
        Save checkpoint with validation
        
        Returns:
            bool: True if checkpoint was saved successfully
        """
        session_lock = self._get_session_lock(checkpoint.session_id)
        with session_lock:
            try:
                # Validate checkpoint integrity first
                if not checkpoint.validate_integrity():
                    logger.error(f"Checkpoint integrity validation failed: {checkpoint.checkpoint_id}")
                    return False
                
                checkpoint_file = self.checkpoints_dir / f"{checkpoint.checkpoint_id}.json"
                
                # Convert to dictionary and save
                checkpoint_data = checkpoint.to_dict()
                
                # Atomic write
                temp_file = checkpoint_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(checkpoint_data, f, indent=2, default=str)
                
                temp_file.rename(checkpoint_file)
                
                logger.info(f"Saved checkpoint: {checkpoint.checkpoint_id} for session {checkpoint.session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save checkpoint {checkpoint.checkpoint_id}: {e}")
                return False
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """
        Load and validate checkpoint
        
        Returns:
            CheckpointData if valid, None otherwise
        """
        try:
            checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
            
            if not checkpoint_file.exists():
                logger.warning(f"Checkpoint file not found: {checkpoint_id}")
                return None
            
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            checkpoint = CheckpointData.from_dict(checkpoint_data)
            
            # Validate integrity
            if not checkpoint.validate_integrity():
                logger.error(f"Checkpoint integrity validation failed: {checkpoint_id}")
                checkpoint.validation_status = "corrupted"
                return checkpoint  # Return corrupted checkpoint for analysis
            
            logger.info(f"Loaded valid checkpoint: {checkpoint_id}")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}")
            return None
    
    def list_session_checkpoints(self, session_id: str) -> List[str]:
        """
        List all checkpoint IDs for a session
        
        Returns:
            List of checkpoint IDs ordered by timestamp
        """
        try:
            checkpoints = []
            
            for checkpoint_file in self.checkpoints_dir.glob("*.json"):
                try:
                    with open(checkpoint_file, 'r') as f:
                        data = json.load(f)
                    
                    if data.get('session_id') == session_id:
                        checkpoints.append({
                            'checkpoint_id': data['checkpoint_id'],
                            'timestamp': datetime.fromisoformat(data['timestamp'])
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to read checkpoint file {checkpoint_file}: {e}")
                    continue
            
            # Sort by timestamp
            checkpoints.sort(key=lambda x: x['timestamp'])
            return [cp['checkpoint_id'] for cp in checkpoints]
            
        except Exception as e:
            logger.error(f"Failed to list checkpoints for session {session_id}: {e}")
            return []
    
    def validate_checkpoints(self, session_id: str) -> List[CheckpointValidationResult]:
        """
        Validate all checkpoints for a session
        
        Returns:
            List of validation results for each checkpoint
        """
        checkpoint_ids = self.list_session_checkpoints(session_id)
        validation_results = []
        
        for checkpoint_id in checkpoint_ids:
            checkpoint = self.load_checkpoint(checkpoint_id)
            
            if checkpoint is None:
                validation_results.append(CheckpointValidationResult(
                    checkpoint_id=checkpoint_id,
                    is_valid=False,
                    validation_errors=["Failed to load checkpoint"],
                    integrity_score=0.0,
                    can_be_used_for_recovery=False
                ))
                continue
            
            # Validate checkpoint
            validation_errors = []
            integrity_score = 1.0
            
            # Check integrity
            if not checkpoint.validate_integrity():
                validation_errors.append("Integrity validation failed")
                integrity_score -= 0.5
            
            # Check data consistency
            if checkpoint.papers_collected < 0:
                validation_errors.append("Invalid paper count")
                integrity_score -= 0.2
            
            if not checkpoint.venues_completed and not checkpoint.venues_in_progress:
                validation_errors.append("No venue progress recorded")
                integrity_score -= 0.1
            
            # Check timestamp validity
            if checkpoint.timestamp > datetime.now():
                validation_errors.append("Future timestamp detected")
                integrity_score -= 0.3
            
            is_valid = len(validation_errors) == 0
            can_be_used_for_recovery = integrity_score >= 0.7
            
            validation_results.append(CheckpointValidationResult(
                checkpoint_id=checkpoint_id,
                is_valid=is_valid,
                validation_errors=validation_errors,
                integrity_score=max(0.0, integrity_score),
                can_be_used_for_recovery=can_be_used_for_recovery
            ))
        
        return validation_results
    
    def check_data_integrity(self, session_id: str) -> List[IntegrityCheckResult]:
        """
        Check integrity of all data files for a session
        
        Returns:
            List of integrity check results
        """
        integrity_results = []
        
        # Check session file
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            integrity_results.append(self._check_file_integrity(session_file, "session"))
        
        # Check checkpoint files
        for checkpoint_id in self.list_session_checkpoints(session_id):
            checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                integrity_results.append(self._check_file_integrity(checkpoint_file, "checkpoint"))
        
        return integrity_results
    
    def _check_file_integrity(self, file_path: Path, file_type: str) -> IntegrityCheckResult:
        """Check integrity of a single file"""
        try:
            if not file_path.exists():
                return IntegrityCheckResult(
                    file_path=file_path,
                    integrity_status="missing",
                    checksum_valid=False,
                    size_expected=0,
                    size_actual=0,
                    last_modified=datetime.now(),
                    recovery_action="recreate_from_backup"
                )
            
            size_actual = file_path.stat().st_size
            last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # Try to parse as JSON
            try:
                with open(file_path, 'r') as f:
                    json.load(f)
                
                status = "valid"
                checksum_valid = True
                recovery_action = None
                
            except json.JSONDecodeError:
                status = "corrupted"
                checksum_valid = False
                recovery_action = "restore_from_checkpoint"
            
            return IntegrityCheckResult(
                file_path=file_path,
                integrity_status=status,
                checksum_valid=checksum_valid,
                size_expected=size_actual,  # We don't have expected size
                size_actual=size_actual,
                last_modified=last_modified,
                recovery_action=recovery_action
            )
            
        except Exception as e:
            logger.error(f"Failed to check integrity of {file_path}: {e}")
            return IntegrityCheckResult(
                file_path=file_path,
                integrity_status="partial",
                checksum_valid=False,
                size_expected=0,
                size_actual=0,
                last_modified=datetime.now(),
                recovery_action="manual_inspection"
            )
    
    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, int]:
        """
        Clean up old session data and checkpoints
        
        Args:
            days_old: Remove data older than this many days
        
        Returns:
            Dict with counts of cleaned files
        """
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 3600)
        cleanup_stats = {
            'sessions_removed': 0,
            'checkpoints_removed': 0,
            'recovery_files_removed': 0
        }
        
        try:
            # Clean old session files
            for session_file in self.sessions_dir.glob("*.json"):
                if session_file.stat().st_mtime < cutoff_date:
                    session_file.unlink()
                    cleanup_stats['sessions_removed'] += 1
            
            # Clean old checkpoint files
            for checkpoint_file in self.checkpoints_dir.glob("*.json"):
                if checkpoint_file.stat().st_mtime < cutoff_date:
                    checkpoint_file.unlink()
                    cleanup_stats['checkpoints_removed'] += 1
            
            # Clean old recovery files
            for recovery_file in self.recovery_dir.glob("*.json"):
                if recovery_file.stat().st_mtime < cutoff_date:
                    recovery_file.unlink()
                    cleanup_stats['recovery_files_removed'] += 1
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return cleanup_stats