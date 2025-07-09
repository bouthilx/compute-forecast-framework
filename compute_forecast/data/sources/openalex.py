import requests
from datetime import datetime
from typing import Dict, Any
from .base import BaseCitationSource
from ..models import Paper, Author, CollectionQuery, CollectionResult
from ...core.config import ConfigManager
from ...core.logging import setup_logging


class OpenAlexSource(BaseCitationSource):
    """OpenAlex API citation source implementation"""

    def __init__(self):
        config_manager = ConfigManager()
        config = config_manager.get_citation_config("openalex")
        super().__init__(config.__dict__)
        self.base_url = "https://api.openalex.org"
        self.logger = setup_logging()

    def search_papers(self, query: CollectionQuery) -> CollectionResult:
        """Search OpenAlex for papers matching query"""

        papers = []
        errors = []

        try:
            # Validate query parameters
            if not query.domain:
                raise ValueError("Domain is required for search")
            if query.year < 1950 or query.year > datetime.now().year:
                raise ValueError(f"Invalid year: {query.year}")

            search_url = f"{self.base_url}/works"
            params = self._build_search_params(query)
            self.logger.info(f"OpenAlex search params: {params}")

            response = requests.get(
                search_url, params=params, timeout=self.config.get("timeout", 30)
            )

            if response.status_code == 200:
                data = response.json()
                total_works = data.get("meta", {}).get("count", 0)
                self.logger.info(f"OpenAlex found {total_works} total works")

                for work in data.get("results", []):
                    try:
                        paper = self._parse_openalex_result(work, query)
                        if paper and paper.citations >= query.min_citations:
                            papers.append(paper)
                    except Exception as e:
                        errors.append(f"Failed to parse work: {e}")
                        self.logger.warning(f"Parse error: {e}")
            else:
                errors.append(
                    f"API request failed: {response.status_code} - {response.text[:200]}"
                )
                self.logger.error(
                    f"OpenAlex API error {response.status_code}: {response.text[:200]}"
                )

        except ValueError as e:
            errors.append(f"Invalid query parameters: {e}")
            self.logger.error(f"Query validation failed: {e}")
        except Exception as e:
            errors.append(f"Search failed: {e}")
            self.logger.error(f"OpenAlex search failed: {e}")

        return CollectionResult(
            papers=papers,
            query=query,
            source="openalex",
            collection_timestamp=datetime.now().isoformat(),
            success_count=len(papers),
            failed_count=len(errors),
            errors=errors,
        )

    def _build_search_params(self, query: CollectionQuery) -> dict:
        """Build OpenAlex API parameters"""
        filters = []
        search_terms = []

        # Use search parameter for venue (filter doesn't support venue filtering)
        if query.venue:
            search_terms.append(query.venue)

        if query.year:
            filters.append(f"publication_year:{query.year}")

        if query.keywords:
            # Add keywords to search terms
            search_terms.extend(query.keywords[:2])  # Limit keywords

        params = {
            "per-page": min(query.max_results, 200),
            "select": "id,title,display_name,publication_year,cited_by_count,doi,authorships,locations",
        }

        if filters:
            params["filter"] = ",".join(filters)

        if search_terms:
            params["search"] = " ".join(search_terms)

        return params

    def _parse_openalex_result(self, work: dict, query: CollectionQuery) -> Paper:
        """Parse OpenAlex work into Paper object"""

        if not work:
            raise ValueError("Empty work provided")

        title = work.get("display_name", "").strip()
        if not title:
            raise ValueError("Work title is required")

        # Parse authors from authorships with validation
        authors = []
        authorships = work.get("authorships", [])
        if isinstance(authorships, list):
            for authorship in authorships:
                if isinstance(authorship, dict):
                    author_info = authorship.get("author", {})
                    if isinstance(author_info, dict):
                        author_name = author_info.get("display_name", "").strip()
                        if author_name:  # Only add authors with names
                            institutions = authorship.get("institutions", [])
                            affiliation = ""
                            if (
                                institutions
                                and isinstance(institutions, list)
                                and institutions[0]
                            ):
                                affiliation = (
                                    institutions[0].get("display_name", "").strip()
                                )

                            author = Author(
                                name=author_name,
                                affiliation=affiliation,
                                author_id=author_info.get("id", "").strip(),
                            )
                            authors.append(author)

        # Validate numeric fields
        citations = work.get("cited_by_count", 0)
        if not isinstance(citations, int) or citations < 0:
            citations = 0

        year = work.get("publication_year", query.year)
        if not isinstance(year, int) or year < 1950 or year > datetime.now().year:
            year = query.year

        # Extract venue from locations (replaces deprecated host_venue)
        venue = ""
        locations = work.get("locations", [])
        if locations and isinstance(locations, list):
            for location in locations:
                source = location.get("source", {})
                if source and isinstance(source, dict):
                    venue_name = source.get("display_name", "").strip()
                    if venue_name:
                        venue = venue_name
                        break

        # Fallback to query venue if no venue found in locations
        if not venue:
            venue = query.venue or ""

        # Create paper object
        paper = Paper(
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            citations=citations,
            abstract="",  # Abstract not available in basic API response
            doi=work.get("doi", "").strip(),
            urls=[str(work.get("id"))] if work.get("id") else [],
            source="openalex",
            collection_timestamp=datetime.now(),
            mila_domain=query.domain,
        )

        return paper

    def get_paper_details(self, work_id: str) -> Paper:
        """Get detailed work information by OpenAlex ID"""
        try:
            # Ensure work_id is a full OpenAlex URL
            if not work_id.startswith("https://openalex.org/"):
                work_id = (
                    f"https://openalex.org/W{work_id}"
                    if not work_id.startswith("W")
                    else f"https://openalex.org/{work_id}"
                )

            # Get detailed work info from OpenAlex API
            work_url = f"{self.base_url}/works/{work_id}"
            params = {
                "select": "id,title,display_name,publication_year,cited_by_count,doi,authorships"
            }

            response = requests.get(
                work_url, params=params, timeout=self.config.get("timeout", 30)
            )

            if response.status_code != 200:
                raise ValueError(
                    f"Work {work_id} not found or API error: {response.status_code}"
                )

            work_data = response.json()

            # Parse authors from detailed authorships
            authors = []
            for authorship in work_data.get("authorships", []):
                author_info = authorship.get("author", {})
                institutions = authorship.get("institutions", [])
                affiliation = (
                    institutions[0].get("display_name", "") if institutions else ""
                )

                author = Author(
                    name=author_info.get("display_name", ""),
                    affiliation=affiliation,
                    author_id=author_info.get("id", ""),
                )
                authors.append(author)

            # Venue info not available in basic select, use empty string
            venue_name = ""

            # Create detailed paper object
            paper = Paper(
                title=work_data.get("display_name", ""),
                authors=authors,
                venue=venue_name,
                year=work_data.get("publication_year", 0),
                citations=work_data.get("cited_by_count", 0),
                abstract="",  # Abstract not available in basic API response
                doi=work_data.get("doi", ""),
                urls=[str(work_data.get("id"))] if work_data.get("id") else [],
                source="openalex",
                collection_timestamp=datetime.now(),
            )

            return paper

        except Exception as e:
            self.logger.error(f"Failed to get work details for {work_id}: {e}")
            raise

    def test_connectivity(self) -> bool:
        """Test OpenAlex API connectivity"""
        try:
            test_url = f"{self.base_url}/works"
            params: Dict[str, Any] = {
                "filter": "title.search:machine learning",
                "per-page": 1,
            }
            response = requests.get(test_url, params=params, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"OpenAlex connectivity test failed: {e}")
            return False
            return False
