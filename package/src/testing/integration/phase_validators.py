"""
Phase validators for pipeline testing.
Ensures data integrity and quality at each pipeline phase.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime

from src.testing.integration.pipeline_test_framework import PipelinePhase
from src.data.models import Paper, ComputationalAnalysis


@dataclass
class ValidationResult:
    """Result of phase validation"""
    phase: PipelinePhase
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def add_error(self, error: str) -> None:
        """Add an error and mark as invalid"""
        self.errors.append(error)
        self.is_valid = False
        
    def add_warning(self, warning: str) -> None:
        """Add a warning (doesn't affect validity)"""
        self.warnings.append(warning)


class PhaseValidator(ABC):
    """Base class for phase validators"""
    
    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """Validate phase data"""
        pass
        
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Get list of required fields for this phase"""
        pass


class CollectionPhaseValidator(PhaseValidator):
    """Validator for collection phase"""
    
    def __init__(self, min_papers: int = 1):
        self.min_papers = min_papers
        
    def validate(self, data: List[Paper]) -> ValidationResult:
        """Validate collected papers"""
        result = ValidationResult(phase=PipelinePhase.COLLECTION, is_valid=True)
        
        # Check if we have papers
        if not data:
            result.add_error("No papers collected")
            return result
            
        # Count valid papers
        valid_papers = 0
        paper_ids = set()
        duplicate_count = 0
        
        for idx, paper in enumerate(data):
            # Check required fields
            if not hasattr(paper, 'paper_id') or not paper.paper_id:
                result.add_error(f"Paper at index {idx} missing paper_id")
                continue
                
            if not hasattr(paper, 'title') or not paper.title:
                result.add_error(f"Paper {paper.paper_id} missing title")
                continue
                
            if not hasattr(paper, 'authors') or not paper.authors:
                result.add_warning(f"Paper {paper.paper_id} has no authors")
                
            # Check for duplicates
            if paper.paper_id in paper_ids:
                duplicate_count += 1
                result.add_warning(f"Duplicate paper_id: {paper.paper_id}")
            else:
                paper_ids.add(paper.paper_id)
                valid_papers += 1
                
        # Check minimum threshold
        if valid_papers < self.min_papers:
            result.add_error(f"Insufficient valid papers: {valid_papers} < {self.min_papers}")
            
        # Add metrics
        result.metrics = {
            "paper_count": len(data),
            "valid_papers": valid_papers,
            "duplicate_count": duplicate_count,
            "unique_papers": len(paper_ids),
            "invalid_papers": len(data) - valid_papers
        }
        
        return result
        
    def get_required_fields(self) -> List[str]:
        return ["paper_id", "title", "authors"]


class ExtractionPhaseValidator(PhaseValidator):
    """Validator for extraction phase"""
    
    def validate(self, data: List[Paper]) -> ValidationResult:
        """Validate extracted paper data"""
        result = ValidationResult(phase=PipelinePhase.EXTRACTION, is_valid=True)
        
        if not data:
            result.add_error("No papers to validate in extraction phase")
            return result
            
        papers_with_abstract = 0
        papers_with_computational = 0
        extraction_issues = 0
        
        for paper in data:
            # Check abstract extraction
            if not hasattr(paper, 'abstract') or not paper.abstract:
                result.add_warning(f"Paper {paper.paper_id} missing abstract")
            else:
                papers_with_abstract += 1
                
            # Check computational content extraction
            if hasattr(paper, 'computational_content') and paper.computational_content:
                papers_with_computational += 1
            else:
                extraction_issues += 1
                
        # Calculate extraction rate
        extraction_rate = papers_with_abstract / len(data) if data else 0
        
        if extraction_rate < 0.5:  # Less than 50% extracted
            result.add_error(f"Low extraction rate: {extraction_rate:.1%}")
            
        result.metrics = {
            "total_papers": len(data),
            "papers_with_abstract": papers_with_abstract,
            "papers_without_abstract": len(data) - papers_with_abstract,
            "papers_with_computational": papers_with_computational,
            "extraction_rate": extraction_rate,
            "extraction_issues": extraction_issues
        }
        
        return result
        
    def get_required_fields(self) -> List[str]:
        return ["paper_id", "title", "abstract"]


class AnalysisPhaseValidator(PhaseValidator):
    """Validator for analysis phase"""
    
    def validate(self, data: List[ComputationalAnalysis]) -> ValidationResult:
        """Validate computational analyses"""
        result = ValidationResult(phase=PipelinePhase.ANALYSIS, is_valid=True)
        
        if not data:
            result.add_error("No analyses to validate")
            return result
            
        valid_analyses = 0
        computational_papers = 0
        missing_metrics = 0
        
        for analysis in data:
            # Check required fields
            if not hasattr(analysis, 'paper_id') or not analysis.paper_id:
                result.add_error("Analysis missing paper_id")
                continue
                
            # Check computational content flag
            if hasattr(analysis, 'has_computational_content'):
                if analysis.has_computational_content:
                    computational_papers += 1
                    
                    # Check resource metrics for computational papers
                    if not hasattr(analysis, 'resource_metrics') or not analysis.resource_metrics:
                        missing_metrics += 1
                        result.add_error(f"Paper {analysis.paper_id} missing resource metrics")
                    else:
                        valid_analyses += 1
            else:
                result.add_error(f"Analysis {analysis.paper_id} missing computational content flag")
                
        # Check if we have enough valid analyses
        if valid_analyses == 0:
            result.add_error("No valid analyses produced")
            
        result.metrics = {
            "analysis_count": len(data),
            "valid_analyses": valid_analyses,
            "computational_papers": computational_papers,
            "missing_metrics": missing_metrics,
            "analysis_rate": valid_analyses / len(data) if data else 0
        }
        
        return result
        
    def get_required_fields(self) -> List[str]:
        return ["paper_id", "has_computational_content", "resource_metrics"]


class ProjectionPhaseValidator(PhaseValidator):
    """Validator for projection phase"""
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate projection data"""
        result = ValidationResult(phase=PipelinePhase.PROJECTION, is_valid=True)
        
        # Check required fields
        required_fields = [
            "total_papers",
            "computational_papers", 
            "projection_years",
            "resource_projections"
        ]
        
        for req_field in required_fields:
            if req_field not in data:
                result.add_error(f"Missing {req_field} in projections")
                
        if not result.is_valid:
            return result
            
        # Validate projection data
        projection_years = data.get("projection_years", [])
        if len(projection_years) < 2:
            result.add_error("Need at least 2 projection years")
            
        # Check resource projections
        resource_projections = data.get("resource_projections", {})
        for year in projection_years:
            year_str = str(year)
            if year_str not in resource_projections:
                result.add_error(f"Missing projections for year {year}")
            else:
                year_data = resource_projections[year_str]
                if not isinstance(year_data, dict) or not year_data:
                    result.add_error(f"Invalid projection data for year {year}")
                    
        # Check confidence intervals if present
        if "confidence_intervals" in data:
            ci_data = data["confidence_intervals"]
            for year in projection_years:
                year_str = str(year)
                if year_str in ci_data:
                    ci = ci_data[year_str]
                    if "lower" not in ci or "upper" not in ci:
                        result.add_warning(f"Incomplete confidence interval for year {year}")
                        
        result.metrics = {
            "projection_years_count": len(projection_years),
            "has_confidence_intervals": "confidence_intervals" in data,
            "resource_types": len(resource_projections.get(str(projection_years[0]), {})) if projection_years else 0
        }
        
        return result
        
    def get_required_fields(self) -> List[str]:
        return ["total_papers", "computational_papers", "projection_years", "resource_projections"]


class ReportingPhaseValidator(PhaseValidator):
    """Validator for reporting phase"""
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate report data"""
        result = ValidationResult(phase=PipelinePhase.REPORTING, is_valid=True)
        
        # Check basic structure
        if not isinstance(data, dict):
            result.add_error("Report must be a dictionary")
            return result
            
        # Check required sections
        required_sections = ["summary", "generated_at"]
        optional_sections = ["methodology", "results", "visualizations", "recommendations"]
        
        for section in required_sections:
            if section not in data:
                result.add_error(f"Missing required section: {section}")
                
        # Check optional but recommended sections
        for section in optional_sections:
            if section not in data:
                result.add_warning(f"Missing recommended section: {section}")
                
        # Validate summary
        if "summary" in data:
            summary = data["summary"]
            if not isinstance(summary, dict):
                result.add_error("Summary must be a dictionary")
            elif "total_analyzed" not in summary:
                result.add_warning("Summary missing total_analyzed count")
                
        # Check timestamp
        if "generated_at" in data:
            try:
                # Try to parse timestamp
                datetime.fromisoformat(data["generated_at"].replace('Z', '+00:00'))
            except Exception:
                result.add_error("Invalid timestamp format in generated_at")
                
        result.metrics = {
            "sections_count": len(data),
            "has_visualizations": "visualizations" in data,
            "visualization_count": len(data.get("visualizations", [])),
            "has_recommendations": "recommendations" in data
        }
        
        return result
        
    def get_required_fields(self) -> List[str]:
        return ["summary", "generated_at"]


class TransitionValidator:
    """Validates data transitions between pipeline phases"""
    
    def validate_transition(self,
                           from_phase: PipelinePhase,
                           to_phase: PipelinePhase,
                           from_data: Any,
                           to_data: Any) -> ValidationResult:
        """Validate data transition between phases"""
        result = ValidationResult(
            phase=to_phase,
            is_valid=True
        )
        
        # Check phase sequence
        all_phases = list(PipelinePhase)
        from_idx = all_phases.index(from_phase)
        to_idx = all_phases.index(to_phase)
        
        if to_idx != from_idx + 1:
            result.add_warning(f"Non-sequential transition: {from_phase.value} -> {to_phase.value}")
            
        # Phase-specific transition validation
        if from_phase == PipelinePhase.COLLECTION and to_phase == PipelinePhase.EXTRACTION:
            self._validate_collection_to_extraction(from_data, to_data, result)
        elif from_phase == PipelinePhase.EXTRACTION and to_phase == PipelinePhase.ANALYSIS:
            self._validate_extraction_to_analysis(from_data, to_data, result)
        elif from_phase == PipelinePhase.ANALYSIS and to_phase == PipelinePhase.PROJECTION:
            self._validate_analysis_to_projection(from_data, to_data, result)
        elif from_phase == PipelinePhase.PROJECTION and to_phase == PipelinePhase.REPORTING:
            self._validate_projection_to_reporting(from_data, to_data, result)
            
        return result
        
    def _validate_collection_to_extraction(self, 
                                         from_data: List[Paper],
                                         to_data: List[Paper],
                                         result: ValidationResult) -> None:
        """Validate collection -> extraction transition"""
        if isinstance(from_data, list) and isinstance(to_data, list):
            from_count = len(from_data)
            to_count = len(to_data)
            
            if to_count < from_count:
                loss_percent = ((from_count - to_count) / from_count) * 100
                result.add_warning(f"Data loss in transition: {loss_percent:.1f}% papers lost")
                result.metrics["data_loss_percent"] = loss_percent
            else:
                result.metrics["data_loss_percent"] = 0.0
                
            result.metrics["from_count"] = from_count
            result.metrics["to_count"] = to_count
            
    def _validate_extraction_to_analysis(self,
                                       from_data: List[Paper],
                                       to_data: Any,
                                       result: ValidationResult) -> None:
        """Validate extraction -> analysis transition"""
        # Analysis phase may transform data structure
        if isinstance(from_data, list):
            result.metrics["input_papers"] = len(from_data)
            
        if isinstance(to_data, list):
            result.metrics["output_analyses"] = len(to_data)
        elif isinstance(to_data, dict):
            result.metrics["output_type"] = "dictionary"
            
    def _validate_analysis_to_projection(self,
                                       from_data: Any,
                                       to_data: Dict[str, Any],
                                       result: ValidationResult) -> None:
        """Validate analysis -> projection transition"""
        if isinstance(to_data, dict):
            if "total_papers" in to_data:
                result.metrics["projected_papers"] = to_data["total_papers"]
        else:
            result.add_error("Projection data must be a dictionary")
            
    def _validate_projection_to_reporting(self,
                                        from_data: Dict[str, Any],
                                        to_data: Dict[str, Any],
                                        result: ValidationResult) -> None:
        """Validate projection -> reporting transition"""
        # Ensure projection data is included in report
        if isinstance(from_data, dict) and isinstance(to_data, dict):
            if "summary" in to_data and isinstance(to_data["summary"], dict):
                summary = to_data["summary"]
                # Check if projection data made it to report
                if "total_papers" in from_data and "total_analyzed" not in summary:
                    result.add_warning("Projection data not reflected in report summary")


class DataIntegrityChecker:
    """Checks data integrity across the pipeline"""
    
    def check_papers(self, papers: List[Paper]) -> List[str]:
        """Check integrity of paper data"""
        issues = []
        
        for idx, paper in enumerate(papers):
            paper_ref = f"Paper {getattr(paper, 'paper_id', idx)}"
            
            # Check required fields
            if not hasattr(paper, 'paper_id') or not paper.paper_id:
                issues.append(f"{paper_ref}: Missing paper_id")
                
            if not hasattr(paper, 'title') or not paper.title or paper.title == "":
                issues.append(f"{paper_ref}: Empty title")
                
            if not hasattr(paper, 'authors') or not paper.authors:
                issues.append(f"{paper_ref}: No authors")
                
            if not hasattr(paper, 'year') or not paper.year:
                issues.append(f"{paper_ref}: Missing year")
                
            if hasattr(paper, 'venue') and not paper.venue:
                issues.append(f"{paper_ref}: Empty venue")
                
        return issues
        
    def check_unique_ids(self, items: List[Dict[str, Any]], 
                        id_field: str = "id") -> Tuple[bool, Set[str]]:
        """Check for duplicate IDs"""
        seen_ids = set()
        duplicates = set()
        
        for item in items:
            item_id = item.get(id_field)
            if item_id:
                if item_id in seen_ids:
                    duplicates.add(item_id)
                else:
                    seen_ids.add(item_id)
                    
        return len(duplicates) > 0, duplicates