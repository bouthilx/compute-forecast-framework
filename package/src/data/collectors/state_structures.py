"""
State management data structures for paper collection system.
Defines core structures for checkpoints, recovery, and session management.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal, Tuple, Union
from datetime import datetime
from pathlib import Path
import hashlib
import json

from src.data.models import APIHealthStatus, RateLimitStatus


@dataclass
class ErrorContext:
    """Context information when an error occurs during collection"""
    error_type: str
    error_message: str
    stack_trace: str
    venue_context: Optional[str] = None
    year_context: Optional[int] = None
    api_context: Optional[str] = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CheckpointData:
    """Core checkpoint data structure for state persistence"""
    checkpoint_id: str
    session_id: str
    checkpoint_type: Literal["venue_completed", "batch_completed", "api_call_completed", "error_occurred", "session_started"]
    timestamp: datetime
    
    # Collection progress
    venues_completed: List[Tuple[str, int]]     # (venue, year) pairs
    venues_in_progress: List[Tuple[str, int]]   # (venue, year) pairs
    venues_not_started: List[Tuple[str, int]]   # (venue, year) pairs
    
    # Data state
    papers_collected: int
    papers_by_venue: Dict[str, Dict[int, int]]  # venue -> year -> count
    last_successful_operation: str
    
    # API state
    api_health_status: Dict[str, APIHealthStatus]
    rate_limit_status: Dict[str, RateLimitStatus]
    
    # Error context (if checkpoint_type == "error_occurred")
    error_context: Optional[ErrorContext] = None
    
    # Validation
    checksum: str = ""                          # Data integrity checksum
    validation_status: Literal["valid", "corrupted", "incomplete"] = "valid"
    
    def __post_init__(self):
        """Calculate checksum after initialization"""
        if not self.checksum:
            self.checksum = self.calculate_checksum()
    
    def calculate_checksum(self) -> str:
        """Calculate SHA256 checksum of critical data"""
        # Create a deterministic string representation of critical data
        data_for_checksum = {
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'venues_completed': sorted(self.venues_completed),
            'venues_in_progress': sorted(self.venues_in_progress),
            'papers_collected': self.papers_collected,
            'papers_by_venue': dict(sorted(self.papers_by_venue.items())),
            'last_successful_operation': self.last_successful_operation
        }
        
        data_str = json.dumps(data_for_checksum, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def validate_integrity(self) -> bool:
        """Validate checkpoint data integrity"""
        calculated_checksum = self.calculate_checksum()
        return calculated_checksum == self.checksum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif hasattr(value, '__dict__'):
                result[key] = value.__dict__ if value else None
            elif isinstance(value, dict):
                # Handle nested dictionaries with complex objects
                serialized_dict = {}
                for k, v in value.items():
                    if hasattr(v, '__dict__'):
                        serialized_dict[k] = v.__dict__
                    elif isinstance(v, dict):
                        # Handle nested dict like papers_by_venue
                        serialized_dict[k] = v
                    else:
                        serialized_dict[k] = v
                result[key] = serialized_dict
            else:
                result[key] = value
        return result


@dataclass
class InterruptionAnalysis:
    """Analysis of what happened during interruption"""
    session_id: str
    analysis_timestamp: datetime
    interruption_time: datetime
    last_successful_operation: str
    last_checkpoint_id: str
    
    # State assessment
    venues_definitely_completed: List[Tuple[str, int]]
    venues_possibly_incomplete: List[Tuple[str, int]]
    venues_unknown_status: List[Tuple[str, int]]
    venues_not_started: List[Tuple[str, int]]
    
    # Data integrity
    corrupted_checkpoints: List[str]
    missing_checkpoints: List[str]
    data_files_found: List[Path]
    data_files_corrupted: List[Path]
    valid_checkpoints: List[str]
    
    # Recovery complexity
    recovery_complexity: Literal["trivial", "simple", "complex", "problematic"]
    blocking_issues: List[str]
    estimated_papers_collected: int
    estimated_papers_lost: int
    
    # Interruption cause analysis
    interruption_cause: 'InterruptionCause'
    system_state_at_interruption: Dict[str, Any]


@dataclass
class InterruptionCause:
    """Analysis of interruption cause"""
    cause_type: Literal["process_killed", "system_crash", "network_failure", "api_failure", "disk_full", "memory_error", "unknown"]
    confidence: float                           # 0.0 to 1.0
    evidence: List[str]                        # Evidence supporting the cause
    recovery_implications: List[str]           # How this affects recovery


@dataclass
class RecoveryPlan:
    """Detailed plan for resuming interrupted collection"""
    session_id: str
    plan_id: str
    created_at: datetime
    based_on_analysis: InterruptionAnalysis
    
    # Recovery strategy
    resumption_strategy: Literal["from_last_checkpoint", "from_venue_start", "partial_restart", "full_restart"]
    optimal_checkpoint_id: Optional[str]
    
    # Recovery actions
    venues_to_skip: List[Tuple[str, int]]       # Already completed
    venues_to_resume: List[Tuple[str, int]]     # Partially completed
    venues_to_restart: List[Tuple[str, int]]    # Start from beginning
    venues_to_validate: List[Tuple[str, int]]   # Need validation
    
    # Data recovery actions
    checkpoints_to_restore: List[str]
    data_files_to_recover: List[Path]
    corrupted_data_to_discard: List[Path]
    
    # Estimates
    estimated_recovery_time_minutes: float
    estimated_papers_to_recover: int
    data_loss_estimate: int                     # Papers potentially lost
    confidence_score: float                     # 0.0 to 1.0
    
    # Validation
    recovery_confidence: float                  # 0.0 to 1.0
    recommended_validation_steps: List[str]
    risk_assessment: List[str]


@dataclass
class IntegrityCheckResult:
    """Data integrity check result"""
    file_path: Path
    integrity_status: Literal["valid", "corrupted", "missing", "partial"]
    checksum_valid: bool
    size_expected: int
    size_actual: int
    last_modified: datetime
    recovery_action: Optional[str] = None


@dataclass
class CheckpointValidationResult:
    """Checkpoint validation result"""
    checkpoint_id: str
    is_valid: bool
    validation_errors: List[str]
    integrity_score: float
    can_be_used_for_recovery: bool


@dataclass
class SessionResumeResult:
    """Result of session resumption"""
    session_id: str
    plan_id: str
    success: bool
    recovery_start_time: datetime
    recovery_end_time: datetime
    recovery_duration_seconds: float
    
    # Recovery statistics
    checkpoints_recovered: int
    papers_recovered: int
    venues_recovered: int
    data_files_recovered: int
    
    # Recovery actions taken
    recovery_steps_executed: List[str]
    recovery_steps_failed: List[str]
    
    # Validation results
    data_integrity_checks: List[IntegrityCheckResult]
    state_consistency_validated: bool
    checkpoint_validation_results: List[CheckpointValidationResult]
    
    # Final state
    session_state_after_recovery: Optional['CollectionSession'] = None
    ready_for_continuation: bool = False
    
    # Errors/warnings
    resume_warnings: List[str] = field(default_factory=list)
    resume_errors: List[str] = field(default_factory=list)
    partial_recovery_issues: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Individual validation check result"""
    validation_type: str
    passed: bool
    confidence: float
    details: str
    recommendations: List[str]


@dataclass
class VenueConfig:
    """Configuration for a venue to be collected"""
    venue_name: str
    target_years: List[int]
    max_papers_per_year: int = 50
    priority: int = 1  # 1 = high, 5 = low
    

@dataclass
class CollectionSession:
    """Main session state for paper collection"""
    session_id: str
    creation_time: datetime
    last_activity_time: datetime
    status: Literal["active", "paused", "completed", "failed", "interrupted"]
    
    # Collection configuration
    target_venues: List[VenueConfig]
    target_years: List[int]
    collection_config: Dict[str, Any]  # From existing CollectionConfig
    
    # Progress tracking
    venues_completed: List[Tuple[str, int]]
    venues_in_progress: List[Tuple[str, int]]
    venues_failed: List[Tuple[str, int]]
    
    # Collection statistics
    total_papers_collected: int = 0
    papers_by_venue: Dict[str, Dict[int, int]] = field(default_factory=dict)
    collection_duration_seconds: float = 0.0
    
    # Session metadata
    last_checkpoint_id: Optional[str] = None
    checkpoint_count: int = 0
    error_count: int = 0
    
    # API status tracking
    api_status: Dict[str, APIHealthStatus] = field(default_factory=dict)
    rate_limits: Dict[str, RateLimitStatus] = field(default_factory=dict)


@dataclass
class DataIntegrityAssessment:
    """Assessment of data integrity after interruption"""
    session_id: str
    assessment_time: datetime
    
    # File integrity
    total_data_files: int
    valid_data_files: int
    corrupted_data_files: int
    missing_data_files: int
    
    # Checkpoint integrity  
    total_checkpoints: int
    valid_checkpoints: int
    corrupted_checkpoints: int
    
    # Data consistency
    venue_data_consistency: Dict[str, bool]  # venue -> is_consistent
    paper_count_consistency: bool
    timestamp_consistency: bool
    
    # Recovery implications
    data_loss_severity: Literal["none", "minimal", "moderate", "severe"]
    recovery_feasibility: Literal["trivial", "simple", "complex", "impossible"]
    estimated_recovery_time_minutes: float


@dataclass
class RecoveryPlanValidation:
    """Validation result for a recovery plan"""
    plan_id: str
    is_valid: bool
    validation_timestamp: datetime
    
    # Validation checks
    strategy_feasible: bool
    data_availability_confirmed: bool
    checkpoint_integrity_verified: bool
    venue_status_consistent: bool
    
    # Issues found
    validation_errors: List[str]
    validation_warnings: List[str]
    
    # Recommendations
    recommended_modifications: List[str]
    confidence_assessment: float


@dataclass
class RecoveryResultValidation:
    """Validation result after recovery execution"""
    session_id: str
    validation_timestamp: datetime
    
    # State validation
    session_state_valid: bool
    checkpoint_consistency: bool
    data_file_integrity: bool
    venue_progress_accurate: bool
    
    # Validation details
    validation_checks_passed: int
    validation_checks_failed: int
    critical_issues: List[str]
    minor_issues: List[str]
    
    # Recovery assessment
    recovery_success_confidence: float
    ready_for_continuation: bool
    recommended_next_steps: List[str]