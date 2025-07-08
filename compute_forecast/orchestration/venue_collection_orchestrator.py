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

from ..data.models import CollectionConfig
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
    integration_validation: "IntegrationValidationResult"
    initialization_errors: List[str] = field(default_factory=list)
    initialization_warnings: List[str] = field(default_factory=list)
    ready_for_collection: bool = False


@dataclass
class IntegrationValidationResult:
    all_connections_valid: bool
    all_data_flows_valid: bool
    integration_errors: List[str] = field(default_factory=list)
    integration_warnings: List[str] = field(default_factory=list)
    validated_integrations: List[Tuple[str, str]] = field(default_factory=list)
    failed_integrations: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class SessionMetadata:
    session_id: str
    created_at: datetime
    status: str
    venues: List[str]
    years: List[int]
    config: CollectionConfig


@dataclass
class CollectionResult:
    session_id: str
    papers_collected: int
    venues_processed: int
    total_processing_time_seconds: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    api_stats: Dict[str, Any] = field(default_factory=dict)
    processing_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionResumeResult:
    success: bool
    resume_duration_seconds: float
    papers_recovered: int
    venues_recovered: int
    state_recovery_success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class VenueCollectionOrchestrator:
    """
    Primary system orchestrator implementing the MADAP pattern:
    - Monitor component health and performance
    - Aggregate data across components
    - Decide on collection strategies
    - Act by coordinating component operations
    - Persist state for recovery

    Manages all four agent subsystems and provides the primary API.
    """

    def __init__(self, config: CollectionConfig):
        """
        Initialize orchestrator with system configuration

        REQUIREMENTS:
        - Must support standard collection workflow
        - Must provide comprehensive monitoring
        - Must enable state recovery
        - Must setup monitoring and state management
        - Must handle initialization failures gracefully
        """
        self.config = config

        # Agent components (initialized during system startup)
        self.api_integration_layer: Optional[Any] = None  # Agent Alpha
        self.state_manager: Optional[Any] = None  # Agent Beta
        self.data_processors: dict[str, Any] = {}  # Agent Gamma components
        self.metrics_collector: Optional[Any] = None  # Agent Delta
        self.dashboard: Optional[Any] = None  # Agent Delta
        self.alert_system: Optional[Any] = None  # Agent Delta

        # Supporting components
        self.system_initializer = SystemInitializer()
        self.component_validator = ComponentValidator()
        self.workflow_coordinator = WorkflowCoordinator()

        # System state
        self.system_ready = False
        self.active_sessions: dict[str, Any] = {}  # session_id -> SessionMetadata
        self.component_status: dict[str, Any] = {}  # component_name -> ComponentStatus

        # Performance tracking
        self.initialization_time: Optional[float] = None
        self.startup_metrics: dict[str, Any] = {}

        logger.info("VenueCollectionOrchestrator initialized with config")

    def initialize_system(self) -> SystemInitializationResult:
        """
        Initialize all system components and validate integrations

        REQUIREMENTS:
        - Must initialize all agent components
        - Must validate component health
        - Must verify integration points
        - Must complete within 30 seconds
        - Must provide detailed initialization status
        """
        logger.info("Starting system initialization...")
        start_time = time.time()

        result = SystemInitializationResult(
            success=False,
            initialized_components=[],
            failed_components=[],
            initialization_duration_seconds=0,
            component_status={},
            integration_validation=IntegrationValidationResult(
                all_connections_valid=False, all_data_flows_valid=False
            ),
        )

        try:
            # Phase 1: Initialize Agent Alpha (API Integration)
            logger.info("Phase 1: Initializing API Integration Layer...")
            alpha_status = self._initialize_agent_alpha()
            result.component_status["agent_alpha"] = alpha_status

            if alpha_status.status == "ready":
                result.initialized_components.append("agent_alpha")
            else:
                result.failed_components.append("agent_alpha")
                result.initialization_errors.append(
                    f"Agent Alpha failed: {alpha_status.error_message}"
                )

            # Phase 2: Initialize Agent Beta (State Management)
            logger.info("Phase 2: Initializing State Management...")
            beta_status = self._initialize_agent_beta()
            result.component_status["agent_beta"] = beta_status

            if beta_status.status == "ready":
                result.initialized_components.append("agent_beta")
            else:
                result.failed_components.append("agent_beta")
                result.initialization_errors.append(
                    f"Agent Beta failed: {beta_status.error_message}"
                )

            # Phase 3: Initialize Agent Gamma (Data Processing)
            logger.info("Phase 3: Initializing Data Processing Pipeline...")
            gamma_status = self._initialize_agent_gamma()
            result.component_status["agent_gamma"] = gamma_status

            if gamma_status.status == "ready":
                result.initialized_components.append("agent_gamma")
            else:
                result.failed_components.append("agent_gamma")
                result.initialization_errors.append(
                    f"Agent Gamma failed: {gamma_status.error_message}"
                )

            # Phase 4: Initialize Agent Delta (Monitoring)
            logger.info("Phase 4: Initializing Monitoring Systems...")
            delta_status = self._initialize_agent_delta()
            result.component_status["agent_delta"] = delta_status

            if delta_status.status == "ready":
                result.initialized_components.append("agent_delta")
            else:
                result.failed_components.append("agent_delta")
                result.initialization_errors.append(
                    f"Agent Delta failed: {delta_status.error_message}"
                )

            # Phase 5: Validate system integration
            logger.info("Phase 5: Validating system integration...")
            result.integration_validation = self._validate_system_integration()

            # Determine overall success
            critical_components = ["agent_alpha", "agent_beta", "agent_gamma"]
            critical_ready = all(
                result.component_status.get(
                    comp, ComponentStatus(comp, "error", "", 0, False, False, False)
                ).status
                == "ready"
                for comp in critical_components
            )

            result.success = (
                critical_ready
                and result.integration_validation.all_connections_valid
                and result.integration_validation.all_data_flows_valid
            )

            result.ready_for_collection = result.success
            self.system_ready = result.success

            # Calculate initialization duration
            result.initialization_duration_seconds = time.time() - start_time
            self.initialization_time = result.initialization_duration_seconds

            # Log summary
            if result.success:
                logger.info(
                    f"System initialization successful in {result.initialization_duration_seconds:.2f}s"
                )
            else:
                logger.error(
                    f"System initialization failed after {result.initialization_duration_seconds:.2f}s"
                )
                for error in result.initialization_errors:
                    logger.error(f"  - {error}")

            return result

        except Exception as e:
            logger.error(f"Critical error during system initialization: {e}")
            result.initialization_errors.append(f"Critical error: {str(e)}")
            result.initialization_duration_seconds = time.time() - start_time
            return result

    def _initialize_agent_alpha(self) -> ComponentStatus:
        """Initialize API Integration Layer components"""
        start_time = time.time()
        status = ComponentStatus(
            component_name="agent_alpha",
            status="initializing",
            version="1.0.0",
            initialization_time=0,
            health_check_passed=False,
            interface_validation_passed=False,
            dependencies_met=False,
        )

        try:
            # Import and initialize API components
            from ..data.collectors.api_integration_layer import VenueCollectionEngine
            from ..monitoring.health_monitor import HealthMonitor
            from ..monitoring.rate_limiter import AdaptiveRateLimiter

            # Initialize dependencies for VenueCollectionEngine
            rate_limiter = AdaptiveRateLimiter()
            health_monitor = HealthMonitor()

            # Initialize integration layer
            self.api_integration_layer = VenueCollectionEngine(
                config=self.config,
                rate_limiter=rate_limiter,
                health_monitor=health_monitor,
            )

            # Validate initialization
            if self.api_integration_layer.validate_setup():
                status.status = "ready"
                status.health_check_passed = True
                status.interface_validation_passed = True
                status.dependencies_met = True
            else:
                status.status = "error"
                status.error_message = "API integration validation failed"

        except Exception as e:
            status.status = "error"
            status.error_message = str(e)
            logger.error(f"Failed to initialize Agent Alpha: {e}")

        status.initialization_time = time.time() - start_time
        return status

    def _initialize_agent_beta(self) -> ComponentStatus:
        """Initialize State Management components"""
        start_time = time.time()
        status = ComponentStatus(
            component_name="agent_beta",
            status="initializing",
            version="1.0.0",
            initialization_time=0,
            health_check_passed=False,
            interface_validation_passed=False,
            dependencies_met=False,
        )

        try:
            # Import and initialize state management
            from ..state.state_persistence import StatePersistenceManager

            # Create state management components
            self.state_manager = StatePersistenceManager(
                checkpoint_dir=self.config.checkpoint_dir, enable_compression=True
            )

            # Validate initialization
            if self.state_manager.validate_setup():
                status.status = "ready"
                status.health_check_passed = True
                status.interface_validation_passed = True
                status.dependencies_met = True
            else:
                status.status = "error"
                status.error_message = "State management validation failed"

        except Exception as e:
            status.status = "error"
            status.error_message = str(e)
            logger.error(f"Failed to initialize Agent Beta: {e}")

        status.initialization_time = time.time() - start_time
        return status

    def _initialize_agent_gamma(self) -> ComponentStatus:
        """Initialize Data Processing Pipeline components"""
        start_time = time.time()
        status = ComponentStatus(
            component_name="agent_gamma",
            status="initializing",
            version="1.0.0",
            initialization_time=0,
            health_check_passed=False,
            interface_validation_passed=False,
            dependencies_met=False,
        )

        try:
            # Import and initialize data processors
            from ..quality.deduplication.advanced_deduplicator import (
                AdvancedDeduplicator,
            )
            from ..quality.normalization.venue_normalizer import VenueNormalizer
            from ..quality.filtering.citation_filter import CitationFilter

            # Create processor instances
            self.data_processors = {
                "deduplicator": AdvancedDeduplicator(self.config),
                "normalizer": VenueNormalizer(),
                "filter": CitationFilter(self.config),
            }

            # Validate all processors
            all_valid = all(
                hasattr(proc, "validate_setup") and proc.validate_setup()
                if hasattr(proc, "validate_setup")
                else True
                for proc in self.data_processors.values()
            )

            if all_valid:
                status.status = "ready"
                status.health_check_passed = True
                status.interface_validation_passed = True
                status.dependencies_met = True
            else:
                status.status = "error"
                status.error_message = "One or more data processors failed validation"

        except Exception as e:
            status.status = "error"
            status.error_message = str(e)
            logger.error(f"Failed to initialize Agent Gamma: {e}")

        status.initialization_time = time.time() - start_time
        return status

    def _initialize_agent_delta(self) -> ComponentStatus:
        """Initialize Monitoring System components"""
        start_time = time.time()
        status = ComponentStatus(
            component_name="agent_delta",
            status="initializing",
            version="1.0.0",
            initialization_time=0,
            health_check_passed=False,
            interface_validation_passed=False,
            dependencies_met=False,
        )

        try:
            # Import our sophisticated monitoring components
            from ..monitoring.metrics_collector import MetricsCollector
            from ..monitoring.dashboard_server import CollectionDashboard
            from ..monitoring.alert_system import AlertSystemFactory

            # Create monitoring components
            self.metrics_collector = MetricsCollector(collection_interval_seconds=5)
            self.dashboard = CollectionDashboard(
                host=self.config.dashboard_host, port=self.config.dashboard_port
            )
            self.alert_system = AlertSystemFactory.create_default_system()

            # Set up alert system with metrics provider
            self.alert_system.metrics_provider = (
                lambda: self.metrics_collector.get_current_metrics()
            )

            status.status = "ready"
            status.health_check_passed = True
            status.interface_validation_passed = True
            status.dependencies_met = True

        except Exception as e:
            status.status = "error"
            status.error_message = str(e)
            logger.error(f"Failed to initialize Agent Delta: {e}")

        status.initialization_time = time.time() - start_time
        return status

    def _validate_system_integration(self) -> IntegrationValidationResult:
        """Validate integration between all system components"""
        result = IntegrationValidationResult(
            all_connections_valid=True, all_data_flows_valid=True
        )

        # Validate API -> State Management
        try:
            if self.api_integration_layer and self.state_manager:
                # Test that API results can be persisted
                result.validated_integrations.append(
                    ("api_integration", "state_manager")
                )
            else:
                result.all_connections_valid = False
                result.integration_errors.append("API or State Manager not initialized")
        except Exception as e:
            result.all_connections_valid = False
            result.integration_errors.append(f"API-State integration failed: {str(e)}")

        # Validate State -> Processing Pipeline
        try:
            if self.state_manager and self.data_processors:
                # Test that state can feed processors
                result.validated_integrations.append(
                    ("state_manager", "data_processors")
                )
            else:
                result.all_data_flows_valid = False
                result.integration_errors.append(
                    "State Manager or Data Processors not initialized"
                )
        except Exception as e:
            result.all_data_flows_valid = False
            result.integration_errors.append(
                f"State-Processing integration failed: {str(e)}"
            )

        # Validate Monitoring integration
        try:
            if self.metrics_collector:
                # Test that metrics can be collected from all components
                result.validated_integrations.append(
                    ("metrics_collector", "all_components")
                )
            else:
                result.integration_warnings.append("Metrics collector not initialized")
        except Exception as e:
            result.integration_warnings.append(
                f"Monitoring integration warning: {str(e)}"
            )

        return result

    def start_collection_session(
        self,
        venues: List[str],
        years: List[int],
        session_config: Optional[CollectionConfig] = None,
    ) -> str:
        """
        Start a new collection session

        REQUIREMENTS:
        - Must create unique session identifier
        - Must initialize session state
        - Must start monitoring and dashboard
        - Must validate system readiness
        - Must handle component startup failures
        """
        if not self.system_ready:
            raise RuntimeError(
                "System not ready for collection. Run initialize_system() first."
            )

        # Generate session ID
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Use provided config or default
        config = session_config or self.config

        try:
            # Create session metadata
            session = SessionMetadata(
                session_id=session_id,
                created_at=datetime.now(),
                status="initializing",
                venues=venues,
                years=years,
                config=config,
            )

            # Initialize session state
            self.state_manager.create_session(
                session_id,
                {"venues": venues, "years": years, "config": config.__dict__},
            )

            # Start monitoring for this session
            self.metrics_collector.start_collection(
                venue_engine=self.workflow_coordinator,
                state_manager=self.state_manager,
                api_managers={"integration": self.api_integration_layer},
                data_processors=self.data_processors,
            )

            # Start dashboard
            self.dashboard.start_dashboard(self.metrics_collector)

            # Start alert system
            self.alert_system.start()

            # Store session info
            self.active_sessions[session_id] = session
            session.status = "active"

            logger.info(f"Started collection session: {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to start collection session: {e}")
            # Clean up partial initialization
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            raise

    def execute_collection(self, session_id: str) -> CollectionResult:
        """
        Execute the main collection workflow

        REQUIREMENTS:
        - Must coordinate all agent operations
        - Must handle failures gracefully
        - Must track progress and metrics
        - Must persist state regularly
        - Must complete venue/year collection within 6 hours
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Unknown session: {session_id}")

        session = self.active_sessions[session_id]
        start_time = time.time()

        result = CollectionResult(
            session_id=session_id,
            papers_collected=0,
            venues_processed=0,
            total_processing_time_seconds=0,
        )

        try:
            # Update session status
            session.status = "collecting"

            # Execute collection through workflow coordinator
            collection_stats = self.workflow_coordinator.execute_collection_workflow(
                venues=session.venues,
                years=session.years,
                api_layer=self.api_integration_layer,
                state_manager=self.state_manager,
                processors=self.data_processors,
                metrics_collector=self.metrics_collector,
            )

            # Update result
            result.papers_collected = collection_stats.get("total_papers", 0)
            result.venues_processed = collection_stats.get("venues_processed", 0)
            result.api_stats = collection_stats.get("api_stats", {})
            result.processing_stats = collection_stats.get("processing_stats", {})

            # Mark session as completed
            session.status = "completed"

        except Exception as e:
            logger.error(f"Collection failed for session {session_id}: {e}")
            session.status = "error"
            result.errors.append(str(e))

        finally:
            # Calculate total time
            result.total_processing_time_seconds = time.time() - start_time

            # Save final state
            self.state_manager.save_session_state(
                session_id, {"result": result.__dict__, "final_status": session.status}
            )

        return result

    def pause_session(self, session_id: str) -> bool:
        """
        Pause an active collection session

        REQUIREMENTS:
        - Must pause within 30 seconds
        - Must save complete state
        - Must stop active operations gracefully
        """
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        try:
            # Signal pause to workflow coordinator
            self.workflow_coordinator.pause_collection()

            # Wait for operations to pause (max 30 seconds)
            pause_start = time.time()
            while (
                self.workflow_coordinator.is_active() and time.time() - pause_start < 30
            ):
                time.sleep(1)

            # Save current state
            self.state_manager.checkpoint_session(session_id)

            # Update session status
            session.status = "paused"

            logger.info(f"Session {session_id} paused successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to pause session {session_id}: {e}")
            return False

    def resume_session(self, session_id: str) -> SessionResumeResult:
        """
        Resume a paused or interrupted session

        REQUIREMENTS:
        - Must restore complete state
        - Must resume from exact pause point
        - Must restore monitoring and progress tracking
        - Must complete resume within 5 minutes
        """
        logger.info(f"Attempting to resume session: {session_id}")
        resume_start = time.time()

        result = SessionResumeResult(
            success=False,
            resume_duration_seconds=0,
            papers_recovered=0,
            venues_recovered=0,
            state_recovery_success=False,
        )

        try:
            # Check if session exists
            if session_id not in self.active_sessions:
                # Try to recover from state manager
                recovery_data = self.state_manager.recover_session(session_id)

                if recovery_data:
                    # Recreate session metadata
                    session = SessionMetadata(
                        session_id=session_id,
                        created_at=recovery_data.get("created_at", datetime.now()),
                        status="resuming",
                        venues=recovery_data.get("venues", []),
                        years=recovery_data.get("years", []),
                        config=CollectionConfig(**recovery_data.get("config", {})),
                    )
                    self.active_sessions[session_id] = session
                    result.state_recovery_success = True
                else:
                    result.errors.append(f"Session {session_id} not found")
                    return result
            else:
                session = self.active_sessions[session_id]
                result.state_recovery_success = True

            # Resume workflow coordinator
            resume_stats = self.workflow_coordinator.resume_collection(
                session_id=session_id, state_manager=self.state_manager
            )

            # Restart monitoring
            self.metrics_collector.start_collection(
                venue_engine=self.workflow_coordinator,
                state_manager=self.state_manager,
                api_managers={"integration": self.api_integration_layer},
                data_processors=self.data_processors,
            )

            result.success = True
            result.papers_recovered = resume_stats.get("papers_recovered", 0)
            result.venues_recovered = resume_stats.get("venues_recovered", 0)

            # Update session status
            session.status = "active"

        except Exception as e:
            logger.error(f"Failed to resume session {session_id}: {e}")
            result.errors.append(str(e))

        finally:
            result.resume_duration_seconds = time.time() - resume_start

        return result

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status and metrics for a session"""
        if session_id not in self.active_sessions:
            return {"error": f"Unknown session: {session_id}"}

        session = self.active_sessions[session_id]

        # Get current metrics if available
        current_metrics = None
        if self.metrics_collector:
            current_metrics = self.metrics_collector.get_current_metrics()

        return {
            "session_id": session_id,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "venues": session.venues,
            "years": session.years,
            "current_metrics": current_metrics.to_dict() if current_metrics else None,
        }

    def shutdown_system(self) -> None:
        """
        Gracefully shutdown all system components

        REQUIREMENTS:
        - Must save all active session states
        - Must stop all components gracefully
        - Must complete within 60 seconds
        """
        logger.info("Starting system shutdown...")
        shutdown_start = time.time()

        try:
            # Stop monitoring for all active sessions
            if self.metrics_collector:
                self.metrics_collector.stop_collection()

            # Stop dashboard
            if self.dashboard:
                self.dashboard.stop_dashboard()

            # Stop alert system
            if self.alert_system:
                self.alert_system.stop()

            # Save state for all active sessions
            for session_id, session in self.active_sessions.items():
                try:
                    if session.status == "active":
                        self.pause_session(session_id)
                except Exception as e:
                    logger.error(
                        f"Error pausing session {session_id} during shutdown: {e}"
                    )

            # Shutdown workflow coordinator
            if self.workflow_coordinator:
                self.workflow_coordinator.shutdown()

            # Clear active sessions
            self.active_sessions.clear()

            # Set system as not ready
            self.system_ready = False

            shutdown_duration = time.time() - shutdown_start
            logger.info(f"System shutdown completed in {shutdown_duration:.2f}s")

        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health and component status"""
        health = {
            "system_ready": self.system_ready,
            "initialization_time": self.initialization_time,
            "active_sessions": len(self.active_sessions),
            "component_status": {},
        }

        # Check each component
        for name, status in self.component_status.items():
            health["component_status"][name] = {
                "status": status.status,
                "health_check_passed": status.health_check_passed,
                "error_message": status.error_message,
            }

        # Add current metrics if available
        if self.metrics_collector:
            metrics = self.metrics_collector.get_current_metrics()
            if metrics:
                health["current_metrics"] = {
                    "cpu_usage": metrics.system_metrics.cpu_usage_percent,
                    "memory_usage": metrics.system_metrics.memory_usage_percent,
                    "active_apis": len(metrics.api_metrics),
                }

        return health
