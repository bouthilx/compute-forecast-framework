#!/usr/bin/env python3
"""
Example script demonstrating how to collect NeurIPS papers using the citation collectors.

This script shows how to:
1. Use the CitationCollector to gather papers from multiple sources (OpenAlex, Semantic Scholar, Google Scholar)
2. Collect papers from a specific venue (NeurIPS) for multiple years
3. Handle API rate limiting and errors gracefully
4. Save collected papers to JSON for further analysis
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Import the citation collectors
from compute_forecast.data.collectors.citation_collector import CitationCollector
from compute_forecast.data.models import CollectionQuery

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NeurIPSCollector:
    """Collector specifically for NeurIPS papers across multiple years."""
    
    def __init__(self, output_dir: str = "neurips_papers"):
        """Initialize the NeurIPS collector."""
        self.collector = CitationCollector()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Test API connectivity
        logger.info("Testing API connectivity...")
        self.api_status = self.collector.test_all_sources()
        self.working_apis = [api for api, status in self.api_status.items() if status]
        
        if not self.working_apis:
            raise RuntimeError("No working APIs available!")
        
        logger.info(f"Working APIs: {self.working_apis}")
    
    def collect_neurips_by_year(self, year: int, max_papers: int = 50) -> List[Dict[str, Any]]:
        """Collect NeurIPS papers for a specific year."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Collecting NeurIPS papers for {year}")
        logger.info(f"{'='*60}")
        
        # Create a query for NeurIPS papers
        query = CollectionQuery(
            domain="Machine Learning",  # General domain
            year=year,
            venue="NeurIPS",
            keywords=["neural", "deep learning", "machine learning"],
            max_results=max_papers,
            min_citations=0  # Include all papers regardless of citations
        )
        
        # Collect from all working sources
        results = self.collector.collect_from_all_sources(query)
        
        # Combine papers from all sources
        all_papers = []
        for source_name, result in results.items():
            if result and result.papers:
                logger.info(f"  {source_name}: {len(result.papers)} papers collected")
                
                # Convert Paper objects to dictionaries
                for paper in result.papers:
                    paper_dict = {
                        'title': paper.title,
                        'authors': [author.name for author in paper.authors] if paper.authors else [],
                        'year': paper.year,
                        'venue': paper.venue,
                        'citations': paper.citations,
                        'abstract': paper.abstract[:500] + '...' if len(paper.abstract) > 500 else paper.abstract,
                        'doi': paper.doi,
                        'urls': paper.urls,
                        'source': source_name,
                        'collection_timestamp': paper.collection_timestamp
                    }
                    all_papers.append(paper_dict)
        
        # Remove duplicates based on title similarity
        unique_papers = self._deduplicate_papers(all_papers)
        logger.info(f"Total unique papers collected for {year}: {len(unique_papers)}")
        
        return unique_papers
    
    def _deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers based on title similarity."""
        seen_titles = set()
        unique_papers = []
        
        for paper in papers:
            # Normalize title for comparison
            normalized_title = paper['title'].lower().strip()
            
            # Check if we've seen a similar title
            is_duplicate = False
            for seen_title in seen_titles:
                if self._are_titles_similar(normalized_title, seen_title):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_titles.add(normalized_title)
                unique_papers.append(paper)
        
        logger.info(f"Deduplication: {len(papers)} -> {len(unique_papers)} papers")
        return unique_papers
    
    def _are_titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough to be considered duplicates."""
        # Simple check: exact match or one is substring of other
        return (title1 == title2 or 
                title1 in title2 or 
                title2 in title1)
    
    def collect_multiple_years(self, start_year: int, end_year: int, papers_per_year: int = 50) -> Dict[int, List[Dict[str, Any]]]:
        """Collect NeurIPS papers for multiple years."""
        all_results = {}
        
        for year in range(start_year, end_year + 1):
            try:
                papers = self.collect_neurips_by_year(year, papers_per_year)
                all_results[year] = papers
                
                # Save intermediate results
                self._save_year_results(year, papers)
                
            except Exception as e:
                logger.error(f"Failed to collect papers for {year}: {e}")
                all_results[year] = []
        
        return all_results
    
    def _save_year_results(self, year: int, papers: List[Dict[str, Any]]):
        """Save collected papers for a specific year."""
        output_file = self.output_dir / f"neurips_{year}_papers.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'venue': 'NeurIPS',
                'year': year,
                'collection_date': datetime.now().isoformat(),
                'paper_count': len(papers),
                'papers': papers
            }, f, indent=2)
        
        logger.info(f"Saved {len(papers)} papers to {output_file}")
    
    def generate_summary_report(self, results: Dict[int, List[Dict[str, Any]]]):
        """Generate a summary report of the collection."""
        report = {
            'collection_summary': {
                'venue': 'NeurIPS',
                'collection_date': datetime.now().isoformat(),
                'api_status': self.api_status,
                'years_collected': list(results.keys()),
                'total_papers': sum(len(papers) for papers in results.values())
            },
            'yearly_statistics': {}
        }
        
        for year, papers in results.items():
            if papers:
                # Calculate statistics
                citations = [p['citations'] for p in papers]
                report['yearly_statistics'][year] = {
                    'paper_count': len(papers),
                    'avg_citations': sum(citations) / len(citations) if citations else 0,
                    'max_citations': max(citations) if citations else 0,
                    'min_citations': min(citations) if citations else 0,
                    'sources': {}
                }
                
                # Count papers by source
                for paper in papers:
                    source = paper['source']
                    if source not in report['yearly_statistics'][year]['sources']:
                        report['yearly_statistics'][year]['sources'][source] = 0
                    report['yearly_statistics'][year]['sources'][source] += 1
        
        # Save report
        report_file = self.output_dir / "neurips_collection_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Summary report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("NEURIPS COLLECTION SUMMARY")
        print("="*60)
        print(f"Total papers collected: {report['collection_summary']['total_papers']}")
        print(f"Years covered: {min(results.keys())} - {max(results.keys())}")
        print("\nPapers by year:")
        for year in sorted(results.keys()):
            count = len(results[year])
            print(f"  {year}: {count} papers")
        print("\nPapers by source:")
        source_totals = {}
        for year_stats in report['yearly_statistics'].values():
            for source, count in year_stats['sources'].items():
                source_totals[source] = source_totals.get(source, 0) + count
        for source, total in sorted(source_totals.items()):
            print(f"  {source}: {total} papers")
        print("="*60)


def main():
    """Main function to demonstrate NeurIPS paper collection."""
    try:
        # Initialize collector
        collector = NeurIPSCollector()
        
        # Example 1: Collect papers for a single year
        logger.info("\nExample 1: Collecting NeurIPS 2023 papers")
        papers_2023 = collector.collect_neurips_by_year(2023, max_papers=20)
        
        # Show sample papers
        print("\nSample papers from NeurIPS 2023:")
        for i, paper in enumerate(papers_2023[:5], 1):
            print(f"\n{i}. {paper['title']}")
            print(f"   Authors: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
            print(f"   Citations: {paper['citations']}")
            print(f"   Source: {paper['source']}")
        
        # Example 2: Collect papers for multiple years
        logger.info("\nExample 2: Collecting NeurIPS papers from 2020-2023")
        multi_year_results = collector.collect_multiple_years(
            start_year=2020,
            end_year=2023,
            papers_per_year=30
        )
        
        # Generate summary report
        collector.generate_summary_report(multi_year_results)
        
        # Example 3: Using alternative collection methods
        logger.info("\nExample 3: Direct venue search")
        direct_papers = collector.collector.collect_from_venue_year(
            venue="NeurIPS",
            year=2022,
            citation_threshold=5,
            working_apis=collector.working_apis
        )
        
        print(f"\nDirect search found {len(direct_papers)} papers from NeurIPS 2022 with 5+ citations")
        
        return 0
        
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())