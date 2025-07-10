"""Collection quality checker implementation."""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from compute_forecast.quality.stages.base import StageQualityChecker
from compute_forecast.quality.core.interfaces import (
    QualityCheckResult, QualityCheckType, QualityConfig
)
from .validators import (
    CompletenessValidator,
    ConsistencyValidator,
    AccuracyValidator,
    CoverageValidator
)
from .models import CollectionQualityMetrics, CollectionContext


class CollectionQualityChecker(StageQualityChecker):
    """Quality checker for collection stage."""
    
    def __init__(self):
        self.completeness_validator = CompletenessValidator()
        self.consistency_validator = ConsistencyValidator()
        self.accuracy_validator = AccuracyValidator()
        self.coverage_validator = CoverageValidator()
        super().__init__()
    
    def get_stage_name(self) -> str:
        return "collection"
    
    def load_data(self, data_path: Path) -> Dict[str, Any]:
        """Load collection data from file or directory."""
        if data_path.is_file():
            return self._load_from_file(data_path)
        elif data_path.is_dir():
            return self._load_from_directory(data_path)
        else:
            raise ValueError(f"Data path does not exist: {data_path}")
    
    def _load_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Load data from a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different data formats
            if isinstance(data, list):
                papers = data
            elif isinstance(data, dict):
                if "papers" in data:
                    papers = data["papers"]
                elif "data" in data:
                    papers = data["data"]
                else:
                    # Assume the dict values are papers
                    papers = list(data.values()) if data else []
            else:
                raise ValueError(f"Unexpected data format in {file_path}")
            
            return {
                "papers": papers,
                "source_file": str(file_path),
                "load_timestamp": datetime.now()
            }
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading {file_path}: {e}")
    
    def _load_from_directory(self, dir_path: Path) -> Dict[str, Any]:
        """Load data from multiple files in a directory."""
        papers = []
        source_files = []
        
        # Look for JSON files
        json_files = list(dir_path.glob("*.json"))
        if not json_files:
            raise ValueError(f"No JSON files found in {dir_path}")
        
        for file_path in json_files:
            try:
                file_data = self._load_from_file(file_path)
                papers.extend(file_data["papers"])
                source_files.append(str(file_path))
            except Exception as e:
                # Log warning but continue with other files
                print(f"Warning: Could not load {file_path}: {e}")
        
        if not papers:
            raise ValueError(f"No valid papers found in {dir_path}")
        
        return {
            "papers": papers,
            "source_files": source_files,
            "load_timestamp": datetime.now()
        }
    
    def _register_checks(self) -> Dict[str, callable]:
        """Register all collection quality checks."""
        return {
            "completeness": self._run_completeness_check,
            "consistency": self._run_consistency_check,
            "accuracy": self._run_accuracy_check,
            "coverage": self._run_coverage_check,
        }
    
    def _run_completeness_check(self, data: Dict[str, Any], config: QualityConfig) -> QualityCheckResult:
        """Run completeness validation."""
        papers = data.get("papers", [])
        return self.completeness_validator.validate(papers, config)
    
    def _run_consistency_check(self, data: Dict[str, Any], config: QualityConfig) -> QualityCheckResult:
        """Run consistency validation."""
        papers = data.get("papers", [])
        return self.consistency_validator.validate(papers, config)
    
    def _run_accuracy_check(self, data: Dict[str, Any], config: QualityConfig) -> QualityCheckResult:
        """Run accuracy validation."""
        papers = data.get("papers", [])
        return self.accuracy_validator.validate(papers, config)
    
    def _run_coverage_check(self, data: Dict[str, Any], config: QualityConfig) -> QualityCheckResult:
        """Run coverage validation."""
        papers = data.get("papers", [])
        return self.coverage_validator.validate(papers, config)
    
    def generate_metrics(self, data: Dict[str, Any], check_results: List[QualityCheckResult]) -> CollectionQualityMetrics:
        """Generate collection quality metrics."""
        papers = data.get("papers", [])
        
        # Basic metrics
        metrics = CollectionQualityMetrics(
            total_papers_collected=len(papers),
            quality_check_timestamp=datetime.now()
        )
        
        # Extract metrics from check results
        for result in check_results:
            if result.check_name == "completeness":
                self._extract_completeness_metrics(papers, result, metrics)
            elif result.check_name == "consistency":
                self._extract_consistency_metrics(papers, result, metrics)
            elif result.check_name == "accuracy":
                self._extract_accuracy_metrics(papers, result, metrics)
            elif result.check_name == "coverage":
                self._extract_coverage_metrics(papers, result, metrics)
        
        return metrics
    
    def _extract_completeness_metrics(self, papers: List[Dict[str, Any]], result: QualityCheckResult, metrics: CollectionQualityMetrics):
        """Extract completeness metrics from validation results."""
        total_papers = len(papers)
        
        # Count papers with required fields
        papers_with_all_required = sum(1 for paper in papers 
                                     if all(field in paper and paper[field] for field in ["title", "authors", "venue", "year"]))
        
        # Count papers with optional fields
        papers_with_abstracts = sum(1 for paper in papers if paper.get("abstract"))
        papers_with_pdfs = sum(1 for paper in papers if paper.get("pdf_url"))
        papers_with_dois = sum(1 for paper in papers if paper.get("doi"))
        
        # Calculate field completeness scores
        field_completeness = {}
        for field in ["title", "authors", "venue", "year", "abstract", "pdf_url", "doi"]:
            present_count = sum(1 for paper in papers if paper.get(field))
            field_completeness[field] = present_count / total_papers if total_papers > 0 else 0.0
        
        # Update metrics
        metrics.papers_with_all_required_fields = papers_with_all_required
        metrics.papers_with_abstracts = papers_with_abstracts
        metrics.papers_with_pdfs = papers_with_pdfs
        metrics.papers_with_dois = papers_with_dois
        metrics.field_completeness_scores = field_completeness
    
    def _extract_consistency_metrics(self, papers: List[Dict[str, Any]], result: QualityCheckResult, metrics: CollectionQualityMetrics):
        """Extract consistency metrics from validation results."""
        # Count duplicates based on issues
        duplicate_issues = [issue for issue in result.issues if issue.field == "duplicates"]
        metrics.duplicate_count = len(duplicate_issues)
        metrics.duplicate_rate = len(duplicate_issues) / len(papers) if papers else 0.0
        
        # Venue and year consistency scores from result
        metrics.venue_consistency_score = min(1.0, result.score + 0.2)  # Approximate from overall score
        metrics.year_consistency_score = min(1.0, result.score + 0.1)
    
    def _extract_accuracy_metrics(self, papers: List[Dict[str, Any]], result: QualityCheckResult, metrics: CollectionQualityMetrics):
        """Extract accuracy metrics from validation results."""
        # Count valid entries
        valid_years = sum(1 for paper in papers 
                         if paper.get("year") and isinstance(paper["year"], (int, str)) 
                         and str(paper["year"]).isdigit())
        
        valid_authors = sum(1 for paper in papers 
                           if paper.get("authors") and isinstance(paper["authors"], list) 
                           and all(isinstance(author, str) for author in paper["authors"]))
        
        valid_urls = sum(1 for paper in papers 
                        if paper.get("pdf_url") and isinstance(paper["pdf_url"], str) 
                        and paper["pdf_url"].startswith("http"))
        
        # Update metrics
        metrics.valid_years_count = valid_years
        metrics.valid_authors_count = valid_authors
        metrics.valid_urls_count = valid_urls
        
        # Calculate accuracy scores
        total_papers = len(papers)
        if total_papers > 0:
            metrics.accuracy_scores = {
                "years": valid_years / total_papers,
                "authors": valid_authors / total_papers,
                "urls": valid_urls / total_papers
            }
    
    def _extract_coverage_metrics(self, papers: List[Dict[str, Any]], result: QualityCheckResult, metrics: CollectionQualityMetrics):
        """Extract coverage metrics from validation results."""
        # Count papers by scraper source
        scraper_counts = {}
        for paper in papers:
            scraper = paper.get("scraper_source", "Unknown")
            scraper_counts[scraper] = scraper_counts.get(scraper, 0) + 1
        
        # Calculate success rates (simplified)
        scraper_success_rates = {}
        for scraper, count in scraper_counts.items():
            # Assume success rate based on relative count
            scraper_success_rates[scraper] = count / len(papers) if papers else 0.0
        
        # Update metrics
        metrics.papers_by_scraper = scraper_counts
        metrics.scraper_success_rates = scraper_success_rates
        
        # Calculate coverage rate (simplified)
        if len(papers) > 0:
            # Assume coverage rate based on overall score
            metrics.coverage_rate = min(1.0, result.score)