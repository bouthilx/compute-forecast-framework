#!/usr/bin/env python3
"""Compare different consolidation sources for coverage, speed, and accuracy."""

import time
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
from datetime import datetime

# Add the project root to the Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compute_forecast.pipeline.consolidation.sources.semantic_scholar import SemanticScholarSource
from compute_forecast.pipeline.consolidation.sources.openalex import OpenAlexSource
from compute_forecast.pipeline.metadata_collection.sources.scrapers.models import SimplePaper


@dataclass
class SourceMetrics:
    """Metrics for a consolidation source."""
    name: str
    papers_found: int
    papers_total: int
    avg_title_search_time: float
    avg_doi_search_time: float
    avg_arxiv_search_time: float
    field_coverage: Dict[str, int]
    has_abstract: int
    has_citations: int
    has_venue: int
    has_authors: int
    errors: List[str]


class CrossrefClient:
    """Simple Crossref client for testing."""
    
    def __init__(self):
        self.base_url = "https://api.crossref.org/works"
        self.headers = {"User-Agent": "ComputeForecast/1.0 (mailto:test@example.com)"}
    
    def search_by_title(self, title: str) -> Optional[Dict]:
        """Search for a paper by title."""
        try:
            response = requests.get(
                self.base_url,
                params={"query.title": title, "rows": 1},
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("message", {}).get("items", [])
                return items[0] if items else None
        except Exception as e:
            print(f"Crossref title search error: {e}")
        return None
    
    def get_by_doi(self, doi: str) -> Optional[Dict]:
        """Get a paper by DOI."""
        try:
            response = requests.get(
                f"{self.base_url}/{doi}",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("message")
        except Exception as e:
            print(f"Crossref DOI lookup error: {e}")
        return None


class ZetaAlphaClient:
    """Simple Zeta Alpha client for testing (if API is available)."""
    
    def __init__(self):
        # This is a placeholder - would need actual API credentials
        self.base_url = "https://api.zeta-alpha.com/v1"
        self.api_key = os.environ.get("ZETA_ALPHA_API_KEY", "")
    
    def search_by_title(self, title: str) -> Optional[Dict]:
        """Search for a paper by title."""
        if not self.api_key:
            return None
        # Placeholder implementation
        return None
    
    def get_by_doi(self, doi: str) -> Optional[Dict]:
        """Get a paper by DOI."""
        if not self.api_key:
            return None
        # Placeholder implementation
        return None


def load_test_papers() -> List[SimplePaper]:
    """Load a diverse set of test papers."""
    # These are well-known ML/AI papers from different venues and years
    test_papers = [
        SimplePaper(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            year=2017,
            doi="10.48550/arXiv.1706.03762",
            arxiv_id="1706.03762",
            venue="NeurIPS",
            abstract="",
            paper_id="neurips_2017_attention"
        ),
        SimplePaper(
            title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
            year=2019,
            doi="10.18653/v1/N19-1423",
            arxiv_id="1810.04805",
            venue="NAACL",
            abstract="",
            paper_id="naacl_2019_bert"
        ),
        SimplePaper(
            title="Generative Adversarial Networks",
            authors=["Ian J. Goodfellow", "Jean Pouget-Abadie", "Mehdi Mirza"],
            year=2014,
            doi="10.48550/arXiv.1406.2661",
            arxiv_id="1406.2661",
            venue="NeurIPS",
            abstract="",
            paper_id="neurips_2014_gan"
        ),
        SimplePaper(
            title="Deep Residual Learning for Image Recognition",
            authors=["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
            year=2016,
            doi="10.1109/CVPR.2016.90",
            arxiv_id="1512.03385",
            venue="CVPR",
            abstract="",
            paper_id="cvpr_2016_resnet"
        ),
        SimplePaper(
            title="Adam: A Method for Stochastic Optimization",
            authors=["Diederik P. Kingma", "Jimmy Ba"],
            year=2015,
            doi="10.48550/arXiv.1412.6980",
            arxiv_id="1412.6980",
            venue="ICLR",
            abstract="",
            paper_id="iclr_2015_adam"
        ),
        SimplePaper(
            title="The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks",
            authors=["Jonathan Frankle", "Michael Carbin"],
            year=2019,
            doi="10.48550/arXiv.1803.03635",
            arxiv_id="1803.03635",
            venue="ICLR",
            abstract="",
            paper_id="iclr_2019_lottery"
        ),
        SimplePaper(
            title="Language Models are Few-Shot Learners",
            authors=["Tom B. Brown", "Benjamin Mann", "Nick Ryder"],
            year=2020,
            doi="10.48550/arXiv.2005.14165",
            arxiv_id="2005.14165",
            venue="NeurIPS",
            abstract="",
            paper_id="neurips_2020_gpt3"
        ),
        SimplePaper(
            title="CLIP: Connecting Text and Images",
            authors=["Alec Radford", "Jong Wook Kim", "Chris Hallacy"],
            year=2021,
            doi="10.48550/arXiv.2103.00020",
            arxiv_id="2103.00020",
            venue="ICML",
            abstract="",
            paper_id="icml_2021_clip"
        ),
        SimplePaper(
            title="Denoising Diffusion Probabilistic Models",
            authors=["Jonathan Ho", "Ajay Jain", "Pieter Abbeel"],
            year=2020,
            doi="10.48550/arXiv.2006.11239",
            arxiv_id="2006.11239",
            venue="NeurIPS",
            abstract="",
            paper_id="neurips_2020_ddpm"
        ),
        SimplePaper(
            title="Constitutional AI: Harmlessness from AI Feedback",
            authors=["Yuntao Bai", "Saurav Kadavath", "Sandipan Kundu"],
            year=2022,
            doi="10.48550/arXiv.2212.08073",
            arxiv_id="2212.08073",
            venue="arXiv",
            abstract="",
            paper_id="arxiv_2022_constitutional"
        )
    ]
    return test_papers


def test_source(source, papers: List[SimplePaper], source_name: str) -> SourceMetrics:
    """Test a consolidation source with various papers."""
    metrics = SourceMetrics(
        name=source_name,
        papers_found=0,
        papers_total=len(papers),
        avg_title_search_time=0.0,
        avg_doi_search_time=0.0,
        avg_arxiv_search_time=0.0,
        field_coverage={},
        has_abstract=0,
        has_citations=0,
        has_venue=0,
        has_authors=0,
        errors=[]
    )
    
    title_times = []
    doi_times = []
    arxiv_times = []
    
    for paper in papers:
        try:
            # Test title search
            if hasattr(source, 'find_by_title'):
                start = time.time()
                result = source.find_by_title(paper.title)
                title_times.append(time.time() - start)
                if result:
                    metrics.papers_found += 1
                    if result.abstract:
                        metrics.has_abstract += 1
                    if hasattr(result, 'citations') and result.citations is not None:
                        metrics.has_citations += 1
                    if result.venue:
                        metrics.has_venue += 1
                    if result.authors:
                        metrics.has_authors += 1
                    
                    # Track field coverage
                    if hasattr(result, 'fields_of_study'):
                        for field in result.fields_of_study or []:
                            metrics.field_coverage[field] = metrics.field_coverage.get(field, 0) + 1
                    elif hasattr(result, 'concepts'):
                        for concept in result.concepts or []:
                            field = concept.get('display_name', '')
                            if field:
                                metrics.field_coverage[field] = metrics.field_coverage.get(field, 0) + 1
            
            # Test DOI lookup
            if paper.doi and hasattr(source, 'find_by_doi'):
                start = time.time()
                result = source.find_by_doi(paper.doi)
                doi_times.append(time.time() - start)
            
            # Test arXiv lookup
            if paper.arxiv_id and hasattr(source, 'find_by_arxiv_id'):
                start = time.time()
                result = source.find_by_arxiv_id(paper.arxiv_id)
                arxiv_times.append(time.time() - start)
            
            # Small delay to respect rate limits
            time.sleep(0.1)
            
        except Exception as e:
            metrics.errors.append(f"Error with paper '{paper.title}': {str(e)}")
    
    # Calculate averages
    if title_times:
        metrics.avg_title_search_time = sum(title_times) / len(title_times)
    if doi_times:
        metrics.avg_doi_search_time = sum(doi_times) / len(doi_times)
    if arxiv_times:
        metrics.avg_arxiv_search_time = sum(arxiv_times) / len(arxiv_times)
    
    return metrics


def test_crossref(papers: List[SimplePaper]) -> SourceMetrics:
    """Test Crossref API."""
    client = CrossrefClient()
    metrics = SourceMetrics(
        name="Crossref",
        papers_found=0,
        papers_total=len(papers),
        avg_title_search_time=0.0,
        avg_doi_search_time=0.0,
        avg_arxiv_search_time=0.0,
        field_coverage={},
        has_abstract=0,
        has_citations=0,
        has_venue=0,
        has_authors=0,
        errors=[]
    )
    
    title_times = []
    doi_times = []
    
    for paper in papers:
        try:
            # Test title search
            start = time.time()
            result = client.search_by_title(paper.title)
            title_times.append(time.time() - start)
            
            if result:
                metrics.papers_found += 1
                if result.get('abstract'):
                    metrics.has_abstract += 1
                if result.get('is-referenced-by-count'):
                    metrics.has_citations += 1
                if result.get('container-title'):
                    metrics.has_venue += 1
                if result.get('author'):
                    metrics.has_authors += 1
                
                # Track subjects
                for subject in result.get('subject', []):
                    metrics.field_coverage[subject] = metrics.field_coverage.get(subject, 0) + 1
            
            # Test DOI lookup
            if paper.doi:
                start = time.time()
                result = client.get_by_doi(paper.doi)
                doi_times.append(time.time() - start)
            
            time.sleep(0.5)  # Be nice to Crossref
            
        except Exception as e:
            metrics.errors.append(f"Error with paper '{paper.title}': {str(e)}")
    
    if title_times:
        metrics.avg_title_search_time = sum(title_times) / len(title_times)
    if doi_times:
        metrics.avg_doi_search_time = sum(doi_times) / len(doi_times)
    
    return metrics


def main():
    """Run the comparison."""
    print("Loading test papers...")
    papers = load_test_papers()
    print(f"Testing with {len(papers)} diverse ML/AI papers\n")
    
    results = []
    
    # Test Semantic Scholar
    print("Testing Semantic Scholar...")
    ss_source = SemanticScholarSource()
    ss_metrics = test_source(ss_source, papers, "Semantic Scholar")
    results.append(ss_metrics)
    print(f"  Found {ss_metrics.papers_found}/{ss_metrics.papers_total} papers")
    print(f"  Avg title search: {ss_metrics.avg_title_search_time:.3f}s")
    print(f"  Avg DOI lookup: {ss_metrics.avg_doi_search_time:.3f}s")
    print(f"  Avg arXiv lookup: {ss_metrics.avg_arxiv_search_time:.3f}s\n")
    
    # Test OpenAlex
    print("Testing OpenAlex...")
    oa_source = OpenAlexSource()
    oa_metrics = test_source(oa_source, papers, "OpenAlex")
    results.append(oa_metrics)
    print(f"  Found {oa_metrics.papers_found}/{oa_metrics.papers_total} papers")
    print(f"  Avg title search: {oa_metrics.avg_title_search_time:.3f}s")
    print(f"  Avg DOI lookup: {oa_metrics.avg_doi_search_time:.3f}s\n")
    
    # Test Crossref
    print("Testing Crossref...")
    cr_metrics = test_crossref(papers)
    results.append(cr_metrics)
    print(f"  Found {cr_metrics.papers_found}/{cr_metrics.papers_total} papers")
    print(f"  Avg title search: {cr_metrics.avg_title_search_time:.3f}s")
    print(f"  Avg DOI lookup: {cr_metrics.avg_doi_search_time:.3f}s\n")
    
    # Note about Zeta Alpha
    print("Note: Zeta Alpha requires API credentials and is not tested here.\n")
    
    # Save results
    results_dict = {
        "test_date": datetime.now().isoformat(),
        "papers_tested": len(papers),
        "results": [asdict(r) for r in results]
    }
    
    with open("source_comparison_results.json", "w") as f:
        json.dump(results_dict, f, indent=2)
    
    print("\n=== SUMMARY ===")
    print(f"{'Source':<20} {'Found':<10} {'Title(s)':<10} {'DOI(s)':<10} {'arXiv(s)':<10} {'Abstract':<10} {'Citations':<10}")
    print("-" * 90)
    
    for r in results:
        print(f"{r.name:<20} {r.papers_found}/{r.papers_total:<8} "
              f"{r.avg_title_search_time:<10.3f} {r.avg_doi_search_time:<10.3f} "
              f"{r.avg_arxiv_search_time:<10.3f} {r.has_abstract:<10} {r.has_citations:<10}")
    
    print("\n=== FIELD COVERAGE ===")
    for r in results:
        if r.field_coverage:
            print(f"\n{r.name}:")
            for field, count in sorted(r.field_coverage.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {field}: {count}")
    
    print("\nResults saved to source_comparison_results.json")


if __name__ == "__main__":
    main()