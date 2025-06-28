"""
Interface Contract Validation Engine for Analysis Pipeline.
Provides contract validation for data flow between pipeline components.
"""

from .base_contracts import (
    ContractViolationType,
    ContractViolation,
    AnalysisContract,
    ContractValidationResult,
)
from .analysis_contracts import (
    ComputationalAnalysisContract,
    PaperMetadataContract,
    ResourceMetricsContract,
)
from .pipeline_validator import (
    AnalysisContractValidator,
    PipelineIntegrationValidator,
)

__all__ = [
    # Base classes
    "ContractViolationType",
    "ContractViolation",
    "AnalysisContract",
    "ContractValidationResult",
    # Contracts
    "ComputationalAnalysisContract",
    "PaperMetadataContract",
    "ResourceMetricsContract",
    # Validators
    "AnalysisContractValidator",
    "PipelineIntegrationValidator",
]
