"""Data models for benchmark extraction."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

from compute_forecast.data.models import Paper, ComputationalAnalysis


class BenchmarkDomain(Enum):
    """Domains for benchmark papers."""
    
    NLP = "nlp"
    CV = "computer_vision"
    RL = "reinforcement_learning"
    GENERAL = "general"


@dataclass
class BenchmarkPaper:
    """Represents a paper with benchmark and computational information."""
    
    paper: Paper
    domain: BenchmarkDomain
    is_sota: bool  # State-of-the-art at publication
    benchmark_datasets: List[str]
    computational_requirements: ComputationalAnalysis
    extraction_confidence: float
    manual_verification: bool = False


@dataclass
class ExtractionBatch:
    """Results from extracting a batch of papers."""
    
    domain: BenchmarkDomain
    year: int
    papers: List[BenchmarkPaper]
    total_extracted: int
    high_confidence_count: int
    requires_manual_review: List[str]  # paper_ids


@dataclass
class BenchmarkExport:
    """Standardized export format for downstream analysis."""
    
    paper_id: str
    title: str
    year: int
    domain: BenchmarkDomain
    venue: str
    
    # Computational metrics
    gpu_hours: Optional[float]
    gpu_type: Optional[str]
    gpu_count: Optional[int]
    training_days: Optional[float]
    parameters_millions: Optional[float]
    dataset_size_gb: Optional[float]
    
    # Metadata
    extraction_confidence: float
    is_sota: bool
    benchmark_datasets: List[str]
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to CSV-compatible format."""
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "year": self.year,
            "domain": self.domain.value,
            "venue": self.venue,
            "gpu_hours": self.gpu_hours if self.gpu_hours is not None else "",
            "gpu_type": self.gpu_type if self.gpu_type else "",
            "gpu_count": self.gpu_count if self.gpu_count is not None else "",
            "training_days": self.training_days if self.training_days is not None else "",
            "parameters_millions": self.parameters_millions if self.parameters_millions is not None else "",
            "dataset_size_gb": self.dataset_size_gb if self.dataset_size_gb is not None else "",
            "extraction_confidence": self.extraction_confidence,
            "is_sota": self.is_sota,
            "benchmark_datasets": ",".join(self.benchmark_datasets) if self.benchmark_datasets else "",
        }


@dataclass
class ExtractionQA:
    """Quality assurance metrics for extraction."""
    
    total_papers: int
    successfully_extracted: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    manual_review_required: int
    domain_distribution: Dict[BenchmarkDomain, int]
    year_distribution: Dict[int, int]