"""Scraper for CVF Open Access proceedings (CVPR, ICCV, ECCV, WACV)"""

import re
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
from datetime import datetime

from ..base import ConferenceProceedingsScraper, ScrapingConfig, ScrapingResult
from ..models import SimplePaper
from ..error_handling import retry_on_error


class CVFScraper(ConferenceProceedingsScraper):
    """Scraper for CVF Open Access proceedings"""

    def __init__(self, config: Optional[ScrapingConfig] = None):
        super().__init__("cvf", config or ScrapingConfig())
        self.base_url = "https://openaccess.thecvf.com/"
        self.venue_schedules = {
            "CVPR": "annual",
            "ICCV": "odd_years",
            "ECCV": "even_years",
            "WACV": "annual",
        }

    def get_supported_venues(self) -> List[str]:
        """Return supported CVF venues"""
        return ["CVPR", "ICCV", "ECCV", "WACV", "cvpr", "iccv", "eccv", "wacv"]

    def get_available_years(self, venue: str) -> List[int]:
        """Get years available for venue respecting conference schedules"""
        venue_upper = venue.upper()
        if venue_upper not in self.venue_schedules:
            return []

        # Generate recent years based on conference schedule
        current_year = datetime.now().year
        base_years = list(range(current_year, 2012, -1))  # CVF started around 2013

        schedule = self.venue_schedules[venue_upper]
        if schedule == "odd_years":
            return [year for year in base_years if year % 2 == 1]
        elif schedule == "even_years":
            return [year for year in base_years if year % 2 == 0]
        else:  # annual
            return base_years

    def get_proceedings_url(self, venue: str, year: int) -> str:
        """Construct CVF proceedings URL"""
        return urljoin(self.base_url, f"{venue.upper()}{year}?day=all")

    @retry_on_error(max_retries=3, delay=1.0)
    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Scrape CVF papers for venue/year"""
        if venue not in self.get_supported_venues():
            return ScrapingResult.failure_result(
                errors=[f"Venue {venue} not supported"],
                metadata={"venue": venue, "year": year},
            )

        # Validate conference schedule
        available_years = self.get_available_years(venue)
        if year not in available_years:
            return ScrapingResult.failure_result(
                errors=[f"{venue} {year} not available (conference schedule)"],
                metadata={"venue": venue, "year": year},
            )

        try:
            url = self.get_proceedings_url(venue, year)
            response = self._make_request(url)
            papers = self.parse_proceedings_page(response.text, venue, year)

            return ScrapingResult.success_result(
                papers_count=len(papers),
                metadata={"url": url, "venue": venue, "year": year, "papers": papers},
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
        """Parse CVF proceedings HTML to extract papers"""
        soup = BeautifulSoup(html, "html.parser")
        papers = []

        # CVF uses <dt class="ptitle"> for paper titles
        paper_entries = soup.find_all("dt", class_="ptitle")

        for entry in paper_entries:
            try:
                paper = self._extract_paper_from_entry(entry, venue, year)
                if paper:
                    papers.append(paper)
            except Exception as e:
                self.logger.warning(f"Failed to extract paper from entry: {e}")
                continue

        self.logger.info(f"Extracted {len(papers)} papers from {venue} {year}")
        return papers

    def _extract_paper_from_entry(
        self, entry, venue: str, year: int
    ) -> Optional[SimplePaper]:
        """Extract paper from CVF proceedings entry"""

        # Get title from the link in dt element
        title_link = entry.find("a")
        if not title_link:
            return None

        title = title_link.get_text(strip=True)
        paper_detail_url = title_link.get("href", "")

        if paper_detail_url and not paper_detail_url.startswith("http"):
            paper_detail_url = urljoin(self.base_url, paper_detail_url)

        # Get authors from next dd element with forms
        authors_elem = entry.find_next_sibling("dd")
        authors = (
            self._extract_authors_from_element(authors_elem) if authors_elem else []
        )

        # Look for PDF link in the following dd element
        pdf_elem = authors_elem.find_next_sibling("dd") if authors_elem else None
        pdf_url = self._extract_pdf_url(pdf_elem) if pdf_elem else None

        # Extract paper ID from detail URL or create from title
        paper_id_match = (
            re.search(r"/([^/]+)\.html$", paper_detail_url)
            if paper_detail_url
            else None
        )
        paper_id = (
            paper_id_match.group(1) if paper_id_match else title.replace(" ", "_")[:50]
        )

        return SimplePaper(
            paper_id=f"cvf_{venue.lower()}_{year}_{paper_id}",
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            pdf_urls=[pdf_url] if pdf_url else [],
            source_scraper="cvf",
            source_url=paper_detail_url,
            metadata_completeness=self._calculate_completeness(title, authors, pdf_url),
            extraction_confidence=0.95,  # High confidence for CVF proceedings
        )

    def _extract_authors_from_element(self, element) -> List[str]:
        """Extract authors from CVF author element with forms"""
        authors: List[str] = []

        if not element:
            return authors

        # CVF stores authors in form elements with hidden inputs
        forms = element.find_all("form", class_="authsearch")

        for form in forms:
            hidden_input = form.find(
                "input", {"type": "hidden", "name": "query_author"}
            )
            if hidden_input:
                author_name = hidden_input.get("value", "").strip()
                if author_name:
                    authors.append(author_name)

        # Fallback: extract from anchor text if forms don't work
        if not authors:
            anchors = element.find_all("a")
            for anchor in anchors:
                author_name = anchor.get_text(strip=True)
                if author_name and len(author_name) > 2:
                    authors.append(author_name)

        return authors

    def _extract_pdf_url(self, element) -> Optional[str]:
        """Extract PDF URL from links element"""
        if not element:
            return None

        # Look for [pdf] link
        pdf_link = element.find("a", string="pdf")
        if pdf_link:
            href = pdf_link.get("href", "")
            if href:
                if not href.startswith("http"):
                    href = urljoin(self.base_url, href)
                return str(href)

        return None

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
