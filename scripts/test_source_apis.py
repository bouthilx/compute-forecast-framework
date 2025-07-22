#!/usr/bin/env python3
"""Direct API testing for consolidation sources."""

import time
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import requests
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@dataclass
class APITestResult:
    """Results from API testing."""

    source_name: str
    papers_found_by_title: int
    papers_found_by_doi: int
    papers_found_by_arxiv: int
    total_papers_tested: int
    avg_title_search_time: float
    avg_doi_search_time: float
    avg_arxiv_search_time: float
    has_abstracts: int
    has_citations: int
    has_venues: int
    has_authors: int
    has_affiliations: int
    fields_of_study: List[str]
    errors: List[str]
    sample_response: Optional[Dict] = None


class SemanticScholarAPI:
    """Direct Semantic Scholar API client."""

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key
        self.fields = (
            "paperId,title,abstract,authors,venue,year,citationCount,fieldsOfStudy,url"
        )

    def search_by_title(self, title: str) -> Optional[Dict]:
        """Search by title."""
        try:
            # Use paper search endpoint
            response = requests.get(
                f"{self.base_url}/paper/search",
                params={"query": title, "fields": self.fields, "limit": 1},
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                papers = data.get("data", [])
                return papers[0] if papers else None
            else:
                logging.error(
                    f"S2 title search failed: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logging.error(f"S2 title search error: {e}")
        return None

    def get_by_doi(self, doi: str) -> Optional[Dict]:
        """Get by DOI."""
        try:
            response = requests.get(
                f"{self.base_url}/paper/DOI:{doi}",
                params={"fields": self.fields},
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"S2 DOI lookup error: {e}")
        return None

    def get_by_arxiv(self, arxiv_id: str) -> Optional[Dict]:
        """Get by arXiv ID."""
        try:
            response = requests.get(
                f"{self.base_url}/paper/ARXIV:{arxiv_id}",
                params={"fields": self.fields},
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"S2 arXiv lookup error: {e}")
        return None


class OpenAlexAPI:
    """Direct OpenAlex API client."""

    def __init__(self):
        self.base_url = "https://api.openalex.org"
        self.headers = {"User-Agent": "ComputeForecast/1.0 (mailto:test@example.com)"}

    def search_by_title(self, title: str) -> Optional[Dict]:
        """Search by title."""
        try:
            response = requests.get(
                f"{self.base_url}/works",
                params={"filter": f"title.search:{title}", "per_page": 1},
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                works = data.get("results", [])
                return works[0] if works else None
        except Exception as e:
            logging.error(f"OpenAlex title search error: {e}")
        return None

    def get_by_doi(self, doi: str) -> Optional[Dict]:
        """Get by DOI."""
        try:
            # Clean DOI
            if doi.startswith("10."):
                doi = f"https://doi.org/{doi}"
            response = requests.get(
                f"{self.base_url}/works/{doi}", headers=self.headers, timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"OpenAlex DOI lookup error: {e}")
        return None


class CrossrefAPI:
    """Direct Crossref API client."""

    def __init__(self):
        self.base_url = "https://api.crossref.org/works"
        self.headers = {"User-Agent": "ComputeForecast/1.0 (mailto:test@example.com)"}

    def search_by_title(self, title: str) -> Optional[Dict]:
        """Search by title."""
        try:
            response = requests.get(
                self.base_url,
                params={"query.title": title, "rows": 1},
                headers=self.headers,
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("message", {}).get("items", [])
                return items[0] if items else None
        except Exception as e:
            logging.error(f"Crossref title search error: {e}")
        return None

    def get_by_doi(self, doi: str) -> Optional[Dict]:
        """Get by DOI."""
        try:
            response = requests.get(
                f"{self.base_url}/{doi}", headers=self.headers, timeout=10
            )
            if response.status_code == 200:
                return response.json().get("message")
        except Exception as e:
            logging.error(f"Crossref DOI lookup error: {e}")
        return None


# Test papers - well-known ML/AI papers
TEST_PAPERS = [
    {
        "title": "Attention Is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "arxiv_id": "1706.03762",
        "venue": "NeurIPS 2017",
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "doi": "10.18653/v1/N19-1423",
        "arxiv_id": "1810.04805",
        "venue": "NAACL 2019",
    },
    {
        "title": "Generative Adversarial Networks",
        "doi": "10.48550/arXiv.1406.2661",
        "arxiv_id": "1406.2661",
        "venue": "NeurIPS 2014",
    },
    {
        "title": "Deep Residual Learning for Image Recognition",
        "doi": "10.1109/CVPR.2016.90",
        "arxiv_id": "1512.03385",
        "venue": "CVPR 2016",
    },
    {
        "title": "Adam: A Method for Stochastic Optimization",
        "doi": "10.48550/arXiv.1412.6980",
        "arxiv_id": "1412.6980",
        "venue": "ICLR 2015",
    },
    {
        "title": "Language Models are Few-Shot Learners",
        "doi": "10.48550/arXiv.2005.14165",
        "arxiv_id": "2005.14165",
        "venue": "NeurIPS 2020",
    },
    {
        "title": "Denoising Diffusion Probabilistic Models",
        "doi": "10.48550/arXiv.2006.11239",
        "arxiv_id": "2006.11239",
        "venue": "NeurIPS 2020",
    },
    {
        "title": "Constitutional AI: Harmlessness from AI Feedback",
        "doi": "10.48550/arXiv.2212.08073",
        "arxiv_id": "2212.08073",
        "venue": "arXiv 2022",
    },
]


def test_api(api_client, api_name: str) -> APITestResult:
    """Test an API with various lookups."""
    result = APITestResult(
        source_name=api_name,
        papers_found_by_title=0,
        papers_found_by_doi=0,
        papers_found_by_arxiv=0,
        total_papers_tested=len(TEST_PAPERS),
        avg_title_search_time=0.0,
        avg_doi_search_time=0.0,
        avg_arxiv_search_time=0.0,
        has_abstracts=0,
        has_citations=0,
        has_venues=0,
        has_authors=0,
        has_affiliations=0,
        fields_of_study=[],
        errors=[],
    )

    title_times = []
    doi_times = []
    arxiv_times = []
    fields_seen = set()

    for i, paper in enumerate(TEST_PAPERS):
        # Title search
        if hasattr(api_client, "search_by_title"):
            start = time.time()
            response = api_client.search_by_title(paper["title"])
            elapsed = time.time() - start
            title_times.append(elapsed)

            if response:
                result.papers_found_by_title += 1
                if i == 0:  # Save first response as sample
                    result.sample_response = response

                # Check fields
                if api_name == "Semantic Scholar":
                    if response.get("abstract"):
                        result.has_abstracts += 1
                    if response.get("citationCount") is not None:
                        result.has_citations += 1
                    if response.get("venue"):
                        result.has_venues += 1
                    if response.get("authors"):
                        result.has_authors += 1
                        # Check for affiliations
                        for author in response.get("authors", []):
                            if author.get("affiliations"):
                                result.has_affiliations += 1
                                break
                    for field in response.get("fieldsOfStudy", []):
                        if isinstance(field, dict):
                            fields_seen.add(field.get("category", ""))
                        else:
                            fields_seen.add(str(field))

                elif api_name == "OpenAlex":
                    if response.get("abstract_inverted_index"):
                        result.has_abstracts += 1
                    if response.get("cited_by_count") is not None:
                        result.has_citations += 1
                    if response.get("host_venue", {}).get("display_name"):
                        result.has_venues += 1
                    if response.get("authorships"):
                        result.has_authors += 1
                        for authorship in response.get("authorships", []):
                            if authorship.get("institutions"):
                                result.has_affiliations += 1
                                break
                    for concept in response.get("concepts", []):
                        fields_seen.add(concept.get("display_name", ""))

                elif api_name == "Crossref":
                    if response.get("abstract"):
                        result.has_abstracts += 1
                    if response.get("is-referenced-by-count") is not None:
                        result.has_citations += 1
                    if response.get("container-title"):
                        result.has_venues += 1
                    if response.get("author"):
                        result.has_authors += 1
                        for author in response.get("author", []):
                            if author.get("affiliation"):
                                result.has_affiliations += 1
                                break
                    for subject in response.get("subject", []):
                        fields_seen.add(subject)

        # DOI lookup
        if paper.get("doi") and hasattr(api_client, "get_by_doi"):
            start = time.time()
            response = api_client.get_by_doi(paper["doi"])
            elapsed = time.time() - start
            doi_times.append(elapsed)
            if response:
                result.papers_found_by_doi += 1

        # ArXiv lookup (only for Semantic Scholar)
        if paper.get("arxiv_id") and hasattr(api_client, "get_by_arxiv"):
            start = time.time()
            response = api_client.get_by_arxiv(paper["arxiv_id"])
            elapsed = time.time() - start
            arxiv_times.append(elapsed)
            if response:
                result.papers_found_by_arxiv += 1

        # Rate limiting
        if api_name == "Semantic Scholar":
            time.sleep(1.5)  # S2 has stricter rate limits without API key
        else:
            time.sleep(0.5)

    # Calculate averages
    if title_times:
        result.avg_title_search_time = sum(title_times) / len(title_times)
    if doi_times:
        result.avg_doi_search_time = sum(doi_times) / len(doi_times)
    if arxiv_times:
        result.avg_arxiv_search_time = sum(arxiv_times) / len(arxiv_times)

    result.fields_of_study = sorted(list(fields_seen))

    return result


def main():
    """Run API tests."""
    print(f"Testing {len(TEST_PAPERS)} well-known ML/AI papers across different APIs\n")

    results = []

    # Test Semantic Scholar
    print("Testing Semantic Scholar API...")
    s2_api = SemanticScholarAPI(api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"))
    s2_result = test_api(s2_api, "Semantic Scholar")
    results.append(s2_result)
    print(
        f"  Title search: {s2_result.papers_found_by_title}/{s2_result.total_papers_tested} found"
    )
    print(
        f"  DOI lookup: {s2_result.papers_found_by_doi}/{s2_result.total_papers_tested} found"
    )
    print(
        f"  ArXiv lookup: {s2_result.papers_found_by_arxiv}/{s2_result.total_papers_tested} found"
    )
    print(
        f"  Avg response times: Title={s2_result.avg_title_search_time:.3f}s, DOI={s2_result.avg_doi_search_time:.3f}s, ArXiv={s2_result.avg_arxiv_search_time:.3f}s\n"
    )

    # Test OpenAlex
    print("Testing OpenAlex API...")
    oa_api = OpenAlexAPI()
    oa_result = test_api(oa_api, "OpenAlex")
    results.append(oa_result)
    print(
        f"  Title search: {oa_result.papers_found_by_title}/{oa_result.total_papers_tested} found"
    )
    print(
        f"  DOI lookup: {oa_result.papers_found_by_doi}/{oa_result.total_papers_tested} found"
    )
    print(
        f"  Avg response times: Title={oa_result.avg_title_search_time:.3f}s, DOI={oa_result.avg_doi_search_time:.3f}s\n"
    )

    # Test Crossref
    print("Testing Crossref API...")
    cr_api = CrossrefAPI()
    cr_result = test_api(cr_api, "Crossref")
    results.append(cr_result)
    print(
        f"  Title search: {cr_result.papers_found_by_title}/{cr_result.total_papers_tested} found"
    )
    print(
        f"  DOI lookup: {cr_result.papers_found_by_doi}/{cr_result.total_papers_tested} found"
    )
    print(
        f"  Avg response times: Title={cr_result.avg_title_search_time:.3f}s, DOI={cr_result.avg_doi_search_time:.3f}s\n"
    )

    # Summary table
    print("\n=== COVERAGE SUMMARY ===")
    print(
        f"{'Source':<20} {'Title':<10} {'DOI':<10} {'ArXiv':<10} {'Abstract':<10} {'Citations':<10} {'Venue':<10} {'Affiliations':<15}"
    )
    print("-" * 105)

    for r in results:
        print(
            f"{r.source_name:<20} "
            f"{r.papers_found_by_title}/{r.total_papers_tested:<9} "
            f"{r.papers_found_by_doi}/{r.total_papers_tested:<9} "
            f"{r.papers_found_by_arxiv}/{r.total_papers_tested:<9} "
            f"{r.has_abstracts}/{r.total_papers_tested:<9} "
            f"{r.has_citations}/{r.total_papers_tested:<9} "
            f"{r.has_venues}/{r.total_papers_tested:<9} "
            f"{r.has_affiliations}/{r.total_papers_tested:<14}"
        )

    print("\n=== API SPEED SUMMARY (seconds) ===")
    print(
        f"{'Source':<20} {'Title Search':<15} {'DOI Lookup':<15} {'ArXiv Lookup':<15}"
    )
    print("-" * 65)

    for r in results:
        arxiv_str = (
            f"{r.avg_arxiv_search_time:.3f}" if r.avg_arxiv_search_time > 0 else "N/A"
        )
        print(
            f"{r.source_name:<20} {r.avg_title_search_time:<15.3f} {r.avg_doi_search_time:<15.3f} {arxiv_str:<15}"
        )

    print("\n=== FIELD COVERAGE ===")
    for r in results:
        if r.fields_of_study:
            print(f"\n{r.source_name} covers these fields:")
            for field in r.fields_of_study[:10]:  # Top 10
                if field:  # Skip empty strings
                    print(f"  - {field}")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"api_comparison_{timestamp}.json"

    results_dict = {
        "test_date": datetime.now().isoformat(),
        "papers_tested": TEST_PAPERS,
        "results": [asdict(r) for r in results],
    }

    with open(filename, "w") as f:
        json.dump(results_dict, f, indent=2)

    print(f"\nDetailed results saved to {filename}")

    # Note about Zeta Alpha
    print("\n=== ZETA ALPHA ===")
    print(
        "Zeta Alpha is a commercial service focused on AI/ML literature search and discovery."
    )
    print("Key features:")
    print("  - Specialized in AI/ML papers with semantic search capabilities")
    print("  - Provides paper recommendations and citation analysis")
    print("  - Requires paid API access (no free tier)")
    print(
        "  - Not suitable for bulk metadata collection due to commercial restrictions"
    )
    print(
        "  - Better suited as a discovery/search tool rather than a consolidation source"
    )


if __name__ == "__main__":
    main()
