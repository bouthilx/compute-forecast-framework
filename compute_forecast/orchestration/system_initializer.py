"""
System Initializer for coordinating component startup sequence.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InitializationStep:
    step_name: str
    component_name: str
    dependencies: List[str]
    timeout_seconds: int
    critical: bool


class SystemInitializer:
    """Handles system component initialization in correct dependency order"""

    def __init__(self):
        self.initialization_steps = [
            InitializationStep(
                step_name="initialize_configuration",
                component_name="config",
                dependencies=[],
                timeout_seconds=10,
                critical=True,
            ),
            InitializationStep(
                step_name="initialize_alpha_apis",
                component_name="agent_alpha",
                dependencies=["config"],
                timeout_seconds=30,
                critical=True,
            ),
            InitializationStep(
                step_name="initialize_beta_state",
                component_name="agent_beta",
                dependencies=["config"],
                timeout_seconds=15,
                critical=True,
            ),
            InitializationStep(
                step_name="initialize_gamma_processing",
                component_name="agent_gamma",
                dependencies=["config"],
                timeout_seconds=20,
                critical=True,
            ),
            InitializationStep(
                step_name="initialize_delta_monitoring",
                component_name="agent_delta",
                dependencies=["agent_alpha", "agent_beta", "agent_gamma"],
                timeout_seconds=15,
                critical=False,
            ),
        ]

    def get_initialization_order(self) -> List[InitializationStep]:
        """Get components in correct initialization order based on dependencies"""

        ordered_steps: List[InitializationStep] = []
        completed_components = set()

        while len(ordered_steps) < len(self.initialization_steps):
            progress_made = False

            for step in self.initialization_steps:
                if step.component_name in completed_components:
                    continue

                # Check if all dependencies are met
                dependencies_met = all(
                    dep in completed_components for dep in step.dependencies
                )

                if dependencies_met:
                    ordered_steps.append(step)
                    completed_components.add(step.component_name)
                    progress_made = True
                    break

            if not progress_made:
                # Circular dependency or missing dependency
                remaining_steps = [
                    step
                    for step in self.initialization_steps
                    if step.component_name not in completed_components
                ]
                logger.error(
                    f"Cannot resolve dependencies for remaining steps: {[s.step_name for s in remaining_steps]}"
                )
                break

        return ordered_steps

    def validate_dependencies(self) -> Dict[str, List[str]]:
        """Validate that all dependencies are resolvable"""

        issues = {}
        all_components = {step.component_name for step in self.initialization_steps}

        for step in self.initialization_steps:
            step_issues = []

            for dependency in step.dependencies:
                if dependency not in all_components:
                    step_issues.append(f"Unknown dependency: {dependency}")

            if step_issues:
                issues[step.step_name] = step_issues

        return issues

    def create_initialization_plan(self) -> Dict[str, Any]:
        """Create detailed initialization plan"""

        dependency_issues = self.validate_dependencies()
        if dependency_issues:
            return {"valid": False, "issues": dependency_issues, "plan": []}

        ordered_steps = self.get_initialization_order()

        plan = {
            "valid": True,
            "issues": {},
            "plan": [
                {
                    "step_name": step.step_name,
                    "component_name": step.component_name,
                    "dependencies": step.dependencies,
                    "timeout_seconds": step.timeout_seconds,
                    "critical": step.critical,
                    "order_index": i,
                }
                for i, step in enumerate(ordered_steps)
            ],
            "total_estimated_time": sum(step.timeout_seconds for step in ordered_steps),
            "critical_steps": len([step for step in ordered_steps if step.critical]),
        }

        return plan

    def execute_initialization_step(
        self, step: InitializationStep, initialization_function
    ) -> Tuple[bool, float, Optional[str]]:
        """Execute a single initialization step with timeout"""

        logger.info(f"Executing initialization step: {step.step_name}")
        start_time = time.time()

        try:
            # Execute initialization function with timeout monitoring
            success = initialization_function()
            execution_time = time.time() - start_time

            if execution_time > step.timeout_seconds:
                logger.warning(
                    f"Step {step.step_name} took {execution_time:.1f}s "
                    f"(>{step.timeout_seconds}s timeout)"
                )

            if success:
                logger.info(f"✓ {step.step_name} completed in {execution_time:.1f}s")
                return True, execution_time, None
            else:
                logger.error(f"✗ {step.step_name} failed")
                return False, execution_time, f"{step.step_name} returned False"

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"{step.step_name} failed with exception: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return False, execution_time, error_msg

    def check_initialization_health(
        self, completed_steps: List[str], failed_steps: List[str]
    ) -> Dict[str, Any]:
        """Check overall health of initialization process"""

        total_steps = len(self.initialization_steps)
        completed_count = len(completed_steps)
        failed_count = len(failed_steps)

        critical_steps = [step for step in self.initialization_steps if step.critical]
        critical_completed = [
            step for step in critical_steps if step.component_name in completed_steps
        ]
        critical_failed = [
            step for step in critical_steps if step.component_name in failed_steps
        ]

        health_status = "healthy"
        if len(critical_failed) > 0:
            health_status = "critical"
        elif failed_count > 0:
            health_status = "degraded"

        return {
            "health_status": health_status,
            "total_steps": total_steps,
            "completed_steps": completed_count,
            "failed_steps": failed_count,
            "success_rate": completed_count / total_steps if total_steps > 0 else 0,
            "critical_steps_total": len(critical_steps),
            "critical_steps_completed": len(critical_completed),
            "critical_steps_failed": len(critical_failed),
            "system_ready": len(critical_failed) == 0
            and len(critical_completed) == len(critical_steps),
        }
