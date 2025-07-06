#!/usr/bin/env python3
"""
Correct venue merger analysis - only merge true duplicates/variants of the same conference.
"""

import json
from pathlib import Path
from collections import defaultdict

def load_venue_data():
    """Load venue statistics and original duplicate mapping."""
    
    # Load mila venue statistics
    mila_stats_file = Path('data/mila_venue_statistics.json')
    with open(mila_stats_file, 'r') as f:
        mila_data = json.load(f)
    
    # Load original venue duplicate mapping
    mapping_file = Path('venue_duplicate_mapping.json')
    with open(mapping_file, 'r') as f:
        mapping_data = json.load(f)
    
    return mila_data.get('venue_counts', {}), mapping_data

def create_corrected_mergers(venue_counts, original_mapping):
    """Create corrected venue mergers - only true conference/journal variants."""
    
    # Define corrected mergers - only actual venue duplicates
    corrected_mergers = {
        # NeurIPS variants (all legitimate)
        'NeurIPS': [
            'NeurIPS',
            'NeurIPS.cc/2024/Conference',
            'NeurIPS.cc/2023/Conference', 
            'Advances in Neural Information Processing Systems 36  (NeurIPS 2023)',
            'Neural Information Processing Systems',
            'Advances in Neural Information Processing Systems 35  (NeurIPS 2022)',
            'NeurIPS (Competition and Demos)'
        ],
        
        # ICML variants (only conference proceedings, NOT separate ML journals)
        'ICML': [
            'ICML',
            'Proceedings of the 41st International Conference on Machine Learning',
            'Proceedings of the 40th International Conference on Machine Learning', 
            'ICML.cc/2024/Conference'
        ],
        
        # ICLR variants
        'ICLR': [
            'ICLR',
            'ICLR.cc/2024/Conference',
            'ICLR.cc/2023/Conference'
        ],
        
        # EMNLP variants (all legitimate)
        'EMNLP': [
            'EMNLP',
            'EMNLP (Findings)',
            'Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing',
            'EMNLP/2023/Conference',
            'Findings of the Association for Computational Linguistics: EMNLP 2023',
            'Findings of the Association for Computational Linguistics: EMNLP 2022',
            'Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing'
        ],
        
        # ACL family - only keep clear ACL variants, separate EACL/NAACL
        'ACL': [
            'ACL (1)',
            'Findings of the Association for Computational Linguistics ACL 2024',
            'Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)',
            'Findings of the Association for Computational Linguistics: ACL 2023',
            'Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)',
            'Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 2: Short Papers)',
            'Findings of the Association for Computational Linguistics: ACL 2022',
            'Annual Meeting of the Association for Computational Linguistics',
            'Transactions of the Association for Computational Linguistics'
        ],
        
        # EACL variants
        'EACL': [
            'EACL (1)',
            'EACL',
            'Proceedings of the 17th Conference of the European Chapter of the Association for Computational Linguistics',
            'Findings of the Association for Computational Linguistics: EACL 2023'
        ],
        
        # NAACL variants  
        'NAACL': [
            'Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)',
            'Findings of the Association for Computational Linguistics: NAACL 2024',
            'Proceedings of the 2022 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies'
        ],
        
        # AAAI variants (only conference proceedings, not separate AI journals)
        'AAAI': [
            'AAAI',
            'Proceedings of the AAAI Conference on Artificial Intelligence',
            'AAAI.org/2023/Bridge/CCBridge'
        ],
        
        # ICRA variants (robotics conference)
        'ICRA': [
            'ICRA',
            '2024 IEEE International Conference on Robotics and Automation (ICRA)',
            '2023 IEEE International Conference on Robotics and Automation (ICRA)', 
            '2022 International Conference on Robotics and Automation (ICRA)'
        ],
        
        # IROS variants (robotics conference)
        'IROS': [
            '2024 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)',
            '2023 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)',
            '2022 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)'
        ],
        
        # AISTATS variants
        'AISTATS': [
            'AISTATS',
            'Proceedings of The 27th International Conference on Artificial Intelligence and Statistics',
            'International Conference on Artificial Intelligence and Statistics',
            'Proceedings of The 26th International Conference on Artificial Intelligence and Statistics'
        ],
        
        # UAI variants
        'UAI': [
            'UAI',
            'auai.org/UAI/2024/Conference',
            'auai.org/UAI/2023/Conference',
            'auai.org/UAI/2022/Conference',
            'Proceedings of the Fortieth Conference on Uncertainty in Artificial Intelligence'
        ],
        
        # CHI variants
        'CHI': [
            'Proceedings of the CHI Conference on Human Factors in Computing Systems',
            'Proceedings of the 2023 CHI Conference on Human Factors in Computing Systems',
            'CHI Conference on Human Factors in Computing Systems'
        ],
        
        # SIGIR variants
        'SIGIR': [
            'Proceedings of the 47th International ACM SIGIR Conference on Research and Development in Information Retrieval',
            'Proceedings of the 45th International ACM SIGIR Conference on Research and Development in Information Retrieval'
        ],
        
        # ICASSP variants
        'ICASSP': [
            'ICASSP 2024 - 2024 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)',
            'ICASSP 2023 - 2023 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)',
            'ICASSP 2022 - 2022 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)'
        ],
        
        # INTERSPEECH variants
        'INTERSPEECH': [
            'Interspeech 2024',
            'INTERSPEECH 2023', 
            'Interspeech 2022'
        ],
        
        # ICC variants
        'ICC': [
            'ICC 2024 - IEEE International Conference on Communications',
            'ICC 2023 - IEEE International Conference on Communications'
        ],
        
        # ICDE variants
        'ICDE': [
            '2023 IEEE 39th International Conference on Data Engineering (ICDE)',
            '2022 IEEE 38th International Conference on Data Engineering (ICDE)'
        ],
        
        # SIGGRAPH Asia variants
        'SIGGRAPH Asia': [
            'SIGGRAPH Asia 2023 Conference Papers',
            'SIGGRAPH Asia 2022 Conference Papers'
        ],
        
        # Lifelong Learning Agents
        'CoLLAs': [
            'Proceedings of The 2nd Conference on Lifelong Learning Agents',
            'Proceedings of The 1st Conference on Lifelong Learning Agents'
        ],
        
        # LoG variants
        'LoG': [
            'logconference.io/LOG/2024/Conference',
            'logconference.io/LOG/2023/Conference'
        ],
        
        # ACM FAT variants
        'ACM FAccT': [
            '2023 ACM Conference on Fairness, Accountability, and Transparency',
            '2022 ACM Conference on Fairness, Accountability, and Transparency'
        ],
        
        # ASE variants  
        'ASE': [
            'Proceedings of the 39th IEEE/ACM International Conference on Automated Software Engineering',
            'Proceedings of the 37th IEEE/ACM International Conference on Automated Software Engineering'
        ],
        
        # WACV variants (adding to Computer Vision)
        'WACV': [
            '2023 IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)'
        ],
        
        # Journal duplicates (case variations)
        'PLOS ONE': [
            'PLoS ONE',
            'PLOS ONE',
            'PLOS One'
        ],
        
        'Nature Methods': [
            'Nature methods',
            'Nature Methods'
        ],
        
        'Canadian Journal of Public Health': [
            'Canadian Journal of Public Health',
            'Canadian journal of public health'
        ],
        
        'Electric Power Systems Research': [
            'Electric Power Systems Research',
            'Electric power systems research'
        ]
    }
    
    return corrected_mergers

def apply_corrected_merging(venue_counts, corrected_mergers):
    """Apply only the corrected venue merging."""
    
    merged_venue_counts = {}
    venues_used = set()
    
    # Apply mergers
    for canonical_venue, variant_list in corrected_mergers.items():
        merged_data = {
            'total': 0,
            'by_year': defaultdict(int),
            'domains': set(),
            'paper_count': 0,
            'unique_paper_count': 0
        }
        
        found_variants = []
        
        for variant in variant_list:
            if variant in venue_counts:
                found_variants.append(variant)
                venues_used.add(variant)
                data = venue_counts[variant]
                
                # Merge the data
                merged_data['total'] += data.get('total', 0)
                merged_data['paper_count'] += data.get('paper_count', 0) 
                merged_data['unique_paper_count'] += data.get('unique_paper_count', 0)
                
                # Merge by_year data
                for year, count in data.get('by_year', {}).items():
                    merged_data['by_year'][year] += count
                
                # Merge domains
                merged_data['domains'].update(data.get('domains', []))
        
        if found_variants:
            # Convert back to regular dict/list
            merged_data['by_year'] = dict(merged_data['by_year'])
            merged_data['domains'] = list(merged_data['domains'])
            
            merged_venue_counts[canonical_venue] = {
                'total': merged_data['total'],
                'by_year': merged_data['by_year'],
                'domains': merged_data['domains'],
                'paper_count': merged_data['paper_count'],
                'unique_paper_count': merged_data['unique_paper_count'],
                'merged_from': found_variants,
                'is_merged': len(found_variants) > 1
            }
    
    # Add venues that were not merged
    for venue, data in venue_counts.items():
        if venue not in venues_used:
            merged_venue_counts[venue] = {
                'total': data.get('total', 0),
                'by_year': data.get('by_year', {}),
                'domains': data.get('domains', []),
                'paper_count': data.get('paper_count', 0),
                'unique_paper_count': data.get('unique_paper_count', 0),
                'merged_from': [venue],
                'is_merged': False
            }
    
    return merged_venue_counts

def print_corrected_mergers(corrected_mergers, merged_venue_counts, venue_counts):
    """Print the corrected merger analysis."""
    
    print("="*80)
    print("CORRECTED VENUE MERGERS - ONLY TRUE DUPLICATES")
    print("="*80)
    
    # Sort mergers by total papers
    merger_stats = []
    for canonical, info in merged_venue_counts.items():
        if info['is_merged']:
            merger_stats.append((canonical, info))
    
    merger_stats.sort(key=lambda x: x[1]['total'], reverse=True)
    
    print(f"\nFound {len(merger_stats)} legitimate venue mergers:\n")
    
    for rank, (canonical, info) in enumerate(merger_stats, 1):
        total_papers = info['total']
        merged_from = info['merged_from']
        by_year = info['by_year']
        
        years = sorted([int(y) for y in by_year.keys() if y.isdigit()]) if by_year else []
        year_range = f"{years[0]}-{years[-1]}" if len(years) > 1 else str(years[0]) if years else "no years"
        
        print(f"{rank:2d}. {canonical}")
        print(f"    📊 Total Papers: {total_papers}")
        print(f"    📅 Years: {year_range}")
        print(f"    🔗 Merged from {len(merged_from)} variants:")
        
        for i, variant in enumerate(merged_from, 1):
            variant_data = venue_counts.get(variant, {})
            variant_papers = variant_data.get('total', 0)
            print(f"        {i:2d}. {variant} ({variant_papers} papers)")
        print()
    
    # Show venues that were incorrectly merged in original
    print("="*80)
    print("INCORRECTLY MERGED VENUES (NOW SEPARATED)")
    print("="*80)
    
    incorrectly_merged = [
        ("ICML", ["Machine Learning with Applications", "Machine Learning for Biomedical Imaging", "Machine Learning"]),
        ("AAAI", ["Annals of Mathematics and Artificial Intelligence", "Integration of Constraint Programming, Artificial Intelligence, and Operations Research", 
                 "Frontiers in Artificial Intelligence and Applications", "Frontiers in Artificial Intelligence",
                 "Journal of Artificial Intelligence Research", "European Conference on Artificial Intelligence",
                 "Proceedings of the 2023 AAAI/ACM Conference on AI, Ethics, and Society",
                 "Proceedings of the Thirty-ThirdInternational Joint Conference on Artificial Intelligence",
                 "Proceedings of the Canadian Conference on Artificial Intelligence",
                 "Proceedings of the Twenty-Eighth International Joint Conference on Artificial Intelligence",
                 "Proceedings of the Twenty Third International Conference on Artificial Intelligence and Statistics",
                 "ML4CMH@AAAI"])
    ]
    
    for canonical, incorrects in incorrectly_merged:
        print(f"\n{canonical} - These should NOT be merged:")
        for incorrect in incorrects:
            if incorrect in venue_counts:
                papers = venue_counts[incorrect].get('total', 0)
                print(f"  - {incorrect} ({papers} papers)")
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("CORRECTED SUMMARY STATISTICS")
    print(f"{'='*80}")
    
    total_venues_after = len(merged_venue_counts)
    total_merged = len(merger_stats)
    total_standalone = total_venues_after - total_merged
    
    venues_eliminated = sum(len(info['merged_from']) - 1 for _, info in merger_stats)
    original_venue_count = len(venue_counts)
    
    print(f"Original venues: {original_venue_count}")
    print(f"Venues after corrected merging: {total_venues_after}")
    print(f"Legitimate mergers: {total_merged}")
    print(f"Standalone venues: {total_standalone}")
    print(f"Venues eliminated: {venues_eliminated}")
    print(f"Reduction: {venues_eliminated/original_venue_count:.1%}")

def save_corrected_mergers(merged_venue_counts, corrected_mergers):
    """Save corrected venue mergers."""
    
    # Sort by total papers
    sorted_venues = sorted(merged_venue_counts.items(), 
                          key=lambda x: x[1]['total'], 
                          reverse=True)
    
    output_data = {
        'corrected_mergers': corrected_mergers,
        'merged_venues': {
            venue: {
                'total_papers': info['total'],
                'by_year': info['by_year'],
                'merged_from': info['merged_from'],
                'is_merged': info['is_merged']
            }
            for venue, info in sorted_venues
        },
        'summary': {
            'total_venues_after_merge': len(merged_venue_counts),
            'legitimate_mergers': sum(1 for _, info in merged_venue_counts.items() if info['is_merged']),
            'venues_eliminated': sum(len(info['merged_from']) - 1 for _, info in merged_venue_counts.items() if info['is_merged'])
        }
    }
    
    with open('corrected_venue_mergers.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nCorrected venue mergers saved to: corrected_venue_mergers.json")

def main():
    """Main function."""
    print("Loading venue data...")
    
    try:
        venue_counts, original_mapping = load_venue_data()
        
        print(f"Original venues: {len(venue_counts)}")
        
        # Create corrected mergers
        corrected_mergers = create_corrected_mergers(venue_counts, original_mapping)
        
        # Apply corrected merging
        merged_venue_counts = apply_corrected_merging(venue_counts, corrected_mergers)
        
        # Print analysis
        print_corrected_mergers(corrected_mergers, merged_venue_counts, venue_counts)
        
        # Save results
        save_corrected_mergers(merged_venue_counts, corrected_mergers)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()