#!/usr/bin/env python3
"""
Collection Validation Script - Task 6.3
Validates collection results and generates comprehensive statistics
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

def validate_collection_results() -> Dict[str, Any]:
    """Validate collection completeness and quality"""
    
    # Expected domains and years
    expected_domains = [
        'Computer Vision & Medical Imaging',
        'Natural Language Processing', 
        'Reinforcement Learning & Robotics',
        'Graph Learning & Network Analysis',
        'Scientific Computing & Applications'
    ]
    expected_years = list(range(2019, 2025))  # 2019-2024
    expected_combinations = len(expected_domains) * len(expected_years)
    
    validation = {
        'collection_completeness': {},
        'quality_indicators': {},
        'coverage_gaps': [],
        'recommendations': [],
        'domain_analysis': {},
        'success_criteria_assessment': {}
    }
    
    # Check if collection files exist
    raw_papers_file = 'data/raw_collected_papers.json'
    stats_file = 'data/collection_statistics.json' 
    failed_file = 'data/failed_searches.json'
    
    files_exist = {
        'raw_papers': os.path.exists(raw_papers_file),
        'statistics': os.path.exists(stats_file),
        'failed_searches': os.path.exists(failed_file)
    }
    
    print(f"📂 Checking collection output files:")
    for file_type, exists in files_exist.items():
        status = "✅ Found" if exists else "❌ Missing"
        print(f"  {file_type}: {status}")
    
    if not files_exist['raw_papers']:
        print("❌ No collection data found. Collection may have failed or is incomplete.")
        validation['collection_completeness']['status'] = 'failed'
        validation['recommendations'].append('Re-run collection process')
        return validation
    
    # Load collection data
    try:
        with open(raw_papers_file, 'r') as f:
            papers = json.load(f)
        print(f"📚 Loaded {len(papers)} collected papers")
    except Exception as e:
        print(f"❌ Failed to load papers: {e}")
        validation['collection_completeness']['status'] = 'failed'
        return validation
    
    # Analyze domain/year coverage
    actual_combinations = set()
    domain_year_counts = defaultdict(lambda: defaultdict(int))
    source_distribution = defaultdict(int)
    
    for paper in papers:
        domain = paper.get('mila_domain', 'Unknown')
        year = paper.get('collection_year', paper.get('year', 0))
        source = paper.get('source', 'unknown')
        
        if domain in expected_domains and year in expected_years:
            actual_combinations.add((domain, year))
            domain_year_counts[domain][year] += 1
        
        source_distribution[source] += 1
    
    # Calculate coverage
    coverage_percentage = len(actual_combinations) / expected_combinations
    
    validation['collection_completeness'] = {
        'expected_combinations': expected_combinations,
        'actual_combinations': len(actual_combinations),
        'coverage_percentage': coverage_percentage,
        'total_papers': len(papers),
        'status': 'good' if coverage_percentage >= 0.8 else 'partial' if coverage_percentage >= 0.5 else 'poor'
    }
    
    print(f"📊 Coverage Analysis:")
    print(f"  Expected domain/year combinations: {expected_combinations}")
    print(f"  Actual combinations covered: {len(actual_combinations)}")
    print(f"  Coverage percentage: {coverage_percentage:.1%}")
    
    # Identify coverage gaps
    for domain in expected_domains:
        for year in expected_years:
            if (domain, year) not in actual_combinations:
                validation['coverage_gaps'].append({
                    'domain': domain,
                    'year': year,
                    'papers_found': 0
                })
    
    print(f"  Coverage gaps: {len(validation['coverage_gaps'])}")
    
    # Quality indicators
    papers_with_citations = len([p for p in papers if p.get('citations', 0) > 0])
    papers_with_abstracts = len([p for p in papers if p.get('abstract', '')])
    papers_with_venues = len([p for p in papers if p.get('venue', '')])
    papers_with_computational_analysis = len([p for p in papers if 'computational_analysis' in p])
    
    avg_citations = sum(p.get('citations', 0) for p in papers) / len(papers) if papers else 0
    
    validation['quality_indicators'] = {
        'papers_with_citations_pct': papers_with_citations / len(papers),
        'papers_with_abstracts_pct': papers_with_abstracts / len(papers), 
        'papers_with_venues_pct': papers_with_venues / len(papers),
        'papers_with_computational_analysis_pct': papers_with_computational_analysis / len(papers),
        'avg_citations_per_paper': avg_citations,
        'source_diversity': len(source_distribution),
        'source_distribution': dict(source_distribution)
    }
    
    print(f"📈 Quality Indicators:")
    print(f"  Papers with citations: {papers_with_citations}/{len(papers)} ({papers_with_citations/len(papers):.1%})")
    print(f"  Papers with abstracts: {papers_with_abstracts}/{len(papers)} ({papers_with_abstracts/len(papers):.1%})")
    print(f"  Papers with venues: {papers_with_venues}/{len(papers)} ({papers_with_venues/len(papers):.1%})")
    print(f"  Average citations per paper: {avg_citations:.1f}")
    print(f"  Source diversity: {len(source_distribution)} sources")
    print(f"  Source distribution: {dict(source_distribution)}")
    
    # Domain analysis
    for domain in expected_domains:
        domain_papers = [p for p in papers if p.get('mila_domain') == domain]
        year_coverage = len(set(p.get('collection_year', p.get('year', 0)) for p in domain_papers))
        
        validation['domain_analysis'][domain] = {
            'total_papers': len(domain_papers),
            'years_covered': year_coverage,
            'avg_papers_per_year': len(domain_papers) / year_coverage if year_coverage > 0 else 0,
            'citation_stats': {
                'min': min((p.get('citations', 0) for p in domain_papers), default=0),
                'max': max((p.get('citations', 0) for p in domain_papers), default=0),
                'avg': sum(p.get('citations', 0) for p in domain_papers) / len(domain_papers) if domain_papers else 0
            }
        }
    
    print(f"📋 Domain Analysis:")
    for domain, stats in validation['domain_analysis'].items():
        print(f"  {domain}: {stats['total_papers']} papers, {stats['years_covered']} years")
    
    # Success criteria assessment (from original requirements)
    success_criteria = {
        '800+_papers_collected': len(papers) >= 800,
        'coverage_80%_plus': coverage_percentage >= 0.8,
        'citations_90%_plus': validation['quality_indicators']['papers_with_citations_pct'] >= 0.9,
        'computational_analysis_complete': validation['quality_indicators']['papers_with_computational_analysis_pct'] >= 0.8,
        'source_diversity_good': len(source_distribution) >= 2
    }
    
    validation['success_criteria_assessment'] = success_criteria
    
    print(f"✅ Success Criteria Assessment:")
    for criterion, met in success_criteria.items():
        status = "✅ MET" if met else "❌ NOT MET"
        print(f"  {criterion}: {status}")
    
    # Generate recommendations
    if coverage_percentage < 0.8:
        validation['recommendations'].append('Significant coverage gaps - consider additional collection methods or longer collection time')
    
    if validation['quality_indicators']['papers_with_citations_pct'] < 0.9:
        validation['recommendations'].append('High number of papers without citation data - verify API sources')
    
    if len(validation['coverage_gaps']) > 10:
        validation['recommendations'].append('Many domain/year combinations missing - focus collection on specific gaps')
    
    if validation['quality_indicators']['source_diversity'] < 2:
        validation['recommendations'].append('Low source diversity - ensure multiple APIs are working')
    
    print(f"🔍 Recommendations:")
    for rec in validation['recommendations']:
        print(f"  - {rec}")
    
    return validation

def generate_collection_statistics(validation: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive collection statistics"""
    
    # Try to load existing statistics if available
    stats_file = 'data/collection_statistics.json'
    if os.path.exists(stats_file):
        try:
            with open(stats_file, 'r') as f:
                existing_stats = json.load(f)
        except:
            existing_stats = {}
    else:
        existing_stats = {}
    
    # Enhance with validation results
    enhanced_stats = {
        'collection_summary': existing_stats.get('collection_summary', {}),
        'validation_results': validation,
        'analysis_timestamp': datetime.now().isoformat(),
        'overall_assessment': {
            'collection_status': validation['collection_completeness']['status'],
            'success_criteria_met': sum(validation['success_criteria_assessment'].values()),
            'success_criteria_total': len(validation['success_criteria_assessment']),
            'ready_for_next_phase': validation['collection_completeness']['coverage_percentage'] >= 0.7
        }
    }
    
    return enhanced_stats

def main():
    print("🔍 Starting Collection Validation (Task 6.3)...")
    
    # Validate collection results
    validation = validate_collection_results()
    
    # Generate enhanced statistics
    stats = generate_collection_statistics(validation)
    
    # Save validation results
    os.makedirs('status', exist_ok=True)
    
    with open('status/worker6-validation.json', 'w') as f:
        json.dump(validation, f, indent=2)
    
    with open('data/enhanced_collection_statistics.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n💾 Validation results saved:")
    print(f"  - status/worker6-validation.json")
    print(f"  - data/enhanced_collection_statistics.json")
    
    # Overall assessment
    overall_status = stats['overall_assessment']['collection_status']
    success_rate = stats['overall_assessment']['success_criteria_met'] / stats['overall_assessment']['success_criteria_total']
    
    print(f"\n🎯 Overall Assessment:")
    print(f"  Collection Status: {overall_status.upper()}")
    print(f"  Success Criteria: {stats['overall_assessment']['success_criteria_met']}/{stats['overall_assessment']['success_criteria_total']} ({success_rate:.1%})")
    print(f"  Ready for Next Phase: {'✅ YES' if stats['overall_assessment']['ready_for_next_phase'] else '❌ NO'}")
    
    return overall_status in ['good', 'partial'] and success_rate >= 0.6

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)