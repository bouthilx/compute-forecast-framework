#!/usr/bin/env python3
"""Extract computational requirements and suppression indicators from selected Mila papers."""

import json
import argparse
from pathlib import Path
import sys
import re
from typing import Dict, List, Optional
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from src.analysis.mila.paper_selector import DomainClassifier
from src.extraction.suppression_templates import (
    SuppressionTemplates,
    SuppressionIndicators
)
from src.analysis.computational.extraction_patterns import ExtractionRegexPatterns


class MilaExtractionPipeline:
    """Pipeline for extracting computational requirements from Mila papers."""
    
    def __init__(self):
        self.domain_classifier = DomainClassifier()
        self.patterns = ExtractionRegexPatterns()
        
        # Get suppression templates by domain
        self.templates = {
            "NLP": SuppressionTemplates.nlp_with_suppression(),
            "CV": SuppressionTemplates.cv_with_suppression(),
            "RL": SuppressionTemplates.rl_with_suppression()
        }
    
    def extract_from_paper(self, paper: Dict) -> Dict:
        """Extract computational requirements and suppression indicators from a paper."""
        # Get paper text
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        paper_text = f"{title}\n\n{abstract}" if abstract else title
        
        # Classify domain
        domain = self.domain_classifier.classify(paper)
        if domain not in self.templates:
            domain = "NLP"  # Default to NLP template
        
        # Get appropriate template
        template = self.templates[domain]
        
        # Extract computational requirements
        compute_req = self._extract_computational_requirements(paper_text)
        
        # Extract suppression indicators
        if hasattr(template, 'extract_suppression_indicators'):
            suppression = template.extract_suppression_indicators(paper_text)
            suppression_dict = self._suppression_to_dict(suppression)
        else:
            suppression_dict = {}
        
        # Calculate suppression score
        if suppression_dict:
            suppression_score = SuppressionTemplates.calculate_suppression_score(suppression)
        else:
            suppression_score = None
        
        # Compile results
        return {
            "paper_id": paper.get("paper_id"),
            "title": title,
            "year": self._extract_year(paper),
            "domain": domain,
            "computational_requirements": compute_req,
            "suppression_indicators": suppression_dict,
            "suppression_score": suppression_score,
            "extraction_metadata": {
                "confidence": self._calculate_confidence(compute_req, abstract),
                "extraction_method": "automated",
                "template_used": template.template_id,
                "extraction_date": datetime.now().isoformat()
            }
        }
    
    def _extract_computational_requirements(self, text: str) -> Dict:
        """Extract computational requirements using patterns."""
        requirements = {}
        
        # GPU information
        gpu_info = self.patterns.extract_gpu_info(text)
        if gpu_info:
            count, gpu_type = gpu_info[0]  # Take first match
            requirements["gpu_count"] = count
            requirements["gpu_type"] = gpu_type
        
        # Training time
        time_info = self.patterns.extract_training_time(text)
        if time_info:
            value, unit = time_info[0]  # Take first match
            requirements["training_time_hours"] = self._convert_time_to_hours(value, unit)
        
        # Parameters
        param_info = self.patterns.extract_parameters(text)
        if param_info:
            value, unit = param_info[0]  # Take first match
            requirements["parameters_millions"] = self._convert_params_to_millions(value, unit)
        
        # GPU hours - check direct patterns first
        gpu_hours_patterns = self.patterns.GPU_HOURS_PATTERNS
        for pattern in gpu_hours_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                gpu_hours_str = match.group(1).replace(',', '')
                requirements["estimated_gpu_hours"] = float(gpu_hours_str)
                break
        
        # Calculate GPU hours if not directly found
        if "estimated_gpu_hours" not in requirements:
            if "gpu_count" in requirements and "training_time_hours" in requirements:
                requirements["estimated_gpu_hours"] = (
                    requirements["gpu_count"] * requirements["training_time_hours"]
                )
        
        return requirements
    
    def _convert_time_to_hours(self, value: float, unit: str) -> float:
        """Convert time value and unit to hours."""
        unit = unit.lower()
        if 'hour' in unit or unit == 'h' or unit == 'hrs':
            return value
        elif 'day' in unit or unit == 'd':
            return value * 24
        elif 'week' in unit or unit == 'w':
            return value * 24 * 7
        return value
    
    def _convert_params_to_millions(self, value: float, unit: str) -> float:
        """Convert parameter value and unit to millions."""
        if isinstance(unit, str):
            unit = unit.upper()
            if unit == 'B' or 'billion' in unit.lower():
                return value * 1000
            elif unit == 'M' or 'million' in unit.lower():
                return value
            elif unit == 'K' or 'thousand' in unit.lower():
                return value / 1000
        return value
    
    def _suppression_to_dict(self, suppression: SuppressionIndicators) -> Dict:
        """Convert SuppressionIndicators to dictionary."""
        return {
            "experimental_scope": suppression.experimental_scope,
            "scale_analysis": suppression.scale_analysis,
            "method_classification": suppression.method_classification,
            "explicit_constraints": suppression.explicit_constraints
        }
    
    def _extract_year(self, paper: Dict) -> Optional[int]:
        """Extract publication year from paper."""
        for release in paper.get("releases", []):
            date_text = release.get("venue", {}).get("date", {}).get("text", "")
            if date_text:
                try:
                    return int(date_text[:4])
                except (ValueError, IndexError):
                    pass
        return None
    
    def _calculate_confidence(self, requirements: Dict, abstract: str) -> float:
        """Calculate extraction confidence score."""
        # Base confidence on how many fields were extracted
        fields_extracted = len(requirements)
        max_fields = 6  # gpu_count, gpu_type, training_time, parameters, etc.
        
        field_confidence = min(1.0, fields_extracted / max_fields)
        
        # Boost confidence if abstract exists
        abstract_confidence = 0.2 if abstract else 0.0
        
        return min(1.0, field_confidence + abstract_confidence)


def main():
    parser = argparse.ArgumentParser(
        description="Extract computational requirements from Mila papers"
    )
    parser.add_argument(
        "--input", "-i",
        default="data/mila_selected_papers.json",
        help="Input JSON file with selected papers"
    )
    parser.add_argument(
        "--output", "-o", 
        default="data/mila_computational_requirements.json",
        help="Output JSON file for extracted requirements"
    )
    parser.add_argument(
        "--csv", "-c",
        default="data/mila_computational_requirements.csv",
        help="Output CSV file for extracted requirements"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of papers to process"
    )
    args = parser.parse_args()
    
    # Load selected papers
    print(f"Loading papers from {args.input}...")
    with open(args.input, 'r') as f:
        papers = json.load(f)
    
    if args.limit:
        papers = papers[:args.limit]
    
    print(f"Processing {len(papers)} papers...")
    
    # Initialize pipeline
    pipeline = MilaExtractionPipeline()
    
    # Extract from each paper
    results = []
    stats = {
        "total_processed": 0,
        "successful_extractions": 0,
        "high_confidence": 0,
        "with_suppression": 0,
        "high_suppression": 0
    }
    
    for i, paper in enumerate(papers):
        print(f"\rProcessing paper {i+1}/{len(papers)}...", end="", flush=True)
        
        try:
            extraction = pipeline.extract_from_paper(paper)
            results.append(extraction)
            
            stats["total_processed"] += 1
            if extraction["computational_requirements"]:
                stats["successful_extractions"] += 1
            if extraction["extraction_metadata"]["confidence"] >= 0.6:
                stats["high_confidence"] += 1
            if extraction["suppression_indicators"]:
                stats["with_suppression"] += 1
            if extraction.get("suppression_score", 0) >= 0.5:
                stats["high_suppression"] += 1
                
        except Exception as e:
            print(f"\nError processing paper {paper.get('paper_id')}: {e}")
    
    print(f"\n\nExtraction complete!")
    print(f"  Total processed: {stats['total_processed']}")
    print(f"  Successful extractions: {stats['successful_extractions']}")
    print(f"  High confidence: {stats['high_confidence']}")
    print(f"  With suppression data: {stats['with_suppression']}")
    print(f"  High suppression: {stats['high_suppression']}")
    
    # Save JSON output
    print(f"\nSaving JSON output to {args.output}...")
    output_data = {
        "extraction_date": datetime.now().isoformat(),
        "summary_statistics": stats,
        "papers": results
    }
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    # Save CSV output
    if args.csv:
        print(f"Saving CSV output to {args.csv}...")
        import csv
        
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, 'w', newline='') as f:
            if results:
                # Flatten the nested structure for CSV
                fieldnames = [
                    "paper_id", "title", "year", "domain",
                    "gpu_type", "gpu_count", "training_hours", "parameters_millions",
                    "estimated_gpu_hours", "confidence", "suppression_score",
                    "num_ablations", "num_seeds", "constraints_mentioned"
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results:
                    row = {
                        "paper_id": result["paper_id"],
                        "title": result["title"][:100],  # Truncate long titles
                        "year": result["year"],
                        "domain": result["domain"],
                        "gpu_type": result["computational_requirements"].get("gpu_type"),
                        "gpu_count": result["computational_requirements"].get("gpu_count"),
                        "training_hours": result["computational_requirements"].get("training_time_hours"),
                        "parameters_millions": result["computational_requirements"].get("parameters_millions"),
                        "estimated_gpu_hours": result["computational_requirements"].get("estimated_gpu_hours"),
                        "confidence": result["extraction_metadata"]["confidence"],
                        "suppression_score": result.get("suppression_score"),
                        "num_ablations": result["suppression_indicators"].get("experimental_scope", {}).get("num_ablations"),
                        "num_seeds": result["suppression_indicators"].get("experimental_scope", {}).get("num_seeds"),
                        "constraints_mentioned": result["suppression_indicators"].get("explicit_constraints", {}).get("mentions_constraints")
                    }
                    writer.writerow(row)
    
    print("\nDone!")


if __name__ == "__main__":
    main()