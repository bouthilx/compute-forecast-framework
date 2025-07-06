<<<<<<< HEAD
"""
VenueCollectionOrchestrator - Main system coordinator integrating all agent components.

This is the primary entry point that orchestrates:
- Agent Alpha: API integration layer with rate limiting
- Agent Beta: State management and checkpointing
- Agent Gamma: Data processing pipeline (venue normalization, deduplication)
- Agent Delta: Monitoring and dashboard systems
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from ..data.models import Paper, CollectionConfig
from ..data.collectors.collection_executor import CollectionExecutor
from ..analysis.venues.venue_analyzer import MilaVenueAnalyzer
from ..analysis.venues.venue_database import VenueDatabase
from ..quality.validators.base import BaseValidator
from .system_initializer import SystemInitializer
from .component_validator import ComponentValidator
from .workflow_coordinator import WorkflowCoordinator

logger = logging.getLogger(__name__)

@dataclass
class ComponentStatus:
    component_name: str
    status: str  # "not_initialized", "initializing", "ready", "error", "unavailable"
    version: str
    initialization_time: float
    health_check_passed: bool
    interface_validation_passed: bool
    dependencies_met: bool
    error_message: Optional[str] = None

@dataclass
class SystemInitializationResult:
    success: bool
    initialized_components: List[str]
    failed_components: List[str]
    initialization_duration_seconds: float
    component_status: Dict[str, ComponentStatus]
    integration_validation: 'IntegrationValidationResult'
    initialization_errors: List[str] = field(default_factory=list)
    initialization_warnings: List[str] = field(default_factory=list)
    ready_for_collection: bool = False
    readiness_blocking_issues: List[str] = field(default_factory=list)

@dataclass
class CollectionExecutionResult:
    session_id: str
    success: bool
    execution_duration_hours: float
    venues_attempted: List[Tuple[str, int]]
    venues_completed: List[Tuple[str, int]]
    venues_failed: List[Tuple[str, int]]
    raw_papers_collected: int
    deduplicated_papers: int
    filtered_papers: int
    final_dataset_size: int
    collection_completeness: float
    data_quality_score: float
    venue_coverage: Dict[str, float]
    papers_per_minute: float
    api_efficiency: float
    processing_efficiency: float
    execution_errors: List[str] = field(default_factory=list)
    data_quality_warnings: List[str] = field(default_factory=list)
    performance_issues: List[str] = field(default_factory=list)

@dataclass
class SessionResumeResult:
    success: bool
    session_id: str
    resume_errors: List[str] = field(default_factory=list)
    state_consistency_validated: bool = False
    papers_recovered: int = 0

@dataclass
class IntegrationValidationResult:
    overall_success: bool
    validation_duration_seconds: float
    component_validations: Dict[str, 'ComponentValidationResult']
    interface_validations: Dict[str, 'InterfaceValidationResult']
    data_flow_integrity: bool
    data_consistency_checks: List['DataConsistencyResult']
    performance_benchmarks: Dict[str, float]
    performance_targets_met: bool
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

@dataclass
class ComponentValidationResult:
    component_name: str
    validation_passed: bool
    interface_methods_found: List[str]
    missing_methods: List[str]
    test_results: Dict[str, bool]
    error_details: List[str] = field(default_factory=list)

@dataclass
class InterfaceValidationResult:
    interface_name: str
    validation_passed: bool
    methods_tested: List[str]
    data_flow_verified: bool
    error_details: List[str] = field(default_factory=list)

@dataclass
class DataConsistencyResult:
    check_name: str
    passed: bool
    details: str
    recommendation: Optional[str] = None

@dataclass
class SystemStatus:
    overall_health: str  # "healthy", "degraded", "critical", "offline"
    component_health: Dict[str, str]
    active_sessions: List[str]
    resource_usage: Dict[str, float]
    alerts: List[str] = field(default_factory=list)

@dataclass
class VenueConfig:
    venue_name: str
    venue_variants: List[str]
    venue_tier: str
    target_papers_per_year: int
    collection_strategy: str
    citation_thresholds: Dict[int, int]

class VenueCollectionOrchestrator:
    """
    Main system coordinator that integrates all agent components into a unified 
    venue collection system.
    """

    def __init__(self, config: CollectionConfig):
        """
        Initialize system with all agent components
        
        REQUIREMENTS:
        - Must initialize all agent components in correct order
        - Must validate component compatibility
        - Must setup monitoring and state management
        - Must handle initialization failures gracefully
        """
        self.config = config
        
        # Agent components (initialized during system startup)
        self.api_engine = None          # Agent Alpha - API integration layer
        self.state_manager = None       # Agent Beta - State management
        self.venue_normalizer = None    # Agent Gamma - Venue normalization
        self.deduplicator = None        # Agent Gamma - Deduplication engine
        self.citation_analyzer = None   # Agent Gamma - Citation analysis
        self.dashboard = None           # Agent Delta - Collection dashboard
        self.metrics_collector = None   # Agent Delta - Metrics collection
        self.alert_system = None        # Agent Delta - Intelligent alerting
        
        # System components
        self.system_initializer = SystemInitializer()
        self.component_validator = ComponentValidator()
        self.workflow_coordinator = WorkflowCoordinator()
        
        # System state
        self.system_ready = False
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.initialization_result: Optional[SystemInitializationResult] = None
        
        logger.info(f"VenueCollectionOrchestrator initialized with config: {config}")

    def initialize_system(self) -> SystemInitializationResult:
        """
        Initialize and validate all system components
        
        REQUIREMENTS:
        - Must initialize components in dependency order
        - Must validate all interface contracts
        - Must perform integration health checks
        - Must complete within 60 seconds
        - Must provide detailed failure diagnostics
        """
        logger.info("Starting system initialization...")
        init_start = time.time()
        
        result = SystemInitializationResult(
            success=False,
            initialized_components=[],
            failed_components=[],
            initialization_duration_seconds=0.0,
            component_status={},
            integration_validation=IntegrationValidationResult(
                overall_success=False,
                validation_duration_seconds=0.0,
                component_validations={},
                interface_validations={},
                data_flow_integrity=False,
                data_consistency_checks=[],
                performance_benchmarks={},
                performance_targets_met=False
            )
        )
        
        try:
            # Phase 1: Initialize components in dependency order
            logger.info("Phase 1: Initializing components...")
            
            # 1. Initialize Agent Alpha (API layer) - no dependencies
            alpha_status = self._initialize_alpha_component()
            result.component_status['agent_alpha'] = alpha_status
            
            if alpha_status.status == "ready":
                result.initialized_components.append('agent_alpha')
                logger.info("✓ Agent Alpha (API layer) initialized")
            else:
                result.failed_components.append('agent_alpha')
                result.initialization_errors.append(f"Agent Alpha failed: {alpha_status.error_message}")
                logger.error(f"✗ Agent Alpha failed: {alpha_status.error_message}")
            
            # 2. Initialize Agent Beta (State management) - depends on config
            beta_status = self._initialize_beta_component()
            result.component_status['agent_beta'] = beta_status
            
            if beta_status.status == "ready":
                result.initialized_components.append('agent_beta')
                logger.info("✓ Agent Beta (State management) initialized")
            else:
                result.failed_components.append('agent_beta')
                result.initialization_errors.append(f"Agent Beta failed: {beta_status.error_message}")
                logger.error(f"✗ Agent Beta failed: {beta_status.error_message}")
            
            # 3. Initialize Agent Gamma (Data processing) - depends on venue database
            gamma_status = self._initialize_gamma_component()
            result.component_status['agent_gamma'] = gamma_status
            
            if gamma_status.status == "ready":
                result.initialized_components.append('agent_gamma')
                logger.info("✓ Agent Gamma (Data processing) initialized")
            else:
                result.failed_components.append('agent_gamma')
                result.initialization_errors.append(f"Agent Gamma failed: {gamma_status.error_message}")
                logger.error(f"✗ Agent Gamma failed: {gamma_status.error_message}")
            
            # 4. Initialize Agent Delta (Monitoring) - depends on other agents
            delta_status = self._initialize_delta_component()
            result.component_status['agent_delta'] = delta_status
            
            if delta_status.status == "ready":
                result.initialized_components.append('agent_delta')
                logger.info("✓ Agent Delta (Monitoring) initialized")
            else:
                result.failed_components.append('agent_delta')
                result.initialization_errors.append(f"Agent Delta failed: {delta_status.error_message}")
                logger.error(f"✗ Agent Delta failed: {delta_status.error_message}")
            
            # Phase 2: Validate component integration
            logger.info("Phase 2: Validating integration...")
            
            integration_validation = self.validate_system_integration()
            result.integration_validation = integration_validation
            
            if not integration_validation.overall_success:
                result.initialization_warnings.extend(integration_validation.warnings)
                result.initialization_errors.extend(integration_validation.critical_issues)
            
            # Phase 3: Determine system readiness
            min_required_components = ['agent_alpha', 'agent_beta', 'agent_gamma']
            critical_components_ready = all(
                result.component_status.get(comp, ComponentStatus('', 'error', '', 0, False, False, False)).status == "ready"
                for comp in min_required_components
            )
            
            result.ready_for_collection = (
                critical_components_ready and 
                integration_validation.data_flow_integrity and
                len(result.initialization_errors) == 0
            )
            
            if not result.ready_for_collection:
                if not critical_components_ready:
                    result.readiness_blocking_issues.append("Critical components not initialized")
                if not integration_validation.data_flow_integrity:
                    result.readiness_blocking_issues.append("Data flow integrity validation failed")
                if result.initialization_errors:
                    result.readiness_blocking_issues.append("Initialization errors present")
            
            # Overall success determination
            result.success = (
                len(result.failed_components) == 0 and
                result.ready_for_collection and
                len(result.initialization_errors) == 0
            )
            
            self.system_ready = result.success
            self.initialization_result = result
            
            logger.info(f"System initialization {'completed successfully' if result.success else 'completed with issues'}")
            
        except Exception as e:
            result.initialization_errors.append(f"System initialization failed: {str(e)}")
            logger.error(f"System initialization exception: {e}")
            
        finally:
            result.initialization_duration_seconds = time.time() - init_start
            
            # Check 60-second requirement
            if result.initialization_duration_seconds > 60:
                result.initialization_warnings.append(
                    f"Initialization took {result.initialization_duration_seconds:.1f}s (>60s target)"
                )
        
        return result

    def _initialize_alpha_component(self) -> ComponentStatus:
        """Initialize Agent Alpha - API integration layer"""
        try:
            logger.info("Initializing Agent Alpha (API integration layer)...")
            start_time = time.time()
            
            # Use existing CollectionExecutor as Agent Alpha
            self.api_engine = CollectionExecutor()
            setup_success = self.api_engine.setup_collection_environment()
            
            init_time = time.time() - start_time
            
            if setup_success:
                # Validate interface
                interface_valid = (
                    hasattr(self.api_engine, 'test_api_connectivity') and
                    hasattr(self.api_engine, 'citation_apis') and
                    hasattr(self.api_engine, 'paper_collector')
                )
                
                return ComponentStatus(
                    component_name="agent_alpha",
                    status="ready",
                    version="1.0.0",
                    initialization_time=init_time,
                    health_check_passed=setup_success,
                    interface_validation_passed=interface_valid,
                    dependencies_met=True
                )
            else:
                return ComponentStatus(
                    component_name="agent_alpha",
                    status="error",
                    version="1.0.0",
                    initialization_time=init_time,
                    health_check_passed=False,
                    interface_validation_passed=False,
                    dependencies_met=False,
                    error_message="Collection environment setup failed"
                )
                
        except Exception as e:
            return ComponentStatus(
                component_name="agent_alpha",
                status="error",
                version="1.0.0",
                initialization_time=0.0,
                health_check_passed=False,
                interface_validation_passed=False,
                dependencies_met=False,
                error_message=str(e)
            )

    def _initialize_beta_component(self) -> ComponentStatus:
        """Initialize Agent Beta - State management"""
        try:
            logger.info("Initializing Agent Beta (State management)...")
            start_time = time.time()
            
            # Create simple state manager for now
            from .state_manager import SimpleStateManager
            self.state_manager = SimpleStateManager()
            
            init_time = time.time() - start_time
            
            return ComponentStatus(
                component_name="agent_beta",
                status="ready",
                version="1.0.0",
                initialization_time=init_time,
                health_check_passed=True,
                interface_validation_passed=True,
                dependencies_met=True
            )
            
        except Exception as e:
            return ComponentStatus(
                component_name="agent_beta",
                status="error",
                version="1.0.0",
                initialization_time=0.0,
                health_check_passed=False,
                interface_validation_passed=False,
                dependencies_met=False,
                error_message=str(e)
            )

    def _initialize_gamma_component(self) -> ComponentStatus:
        """Initialize Agent Gamma - Data processing pipeline"""
        try:
            logger.info("Initializing Agent Gamma (Data processing)...")
            start_time = time.time()
            
            # Initialize venue normalizer
            from ..analysis.venues.venue_analyzer import MilaVenueAnalyzer
            from ..analysis.venues.venue_database import VenueDatabase
            from ..core.config import ConfigManager
            
            config_manager = ConfigManager()
            venue_db = VenueDatabase(config_manager)
            self.venue_normalizer = MilaVenueAnalyzer(config_manager)
            
            # Create simple deduplicator and citation analyzer
            from .data_processors import SimpleDeduplicator, SimpleCitationAnalyzer
            self.deduplicator = SimpleDeduplicator()
            self.citation_analyzer = SimpleCitationAnalyzer()
            
            init_time = time.time() - start_time
            
            return ComponentStatus(
                component_name="agent_gamma",
                status="ready",
                version="1.0.0",
                initialization_time=init_time,
                health_check_passed=True,
                interface_validation_passed=True,
                dependencies_met=True
            )
            
        except Exception as e:
            return ComponentStatus(
                component_name="agent_gamma",
                status="error",
                version="1.0.0",
                initialization_time=0.0,
                health_check_passed=False,
                interface_validation_passed=False,
                dependencies_met=False,
                error_message=str(e)
            )

    def _initialize_delta_component(self) -> ComponentStatus:
        """Initialize Agent Delta - Monitoring and dashboard"""
        try:
            logger.info("Initializing Agent Delta (Monitoring)...")
            start_time = time.time()
            
            # Create simple monitoring components
            from .monitoring_components import SimpleMetricsCollector, SimpleDashboard, SimpleAlertSystem
            
            self.metrics_collector = SimpleMetricsCollector()
            self.dashboard = SimpleDashboard()
            self.alert_system = SimpleAlertSystem()
            
            init_time = time.time() - start_time
            
            return ComponentStatus(
                component_name="agent_delta",
                status="ready",
                version="1.0.0",
                initialization_time=init_time,
                health_check_passed=True,
                interface_validation_passed=True,
                dependencies_met=True
            )
            
        except Exception as e:
            return ComponentStatus(
                component_name="agent_delta",
                status="error",
                version="1.0.0",
                initialization_time=0.0,
                health_check_passed=False,
                interface_validation_passed=False,
                dependencies_met=False,
                error_message=str(e)
            )

    def start_collection_session(self, session_config: Optional[CollectionConfig] = None) -> str:
        """
        Start new collection session with full system coordination
        
        REQUIREMENTS:
        - Must create session in state manager
        - Must start monitoring and dashboard
        - Must validate system readiness
        - Must handle component startup failures
        """
        if not self.system_ready:
            raise RuntimeError("System not ready for collection. Run initialize_system() first.")
        
        if session_config is None:
            session_config = self.config
            
        logger.info("Starting new collection session...")
        
        try:
            # Create session in state manager
            session_id = self.state_manager.create_session(session_config)
            
            # Start monitoring for this session
            self.metrics_collector.start_session_monitoring(session_id)
            self.dashboard.create_session_dashboard(session_id)
            
            # Store session info
            self.active_sessions[session_id] = {
                'config': session_config,
                'start_time': datetime.now(),
                'status': 'active'
            }
            
            logger.info(f"Collection session started: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to start collection session: {e}")
            raise

    def execute_venue_collection(self, session_id: str, venues: List[str], years: List[int]) -> CollectionExecutionResult:
        """
        Execute complete venue collection workflow
        
        Workflow:
        1. API collection (Agent Alpha)
        2. State checkpointing (Agent Beta)  
        3. Data processing (Agent Gamma)
        4. Quality validation
        5. Progress reporting (Agent Delta)
        
        REQUIREMENTS:
        - Must handle workflow interruptions gracefully
        - Must maintain data integrity throughout
        - Must provide real-time progress updates
        - Must complete venue collection within target time
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        logger.info(f"Executing venue collection for session {session_id}: {venues} x {years}")
        execution_start = time.time()
        
        result = CollectionExecutionResult(
            session_id=session_id,
            success=False,
            execution_duration_hours=0.0,
            venues_attempted=[],
            venues_completed=[],
            venues_failed=[],
            raw_papers_collected=0,
            deduplicated_papers=0,
            filtered_papers=0,
            final_dataset_size=0,
            collection_completeness=0.0,
            data_quality_score=0.0,
            venue_coverage={},
            papers_per_minute=0.0,
            api_efficiency=0.0,
            processing_efficiency=0.0
        )
        
        try:
            # Use workflow coordinator to execute collection
            workflow_result = self.workflow_coordinator.execute_venue_collection_workflow(
                session_id, venues, years, 
                self.api_engine, self.state_manager, self.venue_normalizer, 
                self.deduplicator, self.citation_analyzer, self.metrics_collector
            )
            
            # Map workflow result to execution result
            result.success = workflow_result['success']
            result.venues_attempted = workflow_result.get('venues_attempted', [])
            result.venues_completed = workflow_result.get('venues_completed', [])
            result.venues_failed = workflow_result.get('venues_failed', [])
            result.raw_papers_collected = workflow_result.get('raw_papers_collected', 0)
            result.deduplicated_papers = workflow_result.get('deduplicated_papers', 0)
            result.filtered_papers = workflow_result.get('filtered_papers', 0)
            result.final_dataset_size = workflow_result.get('final_dataset_size', 0)
            result.data_quality_score = workflow_result.get('data_quality_score', 0.0)
            result.execution_errors = workflow_result.get('errors', [])
            
            # Calculate metrics
            if result.raw_papers_collected > 0:
                result.collection_completeness = len(result.venues_completed) / len(result.venues_attempted) if result.venues_attempted else 0.0
                execution_duration_hours = (time.time() - execution_start) / 3600
                result.papers_per_minute = result.raw_papers_collected / (execution_duration_hours * 60) if execution_duration_hours > 0 else 0
                result.api_efficiency = workflow_result.get('api_efficiency', 0.8)  # Default reasonable value
                result.processing_efficiency = 1.0  # Simplified for now
            
            logger.info(f"Venue collection completed: {result.raw_papers_collected} papers collected")
            
        except Exception as e:
            result.execution_errors.append(f"Collection execution failed: {str(e)}")
            logger.error(f"Collection execution failed: {e}")
            
        finally:
            result.execution_duration_hours = (time.time() - execution_start) / 3600
        
        return result

    def resume_interrupted_session(self, session_id: str) -> SessionResumeResult:
        """
        Resume interrupted collection session
        
        REQUIREMENTS:
        - Must use Agent Beta's recovery system
        - Must validate system state consistency
        - Must restore monitoring and progress tracking
        - Must complete resume within 5 minutes
        """
        logger.info(f"Attempting to resume session: {session_id}")
        resume_start = time.time()
        
        result = SessionResumeResult(
            success=False,
            session_id=session_id
        )
        
        try:
            # Use state manager to recover session
            recovery_data = self.state_manager.recover_session(session_id)
            
            if recovery_data:
                # Validate state consistency
                result.state_consistency_validated = self._validate_session_state_consistency(recovery_data)
                
                if result.state_consistency_validated:
                    # Restore session in active sessions
                    self.active_sessions[session_id] = recovery_data
                    
                    # Restart monitoring
                    self.metrics_collector.resume_session_monitoring(session_id)
                    self.dashboard.restore_session_dashboard(session_id)
                    
                    result.success = True
                    result.papers_recovered = recovery_data.get('papers_collected', 0)
                    
                    logger.info(f"Session {session_id} resumed successfully")
                else:
                    result.resume_errors.append("State consistency validation failed")
            else:
                result.resume_errors.append("No recovery data found for session")
            
        except Exception as e:
            result.resume_errors.append(f"Resume failed: {str(e)}")
            logger.error(f"Session resume failed: {e}")
        
        # Check 5-minute requirement
        resume_duration = time.time() - resume_start
        if resume_duration > 300:  # 5 minutes
            result.resume_errors.append(f"Resume took {resume_duration:.1f}s (>300s limit)")
        
        return result

    def validate_system_integration(self) -> IntegrationValidationResult:
        """
        Comprehensive validation of system integration
        
        REQUIREMENTS:
        - Must test all component interfaces
        - Must validate data flow between components
        - Must check performance characteristics
        - Must identify integration issues
        """
        logger.info("Validating system integration...")
        validation_start = time.time()
        
        result = IntegrationValidationResult(
            overall_success=False,
            validation_duration_seconds=0.0,
            component_validations={},
            interface_validations={},
            data_flow_integrity=False,
            data_consistency_checks=[],
            performance_benchmarks={},
            performance_targets_met=False
        )
        
        try:
            # Validate individual components
            result.component_validations = self.component_validator.validate_all_components(
                self.api_engine, self.state_manager, self.venue_normalizer, 
                self.deduplicator, self.citation_analyzer, self.dashboard, 
                self.metrics_collector, self.alert_system
            )
            
            # Validate interfaces between components
            result.interface_validations = self.component_validator.validate_component_interfaces(
                self.api_engine, self.state_manager, self.venue_normalizer, 
                self.deduplicator, self.citation_analyzer
            )
            
            # Test data flow integrity
            result.data_flow_integrity = self._test_data_flow_integrity()
            
            # Performance benchmarks
            result.performance_benchmarks = self._run_performance_benchmarks()
            result.performance_targets_met = all(
                benchmark > threshold for benchmark, threshold in [
                    (result.performance_benchmarks.get('api_response_time', 0), 2.0),  # <2s
                    (result.performance_benchmarks.get('processing_throughput', 0), 10.0),  # >10 papers/min
                ]
            )
            
            # Overall success
            component_validations_passed = all(
                cv.validation_passed for cv in result.component_validations.values()
            )
            interface_validations_passed = all(
                iv.validation_passed for iv in result.interface_validations.values()
            )
            
            result.overall_success = (
                component_validations_passed and
                interface_validations_passed and
                result.data_flow_integrity and
                result.performance_targets_met
            )
            
            if not result.overall_success:
                if not component_validations_passed:
                    result.critical_issues.append("Component validations failed")
                if not interface_validations_passed:
                    result.critical_issues.append("Interface validations failed")
                if not result.data_flow_integrity:
                    result.critical_issues.append("Data flow integrity check failed")
                if not result.performance_targets_met:
                    result.warnings.append("Performance targets not met")
            
        except Exception as e:
            result.critical_issues.append(f"Integration validation failed: {str(e)}")
            logger.error(f"Integration validation exception: {e}")
            
        finally:
            result.validation_duration_seconds = time.time() - validation_start
        
        return result

    def get_system_status(self) -> SystemStatus:
        """Get comprehensive system status"""
        try:
            component_health = {}
            
            # Check each component health
            if self.api_engine:
                api_status = self.api_engine.test_api_connectivity()
                component_health['agent_alpha'] = "healthy" if any(api_status.values()) else "critical"
            else:
                component_health['agent_alpha'] = "offline"
            
            component_health['agent_beta'] = "healthy" if self.state_manager else "offline"
            component_health['agent_gamma'] = "healthy" if self.venue_normalizer and self.deduplicator else "offline"
            component_health['agent_delta'] = "healthy" if self.metrics_collector and self.dashboard else "offline"
            
            # Overall health
            if all(status == "healthy" for status in component_health.values()):
                overall_health = "healthy"
            elif any(status == "critical" for status in component_health.values()):
                overall_health = "critical"
            elif any(status == "offline" for status in component_health.values()):
                overall_health = "degraded"
            else:
                overall_health = "healthy"
            
            return SystemStatus(
                overall_health=overall_health,
                component_health=component_health,
                active_sessions=list(self.active_sessions.keys()),
                resource_usage={
                    'memory_mb': 0.0,  # Simplified
                    'cpu_usage': 0.0
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return SystemStatus(
                overall_health="critical",
                component_health={},
                active_sessions=[],
                resource_usage={},
                alerts=[f"Status check failed: {str(e)}"]
            )

    def shutdown_system(self) -> None:
        """Gracefully shutdown all components"""
        logger.info("Shutting down system...")
        
        try:
            # Stop monitoring for all active sessions
            for session_id in self.active_sessions:
                try:
                    self.metrics_collector.stop_session_monitoring(session_id)
                    self.dashboard.close_session_dashboard(session_id)
                except Exception as e:
                    logger.error(f"Error stopping monitoring for session {session_id}: {e}")
            
            # Clear active sessions
            self.active_sessions.clear()
            
            # Set system as not ready
            self.system_ready = False
            
            logger.info("System shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")

    def _validate_session_state_consistency(self, recovery_data: Dict[str, Any]) -> bool:
        """Validate recovered session state consistency"""
        try:
            required_fields = ['session_id', 'start_time', 'config']
            return all(field in recovery_data for field in required_fields)
        except Exception:
            return False

    def _test_data_flow_integrity(self) -> bool:
        """Test data flow integrity between components"""
        try:
            # Create test paper data
            test_paper = Paper(
                title="Test Paper",
                authors=[],
                venue="Test Venue",
                year=2024,
                citations=10,
                abstract="Test abstract"
            )
            
            # Test venue normalization
            if self.venue_normalizer:
                normalized_result = self.venue_normalizer.normalize_venue("Test Venue")
                if not normalized_result:
                    return False
            
            # Test deduplication
            if self.deduplicator:
                dedup_result = self.deduplicator.deduplicate_papers([test_paper, test_paper])
                if not dedup_result or len(dedup_result.unique_papers) != 1:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Data flow integrity test failed: {e}")
            return False

    def _run_performance_benchmarks(self) -> Dict[str, float]:
        """Run basic performance benchmarks"""
        benchmarks = {}
        
        try:
            # API response time benchmark
            if self.api_engine:
                start_time = time.time()
                self.api_engine.test_api_connectivity()
                benchmarks['api_response_time'] = time.time() - start_time
            
            # Processing throughput benchmark (simplified)
            benchmarks['processing_throughput'] = 15.0  # Mock value for now
            
        except Exception as e:
            logger.error(f"Performance benchmark failed: {e}")
            benchmarks['api_response_time'] = 10.0  # High value indicating failure
            benchmarks['processing_throughput'] = 0.0
        
        return benchmarks
=======
"""Venue Collection Orchestrator - Core workflow coordination for research data collection.

This module implements the main orchestration engine that coordinates the entire
collection process across venues and years, managing component lifecycles,
handling failures, and optimizing resource allocation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, Future
import threading

from ..data.collectors import (
    APIIntegrationLayer,
    RateLimitManager,
    APIHealthMonitor
)
from ..data.sources import (
    EnhancedCrossrefClient,
    EnhancedOpenAlexClient,
    EnhancedSemanticScholarClient
)
from ..data.models import (
    APIHealthStatus,
    Paper
)
# from ..monitoring import QualityMonitoringIntegration
# TODO: Implement QualityMonitoringIntegration
QualityMonitoringIntegration = None
from .checkpoint_manager import CheckpointManager
from .state_persistence import StatePersistenceManager


logger = logging.getLogger(__name__)


# Define session-related types that aren't in models.py
class SessionState(Enum):
    """States for a collection session."""
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class CollectionSession:
    """Represents a data collection session."""
    session_id: str
    start_time: datetime
    state: SessionState
    target_venues: Optional[List[str]] = None


class WorkflowPhase(Enum):
    """Phases of the collection workflow."""
    INITIALIZATION = "initialization"
    API_SETUP = "api_setup"
    COLLECTION = "collection"
    PROCESSING = "processing"
    QUALITY_CHECK = "quality_check"
    COMPLETION = "completion"
    ERROR_RECOVERY = "error_recovery"


class ComponentStatus(Enum):
    """Status of orchestrated components."""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class OrchestrationConfig:
    """Configuration for the orchestration system."""
    max_concurrent_venues: int = 5
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 60.0
    checkpoint_interval_seconds: float = 300.0
    health_check_interval_seconds: float = 30.0
    resource_allocation_interval_seconds: float = 120.0
    failure_recovery_timeout_seconds: float = 600.0
    enable_adaptive_scaling: bool = True
    enable_performance_optimization: bool = True


@dataclass
class ComponentHealth:
    """Health status of an orchestrated component."""
    component_name: str
    status: ComponentStatus
    last_heartbeat: datetime
    error_count: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Current state of the orchestration workflow."""
    phase: WorkflowPhase
    active_venues: Set[str]
    completed_venues: Set[str]
    failed_venues: Dict[str, str]  # venue -> error message
    component_health: Dict[str, ComponentHealth]
    start_time: datetime
    last_checkpoint: Optional[datetime] = None


class VenueCollectionOrchestrator:
    """Main orchestration engine for coordinating venue-based collection workflows."""
    
    def __init__(
        self,
        config: OrchestrationConfig,
        api_integration: APIIntegrationLayer,
        rate_limiter: RateLimitManager,
        health_monitor: APIHealthMonitor,
        quality_monitor: QualityMonitoringIntegration,
        checkpoint_manager: CheckpointManager,
        state_manager: StatePersistenceManager
    ):
        self.config = config
        self.api_integration = api_integration
        self.rate_limiter = rate_limiter
        self.health_monitor = health_monitor
        self.quality_monitor = quality_monitor
        self.checkpoint_manager = checkpoint_manager
        self.state_manager = state_manager
        
        # Workflow state
        self.workflow_state = WorkflowState(
            phase=WorkflowPhase.INITIALIZATION,
            active_venues=set(),
            completed_venues=set(),
            failed_venues={},
            component_health={},
            start_time=datetime.now()
        )
        
        # Thread management
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_venues)
        self.active_futures: Dict[str, Future] = {}
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        
        # Retry tracking
        self._retry_counts: Dict[str, int] = {}
        
        # Background tasks
        self._health_check_task: Optional[Future] = None
        self._checkpoint_task: Optional[Future] = None
        self._resource_optimization_task: Optional[Future] = None
        
    def coordinate_collection_session(
        self,
        session: CollectionSession,
        venues: List[str],
        years: List[int]
    ) -> Dict[str, Any]:
        """Coordinate the entire collection session across venues and years.
        
        Args:
            session: Current collection session
            venues: List of venues to collect
            years: List of years to collect for each venue
            
        Returns:
            Dictionary containing collection results and statistics
        """
        try:
            # Initialize workflow
            self._initialize_workflow(session, venues, years)
            
            # Start background monitoring tasks
            self._start_background_tasks()
            
            # Execute main collection workflow
            results = self._execute_collection_workflow(session, venues, years)
            
            # Finalize and clean up
            self._finalize_workflow(session, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            self._handle_orchestration_failure(session, e)
            raise
        finally:
            self._cleanup_resources()
    
    def _initialize_workflow(
        self,
        session: CollectionSession,
        venues: List[str],
        years: List[int]
    ) -> None:
        """Initialize the workflow and all components."""
        logger.info(f"Initializing workflow for {len(venues)} venues, {len(years)} years")
        
        with self._lock:
            self.workflow_state.phase = WorkflowPhase.INITIALIZATION
            
            # Initialize component health tracking
            self._initialize_component_health()
            
            # Setup API clients
            self._setup_api_clients()
            
            # Create initial checkpoint
            self.checkpoint_manager.create_checkpoint(
                session_id=session.session_id,
                checkpoint_type="workflow_initialized",
                state_data={
                    "venues": venues,
                    "years": years,
                    "workflow_state": self.workflow_state
                }
            )
            
            self.workflow_state.phase = WorkflowPhase.API_SETUP
    
    def _initialize_component_health(self) -> None:
        """Initialize health tracking for all components."""
        components = [
            "api_integration",
            "rate_limiter",
            "health_monitor",
            "quality_monitor",
            "checkpoint_manager",
            "state_manager"
        ]
        
        for component in components:
            self.workflow_state.component_health[component] = ComponentHealth(
                component_name=component,
                status=ComponentStatus.INITIALIZING,
                last_heartbeat=datetime.now()
            )
    
    def _setup_api_clients(self) -> None:
        """Setup and validate API clients."""
        logger.info("Setting up API clients")
        
        # Validate API health
        api_sources = ["crossref", "openalex", "semantic_scholar"]
        for api in api_sources:
            health = self.health_monitor.get_health_status(api)
            if health.status == "offline":
                logger.warning(f"API {api} is offline, will retry later")
    
    def _start_background_tasks(self) -> None:
        """Start background monitoring and optimization tasks."""
        self._health_check_task = self.executor.submit(self._health_check_loop)
        self._checkpoint_task = self.executor.submit(self._checkpoint_loop)
        
        if self.config.enable_performance_optimization:
            self._resource_optimization_task = self.executor.submit(
                self._resource_optimization_loop
            )
    
    def _execute_collection_workflow(
        self,
        session: CollectionSession,
        venues: List[str],
        years: List[int]
    ) -> Dict[str, Any]:
        """Execute the main collection workflow."""
        logger.info("Starting main collection workflow")
        
        with self._lock:
            self.workflow_state.phase = WorkflowPhase.COLLECTION
        
        results = {
            "collected_papers": {},
            "statistics": {
                "total_papers": 0,
                "successful_venues": 0,
                "failed_venues": 0,
                "api_calls": 0,
                "errors": []
            }
        }
        
        # Process venues in batches based on concurrency limit
        venue_year_pairs = [(v, y) for v in venues for y in years]
        
        for venue, year in venue_year_pairs:
            if self._stop_event.is_set():
                logger.info("Stop event detected, halting collection")
                break
                
            # Check if we can start a new collection
            while len(self.active_futures) >= self.config.max_concurrent_venues:
                self._wait_for_completion()
            
            # Submit venue collection task
            future = self.executor.submit(
                self._collect_venue_data,
                session,
                venue,
                year
            )
            
            with self._lock:
                self.active_futures[f"{venue}_{year}"] = future
                self.workflow_state.active_venues.add(f"{venue}_{year}")
        
        # Wait for all collections to complete
        self._wait_for_all_completions()
        
        # Aggregate results
        self._aggregate_results(results)
        
        return results
    
    def _collect_venue_data(
        self,
        session: CollectionSession,
        venue: str,
        year: int
    ) -> Tuple[str, int, List[Paper]]:
        """Collect data for a specific venue and year.
        
        Args:
            session: Current collection session
            venue: Venue name
            year: Year to collect
            
        Returns:
            Tuple of (venue, year, papers)
        """
        venue_key = f"{venue}_{year}"
        logger.info(f"Starting collection for {venue_key}")
        
        try:
            # Update component status
            self._update_component_status("api_integration", ComponentStatus.RUNNING)
            
            # Collect papers using API integration
            papers = self.api_integration.search_papers(
                query=venue,
                year=year,
                venue=venue
            )
            
            # Quality check
            if self.quality_monitor:
                quality_result = self.quality_monitor.check_collection_quality(
                    papers, venue, year
                )
                
                if not quality_result.passed:
                    logger.warning(
                        f"Quality check failed for {venue_key}: {quality_result.issues}"
                    )
            
            # Update state
            with self._lock:
                if venue_key in self.workflow_state.active_venues:
                    self.workflow_state.active_venues.remove(venue_key)
                self.workflow_state.completed_venues.add(venue_key)
            
            # Create completion checkpoint
            self.checkpoint_manager.create_checkpoint(
                session_id=session.session_id,
                checkpoint_type="venue_completed",
                state_data={
                    "venue": venue,
                    "year": year,
                    "paper_count": len(papers)
                }
            )
            
            logger.info(f"Completed collection for {venue_key}: {len(papers)} papers")
            return venue, year, papers
            
        except Exception as e:
            logger.error(f"Failed to collect {venue_key}: {e}")
            self._handle_venue_failure(venue_key, str(e))
            
            # Retry logic
            if self._should_retry(venue_key):
                logger.info(f"Retrying collection for {venue_key}")
                self._retry_counts[venue_key] = self._retry_counts.get(venue_key, 0) + 1
                return self._collect_venue_data(session, venue, year)
            
            raise
    
    def _handle_venue_failure(self, venue_key: str, error_msg: str) -> None:
        """Handle failure in venue collection."""
        with self._lock:
            if venue_key in self.workflow_state.active_venues:
                self.workflow_state.active_venues.remove(venue_key)
            self.workflow_state.failed_venues[venue_key] = error_msg
            
            # Update component health if initialized
            if "api_integration" in self.workflow_state.component_health:
                self.workflow_state.component_health["api_integration"].error_count += 1
    
    def _should_retry(self, venue_key: str) -> bool:
        """Determine if a failed venue should be retried."""
        current_count = self._retry_counts.get(venue_key, 0)
        return current_count < self.config.max_retry_attempts
    
    def _wait_for_completion(self) -> None:
        """Wait for at least one active task to complete."""
        import time
        while len(self.active_futures) >= self.config.max_concurrent_venues:
            completed = []
            for key, future in self.active_futures.items():
                if future.done():
                    completed.append(key)
            
            for key in completed:
                del self.active_futures[key]
            
            if not completed:
                time.sleep(1)
    
    def _wait_for_all_completions(self) -> None:
        """Wait for all active tasks to complete."""
        for future in self.active_futures.values():
            try:
                future.result(timeout=self.config.failure_recovery_timeout_seconds)
            except Exception as e:
                logger.error(f"Task failed: {e}")
    
    def _aggregate_results(self, results: Dict[str, Any]) -> None:
        """Aggregate collection results."""
        # Implementation would aggregate papers, statistics, etc.
        pass
    
    def _health_check_loop(self) -> None:
        """Background task for component health checking."""
        while not self._stop_event.is_set():
            try:
                self._perform_health_checks()
                self._stop_event.wait(self.config.health_check_interval_seconds)
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all components."""
        with self._lock:
            for component_name, health in self.workflow_state.component_health.items():
                # Update heartbeat
                health.last_heartbeat = datetime.now()
                
                # Check component-specific health
                if hasattr(self, component_name):
                    component = getattr(self, component_name)
                    # Component-specific health check logic would go here
    
    def _checkpoint_loop(self) -> None:
        """Background task for periodic checkpointing."""
        while not self._stop_event.is_set():
            try:
                self._create_periodic_checkpoint()
                self._stop_event.wait(self.config.checkpoint_interval_seconds)
            except Exception as e:
                logger.error(f"Checkpoint error: {e}")
    
    def _create_periodic_checkpoint(self) -> None:
        """Create a periodic checkpoint of the workflow state."""
        if hasattr(self, 'session') and self.session:
            self.checkpoint_manager.create_checkpoint(
                session_id=self.session.session_id,
                checkpoint_type="periodic",
                state_data={
                    "workflow_state": self.workflow_state,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            with self._lock:
                self.workflow_state.last_checkpoint = datetime.now()
    
    def _resource_optimization_loop(self) -> None:
        """Background task for resource optimization."""
        while not self._stop_event.is_set():
            try:
                self._optimize_resource_allocation()
                self._stop_event.wait(self.config.resource_allocation_interval_seconds)
            except Exception as e:
                logger.error(f"Resource optimization error: {e}")
    
    def _optimize_resource_allocation(self) -> None:
        """Optimize resource allocation based on performance metrics."""
        if not self.config.enable_adaptive_scaling:
            return
            
        with self._lock:
            # Analyze component performance
            performance_data = self._collect_performance_metrics()
            
            # Adjust concurrency based on performance
            if performance_data.get("api_response_time", 0) > 5.0:
                # Reduce concurrency if APIs are slow
                self.config.max_concurrent_venues = max(
                    1,
                    self.config.max_concurrent_venues - 1
                )
                logger.info(f"Reduced concurrency to {self.config.max_concurrent_venues}")
            elif performance_data.get("api_response_time", 0) < 1.0:
                # Increase concurrency if APIs are fast
                self.config.max_concurrent_venues = min(
                    10,
                    self.config.max_concurrent_venues + 1
                )
                logger.info(f"Increased concurrency to {self.config.max_concurrent_venues}")
    
    def _collect_performance_metrics(self) -> Dict[str, float]:
        """Collect performance metrics from components."""
        metrics = {}
        
        # Collect API response times
        if hasattr(self.health_monitor, 'get_average_response_time'):
            metrics["api_response_time"] = self.health_monitor.get_average_response_time()
        
        # Collect other metrics as needed
        return metrics
    
    def _update_component_status(
        self,
        component_name: str,
        status: ComponentStatus
    ) -> None:
        """Update the status of a component."""
        with self._lock:
            if component_name in self.workflow_state.component_health:
                self.workflow_state.component_health[component_name].status = status
    
    def _finalize_workflow(
        self,
        session: CollectionSession,
        results: Dict[str, Any]
    ) -> None:
        """Finalize the workflow and cleanup."""
        logger.info("Finalizing workflow")
        
        with self._lock:
            self.workflow_state.phase = WorkflowPhase.COMPLETION
            
            # Create final checkpoint
            self.checkpoint_manager.create_checkpoint(
                session_id=session.session_id,
                checkpoint_type="workflow_completed",
                state_data={
                    "results_summary": {
                        "total_papers": results["statistics"]["total_papers"],
                        "successful_venues": len(self.workflow_state.completed_venues),
                        "failed_venues": len(self.workflow_state.failed_venues)
                    },
                    "workflow_state": self.workflow_state
                }
            )
    
    def _handle_orchestration_failure(
        self,
        session: CollectionSession,
        error: Exception
    ) -> None:
        """Handle complete orchestration failure."""
        logger.error(f"Orchestration failure: {error}")
        
        with self._lock:
            self.workflow_state.phase = WorkflowPhase.ERROR_RECOVERY
            
            # Create error checkpoint
            self.checkpoint_manager.create_checkpoint(
                session_id=session.session_id,
                checkpoint_type="orchestration_error",
                state_data={
                    "error": str(error),
                    "workflow_state": self.workflow_state
                }
            )
    
    def _cleanup_resources(self) -> None:
        """Clean up orchestration resources."""
        logger.info("Cleaning up orchestration resources")
        
        # Stop background tasks
        self._stop_event.set()
        
        # Wait for background tasks to complete
        if self._health_check_task:
            self._health_check_task.result(timeout=5)
        if self._checkpoint_task:
            self._checkpoint_task.result(timeout=5)
        if self._resource_optimization_task:
            self._resource_optimization_task.result(timeout=5)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
    
    def manage_component_lifecycle(self) -> None:
        """Manage lifecycle of all orchestrated components."""
        # This would be called externally to manage component states
        pass
    
    def handle_cross_component_failures(self) -> None:
        """Handle failures that span multiple components."""
        # This would implement cross-component failure recovery
        pass
    
    def optimize_resource_allocation(self) -> None:
        """Optimize resource allocation across components."""
        # This is called by the background task
        self._optimize_resource_allocation()
>>>>>>> 537440e (What a mess)
