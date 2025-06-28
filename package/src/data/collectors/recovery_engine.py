"""
RecoveryEngine implementation exactly matching Issue #5 specifications.
Provides the exact interface contract required by Issue #5.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from .state_structures import InterruptionAnalysis, RecoveryPlan
from .interruption_recovery import InterruptionRecoveryEngine
from .state_management import StateManager

logger = logging.getLogger(__name__)


class RecoveryEngine:
    """
    RecoveryEngine class with exact Issue #5 interface.
    
    This class provides the interface specified in Issue #5 while leveraging
    the existing InterruptionRecoveryEngine implementation.
    """
    
    def __init__(self, state_manager: StateManager):
        """
        Initialize RecoveryEngine.
        
        Args:
            state_manager: StateManager instance for session management
        """
        self.state_manager = state_manager
        self.interruption_recovery_engine = InterruptionRecoveryEngine(
            state_manager=state_manager
        )
        
        logger.info("RecoveryEngine initialized with Issue #5 interface")
    
    def analyze_interruption(self, session_id: str) -> InterruptionAnalysis:
        """
        REQUIREMENTS from Issue #5:
        - Must scan all checkpoints and state files
        - Must validate data integrity
        - Must assess completion status of all venues
        - Must identify optimal recovery point
        - Must complete analysis within 2 minutes
        
        Args:
            session_id: Session identifier
            
        Returns:
            InterruptionAnalysis with detailed analysis
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting interruption analysis for session {session_id}")
            
            # Use the existing analysis method from InterruptionRecoveryEngine
            analysis = self.interruption_recovery_engine._analyze_interruption(session_id)
            
            # Validate timing requirement (2 minutes = 120 seconds)
            duration = (datetime.now() - start_time).total_seconds()
            if duration > 120:
                logger.warning(f"Analysis took {duration:.1f}s (>120s requirement)")
            else:
                logger.info(f"Analysis completed in {duration:.1f}s")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Interruption analysis failed for session {session_id}: {e}")
            raise
    
    def create_recovery_plan(self, session_id: str, analysis: InterruptionAnalysis) -> RecoveryPlan:
        """
        REQUIREMENTS from Issue #5:
        - Must minimize duplicate work
        - Must ensure data consistency
        - Must provide confidence estimates
        - Must handle edge cases (corruption, missing data)
        
        Args:
            session_id: Session identifier
            analysis: InterruptionAnalysis from analyze_interruption
            
        Returns:
            RecoveryPlan with detailed recovery strategy
        """
        try:
            logger.info(f"Creating recovery plan for session {session_id}")
            
            # Use the existing recovery plan generation from StateManager
            # but enhance it with the analysis data
            recovery_plan = self.state_manager.get_recovery_plan(session_id)
            
            # Update the recovery plan with analysis data
            recovery_plan.based_on_analysis = analysis
            
            # Enhance confidence scoring based on analysis
            if analysis.valid_checkpoints:
                recovery_plan.confidence_score = min(0.95, recovery_plan.confidence_score + 0.1)
            else:
                recovery_plan.confidence_score = max(0.3, recovery_plan.confidence_score - 0.2)
            
            # Update recovery strategy based on analysis complexity
            if analysis.recovery_complexity == "trivial":
                recovery_plan.resumption_strategy = "from_last_checkpoint"
                recovery_plan.estimated_recovery_time_minutes = 1.0
            elif analysis.recovery_complexity == "simple":
                recovery_plan.resumption_strategy = "from_last_checkpoint"
                recovery_plan.estimated_recovery_time_minutes = 2.0
            elif analysis.recovery_complexity == "complex":
                recovery_plan.resumption_strategy = "partial_restart"
                recovery_plan.estimated_recovery_time_minutes = 4.0
            else:  # problematic
                recovery_plan.resumption_strategy = "full_restart"
                recovery_plan.estimated_recovery_time_minutes = 5.0
            
            # Handle edge cases
            if analysis.corrupted_checkpoints:
                recovery_plan.corrupted_data_to_discard.extend([
                    Path(f"checkpoints/{cp}.json") for cp in analysis.corrupted_checkpoints
                ])
                recovery_plan.risk_assessment.append("Corrupted checkpoints detected")
            
            if analysis.missing_checkpoints:
                recovery_plan.risk_assessment.append("Missing checkpoints detected")
                recovery_plan.confidence_score = max(0.4, recovery_plan.confidence_score - 0.1)
            
            # Ensure data consistency requirements
            if analysis.venues_possibly_incomplete:
                recovery_plan.venues_to_validate.extend(analysis.venues_possibly_incomplete)
                recovery_plan.recommended_validation_steps.append("Validate incomplete venues")
            
            if analysis.venues_unknown_status:
                recovery_plan.venues_to_restart.extend(analysis.venues_unknown_status)
                recovery_plan.recommended_validation_steps.append("Restart venues with unknown status")
            
            logger.info(f"Recovery plan created with strategy: {recovery_plan.resumption_strategy}, "
                       f"confidence: {recovery_plan.confidence_score:.2f}")
            
            return recovery_plan
            
        except Exception as e:
            logger.error(f"Recovery plan creation failed for session {session_id}: {e}")
            raise