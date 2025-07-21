import requests
import time
from typing import List, Dict, Optional, Any

from .base import BaseConsolidationSource, SourceConfig
from ...metadata_collection.models import Paper
from ....utils.profiling import profile_operation


class SemanticScholarSource(BaseConsolidationSource):
    """Semantic Scholar consolidation source with efficient batch processing"""

    def __init__(self, config: Optional[SourceConfig] = None):
        if config is None:
            config = SourceConfig()

        # Set optimal batch sizes for Semantic Scholar
        if config.find_batch_size is None:
            config.find_batch_size = 500  # API supports up to 500
        if config.enrich_batch_size is None:
            config.enrich_batch_size = 500  # API supports up to 500

        # Override rate limit based on API key presence
        if config.api_key:
            # With API key: introductory rate limit
            config.rate_limit = 1.0  # 1 request per second
        else:
            # Without API key: be conservative with shared pool
            # Unauthenticated users share 5,000 requests/5 minutes
            # Be very conservative to avoid 429 errors
            config.rate_limit = 0.1  # 1 request per 10 seconds

        super().__init__("semantic_scholar", config)
        self.base_url = "https://api.semanticscholar.org/v1"
        self.graph_url = "https://api.semanticscholar.org/graph/v1"

        self.headers = {}
        if self.config.api_key:
            self.headers["x-api-key"] = self.config.api_key

    def find_papers(self, papers: List[Paper]) -> Dict[str, str]:
        """Find papers using multiple identifiers with efficient batch processing"""
        mapping = {}

        # Try to match by existing Semantic Scholar ID
        for paper in papers:
            if paper.paper_id and paper.paper_id.startswith("SS:"):
                mapping[paper.paper_id] = paper.paper_id[3:]
                continue

        # First attempt: Batch lookup by DOI and ArXiv ID
        id_batch = []
        id_to_paper = {}
        papers_needing_title_search = []

        for paper in papers:
            if paper.paper_id in mapping:
                continue

            # Collect all available IDs (Semantic Scholar can match any)
            has_external_id = False
            if paper.doi:
                id_batch.append(f"DOI:{paper.doi}")
                id_to_paper[f"DOI:{paper.doi}"] = paper.paper_id
                has_external_id = True
            if paper.arxiv_id:
                id_batch.append(f"ARXIV:{paper.arxiv_id}")
                id_to_paper[f"ARXIV:{paper.arxiv_id}"] = paper.paper_id
                has_external_id = True

            # If no external IDs, we'll need to search by title
            if not has_external_id:
                papers_needing_title_search.append(paper)

        if id_batch:
            self.logger.info(f"Batch lookup for {len(id_batch)} external IDs")
            # Use paper batch endpoint
            with profile_operation(
                "id_batch_lookup", source=self.name, count=len(id_batch)
            ) as prof:
                self._rate_limit()

                # Track API response time separately
                api_start = time.time()
                response = requests.post(
                    f"{self.graph_url}/paper/batch",
                    json={"ids": id_batch},  # Already formatted with prefixes
                    headers=self.headers,
                    params={"fields": "paperId,externalIds"},
                    timeout=30,  # Add timeout
                )
                api_time = time.time() - api_start
                self.api_calls += 1

                if prof:
                    prof.metadata["api_response_time"] = api_time
                    prof.metadata["status_code"] = response.status_code

                if response.status_code == 200:
                    matches_found = 0
                    with profile_operation("parse_id_response", source=self.name):
                        for item in response.json():
                            if item and "paperId" in item:
                                ext_ids = item.get("externalIds", {})

                                # Check DOI match
                                doi = ext_ids.get("DOI")
                                if doi:
                                    doi_key = f"DOI:{doi}"
                                    if doi_key in id_to_paper:
                                        paper_id = id_to_paper[doi_key]
                                        if paper_id is not None:
                                            mapping[paper_id] = item["paperId"]
                                            matches_found += 1

                                # Check ArXiv match
                                arxiv = ext_ids.get("ArXiv")
                                if arxiv:
                                    arxiv_key = f"ARXIV:{arxiv}"
                                    if arxiv_key in id_to_paper:
                                        paper_id = id_to_paper[arxiv_key]
                                        if paper_id is not None:
                                            mapping[paper_id] = item["paperId"]
                                            matches_found += 1

                    if prof:
                        prof.metadata["matches_found"] = matches_found
                        prof.metadata["match_rate"] = (
                            matches_found / len(id_batch) if id_batch else 0
                        )

                    self.logger.info(f"Found {matches_found} matches from external IDs")

        # Batch title search for remaining papers
        if papers_needing_title_search:
            self.logger.info(
                f"Batch title search for {len(papers_needing_title_search)} papers"
            )

            # Build a mapping of normalized titles to papers
            title_to_papers: Dict[str, List[Paper]] = {}
            for paper in papers_needing_title_search:
                # We'll use a simplified title for matching
                normalized_title = paper.title.lower().strip()
                if normalized_title not in title_to_papers:
                    title_to_papers[normalized_title] = []
                title_to_papers[normalized_title].append(paper)

            # Semantic Scholar doesn't have a bulk title search endpoint, but we can:
            # 1. Use the paper/search endpoint with a broad query and filter results
            # 2. Or batch multiple specific searches more efficiently

            # For now, we'll have to do individual searches but we'll log the issue
            self.logger.warning(
                f"Semantic Scholar API requires individual title searches for {len(papers_needing_title_search)} papers. "
                f"This will take approximately {len(papers_needing_title_search) * 10} seconds with rate limiting."
            )

            # Search by title for papers without external IDs
            with profile_operation(
                "title_searches",
                source=self.name,
                count=len(papers_needing_title_search),
            ):
                for i, paper in enumerate(papers_needing_title_search):
                    if paper.paper_id in mapping:
                        continue

                    # Log progress every 10 papers
                    if i > 0 and i % 10 == 0:
                        self.logger.info(
                            f"Title search progress: {i}/{len(papers_needing_title_search)}"
                        )

                    with profile_operation(
                        "title_search_single", source=self.name
                    ) as prof:
                        self._rate_limit()
                        query = f'"{paper.title}"'

                        # Track API response time
                        api_start = time.time()
                        response = requests.get(
                            f"{self.graph_url}/paper/search",
                            params={
                                "query": query,
                                "limit": "1",
                                "fields": "paperId,title,year",
                            },
                            headers=self.headers,
                            timeout=30,
                        )
                        api_time = time.time() - api_start
                        self.api_calls += 1

                        if prof:
                            prof.metadata["api_response_time"] = api_time
                            prof.metadata["status_code"] = response.status_code
                            prof.metadata["title_length"] = len(paper.title)

                        if response.status_code == 200:
                            data = response.json()
                            if data.get("data"):
                                result = data["data"][0]
                                # Verify it's the same paper (title similarity and year)
                                if (
                                    self._similar_title(paper.title, result["title"])
                                    and result.get("year") == paper.year
                                ):
                                    if paper.paper_id is not None:
                                        mapping[paper.paper_id] = result["paperId"]
                                    if prof:
                                        prof.metadata["match_found"] = True
                                else:
                                    if prof:
                                        prof.metadata["match_found"] = False
                            else:
                                if prof:
                                    prof.metadata["match_found"] = False

        self.logger.info(f"Total papers mapped: {len(mapping)}/{len(papers)}")
        return mapping

    def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch all available fields in a single API call per batch"""
        results = {}

        # All fields we want in one request (added corpusId)
        fields = "paperId,title,abstract,citationCount,year,authors,externalIds,corpusId,openAccessPdf,fieldsOfStudy,venue"

        # Process in chunks of 500 (API limit)
        for i in range(0, len(source_ids), 500):
            batch = source_ids[i : i + 500]

            with profile_operation(
                "fetch_batch", source=self.name, batch_size=len(batch)
            ) as prof:
                self._rate_limit()

                api_start = time.time()
                response = requests.post(
                    f"{self.graph_url}/paper/batch",
                    json={"ids": batch},
                    headers=self.headers,
                    params={"fields": fields},
                    timeout=30,
                )
                api_time = time.time() - api_start
                self.api_calls += 1

                if prof:
                    prof.metadata["api_response_time"] = api_time
                    prof.metadata["status_code"] = response.status_code

                if response.status_code == 200:
                    with profile_operation(
                        "parse_enrichment_response", source=self.name
                    ):
                        for item in response.json():
                            if item is None:
                                continue

                            paper_id = item.get("paperId")
                            if not paper_id:
                                continue

                            # Extract all data from single response
                            paper_data = {
                                "citations": item.get("citationCount"),
                                "abstract": item.get("abstract"),
                                "urls": [],
                                "identifiers": [],
                                "authors": item.get("authors", []),
                                "venue": item.get("venue"),
                                "fields_of_study": item.get("fieldsOfStudy", []),
                            }

                            # Add open access PDF URL if available
                            if item.get("openAccessPdf") and item["openAccessPdf"].get(
                                "url"
                            ):
                                paper_data["urls"].append(item["openAccessPdf"]["url"])

                            # Extract all identifiers
                            # Add Semantic Scholar IDs
                            if item.get("paperId"):
                                paper_data["identifiers"].append(
                                    {"type": "s2_paper", "value": item["paperId"]}
                                )

                            if item.get("corpusId"):
                                paper_data["identifiers"].append(
                                    {
                                        "type": "s2_corpus",
                                        "value": str(item["corpusId"]),
                                    }
                                )

                            # Extract external identifiers
                            ext_ids = item.get("externalIds", {})
                            id_mappings = {
                                "DOI": "doi",
                                "ArXiv": "arxiv",
                                "PubMed": "pmid",
                                "ACL": "acl",
                                "MAG": "mag",
                            }

                            for ext_type, our_type in id_mappings.items():
                                if ext_type in ext_ids:
                                    paper_data["identifiers"].append(
                                        {"type": our_type, "value": ext_ids[ext_type]}
                                    )

                            results[paper_id] = paper_data

        return results

    def _similar_title(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough"""
        # Simple normalization and comparison
        norm1 = title1.lower().strip()
        norm2 = title2.lower().strip()

        # Exact match after normalization
        if norm1 == norm2:
            return True

        # Check if one is substring of other (handling subtitles)
        if norm1 in norm2 or norm2 in norm1:
            return True

        # Could add more sophisticated matching here
        return False
