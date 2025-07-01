"""
Extraction quality validator extending the quality framework.

This module validates extraction results with confidence scoring and completeness assessment.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

from src.quality.quality_analyzer import QualityAnalyzer
from src.quality.quality_structures import QualityMetrics
from src.data.models import Paper, ComputationalAnalysis


class ExtractionQuality(Enum):
    """Quality levels for extraction results."""
    HIGH = "high"           # >90% confidence
    MEDIUM = "medium"       # 70-90% confidence
    LOW = "low"            # 50-70% confidence
    UNRELIABLE = "unreliable"  # <50% confidence


@dataclass
class ExtractionValidation:
    """Validation result for a single extraction."""
    paper_id: str
    extraction_type: str  # gpu_hours, memory, parameters, etc.
    extracted_value: Any
    confidence: float
    quality: ExtractionQuality
    validation_method: str
    cross_validation_result: Optional[Dict[str, Any]] = None


class ExtractionQualityValidator(QualityAnalyzer):
    """Extends quality framework for extraction validation."""
    
    def __init__(self):
        """Initialize validator with completeness weights."""
        super().__init__()
        self.completeness_weights = {
            "gpu_hours": 0.3,
            "gpu_type": 0.2,
            "training_time": 0.2,
            "parameters": 0.15,
            "dataset_size": 0.15
        }
        
        # Additional weights for other fields
        self.field_importance = {
            # Critical fields
            "gpu_hours": 1.0,
            "gpu_type": 0.9,
            "gpu_count": 0.9,
            "training_time": 0.9,
            "parameters": 0.85,
            
            # Important fields
            "gpu_memory": 0.7,
            "batch_size": 0.6,
            "dataset_size": 0.7,
            "epochs": 0.6,
            
            # Optional fields
            "learning_rate": 0.4,
            "optimizer": 0.4,
            "framework": 0.5,
            "cost_estimate": 0.5
        }
    
    def validate_extraction(self, 
                          paper: Paper, 
                          extraction: ComputationalAnalysis) -> ExtractionValidation:
        """
        Validate single extraction with confidence scoring.
        
        Args:
            paper: Paper object being analyzed
            extraction: Extracted computational analysis
            
        Returns:
            ExtractionValidation with confidence and quality assessment
        """
        # Calculate completeness score
        completeness = self.calculate_completeness_score(extraction)
        
        # Check field validity
        validity_score = self._calculate_validity_score(extraction)
        
        # Check consistency with paper metadata
        consistency_score = self._check_paper_consistency(paper, extraction)
        
        # Calculate overall confidence
        confidence = (completeness * 0.4 + validity_score * 0.4 + consistency_score * 0.2)
        
        # Determine quality level
        quality = self._determine_quality(confidence)
        
        # Build validation result
        return ExtractionValidation(
            paper_id=paper.paper_id or "unknown",
            extraction_type="computational_analysis",
            extracted_value=extraction,
            confidence=confidence,
            quality=quality,
            validation_method="weighted_scoring",
            cross_validation_result={
                "completeness": completeness,
                "validity": validity_score,
                "consistency": consistency_score
            }
        )
    
    def calculate_completeness_score(self, extraction: ComputationalAnalysis) -> float:
        """
        Score extraction completeness (0-1).
        
        Args:
            extraction: Computational analysis to assess
            
        Returns:
            Completeness score between 0 and 1
        """
        total_weight = 0.0
        completed_weight = 0.0
        
        # Check each field in the extraction
        extraction_dict = extraction.__dict__ if hasattr(extraction, '__dict__') else extraction
        
        for field, weight in self.field_importance.items():
            total_weight += weight
            value = extraction_dict.get(field)
            
            if value is not None and value != "" and value != 0:
                # Check if it's a meaningful value
                if isinstance(value, (int, float)) and value > 0:
                    completed_weight += weight
                elif isinstance(value, str) and len(value.strip()) > 0:
                    completed_weight += weight
                elif isinstance(value, list) and len(value) > 0:
                    completed_weight += weight
        
        return completed_weight / total_weight if total_weight > 0 else 0.0
    
    def _calculate_validity_score(self, extraction: ComputationalAnalysis) -> float:
        """
        Calculate validity score based on value plausibility.
        
        Args:
            extraction: Computational analysis to validate
            
        Returns:
            Validity score between 0 and 1
        """
        valid_fields = 0
        total_fields = 0
        
        extraction_dict = extraction.__dict__ if hasattr(extraction, '__dict__') else extraction
        
        # Check GPU hours
        if "gpu_hours" in extraction_dict and extraction_dict["gpu_hours"] is not None:
            total_fields += 1
            if 0.1 <= extraction_dict["gpu_hours"] <= 1_000_000:
                valid_fields += 1
        
        # Check parameters
        if "parameters" in extraction_dict and extraction_dict["parameters"] is not None:
            total_fields += 1
            if 1e3 <= extraction_dict["parameters"] <= 1e13:
                valid_fields += 1
        
        # Check GPU count
        if "gpu_count" in extraction_dict and extraction_dict["gpu_count"] is not None:
            total_fields += 1
            if 1 <= extraction_dict["gpu_count"] <= 10000:
                valid_fields += 1
        
        # Check training time
        if "training_time" in extraction_dict and extraction_dict["training_time"] is not None:
            total_fields += 1
            if 0.1 <= extraction_dict["training_time"] <= 8760:  # Max 1 year in hours
                valid_fields += 1
        
        # Check batch size
        if "batch_size" in extraction_dict and extraction_dict["batch_size"] is not None:
            total_fields += 1
            if 1 <= extraction_dict["batch_size"] <= 100000:
                valid_fields += 1
        
        return valid_fields / total_fields if total_fields > 0 else 0.5
    
    def _check_paper_consistency(self, paper: Paper, extraction: ComputationalAnalysis) -> float:
        """
        Check consistency between paper metadata and extraction.
        
        Args:
            paper: Paper object
            extraction: Computational analysis
            
        Returns:
            Consistency score between 0 and 1
        """
        consistency_checks = []
        
        # Check year consistency (newer papers tend to use more resources)
        if hasattr(paper, 'year') and paper.year:
            extraction_dict = extraction.__dict__ if hasattr(extraction, '__dict__') else extraction
            if "gpu_hours" in extraction_dict and extraction_dict["gpu_hours"]:
                # Expect higher GPU hours for recent papers
                if paper.year >= 2020 and extraction_dict["gpu_hours"] > 100:
                    consistency_checks.append(1.0)
                elif paper.year < 2020 and extraction_dict["gpu_hours"] < 10000:
                    consistency_checks.append(1.0)
                else:
                    consistency_checks.append(0.7)
        
        # Check domain consistency
        if hasattr(paper, 'title') and paper.title:
            title_lower = paper.title.lower()
            extraction_dict = extraction.__dict__ if hasattr(extraction, '__dict__') else extraction
            
            # Language models should have parameters
            if any(term in title_lower for term in ["language model", "transformer", "gpt", "bert"]):
                if "parameters" in extraction_dict and extraction_dict["parameters"] and extraction_dict["parameters"] > 1e6:
                    consistency_checks.append(1.0)
                else:
                    consistency_checks.append(0.3)
            
            # Vision models often report batch size
            if any(term in title_lower for term in ["vision", "image", "visual", "cnn"]):
                if "batch_size" in extraction_dict and extraction_dict["batch_size"]:
                    consistency_checks.append(1.0)
                else:
                    consistency_checks.append(0.7)
        
        # If no checks performed, return neutral score
        if not consistency_checks:
            return 0.8
        
        return sum(consistency_checks) / len(consistency_checks)
    
    def _determine_quality(self, confidence: float) -> ExtractionQuality:
        """
        Determine quality level based on confidence score.
        
        Args:
            confidence: Confidence score between 0 and 1
            
        Returns:
            ExtractionQuality enum value
        """
        if confidence > 0.9:
            return ExtractionQuality.HIGH
        elif confidence > 0.7:
            return ExtractionQuality.MEDIUM
        elif confidence > 0.5:
            return ExtractionQuality.LOW
        else:
            return ExtractionQuality.UNRELIABLE
    
    def cross_validate_extractions(self, 
                                 manual: Dict[str, Any], 
                                 automated: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare manual vs automated extraction.
        
        Args:
            manual: Manually extracted values
            automated: Automatically extracted values
            
        Returns:
            Dictionary with agreement score and discrepancies
        """
        agreements = []
        discrepancies = []
        
        # Compare common fields
        all_fields = set(manual.keys()) | set(automated.keys())
        
        for field in all_fields:
            manual_value = manual.get(field)
            auto_value = automated.get(field)
            
            if manual_value is None and auto_value is None:
                continue
            
            if manual_value == auto_value:
                agreements.append(field)
            else:
                # Check if values are close enough (for numeric fields)
                if isinstance(manual_value, (int, float)) and isinstance(auto_value, (int, float)):
                    relative_diff = abs(manual_value - auto_value) / max(manual_value, auto_value)
                    if relative_diff < 0.1:  # 10% tolerance
                        agreements.append(field)
                    else:
                        discrepancies.append({
                            "field": field,
                            "manual": manual_value,
                            "automated": auto_value,
                            "relative_diff": relative_diff
                        })
                else:
                    discrepancies.append({
                        "field": field,
                        "manual": manual_value,
                        "automated": auto_value
                    })
        
        total_fields = len(agreements) + len(discrepancies)
        agreement_score = len(agreements) / total_fields if total_fields > 0 else 0.0
        
        return {
            "agreement_score": agreement_score,
            "discrepancies": discrepancies,
            "confidence": 0.9 if agreement_score > 0.85 else 0.7,
            "agreed_fields": agreements
        }