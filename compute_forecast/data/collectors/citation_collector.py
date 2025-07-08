from typing import List, Dict
from datetime import datetime
from ..sources.google_scholar import GoogleScholarSource
from ..sources.semantic_scholar import SemanticScholarSource
from ..sources.openalex import OpenAlexSource
from ..models import Paper, CollectionQuery, CollectionResult
from ...core.logging import setup_logging


class CitationCollector:
    """Unified collector that manages all citation sources"""

    def __init__(self):
        self.sources = {
            "google_scholar": GoogleScholarSource(),
            "semantic_scholar": SemanticScholarSource(),
            "openalex": OpenAlexSource(),
        }
        self.logger = setup_logging()

    def collect_from_all_sources(
        self, query: CollectionQuery
    ) -> Dict[str, CollectionResult]:
        """Collect papers from all available citation sources"""

        # Validate query
        if not query or not query.domain:
            raise ValueError("Valid query with domain is required")

        results = {}
        total_papers_collected = 0

        self.logger.info(
            f"Starting collection for domain '{query.domain}', year {query.year}, max_results={query.max_results}"
        )

        for source_name, source in self.sources.items():
            try:
                self.logger.info(
                    f"Collecting from {source_name} for {query.domain} {query.year}"
                )
                start_time = datetime.now()

                result = source.search_papers(query)
                results[source_name] = result

                collection_time = (datetime.now() - start_time).total_seconds()
                total_papers_collected += result.success_count

                self.logger.info(
                    f"Collected {result.success_count} papers from {source_name} "
                    f"in {collection_time:.2f}s (errors: {result.failed_count})"
                )

                if result.errors:
                    self.logger.warning(
                        f"{source_name} errors: {result.errors[:3]}"
                    )  # Log first 3 errors

            except Exception as e:
                self.logger.error(f"Failed to collect from {source_name}: {e}")
                results[source_name] = CollectionResult(
                    papers=[],
                    query=query,
                    source=source_name,
                    collection_timestamp=datetime.now().isoformat(),
                    success_count=0,
                    failed_count=1,
                    errors=[str(e)],
                )

        self.logger.info(
            f"Collection complete. Total papers: {total_papers_collected} from {len(results)} sources"
        )
        return results

    def test_all_sources(self) -> Dict[str, bool]:
        """Test connectivity for all citation sources"""

        connectivity = {}

        for source_name, source in self.sources.items():
            try:
                connectivity[source_name] = source.test_connectivity()
                status = "OK" if connectivity[source_name] else "FAILED"
                self.logger.info(f"{source_name} connectivity: {status}")
            except Exception as e:
                connectivity[source_name] = False
                self.logger.error(f"{source_name} connectivity test failed: {e}")

        return connectivity

    def get_combined_papers(self, results: Dict[str, CollectionResult]) -> List[Paper]:
        """Combine papers from all sources (before deduplication)"""

        if not results:
            return []

        all_papers = []
        source_counts = {}

        for source_name, result in results.items():
            if result and result.papers:
                all_papers.extend(result.papers)
                source_counts[source_name] = len(result.papers)
            else:
                source_counts[source_name] = 0

        self.logger.info(
            f"Combined papers by source: {source_counts} (total: {len(all_papers)})"
        )
        return all_papers

    def get_paper_by_id(self, paper_id: str, source: str) -> Paper:
        """Get detailed paper information by ID from specific source"""

        if source not in self.sources:
            raise ValueError(f"Unknown source: {source}")

        if not paper_id:
            raise ValueError("Paper ID is required")

        try:
            self.logger.info(f"Getting paper details for {paper_id} from {source}")
            paper = self.sources[source].get_paper_details(paper_id)
            self.logger.info(f"Successfully retrieved paper: {paper.title[:50]}...")
            return paper
        except Exception as e:
            self.logger.error(f"Failed to get paper {paper_id} from {source}: {e}")
            raise

    def collect_from_venue_year(
        self,
        venue: str,
        year: int,
        citation_threshold: int = 0,
        working_apis: List[str] = None,
    ) -> List[Dict]:
        """Collect papers from specific venue and year"""
        papers = []

        # Use only working APIs if specified
        sources_to_try = self.sources
        if working_apis:
            sources_to_try = {
                name: source
                for name, source in self.sources.items()
                if name in working_apis
            }
            self.logger.info(f"Using only working APIs: {list(sources_to_try.keys())}")

        # Try each available source
        for source_name, source in sources_to_try.items():
            try:
                self.logger.info(f"Searching {source_name} for {venue} {year}")

                # Create basic query
                query = CollectionQuery(
                    domain=venue, year=year, keywords=[venue], max_results=20
                )

                result = source.search_papers(query)
                if result and result.papers:
                    # Filter by citation threshold and venue
                    venue_papers = []
                    for paper in result.papers:
                        citations = getattr(paper, "citations", 0) or 0
                        paper_venue = getattr(paper, "venue", "") or ""
                        paper_year = getattr(paper, "year", 0) or 0

                        # Simple venue matching and citation filtering
                        if (
                            citations >= citation_threshold
                            and paper_year == year
                            and (
                                venue.lower() in paper_venue.lower()
                                if paper_venue
                                else False
                            )
                        ):
                            # Convert Paper object to dict
                            paper_dict = {
                                "title": getattr(paper, "title", ""),
                                "authors": getattr(paper, "authors", []),
                                "year": paper_year,
                                "venue": paper_venue,
                                "citations": citations,
                                "abstract": getattr(paper, "abstract", ""),
                                "source": source_name,
                                "paper_id": getattr(paper, "paper_id", ""),
                            }
                            venue_papers.append(paper_dict)

                    papers.extend(venue_papers)
                    self.logger.info(
                        f"Found {len(venue_papers)} papers from {source_name}"
                    )

            except Exception as e:
                self.logger.warning(f"Failed to search {source_name} for {venue}: {e}")
                continue

        return papers

    def collect_from_venue_year_with_keywords(
        self,
        venue: str,
        year: int,
        keywords: List[str],
        domain: str,
        working_apis: List[str] = None,
    ) -> List[Dict]:
        """Collect papers from venue/year combination with domain keywords"""
        papers = []

        # Use only working APIs if specified
        sources_to_try = self.sources
        if working_apis:
            sources_to_try = {
                name: source
                for name, source in self.sources.items()
                if name in working_apis
            }

        # Combine venue, year, and keywords in search
        all_keywords = [venue] + keywords[
            :3
        ]  # Limit keywords to avoid too complex queries

        for source_name, source in sources_to_try.items():
            try:
                self.logger.info(
                    f"Searching {source_name} for {venue} {year} with keywords: {keywords[:3]}"
                )

                query = CollectionQuery(
                    domain=domain, year=year, keywords=all_keywords, max_results=15
                )

                result = source.search_papers(query)
                if result and result.papers:
                    # Filter and convert papers
                    filtered_papers = []
                    for paper in result.papers:
                        paper_year = getattr(paper, "year", 0) or 0
                        paper_venue = getattr(paper, "venue", "") or ""

                        # Check if paper matches venue and year
                        if paper_year == year and (
                            venue.lower() in paper_venue.lower()
                            if paper_venue
                            else True
                        ):
                            paper_dict = {
                                "title": getattr(paper, "title", ""),
                                "authors": getattr(paper, "authors", []),
                                "year": paper_year,
                                "venue": paper_venue,
                                "citations": getattr(paper, "citations", 0) or 0,
                                "abstract": getattr(paper, "abstract", ""),
                                "source": source_name,
                                "paper_id": getattr(paper, "paper_id", ""),
                                "domain": domain,
                            }
                            filtered_papers.append(paper_dict)

                    papers.extend(filtered_papers)
                    self.logger.info(
                        f"Found {len(filtered_papers)} papers from {source_name}"
                    )

            except Exception as e:
                self.logger.warning(
                    f"Failed to search {source_name} for {venue} with keywords: {e}"
                )
                continue

        return papers

    def collect_from_keywords(
        self,
        keywords: List[str],
        year: int,
        domain: str,
        working_apis: List[str] = None,
    ) -> List[Dict]:
        """Collect papers using direct keyword search"""
        papers = []

        # Use only working APIs if specified
        sources_to_try = self.sources
        if working_apis:
            sources_to_try = {
                name: source
                for name, source in self.sources.items()
                if name in working_apis
            }

        # Limit to top keywords to avoid overly complex queries
        search_keywords = keywords[:5]

        for source_name, source in sources_to_try.items():
            try:
                self.logger.info(
                    f"Searching {source_name} with keywords: {search_keywords}"
                )

                query = CollectionQuery(
                    domain=domain, year=year, keywords=search_keywords, max_results=10
                )

                result = source.search_papers(query)
                if result and result.papers:
                    # Convert and filter papers
                    domain_papers = []
                    for paper in result.papers:
                        paper_year = getattr(paper, "year", 0) or 0

                        # Basic year filtering
                        if paper_year == year:
                            paper_dict = {
                                "title": getattr(paper, "title", ""),
                                "authors": getattr(paper, "authors", []),
                                "year": paper_year,
                                "venue": getattr(paper, "venue", ""),
                                "citations": getattr(paper, "citations", 0) or 0,
                                "abstract": getattr(paper, "abstract", ""),
                                "source": source_name,
                                "paper_id": getattr(paper, "paper_id", ""),
                                "domain": domain,
                            }
                            domain_papers.append(paper_dict)

                    papers.extend(domain_papers)
                    self.logger.info(
                        f"Found {len(domain_papers)} papers from {source_name}"
                    )

            except Exception as e:
                self.logger.warning(f"Failed keyword search on {source_name}: {e}")
                continue

        return papers
