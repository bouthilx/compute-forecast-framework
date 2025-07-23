"""Scraper for PMLR (Proceedings of Machine Learning Research) venues"""

import re
from bs4 import BeautifulSoup
from typing import List, Optional, Iterator
from urllib.parse import urljoin

from ..base import ConferenceProceedingsScraper, ScrapingConfig, ScrapingResult
from ..models import SimplePaper
from ..error_handling import retry_on_error


class PMLRScraper(ConferenceProceedingsScraper):
    """Scraper for PMLR proceedings (ICML, AISTATS, UAI, CoLLAs)"""

    def __init__(self, config: Optional[ScrapingConfig] = None):
        super().__init__("pmlr", config or ScrapingConfig())
        self.base_url = "https://proceedings.mlr.press/"

        # Volume mappings for each venue/year
        # These need to be verified and extended
        self.venue_volumes = {
            "ICML": {
                2024: 235,  # To be verified
                2023: 202,
                2022: 162,
                2021: 139,
                2020: 119,
                2019: 97,
            },
            "AISTATS": {
                2024: 238,  # To be verified
                2023: 206,
                2022: 151,
                2021: 130,
                2020: 108,
                2019: 89,
            },
            "UAI": {
                2024: 244,  # To be verified
                2023: 216,
                2022: 180,
                2021: 161,
                2020: 124,
                2019: 115,
            },
            "COLLAS": {  # Conference on Lifelong Learning Agents
                2023: 232,  # 2nd Conference
                2022: 199,  # 1st Conference
            },
        }

    def get_supported_venues(self) -> List[str]:
        """Return supported PMLR venues"""
        venues = []
        for venue in self.venue_volumes.keys():
            venues.extend([venue, venue.lower()])
        # Add alternative names
        venues.extend(["CoLLAs", "collas"])
        return venues

    def get_available_years(self, venue: str) -> List[int]:
        """Get years available for venue"""
        venue_upper = self._normalize_venue(venue)
        if venue_upper in self.venue_volumes:
            return sorted(self.venue_volumes[venue_upper].keys(), reverse=True)
        return []

    def _normalize_venue(self, venue: str) -> str:
        """Normalize venue name to uppercase key"""
        venue_upper = venue.upper()

        # Handle special cases
        if venue_upper in ["COLLAS", "COLLA"]:
            return "COLLAS"

        # Direct mapping
        if venue_upper in self.venue_volumes:
            return venue_upper

        return venue_upper

    def get_proceedings_url(self, venue: str, year: int) -> str:
        """Construct PMLR proceedings URL"""
        venue_upper = self._normalize_venue(venue)

        if venue_upper not in self.venue_volumes:
            raise ValueError(f"Venue {venue} not supported")

        if year not in self.venue_volumes[venue_upper]:
            raise ValueError(f"Year {year} not available for venue {venue}")

        volume = self.venue_volumes[venue_upper][year]
        return urljoin(self.base_url, f"v{volume}/")

    def scrape_venue_year_iter(self, venue: str, year: int) -> Iterator[SimplePaper]:
        """
        Stream PMLR papers one by one as they are scraped.
        """
        venue_normalized = self._normalize_venue(venue)
        
        if venue_normalized not in self.venue_volumes:
            self.logger.error(f"Venue {venue} not supported")
            return
        
        if year not in self.venue_volumes[venue_normalized]:
            self.logger.error(f"Year {year} not available for venue {venue}")
            return
        
        try:
            url = self.get_proceedings_url(venue, year)
            self.logger.info(f"Fetching PMLR proceedings from: {url}")
            
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # PMLR uses <div class="paper"> for each paper entry
            paper_entries = soup.find_all("div", class_="paper")
            
            if not paper_entries:
                # Try alternative structure
                paper_entries = soup.find_all("p", class_="title")
            
            self.logger.info(f"Found {len(paper_entries)} paper entries for {venue} {year}")
            
            for i, entry in enumerate(paper_entries):
                try:
                    paper = self._extract_paper_from_entry(entry, venue_normalized, year, i)
                    if paper:
                        yield paper
                        
                        # Log progress every 50 papers
                        if (i + 1) % 50 == 0:
                            self.logger.info(f"Processed {i + 1}/{len(paper_entries)} papers")
                            
                except Exception as e:
                    self.logger.warning(f"Failed to extract paper from entry {i}: {e}")
                    continue
            
            self.logger.info(f"Finished streaming papers from {venue} {year}")
            
        except Exception as e:
            error_msg = f"Failed to scrape {venue} {year}: {str(e)}"
            self.logger.error(error_msg)
            raise

    @retry_on_error(max_retries=3, delay=1.0)
    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Scrape PMLR papers for venue/year"""
        venue_normalized = self._normalize_venue(venue)

        if venue_normalized not in self.venue_volumes:
            return ScrapingResult.failure_result(
                errors=[f"Venue {venue} not supported"],
                metadata={"venue": venue, "year": year},
            )

        if year not in self.venue_volumes[venue_normalized]:
            return ScrapingResult.failure_result(
                errors=[f"Year {year} not available for venue {venue}"],
                metadata={"venue": venue, "year": year},
            )

        try:
            url = self.get_proceedings_url(venue, year)
            self.logger.info(f"Fetching PMLR proceedings from: {url}")

            response = self._make_request(url)
            papers = self.parse_proceedings_page(response.text, venue_normalized, year)

            return ScrapingResult.success_result(
                papers_count=len(papers),
                metadata={
                    "url": url,
                    "venue": venue_normalized,
                    "year": year,
                    "volume": self.venue_volumes[venue_normalized][year],
                    "papers": papers,
                },
            )

        except Exception as e:
            error_msg = f"Failed to scrape {venue} {year}: {str(e)}"
            self.logger.error(error_msg)
            return ScrapingResult.failure_result(
                errors=[error_msg], metadata={"venue": venue, "year": year}
            )

    def parse_proceedings_page(
        self, html: str, venue: str, year: int
    ) -> List[SimplePaper]:
        """Parse PMLR proceedings HTML to extract papers"""
        soup = BeautifulSoup(html, "html.parser")
        papers = []

        # PMLR uses <div class="paper"> for each paper entry
        paper_entries = soup.find_all("div", class_="paper")

        if not paper_entries:
            # Try alternative structure
            paper_entries = soup.find_all("p", class_="title")

        for i, entry in enumerate(paper_entries):
            try:
                paper = self._extract_paper_from_entry(entry, venue, year, i)
                if paper:
                    papers.append(paper)
            except Exception as e:
                self.logger.warning(f"Failed to extract paper from entry {i}: {e}")
                continue

        self.logger.info(f"Extracted {len(papers)} papers from {venue} {year}")
        return papers

    def _extract_paper_from_entry(
        self, entry, venue: str, year: int, index: int
    ) -> Optional[SimplePaper]:
        """Extract paper from PMLR proceedings entry"""

        # Handle div.paper structure
        if entry.name == "div" and "paper" in entry.get("class", []):
            return self._extract_from_div_paper(entry, venue, year, index)
        # Handle p.title structure
        elif entry.name == "p" and "title" in entry.get("class", []):
            return self._extract_from_p_title(entry, venue, year, index)

        return None

    def _extract_from_div_paper(
        self, entry, venue: str, year: int, index: int
    ) -> Optional[SimplePaper]:
        """Extract paper from div.paper structure"""

        # Get title
        title_elem = entry.find("p", class_="title")
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)

        # Get authors
        authors_elem = entry.find("p", class_="authors") or entry.find(
            "span", class_="authors"
        )
        authors = self._extract_authors(authors_elem) if authors_elem else []

        # Get links
        links_elem = entry.find("p", class_="links")
        pdf_url = None
        paper_url = None

        if links_elem:
            # Look for PDF link
            pdf_link = links_elem.find("a", string=re.compile(r"Download PDF", re.I))
            if not pdf_link:
                pdf_link = links_elem.find("a", href=re.compile(r"\.pdf"))

            if pdf_link:
                pdf_url = pdf_link.get("href", "")
                if pdf_url and not pdf_url.startswith("http"):
                    pdf_url = urljoin(self.base_url, pdf_url)

            # Look for abstract/paper page link
            abs_link = links_elem.find("a", string=re.compile(r"abs", re.I))
            if abs_link:
                paper_url = abs_link.get("href", "")
                if paper_url and not paper_url.startswith("http"):
                    paper_url = urljoin(self.base_url, paper_url)

        # Generate paper ID
        volume = self.venue_volumes[venue][year]
        paper_id = f"pmlr_v{volume}_{venue.lower()}_{year}_{index}"

        return SimplePaper(
            paper_id=paper_id,
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            pdf_urls=[pdf_url] if pdf_url else [],
            source_scraper="pmlr",
            source_url=paper_url or pdf_url or "",
            metadata_completeness=self._calculate_completeness(title, authors, pdf_url),
            extraction_confidence=0.9,
        )

    def _extract_from_p_title(
        self, entry, venue: str, year: int, index: int
    ) -> Optional[SimplePaper]:
        """Extract paper from p.title structure (older PMLR format)"""

        title = entry.get_text(strip=True)
        if not title:
            return None

        # Look for authors in next sibling
        authors = []
        next_elem = entry.find_next_sibling()

        if (
            next_elem
            and next_elem.name == "p"
            and "authors" in next_elem.get("class", [])
        ):
            authors = self._extract_authors(next_elem)

        # Look for links
        pdf_url = None
        paper_url = None

        # Search for links in following siblings
        for sibling in entry.find_next_siblings():
            if sibling.name == "p" and "links" in sibling.get("class", []):
                pdf_link = sibling.find("a", href=re.compile(r"\.pdf"))
                if pdf_link:
                    pdf_url = pdf_link.get("href", "")
                    if pdf_url and not pdf_url.startswith("http"):
                        pdf_url = urljoin(self.base_url, pdf_url)

                abs_link = sibling.find("a", string=re.compile(r"abs", re.I))
                if abs_link:
                    paper_url = abs_link.get("href", "")
                    if paper_url and not paper_url.startswith("http"):
                        paper_url = urljoin(self.base_url, paper_url)
                break

        # Generate paper ID
        volume = self.venue_volumes[venue][year]
        paper_id = f"pmlr_v{volume}_{venue.lower()}_{year}_{index}"

        return SimplePaper(
            paper_id=paper_id,
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            pdf_urls=[pdf_url] if pdf_url else [],
            source_scraper="pmlr",
            source_url=paper_url or pdf_url or "",
            metadata_completeness=self._calculate_completeness(title, authors, pdf_url),
            extraction_confidence=0.85,
        )

    def _extract_authors(self, element) -> List[str]:
        """Extract authors from element"""
        if not element:
            return []

        authors = []
        text = element.get_text(strip=True)

        # Split by comma or semicolon
        author_parts = re.split(r"[,;]", text)

        for part in author_parts:
            author = part.strip()
            # Clean up common suffixes
            author = re.sub(
                r"\s*\([^)]*\)", "", author
            )  # Remove affiliations in parentheses
            author = author.strip()

            if author and len(author) > 2:
                authors.append(author)

        return authors

    def _calculate_completeness(
        self, title: str, authors: List[str], pdf_url: Optional[str]
    ) -> float:
        """Calculate metadata completeness score"""
        score = 0.0

        if title and len(title) > 10:
            score += 0.4
        if authors:
            score += 0.3
        if pdf_url:
            score += 0.3

        return min(1.0, score)

    def estimate_paper_count(self, venue: str, year: int) -> Optional[int]:
        """Estimate paper count based on historical data"""
        estimates = {
            "ICML": {2024: 350, 2023: 350, 2022: 340, 2021: 330},
            "AISTATS": {2024: 70, 2023: 65, 2022: 65, 2021: 60},
            "UAI": {2024: 40, 2023: 38, 2022: 35, 2021: 35},
            "COLLAS": {2023: 15, 2022: 15},
        }

        venue_upper = self._normalize_venue(venue)
        if venue_upper in estimates and year in estimates[venue_upper]:
            return estimates[venue_upper][year]

        return None
