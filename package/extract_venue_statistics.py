#!/usr/bin/env python3
"""
Extract venue statistics from collected papers to support Worker 2 venue analysis.
This script processes collected papers to generate comprehensive venue publication statistics.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def load_collected_papers():
    """Load collected papers from existing collection files."""
    papers = []
    
    # Try multiple sources of collected papers
    paper_files = [
        'data/raw_collected_papers.json',
        'raw_collected_papers.json',
        'simple_collected_papers.json'
    ]
    
    for file_path in paper_files:
        try:
            if Path(file_path).exists():
                with open(file_path, 'r') as f:
                    file_papers = json.load(f)
                    papers.extend(file_papers)
                    print(f"Loaded {len(file_papers)} papers from {file_path}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return papers

def normalize_venue_name(venue):
    """Normalize venue names for consistent statistics."""
    if not venue:
        return ''
    
    venue = venue.strip()
    
    # Remove common variations and normalize
    venue_mappings = {
        'Conference on Computer Vision and Pattern Recognition': 'CVPR',
        'IEEE Conference on Computer Vision and Pattern Recognition': 'CVPR',
        'International Conference on Computer Vision': 'ICCV',
        'European Conference on Computer Vision': 'ECCV',
        'Conference on Neural Information Processing Systems': 'NeurIPS',
        'Neural Information Processing Systems': 'NeurIPS',
        'International Conference on Machine Learning': 'ICML',
        'International Conference on Learning Representations': 'ICLR',
        'Association for Computational Linguistics': 'ACL',
        'Empirical Methods in Natural Language Processing': 'EMNLP',
        'North American Chapter of the Association for Computational Linguistics': 'NAACL',
        'IEEE International Conference on Robotics and Automation': 'ICRA',
        'IEEE/RSJ International Conference on Intelligent Robots and Systems': 'IROS',
        'International Joint Conference on Artificial Intelligence': 'IJCAI',
        'AAAI Conference on Artificial Intelligence': 'AAAI',
        'International Conference on Artificial Intelligence and Statistics': 'AISTATS',
        'Conference on Uncertainty in Artificial Intelligence': 'UAI'
    }
    
    # Check for exact matches first
    if venue in venue_mappings:
        return venue_mappings[venue]
    
    # Remove URL-like suffixes
    venue = venue.replace('.cc/2024/Conference', '').replace('.cc/2023/Conference', '')
    venue = venue.replace('Proceedings of the ', '')
    
    # Check mappings again after cleaning
    if venue in venue_mappings:
        return venue_mappings[venue]
    
    return venue

def categorize_venue_type(venue, venue_type_hint=None):
    """Categorize venue as conference, journal, or workshop."""
    if venue_type_hint and venue_type_hint != 'unknown':
        return venue_type_hint
    
    venue_lower = venue.lower()
    
    # Workshop indicators
    if any(kw in venue_lower for kw in ['workshop', 'wksp', 'symposium']):
        return 'workshop'
    
    # Conference indicators
    if any(kw in venue_lower for kw in ['conference', 'proceedings', 'international', 'acm', 'ieee']):
        return 'conference'
    
    # Journal indicators
    if any(kw in venue_lower for kw in ['journal', 'transactions', 'letters', 'review', 'quarterly']):
        return 'journal'
    
    return 'unknown'

def calculate_venue_statistics(papers):
    """Calculate comprehensive venue statistics from collected papers."""
    
    venue_stats = defaultdict(lambda: {
        'total_papers': 0,
        'by_year': defaultdict(int),
        'by_domain': defaultdict(int),
        'citations': [],
        'venue_type': 'unknown',
        'sources': set()
    })
    
    # Process each paper
    for paper in papers:
        venue = normalize_venue_name(paper.get('venue', ''))
        if not venue or venue.lower() in ['unknown', 'n/a', '']:
            continue
        
        year = paper.get('year', paper.get('collection_year', 0))
        domain = paper.get('mila_domain', paper.get('domain', 'Unknown'))
        citations = paper.get('citations', 0) or 0
        source = paper.get('source', 'unknown')
        venue_type_hint = paper.get('venue_type', 'unknown')
        
        # Update venue statistics
        stats = venue_stats[venue]
        stats['total_papers'] += 1
        stats['by_year'][year] += 1
        stats['by_domain'][domain] += 1
        stats['citations'].append(citations)
        stats['sources'].add(source)
        
        # Determine venue type
        if stats['venue_type'] == 'unknown':
            stats['venue_type'] = categorize_venue_type(venue, venue_type_hint)
    
    # Convert to final format and calculate averages
    final_stats = {}
    for venue, stats in venue_stats.items():
        citations = stats['citations']
        final_stats[venue] = {
            'total_papers': stats['total_papers'],
            'by_year': dict(stats['by_year']),
            'by_domain': dict(stats['by_domain']),
            'venue_type': stats['venue_type'],
            'sources': list(stats['sources']),
            'citation_stats': {
                'total': sum(citations),
                'average': sum(citations) / len(citations) if citations else 0,
                'min': min(citations) if citations else 0,
                'max': max(citations) if citations else 0
            }
        }
    
    return final_stats

def generate_venue_analysis_report(venue_stats):
    """Generate analysis report for venue statistics."""
    
    total_venues = len(venue_stats)
    total_papers = sum(stats['total_papers'] for stats in venue_stats.values())
    
    # Venue type distribution
    venue_types = Counter()
    for stats in venue_stats.values():
        venue_types[stats['venue_type']] += 1
    
    # Top venues by paper count
    top_venues = sorted(venue_stats.items(), 
                       key=lambda x: x[1]['total_papers'], 
                       reverse=True)[:20]
    
    # Multi-domain venues
    multi_domain_venues = {
        venue: stats for venue, stats in venue_stats.items()
        if len(stats['by_domain']) > 1
    }
    
    # Temporal analysis
    all_years = set()
    for stats in venue_stats.values():
        all_years.update(stats['by_year'].keys())
    
    report = {
        'summary': {
            'total_venues': total_venues,
            'total_papers': total_papers,
            'venue_types': dict(venue_types),
            'years_covered': sorted(list(all_years)),
            'multi_domain_venues_count': len(multi_domain_venues)
        },
        'top_venues': [
            {
                'venue': venue,
                'papers': stats['total_papers'],
                'venue_type': stats['venue_type'],
                'avg_citations': stats['citation_stats']['average'],
                'domains': len(stats['by_domain'])
            }
            for venue, stats in top_venues
        ],
        'venue_type_analysis': {
            vtype: {
                'count': count,
                'total_papers': sum(
                    stats['total_papers'] for venue, stats in venue_stats.items()
                    if stats['venue_type'] == vtype
                )
            }
            for vtype, count in venue_types.items()
        }
    }
    
    return report

def main():
    """Main function to extract and save venue statistics."""
    print("Extracting venue statistics from collected papers...")
    
    # Load collected papers
    papers = load_collected_papers()
    if not papers:
        print("No papers found to analyze!")
        return
    
    print(f"Analyzing {len(papers)} collected papers...")
    
    # Calculate venue statistics
    venue_stats = calculate_venue_statistics(papers)
    print(f"Found statistics for {len(venue_stats)} unique venues")
    
    # Generate analysis report
    analysis_report = generate_venue_analysis_report(venue_stats)
    
    # Create output data structure for Worker 3
    output_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source': 'collected_papers_analysis',
            'total_papers_analyzed': len(papers),
            'total_venues_found': len(venue_stats)
        },
        'venue_statistics': venue_stats,
        'analysis_report': analysis_report
    }
    
    # Save to files
    output_file = 'data/venue_statistics_from_collection.json'
    Path('data').mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Venue statistics saved to: {output_file}")
    
    # Print summary
    print("\n=== VENUE STATISTICS SUMMARY ===")
    print(f"Total venues analyzed: {analysis_report['summary']['total_venues']}")
    print(f"Total papers: {analysis_report['summary']['total_papers']}")
    print(f"Venue types: {analysis_report['summary']['venue_types']}")
    print(f"Years covered: {analysis_report['summary']['years_covered']}")
    
    print("\n=== TOP 10 VENUES BY PAPER COUNT ===")
    for i, venue_info in enumerate(analysis_report['top_venues'][:10], 1):
        print(f"{i:2d}. {venue_info['venue']:30s} | "
              f"{venue_info['papers']:3d} papers | "
              f"{venue_info['venue_type']:10s} | "
              f"Avg citations: {venue_info['avg_citations']:.1f}")
    
    return output_data

if __name__ == "__main__":
    main()