#!/usr/bin/env python3
"""Execute benchmark extraction on existing corpus."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import pandas as pd

from src.data.models import Paper
from src.analysis.benchmark.models import BenchmarkDomain
from src.analysis.benchmark.workflow_manager import ExtractionWorkflowManager
from src.analysis.benchmark.export import BenchmarkCSVExporter
from src.analysis.benchmark.quality_assurance import ExtractionQualityAssurance
from src.core.logging import setup_logging


logger = setup_logging("INFO")


class BenchmarkPaperFilter:
    """Filter benchmark papers from corpus."""
    
    def __init__(self):
        # Target institutions - expanded list
        self.target_orgs = [
            'deepmind', 'google research', 'google brain', 'google ai',
            'mit', 'massachusetts institute', 'stanford', 'berkeley', 
            'cmu', 'carnegie mellon', 'oxford', 'meta ai', 'facebook ai',
            'openai', 'microsoft research', 'nvidia', 'amazon',
            'princeton', 'harvard', 'cornell', 'caltech', 'eth zurich'
        ]
        
        # SOTA indicators
        self.sota_patterns = [
            r'state[- ]?of[- ]?the[- ]?art',
            r'\bsota\b',
            r'new record',
            r'surpass(?:es|ed)?',
            r'outperform(?:s|ed)?',
            r'best performance',
            r'achieve(?:s|d)? new',
            r'superior to',
            r'benchmark',
            r'baseline',
        ]
        
        # High-impact venue indicators
        self.high_impact_venues = [
            'neurips', 'nips', 'icml', 'iclr', 'cvpr', 'eccv', 'iccv',
            'acl', 'emnlp', 'naacl', 'aaai', 'ijcai', 'nature', 'science'
        ]
    
    def is_benchmark_paper(self, paper: Paper) -> bool:
        """Check if paper is a benchmark/SOTA paper."""
        text = f"{paper.title} {paper.abstract}".lower()
        
        # Check for SOTA indicators
        for pattern in self.sota_patterns:
            if re.search(pattern, text):
                return True
        
        # Check venue
        if paper.venue:
            venue_lower = paper.venue.lower()
            if any(venue in venue_lower for venue in self.high_impact_venues):
                return True
        
        return False
    
    def has_target_affiliation(self, paper: Paper) -> bool:
        """Check if paper has target institution affiliation."""
        # First check explicit affiliations
        if hasattr(paper, 'authors') and paper.authors:
            for author in paper.authors:
                if isinstance(author, dict) and author.get('affiliation'):
                    affiliation_lower = author['affiliation'].lower()
                    if any(org in affiliation_lower for org in self.target_orgs):
                        return True
        
        # Fallback: check title/abstract for institution mentions
        text = f"{paper.title} {paper.abstract}".lower()
        for org in self.target_orgs:
            if org in text:
                return True
        
        return False
    
    def filter_benchmark_papers(self, all_papers: List[Paper]) -> List[Paper]:
        """Filter papers that are computational benchmarks."""
        benchmark_papers = []
        
        # Statistics
        stats = {
            'total': len(all_papers),
            'sota_papers': 0,
            'target_org_papers': 0,
            'selected': 0,
            'by_year': defaultdict(int)
        }
        
        for paper in all_papers:
            is_sota = self.is_benchmark_paper(paper)
            has_target = self.has_target_affiliation(paper)
            
            if is_sota:
                stats['sota_papers'] += 1
            if has_target:
                stats['target_org_papers'] += 1
            
            # Include if either SOTA or from target org
            if is_sota or has_target:
                benchmark_papers.append(paper)
                stats['selected'] += 1
                stats['by_year'][paper.year] += 1
        
        # Log statistics
        logger.info(f"Filtering statistics:")
        logger.info(f"  Total papers: {stats['total']}")
        logger.info(f"  SOTA papers: {stats['sota_papers']}")
        logger.info(f"  Target org papers: {stats['target_org_papers']}")
        logger.info(f"  Selected benchmark papers: {stats['selected']}")
        logger.info(f"  By year: {dict(stats['by_year'])}")
        
        return benchmark_papers


def main():
    """Execute benchmark extraction pipeline."""
    logger.info("Starting benchmark extraction pipeline")
    
    # Load collected papers
    papers_path = Path("data/raw_collected_papers.json")
    logger.info(f"Loading papers from {papers_path}")
    
    with open(papers_path, 'r') as f:
        raw_papers = json.load(f)
    
    # Convert to Paper objects
    papers = []
    for p in raw_papers:
        paper = Paper(
            paper_id=p.get('paper_id', ''),
            title=p.get('title', ''),
            abstract=p.get('abstract', ''),
            authors=p.get('authors', []),
            year=p.get('year', 2024),
            venue=p.get('venue', ''),
            citations=p.get('citations', 0),
            source=p.get('source', 'unknown')
        )
        papers.append(paper)
    
    logger.info(f"Loaded {len(papers)} papers")
    
    # Filter benchmark papers
    filter = BenchmarkPaperFilter()
    benchmark_papers = filter.filter_benchmark_papers(papers)
    
    if len(benchmark_papers) < 180:
        logger.warning(f"Only found {len(benchmark_papers)} benchmark papers (target: 180-360)")
        logger.info("Proceeding with available papers")
    
    # Initialize workflow manager
    workflow_manager = ExtractionWorkflowManager()
    
    # Plan extraction batches
    logger.info("Planning extraction batches")
    batches = workflow_manager.plan_extraction(benchmark_papers)
    
    # Log batch statistics
    logger.info(f"Created {len(batches)} extraction batches:")
    for batch_key, batch_papers in batches.items():
        logger.info(f"  {batch_key}: {len(batch_papers)} papers")
    
    # Execute extraction
    logger.info("Executing parallel extraction")
    extraction_results = workflow_manager.execute_parallel_extraction(batches)
    
    # Generate extraction report
    logger.info("Generating extraction report")
    report_df = workflow_manager.generate_extraction_report(extraction_results)
    
    # Convert DataFrame to dict for JSON serialization
    report = {
        'successful_extractions': len(extraction_results),
        'high_confidence_count': len([r for r in extraction_results if r.high_confidence_count > 0]),
        'success_rate': (len(extraction_results) / len(benchmark_papers) * 100) if benchmark_papers else 0
    }
    
    # Quality assurance
    qa = ExtractionQualityAssurance()
    qa_results = qa.calculate_extraction_stats(extraction_results)
    
    # Export results
    logger.info("Exporting results")
    exporter = BenchmarkCSVExporter()
    
    # Export computational requirements
    comp_req_path = Path("data/benchmark_computational_requirements.csv")
    exporter.export_batches_to_csv(extraction_results, str(comp_req_path))
    
    # Generate baselines for M3-2 from dataframe
    df = exporter.export_to_dataframe(extraction_results)
    
    # Calculate baseline metrics
    baselines = {
        'computational_baselines': {
            'gpu_hours': {
                'median': 0,
                'p25': 0,
                'p75': 0
            },
            'parameters': {
                'median': 0,
                'ranges_by_year': {}
            }
        },
        'extraction_stats': {
            'total_papers': len(df) if not df.empty else 0,
            'high_confidence': 0
        }
    }
    
    # Try to calculate actual metrics if data exists
    if not df.empty and 'gpu_hours' in df.columns:
        gpu_numeric = pd.to_numeric(df['gpu_hours'], errors='coerce')
        gpu_valid = gpu_numeric[gpu_numeric > 0]
        if len(gpu_valid) > 0:
            baselines['computational_baselines']['gpu_hours'] = {
                'median': float(gpu_valid.median()),
                'p25': float(gpu_valid.quantile(0.25)),
                'p75': float(gpu_valid.quantile(0.75))
            }
    
    if not df.empty and 'parameters_millions' in df.columns:
        param_numeric = pd.to_numeric(df['parameters_millions'], errors='coerce')
        param_valid = param_numeric[param_numeric > 0]
        if len(param_valid) > 0:
            baselines['computational_baselines']['parameters']['median'] = float(param_valid.median() * 1e6)
    
    if not df.empty and 'extraction_confidence' in df.columns:
        confidence_numeric = pd.to_numeric(df['extraction_confidence'], errors='coerce')
        baselines['extraction_stats']['high_confidence'] = len(confidence_numeric[confidence_numeric > 0.7])
    baselines_path = Path("data/benchmark_baselines.json")
    
    with open(baselines_path, 'w') as f:
        json.dump(baselines, f, indent=2)
    
    # Final summary
    logger.info("=" * 60)
    logger.info("Extraction Complete!")
    logger.info(f"Processed {len(benchmark_papers)} benchmark papers")
    logger.info(f"Successful extractions: {report.get('successful_extractions', 0)}")
    logger.info(f"High confidence: {report.get('high_confidence_count', 0)}")
    logger.info(f"Success rate: {report.get('success_rate', 0):.1f}%")
    logger.info("=" * 60)
    
    # Save summary report
    summary = {
        'execution_timestamp': datetime.now().isoformat(),
        'total_papers': len(papers),
        'benchmark_papers': len(benchmark_papers),
        'extraction_summary': report,
        'qa_results': qa_results.dict() if hasattr(qa_results, 'dict') else qa_results,
        'output_files': {
            'computational_requirements': str(comp_req_path),
            'baselines': str(baselines_path)
        }
    }
    
    summary_path = Path("data/benchmark_extraction_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Summary saved to {summary_path}")
    

if __name__ == "__main__":
    main()