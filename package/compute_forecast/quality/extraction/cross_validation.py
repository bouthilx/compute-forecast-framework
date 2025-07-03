"""
Cross-validation framework for manual vs automated extraction comparison.

This module provides tools to validate automated extractions against manual ground truth.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import random
from collections import defaultdict

from compute_forecast.data.models import Paper


@dataclass
class ValidationComparison:
    """Result of comparing manual and automated extractions."""
    paper_id: str
    field: str
    manual_value: Any
    automated_value: Any
    agreement: bool
    accuracy: float
    notes: Optional[str] = None


class CrossValidationFramework:
    """Framework for manual vs automated validation."""
    
    def __init__(self):
        """Initialize with default settings."""
        self.agreement_threshold = 0.8
        self.manual_sample_size = 100
        
        # Field-specific tolerance levels
        self.field_tolerances = {
            "gpu_hours": 0.15,      # 15% tolerance
            "parameters": 0.10,     # 10% tolerance
            "training_time": 0.20,  # 20% tolerance
            "batch_size": 0.05,     # 5% tolerance
            "gpu_count": 0.0,       # Exact match required
            "epochs": 0.0,          # Exact match required
            "dataset_size": 0.10,   # 10% tolerance
            "gpu_memory": 0.05,     # 5% tolerance
        }
        
        # Calibration models stored per field
        self.calibration_models = {}
    
    def select_validation_sample(self, 
                               papers: List[Paper], 
                               stratify_by: str = "year") -> List[Paper]:
        """
        Select representative sample for manual validation.
        
        Args:
            papers: Full list of papers
            stratify_by: Field to stratify sampling by (year, domain, venue)
            
        Returns:
            List of papers selected for manual validation
        """
        if len(papers) <= self.manual_sample_size:
            return papers
        
        if stratify_by == "year":
            return self._stratified_sample_by_year(papers)
        elif stratify_by == "domain":
            return self._stratified_sample_by_domain(papers)
        elif stratify_by == "venue":
            return self._stratified_sample_by_venue(papers)
        else:
            # Random sampling
            return random.sample(papers, self.manual_sample_size)
    
    def compare_extractions(self, 
                          manual: Dict[str, Any], 
                          automated: Dict[str, Any]) -> Dict[str, float]:
        """
        Compare extraction results.
        
        Args:
            manual: Manually extracted values {paper_id: {field: value}}
            automated: Automatically extracted values {paper_id: {field: value}}
            
        Returns:
            Accuracy metrics per field
        """
        field_comparisons = defaultdict(list)
        
        # Compare each paper's extractions
        for paper_id in set(manual.keys()) & set(automated.keys()):
            manual_data = manual[paper_id]
            auto_data = automated[paper_id]
            
            # Compare each field
            for field in set(manual_data.keys()) & set(auto_data.keys()):
                manual_val = manual_data[field]
                auto_val = auto_data[field]
                
                if manual_val is None or auto_val is None:
                    continue
                
                # Calculate agreement based on field type
                agreement, accuracy = self._calculate_field_agreement(
                    field, manual_val, auto_val
                )
                
                field_comparisons[field].append({
                    "paper_id": paper_id,
                    "agreement": agreement,
                    "accuracy": accuracy,
                    "manual": manual_val,
                    "automated": auto_val
                })
        
        # Calculate overall accuracy per field
        field_accuracies = {}
        for field, comparisons in field_comparisons.items():
            if comparisons:
                accuracies = [c["accuracy"] for c in comparisons]
                field_accuracies[field] = sum(accuracies) / len(accuracies)
            else:
                field_accuracies[field] = 0.0
        
        return field_accuracies
    
    def generate_calibration_model(self, 
                                 comparisons: List[Dict[str, Any]]) -> Any:
        """
        Build model to calibrate automated extractions.
        
        Args:
            comparisons: List of comparison results
            
        Returns:
            Calibration model (currently returns calibration parameters)
        """
        # Group comparisons by field
        field_data = defaultdict(list)
        
        for comp in comparisons:
            for field, values in comp.items():
                if isinstance(values, list):
                    for v in values:
                        if "manual" in v and "automated" in v:
                            field_data[field].append(v)
        
        calibration_params = {}
        
        for field, data in field_data.items():
            if len(data) < 5:  # Need minimum data points
                continue
            
            manual_vals = [d["manual"] for d in data if isinstance(d["manual"], (int, float))]
            auto_vals = [d["automated"] for d in data if isinstance(d["automated"], (int, float))]
            
            if len(manual_vals) != len(auto_vals) or len(manual_vals) < 5:
                continue
            
            # Calculate calibration parameters
            # Simple linear calibration: corrected = a * automated + b
            manual_mean = sum(manual_vals) / len(manual_vals)
            auto_mean = sum(auto_vals) / len(auto_vals)
            
            # Calculate covariance and variance
            covariance = sum((m - manual_mean) * (a - auto_mean) 
                           for m, a in zip(manual_vals, auto_vals)) / len(manual_vals)
            auto_variance = sum((a - auto_mean) ** 2 for a in auto_vals) / len(auto_vals)
            
            if auto_variance > 0:
                slope = covariance / auto_variance
                intercept = manual_mean - slope * auto_mean
                
                # Calculate R-squared
                predicted = [slope * a + intercept for a in auto_vals]
                ss_res = sum((m - p) ** 2 for m, p in zip(manual_vals, predicted))
                ss_tot = sum((m - manual_mean) ** 2 for m in manual_vals)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                calibration_params[field] = {
                    "slope": slope,
                    "intercept": intercept,
                    "r_squared": r_squared,
                    "n_samples": len(manual_vals),
                    "reliable": r_squared > 0.7
                }
        
        self.calibration_models.update(calibration_params)
        return calibration_params
    
    def apply_calibration(self, 
                         field: str, 
                         automated_value: float) -> Tuple[float, bool]:
        """
        Apply calibration model to automated extraction.
        
        Args:
            field: Field name
            automated_value: Raw automated extraction value
            
        Returns:
            Tuple of (calibrated_value, is_calibrated)
        """
        if field not in self.calibration_models:
            return automated_value, False
        
        params = self.calibration_models[field]
        if not params.get("reliable", False):
            return automated_value, False
        
        calibrated = params["slope"] * automated_value + params["intercept"]
        return calibrated, True
    
    def validate_extraction_quality(self,
                                  manual_sample: Dict[str, Any],
                                  automated_full: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive validation of extraction quality.
        
        Args:
            manual_sample: Manual extractions for sample
            automated_full: Automated extractions for all papers
            
        Returns:
            Validation report with metrics and recommendations
        """
        # Compare on the overlapping sample
        sample_ids = set(manual_sample.keys())
        automated_sample = {k: v for k, v in automated_full.items() if k in sample_ids}
        
        # Get field accuracies
        field_accuracies = self.compare_extractions(manual_sample, automated_sample)
        
        # Generate calibration model
        comparisons = []
        for paper_id in sample_ids:
            if paper_id in manual_sample and paper_id in automated_sample:
                comparison = {}
                for field in set(manual_sample[paper_id].keys()) & set(automated_sample[paper_id].keys()):
                    comparison[field] = [{
                        "manual": manual_sample[paper_id][field],
                        "automated": automated_sample[paper_id][field]
                    }]
                comparisons.append(comparison)
        
        calibration_params = self.generate_calibration_model(comparisons)
        
        # Identify problematic fields
        problematic_fields = [
            field for field, acc in field_accuracies.items() 
            if acc < self.agreement_threshold
        ]
        
        # Calculate overall quality score
        if field_accuracies:
            overall_accuracy = sum(field_accuracies.values()) / len(field_accuracies)
        else:
            overall_accuracy = 0.0
        
        return {
            "overall_accuracy": overall_accuracy,
            "field_accuracies": field_accuracies,
            "problematic_fields": problematic_fields,
            "calibration_available": list(calibration_params.keys()),
            "sample_size": len(sample_ids),
            "recommendations": self._generate_recommendations(
                field_accuracies, problematic_fields
            )
        }
    
    def _calculate_field_agreement(self, 
                                 field: str, 
                                 manual_val: Any, 
                                 auto_val: Any) -> Tuple[bool, float]:
        """
        Calculate agreement between manual and automated values.
        
        Args:
            field: Field name
            manual_val: Manual extraction value
            auto_val: Automated extraction value
            
        Returns:
            Tuple of (agreement_bool, accuracy_score)
        """
        # Handle string fields
        if isinstance(manual_val, str) and isinstance(auto_val, str):
            agreement = manual_val.lower().strip() == auto_val.lower().strip()
            return agreement, 1.0 if agreement else 0.0
        
        # Handle numeric fields
        if isinstance(manual_val, (int, float)) and isinstance(auto_val, (int, float)):
            tolerance = self.field_tolerances.get(field, 0.1)
            
            if tolerance == 0.0:
                # Exact match required
                agreement = manual_val == auto_val
                return agreement, 1.0 if agreement else 0.0
            else:
                # Relative tolerance
                if manual_val == 0:
                    relative_diff = float('inf') if auto_val != 0 else 0.0
                else:
                    relative_diff = abs(manual_val - auto_val) / abs(manual_val)
                
                agreement = relative_diff <= tolerance
                accuracy = max(0.0, 1.0 - relative_diff)
                return agreement, accuracy
        
        # Handle list fields
        if isinstance(manual_val, list) and isinstance(auto_val, list):
            if len(manual_val) == 0 and len(auto_val) == 0:
                return True, 1.0
            if len(manual_val) == 0 or len(auto_val) == 0:
                return False, 0.0
            
            # Calculate Jaccard similarity
            manual_set = set(str(v).lower() for v in manual_val)
            auto_set = set(str(v).lower() for v in auto_val)
            intersection = manual_set & auto_set
            union = manual_set | auto_set
            
            jaccard = len(intersection) / len(union) if union else 0.0
            agreement = jaccard >= 0.8
            return agreement, jaccard
        
        # Default: exact match
        agreement = manual_val == auto_val
        return agreement, 1.0 if agreement else 0.0
    
    def _stratified_sample_by_year(self, papers: List[Paper]) -> List[Paper]:
        """Stratified sampling by year."""
        # Group papers by year
        papers_by_year = defaultdict(list)
        for paper in papers:
            if hasattr(paper, 'year') and paper.year:
                papers_by_year[paper.year].append(paper)
        
        # Calculate samples per year
        years = sorted(papers_by_year.keys())
        samples_per_year = self.manual_sample_size // len(years)
        remainder = self.manual_sample_size % len(years)
        
        selected = []
        for i, year in enumerate(years):
            year_papers = papers_by_year[year]
            n_samples = samples_per_year + (1 if i < remainder else 0)
            n_samples = min(n_samples, len(year_papers))
            selected.extend(random.sample(year_papers, n_samples))
        
        return selected
    
    def _stratified_sample_by_domain(self, papers: List[Paper]) -> List[Paper]:
        """Stratified sampling by domain."""
        # Simple domain detection based on title
        papers_by_domain = defaultdict(list)
        
        for paper in papers:
            domain = "general"
            if hasattr(paper, 'title') and paper.title:
                title_lower = paper.title.lower()
                if any(term in title_lower for term in ["language", "nlp", "text", "transformer"]):
                    domain = "nlp"
                elif any(term in title_lower for term in ["image", "vision", "visual", "cnn"]):
                    domain = "cv"
                elif any(term in title_lower for term in ["reinforcement", "rl", "agent", "reward"]):
                    domain = "rl"
            
            papers_by_domain[domain].append(paper)
        
        # Sample from each domain
        domains = list(papers_by_domain.keys())
        samples_per_domain = self.manual_sample_size // len(domains)
        remainder = self.manual_sample_size % len(domains)
        
        selected = []
        for i, domain in enumerate(domains):
            domain_papers = papers_by_domain[domain]
            n_samples = samples_per_domain + (1 if i < remainder else 0)
            n_samples = min(n_samples, len(domain_papers))
            selected.extend(random.sample(domain_papers, n_samples))
        
        return selected
    
    def _stratified_sample_by_venue(self, papers: List[Paper]) -> List[Paper]:
        """Stratified sampling by venue."""
        papers_by_venue = defaultdict(list)
        
        for paper in papers:
            if hasattr(paper, 'venue') and paper.venue:
                papers_by_venue[paper.venue].append(paper)
            else:
                papers_by_venue["unknown"].append(paper)
        
        # Sample proportionally from each venue
        total_papers = len(papers)
        selected = []
        
        for venue, venue_papers in papers_by_venue.items():
            proportion = len(venue_papers) / total_papers
            n_samples = int(self.manual_sample_size * proportion)
            n_samples = min(n_samples, len(venue_papers))
            if n_samples > 0:
                selected.extend(random.sample(venue_papers, n_samples))
        
        # Fill remaining slots if needed
        while len(selected) < self.manual_sample_size and len(selected) < len(papers):
            remaining = [p for p in papers if p not in selected]
            if remaining:
                selected.append(random.choice(remaining))
            else:
                break
        
        return selected[:self.manual_sample_size]
    
    def _generate_recommendations(self,
                                field_accuracies: Dict[str, float],
                                problematic_fields: List[str]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if not field_accuracies:
            recommendations.append("No extraction data available for validation")
            return recommendations
        
        overall_accuracy = sum(field_accuracies.values()) / len(field_accuracies)
        
        if overall_accuracy >= 0.9:
            recommendations.append("Extraction quality is excellent. Continue with current approach.")
        elif overall_accuracy >= 0.8:
            recommendations.append("Extraction quality is good. Minor improvements recommended.")
        else:
            recommendations.append("Extraction quality needs improvement. Consider manual review.")
        
        # Field-specific recommendations
        for field in problematic_fields:
            accuracy = field_accuracies.get(field, 0.0)
            if accuracy < 0.5:
                recommendations.append(f"Critical: {field} extraction is unreliable (accuracy: {accuracy:.2f})")
            elif accuracy < 0.8:
                recommendations.append(f"Warning: {field} extraction needs improvement (accuracy: {accuracy:.2f})")
        
        # Calibration recommendations
        if any(acc < 0.9 for acc in field_accuracies.values()):
            recommendations.append("Consider applying calibration models to improve accuracy")
        
        return recommendations