#!/usr/bin/env python3
"""
Simple direct collection script bypassing import issues
"""
import requests
import json
import time
from datetime import datetime
from collections import defaultdict

# Research domains from analysis
DOMAINS = {
    "Computer Vision & Medical Imaging": ["computer vision", "medical imaging", "image processing", "deep learning", "CNN"],
    "Natural Language Processing": ["natural language processing", "NLP", "language model", "text analysis", "machine translation"],
    "Reinforcement Learning & Robotics": ["reinforcement learning", "robotics", "RL", "policy gradient", "robot learning"],
    "Graph Learning & Network Analysis": ["graph neural network", "network analysis", "graph learning", "GNN", "social network"],
    "Scientific Computing & Applications": ["computational biology", "computational physics", "scientific computing", "numerical methods", "simulation"]
}

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
TARGET_PER_DOMAIN_YEAR = 8

def semantic_scholar_search(query, year, limit=10):
    """Search Semantic Scholar API"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        'query': query,
        'year': f"{year}-{year}",
        'limit': limit,
        'fields': 'paperId,title,abstract,authors,year,citationCount,venue,url'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        papers = []
        for paper in data.get('data', []):
            papers.append({
                'id': paper.get('paperId', ''),
                'title': paper.get('title', ''),
                'abstract': paper.get('abstract', ''),
                'authors': [a.get('name', '') for a in paper.get('authors', [])],
                'year': paper.get('year', year),
                'citations': paper.get('citationCount', 0),
                'venue': paper.get('venue', ''),
                'url': paper.get('url', ''),
                'source': 'semantic_scholar'
            })
        
        return papers
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
        return []

def openalex_search(query, year, limit=10):
    """Search OpenAlex API"""
    url = "https://api.openalex.org/works"
    params = {
        'search': query,
        'filter': f'publication_year:{year}',
        'per-page': limit,
        'select': 'id,title,abstract,authorships,publication_year,cited_by_count,primary_location,open_access'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        papers = []
        for work in data.get('results', []):
            # Extract venue from primary_location
            venue = ''
            if work.get('primary_location'):
                source_info = work['primary_location'].get('source', {})
                if source_info:
                    venue = source_info.get('display_name', '')
            
            papers.append({
                'id': work.get('id', ''),
                'title': work.get('title', ''),
                'abstract': work.get('abstract', ''),
                'authors': [a['author']['display_name'] for a in work.get('authorships', []) if a.get('author')],
                'year': work.get('publication_year', year),
                'citations': work.get('cited_by_count', 0),
                'venue': venue,
                'url': work.get('id', ''),
                'source': 'openalex'
            })
        
        return papers
    except Exception as e:
        print(f"OpenAlex error: {e}")
        return []

def collect_papers_for_domain_year(domain_name, keywords, year, target_count):
    """Collect papers for a specific domain and year"""
    collected_papers = []
    
    # Try each keyword
    for keyword in keywords[:3]:  # Use top 3 keywords
        print(f"    Searching for '{keyword}' in {year}...")
        
        # Semantic Scholar
        ss_papers = semantic_scholar_search(keyword, year, limit=5)
        collected_papers.extend(ss_papers)
        time.sleep(1)  # Rate limiting
        
        # OpenAlex
        oa_papers = openalex_search(keyword, year, limit=5)
        collected_papers.extend(oa_papers)
        time.sleep(1)  # Rate limiting
    
    # Remove duplicates by title
    unique_papers = []
    seen_titles = set()
    for paper in collected_papers:
        title = paper.get('title', '').lower().strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            # Add collection metadata
            paper['mila_domain'] = domain_name
            paper['collection_year'] = year
            paper['collection_timestamp'] = datetime.now().isoformat()
            unique_papers.append(paper)
    
    # Sort by citations and take top papers
    unique_papers.sort(key=lambda x: x.get('citations', 0), reverse=True)
    return unique_papers[:target_count]

def main():
    print("=== Worker 6: Full-Scale Paper Collection ===")
    print(f"Starting at: {datetime.now()}")
    print(f"Target: {len(DOMAINS)} domains × {len(YEARS)} years × {TARGET_PER_DOMAIN_YEAR} papers = {len(DOMAINS) * len(YEARS) * TARGET_PER_DOMAIN_YEAR} papers")
    
    all_papers = []
    collection_stats = defaultdict(lambda: defaultdict(int))
    source_distribution = defaultdict(int)
    
    # Update status - starting collection
    status = {
        'worker_id': 'worker6',
        'last_update': datetime.now().isoformat(),
        'overall_status': 'in_progress',
        'completion_percentage': 20,
        'current_task': 'Starting domain collection',
        'collection_progress': {
            'domains_completed': 0,
            'domains_total': len(DOMAINS),
            'papers_collected': 0,
            'setup_complete': True
        },
        'ready_for_handoff': False,
        'outputs_available': []
    }
    
    with open('status/worker6-overall.json', 'w') as f:
        json.dump(status, f, indent=2)
    
    domain_count = 0
    for domain_name, keywords in DOMAINS.items():
        domain_count += 1
        print(f"\n=== Domain {domain_count}/{len(DOMAINS)}: {domain_name} ===")
        
        for year in YEARS:
            print(f"  Collecting {domain_name} - {year}")
            
            papers = collect_papers_for_domain_year(domain_name, keywords, year, TARGET_PER_DOMAIN_YEAR)
            all_papers.extend(papers)
            
            collection_stats[domain_name][year] = len(papers)
            
            # Track source distribution
            for paper in papers:
                source_distribution[paper.get('source', 'unknown')] += 1
            
            print(f"    Collected {len(papers)} papers for {domain_name} {year}")
            
            # Update progress
            total_collected = len(all_papers)
            completion_pct = min(95, 20 + (total_collected / (len(DOMAINS) * len(YEARS) * TARGET_PER_DOMAIN_YEAR)) * 75)
            
            status['last_update'] = datetime.now().isoformat()
            status['completion_percentage'] = int(completion_pct)
            status['current_task'] = f'Collecting {domain_name} - {year}'
            status['collection_progress']['papers_collected'] = total_collected
            status['collection_progress']['domains_completed'] = domain_count if year == YEARS[-1] else domain_count - 1
            
            with open('status/worker6-overall.json', 'w') as f:
                json.dump(status, f, indent=2)
    
    print(f"\n=== Collection Complete ===")
    print(f"Total papers collected: {len(all_papers)}")
    print(f"Source distribution: {dict(source_distribution)}")
    
    # Save results
    with open('data/raw_collected_papers.json', 'w') as f:
        json.dump(all_papers, f, indent=2)
    
    # Convert defaultdict to regular dict for JSON serialization
    stats_dict = {domain: dict(years) for domain, years in collection_stats.items()}
    with open('data/collection_statistics.json', 'w') as f:
        json.dump({
            'collection_stats': stats_dict,
            'source_distribution': dict(source_distribution),
            'total_papers': len(all_papers),
            'domains_covered': len(DOMAINS),
            'years_covered': len(YEARS),
            'collection_timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    # Final status update
    final_status = {
        'worker_id': 'worker6',
        'last_update': datetime.now().isoformat(),
        'overall_status': 'completed',
        'completion_percentage': 100,
        'current_task': f'Collection complete - {len(all_papers)} papers collected',
        'collection_progress': {
            'domains_completed': len(DOMAINS),
            'domains_total': len(DOMAINS),
            'papers_collected': len(all_papers),
            'setup_complete': True
        },
        'ready_for_handoff': len(all_papers) >= 200,  # Reasonable threshold
        'outputs_available': [
            'data/raw_collected_papers.json',
            'data/collection_statistics.json'
        ]
    }
    
    with open('status/worker6-overall.json', 'w') as f:
        json.dump(final_status, f, indent=2)
    
    print(f"\n=== Final Summary ===")
    print(f"✅ Papers collected: {len(all_papers)}")
    print(f"✅ Domains covered: {len(DOMAINS)}")
    print(f"✅ Years covered: {len(YEARS)}")
    print(f"✅ Ready for Worker 7: {len(all_papers) >= 200}")
    
    return len(all_papers) >= 200

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Worker 6 collection completed successfully!")
    else:
        print("\n⚠️ Worker 6 collection completed with low paper count")