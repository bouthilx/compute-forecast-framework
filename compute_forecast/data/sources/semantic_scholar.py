import requests
import time
import random
import os
from datetime import datetime
from .base import BaseCitationSource
from ..models import Paper, Author, CollectionQuery, CollectionResult
from ...core.config import ConfigManager
from ...core.logging import setup_logging


class SemanticScholarSource(BaseCitationSource):
    """Semantic Scholar API citation source implementation"""

    def __init__(self):
        config_manager = ConfigManager()
        config = config_manager.get_citation_config("semantic_scholar")
        super().__init__(config.__dict__)
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.logger = setup_logging()

        # Enhanced rate limiting configuration
        self.base_delay = 2.0  # Minimum 2 seconds between requests
        self.max_delay = 60.0  # Maximum delay for exponential backoff
        self.max_retries = 5  # Maximum retry attempts
        self.last_request_time = 0

        # API key support for higher rate limits
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        if self.api_key:
            self.logger.info("Using Semantic Scholar API key for enhanced rate limits")
        else:
            self.logger.warning("No API key found - using public rate limits (slower)")

    def search_papers(self, query: CollectionQuery) -> CollectionResult:
        """Search Semantic Scholar for papers matching query"""

        papers = []
        errors = []

        try:
            # Validate query parameters
            if not query.domain:
                raise ValueError("Domain is required for search")
            if query.year < 1950 or query.year > datetime.now().year:
                raise ValueError(f"Invalid year: {query.year}")

            search_url = f"{self.base_url}/paper/search"
            params = self._build_search_params(query)
            self.logger.info(f"Semantic Scholar search params: {params}")

            # Make request with aggressive rate limiting and retry logic
            response = self._make_rate_limited_request(search_url, params)

            if response.status_code == 200:
                data = response.json()
                total_papers = data.get("total", 0)
                self.logger.info(f"Semantic Scholar found {total_papers} total papers")

                # If venue search returns 0 results, try fallback strategy
                if total_papers == 0 and query.venue:
                    self.logger.info(
                        "Venue search returned 0 results, trying fallback strategy"
                    )
                    fallback_params = self._build_fallback_search_params(query)
                    self.logger.info(f"Fallback search params: {fallback_params}")

                    response = self._make_rate_limited_request(
                        search_url, fallback_params
                    )
                    if response.status_code == 200:
                        data = response.json()
                        total_papers = data.get("total", 0)
                        self.logger.info(
                            f"Fallback search found {total_papers} total papers"
                        )

                for paper_data in data.get("data", []):
                    try:
                        paper = self._parse_semantic_result(paper_data, query)
                        # Use dynamic citation threshold for recent papers
                        effective_threshold = self._get_dynamic_citation_threshold(
                            query.year, query.min_citations
                        )
                        if paper and paper.citations >= effective_threshold:
                            papers.append(paper)
                    except Exception as e:
                        errors.append(f"Failed to parse paper: {e}")
                        self.logger.warning(f"Parse error: {e}")
            elif response.status_code == 429:
                errors.append("Rate limited by Semantic Scholar API")
                self.logger.warning("Semantic Scholar rate limit hit")
            else:
                errors.append(
                    f"API request failed: {response.status_code} - {response.text[:200]}"
                )
                self.logger.error(
                    f"API error {response.status_code}: {response.text[:200]}"
                )

        except ValueError as e:
            errors.append(f"Invalid query parameters: {e}")
            self.logger.error(f"Query validation failed: {e}")
        except Exception as e:
            errors.append(f"Search failed: {e}")
            self.logger.error(f"Semantic Scholar search failed: {e}")

        return CollectionResult(
            papers=papers,
            query=query,
            source="semantic_scholar",
            collection_timestamp=datetime.now().isoformat(),
            success_count=len(papers),
            failed_count=len(errors),
            errors=errors,
        )

    def _build_search_params(self, query: CollectionQuery) -> dict:
        """Build Semantic Scholar API parameters with improved venue handling"""
        params = {
            "limit": min(query.max_results, 100),
            "fields": "title,authors,venue,year,citationCount,abstract,url,paperId",
        }

        # Build query string with improved venue handling
        query_parts = []

        if query.venue:
            venue_name = query.venue.lower()

            # Map venue names to actual Semantic Scholar venue strings
            venue_mapping = {
                "neurips": "Neural Information Processing Systems",
                "nips": "Neural Information Processing Systems",
                "icml": "International Conference on Machine Learning",
                "iclr": "International Conference on Learning Representations",
                "aaai": "AAAI Conference on Artificial Intelligence",
                "ijcai": "International Joint Conference on Artificial Intelligence",
                "cvpr": "IEEE Conference on Computer Vision and Pattern Recognition",
                "iccv": "IEEE International Conference on Computer Vision",
                "eccv": "European Conference on Computer Vision",
                "acl": "Annual Meeting of the Association for Computational Linguistics",
                "emnlp": "Conference on Empirical Methods in Natural Language Processing",
            }

            # Use mapped venue name if available
            search_venue = venue_mapping.get(venue_name, query.venue)

            # Use simpler venue search - complex OR queries seem to fail
            # Try venue field first, fall back to general search if needed
            query_parts.append(f'venue:"{search_venue}"')

        if query.keywords:
            keyword_str = " ".join(query.keywords[:3])
            query_parts.append(keyword_str)

        query_parts.append(f"year:{query.year}")

        params["query"] = " ".join(query_parts)

        return params

    def _build_fallback_search_params(self, query: CollectionQuery) -> dict:
        """Build fallback search parameters when venue search fails"""
        params = {
            "limit": min(query.max_results, 100),
            "fields": "title,authors,venue,year,citationCount,abstract,url,paperId",
        }

        # Strategy: Use general search with venue keywords instead of venue field
        query_parts = []

        if query.venue:
            venue_name = query.venue.lower()

            # Add venue as general search term instead of venue field
            if venue_name in ["neurips", "nips"]:
                query_parts.append(
                    '("NeurIPS" OR "Neural Information Processing Systems")'
                )
            elif venue_name == "icml":
                query_parts.append(
                    '("ICML" OR "International Conference on Machine Learning")'
                )
            elif venue_name == "iclr":
                query_parts.append(
                    '("ICLR" OR "International Conference on Learning Representations")'
                )
            else:
                # For other venues, just add the venue name as a search term
                query_parts.append(f'"{query.venue}"')

        # Add keywords
        if query.keywords:
            keyword_str = " ".join(query.keywords[:3])
            query_parts.append(keyword_str)

        # Add year filter
        query_parts.append(f"year:{query.year}")

        params["query"] = " ".join(query_parts)

        return params

    def _make_rate_limited_request(self, url: str, params: dict) -> requests.Response:
        """Make API request with aggressive rate limiting and exponential backoff"""

        for attempt in range(self.max_retries):
            # Implement aggressive rate limiting
            self._wait_for_rate_limit()

            # Prepare headers with API key if available
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            try:
                self.logger.debug(
                    f"Making request (attempt {attempt + 1}/{self.max_retries})"
                )
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.config.get("timeout", 30),
                )

                # Handle different response codes
                if response.status_code == 200:
                    self.logger.debug("Request successful")
                    return response
                elif response.status_code == 429:
                    # Rate limited - implement exponential backoff
                    retry_delay = self._calculate_backoff_delay(attempt)
                    self.logger.warning(
                        f"Rate limited (429). Retrying in {retry_delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    # Other error - log and return for handling
                    self.logger.error(
                        f"API error {response.status_code}: {response.text[:200]}"
                    )
                    return response

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    # Re-raise on final attempt
                    raise
                # Wait before retry
                time.sleep(self._calculate_backoff_delay(attempt))

        # If we get here, all retries failed
        raise requests.exceptions.RequestException(
            f"All {self.max_retries} retry attempts failed"
        )

    def _wait_for_rate_limit(self):
        """Ensure minimum delay between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.base_delay:
            sleep_time = self.base_delay - time_since_last
            # Add small random jitter to avoid synchronization issues
            jitter = random.uniform(0, 0.5)
            total_sleep = sleep_time + jitter

            self.logger.debug(f"Rate limiting: sleeping {total_sleep:.1f}s")
            time.sleep(total_sleep)

        self.last_request_time = time.time()

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        # Exponential backoff: 2^attempt * base_delay, capped at max_delay
        delay = min(self.base_delay * (2**attempt), self.max_delay)

        # Add random jitter (±25%)
        jitter_range = delay * 0.25
        jitter = random.uniform(-jitter_range, jitter_range)

        return float(max(delay + jitter, 1.0))  # Minimum 1 second

    def _get_dynamic_citation_threshold(
        self, paper_year: int, base_threshold: int
    ) -> int:
        """Calculate dynamic citation threshold based on paper age"""
        current_year = datetime.now().year
        years_old = current_year - paper_year

        # Adjust thresholds for recent papers
        if years_old <= 1:  # 2024+ papers
            return 0
        elif years_old <= 2:  # 2023 papers
            return max(base_threshold // 3, 1)
        elif years_old <= 3:  # 2022 papers
            return max(base_threshold // 2, 2)
        else:  # Older papers
            return base_threshold

    def _parse_semantic_result(self, result: dict, query: CollectionQuery) -> Paper:
        """Parse Semantic Scholar result into Paper object"""

        if not result:
            raise ValueError("Empty result provided")

        title = result.get("title", "") or ""
        title = title.strip() if title else ""
        if not title:
            raise ValueError("Paper title is required")

        # Parse authors with validation
        authors = []
        author_list = result.get("authors", [])
        if isinstance(author_list, list):
            for author_data in author_list:
                if isinstance(author_data, dict):
                    author_name = author_data.get("name", "").strip()
                    if author_name:  # Only add authors with names
                        author = Author(
                            name=author_name,
                            affiliation="",  # Semantic Scholar doesn't always provide this
                            author_id=author_data.get("authorId", "").strip(),
                        )
                        authors.append(author)

        # Validate numeric fields
        citations = result.get("citationCount", 0)
        if not isinstance(citations, int) or citations < 0:
            citations = 0

        year = result.get("year", query.year)
        if not isinstance(year, int) or year < 1950 or year > datetime.now().year:
            year = query.year

        # Create paper object
        paper = Paper(
            title=title,
            authors=authors,
            venue=result.get("venue", query.venue or ""),
            year=year,
            citations=citations,
            abstract=(result.get("abstract") or "").strip(),
            urls=[str(result.get("url"))] if result.get("url") else [],
            source="semantic_scholar",
            collection_timestamp=datetime.now(),
            mila_domain=query.domain,
        )

        return paper

    def get_paper_details(self, paper_id: str) -> Paper:
        """Get detailed paper information by Semantic Scholar ID"""
        try:
            # Get detailed paper info from Semantic Scholar API
            paper_url = f"{self.base_url}/paper/{paper_id}"
            params = {
                "fields": "title,authors,venue,year,citationCount,abstract,url,doi,references,citations"
            }

            response = self._make_rate_limited_request(paper_url, params)

            if response.status_code != 200:
                raise ValueError(
                    f"Paper {paper_id} not found or API error: {response.status_code}"
                )

            paper_data = response.json()

            # Parse authors with detailed info
            authors = []
            for author_data in paper_data.get("authors", []):
                author = Author(
                    name=author_data.get("name", ""),
                    affiliation="",  # Semantic Scholar doesn't always provide this in basic calls
                    author_id=author_data.get("authorId", ""),
                )
                authors.append(author)

            # Create detailed paper object
            paper = Paper(
                title=paper_data.get("title", ""),
                authors=authors,
                venue=paper_data.get("venue", ""),
                year=paper_data.get("year", 0),
                citations=paper_data.get("citationCount", 0),
                abstract=paper_data.get("abstract", ""),
                doi=paper_data.get("doi", ""),
                urls=[str(paper_data.get("url"))] if paper_data.get("url") else [],
                source="semantic_scholar",
                collection_timestamp=datetime.now(),
            )

            return paper

        except Exception as e:
            self.logger.error(f"Failed to get paper details for {paper_id}: {e}")
            raise

    def test_connectivity(self) -> bool:
        """Test Semantic Scholar API connectivity"""
        try:
            test_url = f"{self.base_url}/paper/search"
            params = {"query": "machine learning", "limit": 1}

            # Use rate limited request method
            response = self._make_rate_limited_request(test_url, params)

            # Accept 200 or 429 (rate limited) as "working"
            if response.status_code in [200, 429]:
                return True
            return False
        except Exception as e:
            self.logger.error(f"Semantic Scholar connectivity test failed: {e}")
            return False
