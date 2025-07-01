#!/usr/bin/env python3
"""Select Mila papers from paperoni dataset for computational analysis."""

import json
import argparse
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.analysis.mila.paper_selector import (
    MilaPaperSelector,
    PaperSelectionCriteria
)


def main():
    parser = argparse.ArgumentParser(
        description="Select Mila papers for computational analysis"
    )
    parser.add_argument(
        "--input", "-i",
        default="/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json",
        help="Input JSON file with Mila papers"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/mila_selected_papers.json",
        help="Output JSON file for selected papers"
    )
    parser.add_argument(
        "--summary", "-s",
        default="data/mila_selection_summary.json",
        help="Output JSON file for selection summary"
    )
    parser.add_argument(
        "--papers-per-year-min",
        type=int,
        default=15,
        help="Minimum papers per year"
    )
    parser.add_argument(
        "--papers-per-year-max",
        type=int,
        default=30,
        help="Maximum papers per year"
    )
    parser.add_argument(
        "--min-richness",
        type=float,
        default=0.1,
        help="Minimum computational richness score"
    )
    parser.add_argument(
        "--with-abstract-only",
        action="store_true",
        help="Only select papers with abstracts"
    )
    args = parser.parse_args()
    
    # Create output directory if needed
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize selector
    selector = MilaPaperSelector()
    
    # Load papers
    print(f"Loading papers from {args.input}...")
    papers = selector.load_papers(args.input)
    print(f"Loaded {len(papers)} papers")
    
    # Filter papers with abstracts if requested
    if args.with_abstract_only:
        papers = [p for p in papers if p.get("abstract", "").strip()]
        print(f"Papers with abstracts: {len(papers)}")
    
    # Create selection criteria
    criteria = PaperSelectionCriteria(
        papers_per_year_min=args.papers_per_year_min,
        papers_per_year_max=args.papers_per_year_max,
        min_computational_richness=args.min_richness
    )
    
    # Select papers
    print("\nSelecting papers...")
    selected = selector.select_papers(papers, criteria)
    print(f"Selected {len(selected)} papers")
    
    # Generate summary
    summary = selector.generate_selection_summary(selected)
    
    # Print summary
    print("\nSelection Summary:")
    print(f"  Total selected: {summary['total_selected']}")
    print("\n  By year:")
    for year in sorted(summary['by_year'].keys()):
        print(f"    {year}: {summary['by_year'][year]} papers")
    print("\n  By domain:")
    for domain in sorted(summary['by_domain'].keys()):
        print(f"    {domain}: {summary['by_domain'][domain]} papers")
    print(f"\n  Venue distribution:")
    print(f"    Top-tier: {summary['by_venue_tier']['top']} papers")
    print(f"    Other: {summary['by_venue_tier']['other']} papers")
    print(f"\n  Computational richness:")
    print(f"    Mean: {summary['computational_richness']['mean']:.3f}")
    print(f"    Std: {summary['computational_richness']['std']:.3f}")
    print(f"    Range: [{summary['computational_richness']['min']:.3f}, {summary['computational_richness']['max']:.3f}]")
    
    # Save selected papers
    print(f"\nSaving selected papers to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(selected, f, indent=2)
    
    # Save summary
    print(f"Saving summary to {args.summary}...")
    with open(args.summary, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\nDone!")


if __name__ == "__main__":
    main()