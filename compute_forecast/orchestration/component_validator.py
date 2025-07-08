"""
Component Validator for validating integration between all agent components.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field

from ..data.models import Paper, Author

logger = logging.getLogger(__name__)


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


class ComponentValidator:
    """Validates integration between all agent components"""

    def __init__(self):
        self.required_interfaces = {
            "agent_alpha": ["test_api_connectivity", "setup_collection_environment"],
            "agent_beta": ["create_session", "save_checkpoint", "recover_session"],
            "agent_gamma_venue": ["normalize_venue"],
            "agent_gamma_dedup": ["deduplicate_papers"],
            "agent_gamma_citation": ["analyze_citation_distributions"],
            "agent_delta_metrics": [
                "start_session_monitoring",
                "collect_current_metrics",
            ],
            "agent_delta_dashboard": ["create_session_dashboard"],
            "agent_delta_alerts": ["check_alerts"],
        }

    def validate_all_components(
        self,
        api_engine,
        state_manager,
        venue_normalizer,
        deduplicator,
        citation_analyzer,
        dashboard,
        metrics_collector,
        alert_system,
    ) -> Dict[str, ComponentValidationResult]:
        """Validate all components have required interfaces"""

        results = {}

        # Validate Agent Alpha
        results["agent_alpha"] = self._validate_component_interface(
            "agent_alpha", api_engine, self.required_interfaces["agent_alpha"]
        )

        # Validate Agent Beta
        results["agent_beta"] = self._validate_component_interface(
            "agent_beta", state_manager, self.required_interfaces["agent_beta"]
        )

        # Validate Agent Gamma components
        results["agent_gamma_venue"] = self._validate_component_interface(
            "agent_gamma_venue",
            venue_normalizer,
            self.required_interfaces["agent_gamma_venue"],
        )

        results["agent_gamma_dedup"] = self._validate_component_interface(
            "agent_gamma_dedup",
            deduplicator,
            self.required_interfaces["agent_gamma_dedup"],
        )

        results["agent_gamma_citation"] = self._validate_component_interface(
            "agent_gamma_citation",
            citation_analyzer,
            self.required_interfaces["agent_gamma_citation"],
        )

        # Validate Agent Delta components
        results["agent_delta_metrics"] = self._validate_component_interface(
            "agent_delta_metrics",
            metrics_collector,
            self.required_interfaces["agent_delta_metrics"],
        )

        results["agent_delta_dashboard"] = self._validate_component_interface(
            "agent_delta_dashboard",
            dashboard,
            self.required_interfaces["agent_delta_dashboard"],
        )

        results["agent_delta_alerts"] = self._validate_component_interface(
            "agent_delta_alerts",
            alert_system,
            self.required_interfaces["agent_delta_alerts"],
        )

        return results

    def _validate_component_interface(
        self, component_name: str, component_instance: Any, required_methods: List[str]
    ) -> ComponentValidationResult:
        """Validate a single component's interface"""

        if component_instance is None:
            return ComponentValidationResult(
                component_name=component_name,
                validation_passed=False,
                interface_methods_found=[],
                missing_methods=required_methods,
                test_results={},
                error_details=[f"Component {component_name} is None"],
            )

        found_methods = []
        missing_methods = []
        test_results = {}
        error_details = []

        # Check for required methods
        for method_name in required_methods:
            if hasattr(component_instance, method_name):
                found_methods.append(method_name)

                # Test method if possible
                try:
                    method = getattr(component_instance, method_name)
                    if callable(method):
                        test_results[method_name] = True
                    else:
                        test_results[method_name] = False
                        error_details.append(f"{method_name} is not callable")
                except Exception as e:
                    test_results[method_name] = False
                    error_details.append(f"Error testing {method_name}: {str(e)}")
            else:
                missing_methods.append(method_name)
                test_results[method_name] = False

        validation_passed = len(missing_methods) == 0 and all(test_results.values())

        return ComponentValidationResult(
            component_name=component_name,
            validation_passed=validation_passed,
            interface_methods_found=found_methods,
            missing_methods=missing_methods,
            test_results=test_results,
            error_details=error_details,
        )

    def validate_component_interfaces(
        self,
        api_engine,
        state_manager,
        venue_normalizer,
        deduplicator,
        citation_analyzer,
    ) -> Dict[str, InterfaceValidationResult]:
        """Validate interfaces between components with actual data flow tests"""

        results = {}

        # Test Alpha-Beta integration
        results["alpha_beta"] = self._test_alpha_beta_integration(
            api_engine, state_manager
        )

        # Test Alpha-Gamma integration
        results["alpha_gamma"] = self._test_alpha_gamma_integration(
            api_engine, venue_normalizer, deduplicator
        )

        # Test Beta-Gamma integration
        results["beta_gamma"] = self._test_beta_gamma_integration(
            state_manager, deduplicator, citation_analyzer
        )

        return results

    def _test_alpha_beta_integration(
        self, api_engine, state_manager
    ) -> InterfaceValidationResult:
        """Test integration between API layer and state management"""

        methods_tested = []
        error_details = []
        data_flow_verified = False

        try:
            # Test session creation
            if hasattr(state_manager, "create_session"):
                from ..data.models import CollectionConfig

                test_config = CollectionConfig()
                session_id = state_manager.create_session(test_config)
                methods_tested.append("create_session")

                if session_id:
                    data_flow_verified = True
                else:
                    error_details.append("Session creation returned empty ID")
            else:
                error_details.append("State manager missing create_session method")

        except Exception as e:
            error_details.append(f"Alpha-Beta integration test failed: {str(e)}")

        return InterfaceValidationResult(
            interface_name="alpha_beta",
            validation_passed=data_flow_verified and len(error_details) == 0,
            methods_tested=methods_tested,
            data_flow_verified=data_flow_verified,
            error_details=error_details,
        )

    def _test_alpha_gamma_integration(
        self, api_engine, venue_normalizer, deduplicator
    ) -> InterfaceValidationResult:
        """Test integration between API layer and data processing"""

        methods_tested = []
        error_details = []
        data_flow_verified = False

        try:
            # Create test paper
            test_paper = Paper(
                title="Test Paper for Integration",
                authors=[Author(name="Test Author")],
                venue="Test Venue",
                year=2024,
                citations=10,
            )

            # Test venue normalization
            if venue_normalizer and hasattr(venue_normalizer, "normalize_venue"):
                try:
                    normalize_result = venue_normalizer.normalize_venue("Test Venue")
                    methods_tested.append("normalize_venue")

                    if normalize_result:
                        data_flow_verified = True

                except Exception as e:
                    error_details.append(f"Venue normalization failed: {str(e)}")

            # Test deduplication
            if deduplicator and hasattr(deduplicator, "deduplicate_papers"):
                try:
                    dedup_result = deduplicator.deduplicate_papers(
                        [test_paper, test_paper]
                    )
                    methods_tested.append("deduplicate_papers")

                    if dedup_result and hasattr(dedup_result, "unique_papers"):
                        if (
                            len(dedup_result.unique_papers) == 1
                        ):  # Should deduplicate to 1 paper
                            data_flow_verified = True
                        else:
                            error_details.append("Deduplication did not work correctly")
                    else:
                        error_details.append("Deduplication returned invalid result")

                except Exception as e:
                    error_details.append(f"Deduplication failed: {str(e)}")

        except Exception as e:
            error_details.append(f"Alpha-Gamma integration test failed: {str(e)}")

        return InterfaceValidationResult(
            interface_name="alpha_gamma",
            validation_passed=data_flow_verified and len(error_details) == 0,
            methods_tested=methods_tested,
            data_flow_verified=data_flow_verified,
            error_details=error_details,
        )

    def _test_beta_gamma_integration(
        self, state_manager, deduplicator, citation_analyzer
    ) -> InterfaceValidationResult:
        """Test integration between state management and data processing"""

        methods_tested = []
        error_details = []
        data_flow_verified = False

        try:
            # Test citation analysis
            if citation_analyzer and hasattr(
                citation_analyzer, "analyze_citation_distributions"
            ):
                test_papers = [
                    Paper(
                        title="Paper 1",
                        authors=[],
                        venue="Venue",
                        year=2024,
                        citations=50,
                    ),
                    Paper(
                        title="Paper 2",
                        authors=[],
                        venue="Venue",
                        year=2024,
                        citations=25,
                    ),
                ]

                try:
                    analysis_result = citation_analyzer.analyze_citation_distributions(
                        test_papers
                    )
                    methods_tested.append("analyze_citation_distributions")

                    if (
                        hasattr(analysis_result, "total_papers")
                        and analysis_result.total_papers == 2
                    ):
                        data_flow_verified = True
                    else:
                        error_details.append(
                            "Citation analysis returned incorrect result"
                        )

                except Exception as e:
                    error_details.append(f"Citation analysis failed: {str(e)}")

        except Exception as e:
            error_details.append(f"Beta-Gamma integration test failed: {str(e)}")

        return InterfaceValidationResult(
            interface_name="beta_gamma",
            validation_passed=data_flow_verified and len(error_details) == 0,
            methods_tested=methods_tested,
            data_flow_verified=data_flow_verified,
            error_details=error_details,
        )
