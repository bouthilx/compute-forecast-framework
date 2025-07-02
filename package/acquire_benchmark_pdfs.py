#!/usr/bin/env python3
"""Acquire PDFs for all benchmark papers identified in issue #74."""

import json
from pathlib import Path
from src.data.pdf import PDFAcquisitionManager
import time

def acquire_benchmark_pdfs():
    """Acquire PDFs for benchmark papers."""
    
    # Load the benchmark extraction summary to get paper count
    summary_path = Path("data/benchmark_extraction_summary.json")
    if summary_path.exists():
        with open(summary_path, "r") as f:
            summary = json.load(f)
        print(f"Found {summary['benchmark_papers']} benchmark papers from extraction")
    
    # Load all papers
    with open("data/raw_collected_papers.json", "r") as f:
        all_papers = json.load(f)
    
    # Filter benchmark papers using same criteria as execute_benchmark_extraction.py
    benchmark_papers = []
    
    # Target institutions
    target_orgs = [
        'deepmind', 'google research', 'google brain', 'google ai',
        'mit', 'massachusetts institute', 'stanford', 'berkeley', 
        'cmu', 'carnegie mellon', 'oxford', 'meta ai', 'facebook ai',
        'openai', 'microsoft research', 'nvidia', 'amazon',
        'princeton', 'harvard', 'cornell', 'caltech', 'eth zurich'
    ]
    
    # SOTA indicators
    sota_patterns = [
        'state-of-the-art', 'sota', 'new record', 'surpass',
        'outperform', 'best performance', 'achieve new',
        'superior to', 'benchmark', 'baseline'
    ]
    
    for paper in all_papers:
        is_benchmark = False
        
        # Check SOTA indicators
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        if any(pattern in text for pattern in sota_patterns):
            is_benchmark = True
        
        # Check high-impact venues
        venue = paper.get('venue', '').lower()
        if any(v in venue for v in ['neurips', 'nips', 'icml', 'iclr', 'cvpr', 'eccv', 'iccv', 'acl', 'emnlp']):
            is_benchmark = True
        
        # Check target affiliations
        if paper.get('authors'):
            for author in paper['authors']:
                if isinstance(author, dict) and author.get('affiliation'):
                    affiliation_lower = author['affiliation'].lower()
                    if any(org in affiliation_lower for org in target_orgs):
                        is_benchmark = True
                        break
        
        # Also check in title/abstract for institution mentions
        for org in target_orgs:
            if org in text:
                is_benchmark = True
                break
        
        if is_benchmark:
            benchmark_papers.append(paper)
    
    print(f"Identified {len(benchmark_papers)} benchmark papers")
    
    # Initialize PDF acquisition manager
    manager = PDFAcquisitionManager()
    
    # Acquire PDFs with progress tracking
    results = []
    successful = 0
    
    print("\nStarting PDF acquisition...")
    start_time = time.time()
    
    for i, paper in enumerate(benchmark_papers):
        # Progress indicator
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(benchmark_papers) - i) / rate if rate > 0 else 0
            print(f"\n[{i}/{len(benchmark_papers)}] Progress: {i/len(benchmark_papers)*100:.1f}% "
                  f"(Rate: {rate:.1f} papers/s, ETA: {eta/60:.1f} min)")
        
        # Acquire PDF
        result = manager.acquire_pdf(paper)
        results.append({
            'title': result.title,
            'pdf_found': result.pdf_found,
            'source': result.source,
            'paper_id': result.paper_id
        })
        
        if result.pdf_found:
            successful += 1
            print(f"  ✓ {paper['title'][:50]}... [{result.source}]")
        else:
            print(f"  ✗ {paper['title'][:50]}...")
    
    # Summary statistics
    elapsed_total = time.time() - start_time
    print("\n" + "="*60)
    print("BENCHMARK PDF ACQUISITION COMPLETE")
    print("="*60)
    print(f"Total papers: {len(benchmark_papers)}")
    print(f"PDFs acquired: {successful} ({successful/len(benchmark_papers)*100:.1f}%)")
    print(f"Total time: {elapsed_total/60:.1f} minutes")
    print(f"Average time per paper: {elapsed_total/len(benchmark_papers):.1f}s")
    
    # Source breakdown
    source_counts = {}
    for r in results:
        if r['pdf_found']:
            source = r['source']
            source_counts[source] = source_counts.get(source, 0) + 1
    
    print("\nPDFs by source:")
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count} ({count/successful*100:.1f}%)")
    
    # Cache statistics
    pdf_dir = Path("data/pdf_cache")
    if pdf_dir.exists():
        pdf_files = list(pdf_dir.glob("*.pdf"))
        total_size = sum(f.stat().st_size for f in pdf_files)
        print(f"\nCache statistics:")
        print(f"  PDF files: {len(pdf_files)}")
        print(f"  Total size: {total_size/1024/1024:.1f} MB")
        print(f"  Average size: {total_size/len(pdf_files)/1024/1024:.1f} MB per PDF")
    
    # Save results
    results_path = Path("data/benchmark_pdf_acquisition_results.json")
    with open(results_path, "w") as f:
        json.dump({
            'total_papers': len(benchmark_papers),
            'pdfs_acquired': successful,
            'acquisition_rate': successful/len(benchmark_papers),
            'time_elapsed': elapsed_total,
            'source_breakdown': source_counts,
            'detailed_results': results
        }, f, indent=2)
    
    print(f"\nResults saved to: {results_path}")
    
    # Papers still needing PDFs
    missing_pdfs = [r for r in results if not r['pdf_found']]
    if missing_pdfs:
        print(f"\nPapers without PDFs: {len(missing_pdfs)}")
        print("First 10 missing:")
        for m in missing_pdfs[:10]:
            print(f"  - {m['title'][:60]}...")

if __name__ == "__main__":
    acquire_benchmark_pdfs()