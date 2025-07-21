"""Scraper for IJCAI conference proceedings"""

import re
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
from datetime import datetime

from ..base import ConferenceProceedingsScraper, ScrapingConfig, ScrapingResult
from ..models import SimplePaper
from ..error_handling import retry_on_error


class IJCAIScraper(ConferenceProceedingsScraper):
    """Scraper for IJCAI conference proceedings"""

    def __init__(self, config: Optional[ScrapingConfig] = None):
        super().__init__("ijcai", config or ScrapingConfig())
        self.base_url = "https://www.ijcai.org/"
        self.proceedings_pattern = "proceedings/{year}/"

    def get_supported_venues(self) -> List[str]:
        return ["IJCAI", "ijcai"]

    def get_available_years(self, venue: str) -> List[int]:
        """Get available IJCAI years by checking proceedings index"""
        if venue.upper() != "IJCAI":
            return []

        try:
            url = urljoin(self.base_url, "proceedings/")
            response = self._make_request(url)

            soup = BeautifulSoup(response.content, "html.parser")
            years = []

            # Look for year links in proceedings index
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                year_match = re.search(r"proceedings/(\d{4})", str(href))
                if year_match:
                    years.append(int(year_match.group(1)))

            return sorted(list(set(years)), reverse=True)

        except Exception as e:
            self.logger.error(f"Failed to get IJCAI years: {e}")
            # Fallback to dynamic year range (current year back to 2018)
            current_year = datetime.now().year
            # Always include at least from 2018 to current year
            start_year = min(2018, current_year - 10)
            return list(range(current_year, start_year - 1, -1))

    def get_proceedings_url(self, venue: str, year: int) -> str:
        """Construct IJCAI proceedings URL"""
        return urljoin(self.base_url, self.proceedings_pattern.format(year=year))

    def estimate_paper_count(self, venue: str, year: int) -> Optional[int]:
        """Estimate the number of papers for IJCAI year."""
        try:
            url = self.get_proceedings_url(venue, year)
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Count paper_wrapper divs
            paper_wrappers = soup.find_all("div", class_="paper_wrapper")
            if paper_wrappers:
                return len(paper_wrappers)

            # Fallback: count PDF links
            pdf_links = soup.find_all("a", href=lambda x: x and ".pdf" in x)
            return len(pdf_links)

        except Exception as e:
            self.logger.warning(f"Could not estimate paper count for IJCAI {year}: {e}")
            return None

    @retry_on_error(max_retries=3, delay=1.0)
    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Scrape IJCAI papers for a specific year"""
        if venue.upper() != "IJCAI":
            return ScrapingResult(
                success=False,
                papers_collected=0,
                errors=[f"Venue {venue} not supported"],
                metadata={},
                timestamp=datetime.now(),
            )

        try:
            url = self.get_proceedings_url(venue, year)
            papers = self.parse_proceedings_page_from_url(url, venue, year)

            # Store papers in metadata for access
            return ScrapingResult(
                success=True,
                papers_collected=len(papers),
                errors=[],
                metadata={"url": url, "venue": venue, "year": year, "papers": papers},
                timestamp=datetime.now(),
            )

        except Exception as e:
            error_msg = f"Failed to scrape {venue} {year}: {str(e)}"
            self.logger.error(error_msg)
            return ScrapingResult(
                success=False,
                papers_collected=0,
                errors=[error_msg],
                metadata={"venue": venue, "year": year},
                timestamp=datetime.now(),
            )

    def parse_proceedings_page_from_url(
        self, url: str, venue: str, year: int
    ) -> List[SimplePaper]:
        """Fetch and parse proceedings page"""
        response = self._make_request(url)
        return self.parse_proceedings_page(response.text, venue, year)

    def parse_proceedings_page(
        self, html: str, venue: str, year: int
    ) -> List[SimplePaper]:
        """Parse IJCAI proceedings HTML to extract papers"""
        soup = BeautifulSoup(html, "html.parser")
        papers = []

        # IJCAI uses paper_wrapper divs to contain each paper
        paper_wrappers = soup.find_all("div", class_="paper_wrapper")

        if paper_wrappers:
            # Modern structure with paper_wrapper
            for wrapper in paper_wrappers:
                try:
                    paper = self._extract_paper_from_wrapper(wrapper, venue, year)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"Failed to extract paper from wrapper: {e}")
                    continue
        else:
            # Fallback to old method if no paper_wrapper found
            pdf_links = soup.find_all("a", href=lambda x: x and ".pdf" in x)

            for pdf_link in pdf_links:
                try:
                    paper = self._extract_paper_from_pdf_link(pdf_link, venue, year)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to extract paper from link {pdf_link}: {e}"
                    )
                    continue

        self.logger.info(f"Extracted {len(papers)} papers from {venue} {year}")
        return papers

    def _extract_paper_from_wrapper(
        self, wrapper, venue: str, year: int
    ) -> Optional[SimplePaper]:
        """Extract paper metadata from a paper_wrapper div"""
        # Extract title
        title_div = wrapper.find("div", class_="title")
        title = title_div.get_text(strip=True) if title_div else ""

        # Extract authors
        authors_div = wrapper.find("div", class_="authors")
        authors = []
        if authors_div:
            # Authors are comma-separated
            author_text = authors_div.get_text(strip=True)
            # Split by comma and clean up each author name
            authors = [
                author.strip() for author in author_text.split(",") if author.strip()
            ]

        # Extract PDF URL
        pdf_link = wrapper.find("a", href=lambda x: x and ".pdf" in x)
        if not pdf_link:
            return None

        pdf_url = pdf_link.get("href", "")
        if not pdf_url:
            return None

        # Make URL absolute - construct proper proceedings URL
        if not pdf_url.startswith("http"):
            base_proceedings_url = f"{self.base_url}proceedings/{year}/"
            pdf_url = urljoin(base_proceedings_url, pdf_url)

        # Validate URL
        if not self._is_valid_url(pdf_url) or not pdf_url.lower().endswith(".pdf"):
            self.logger.warning(f"Invalid PDF URL: {pdf_url}")
            return None

        # Extract paper ID from wrapper id or PDF filename
        paper_id = wrapper.get("id", "")
        if paper_id.startswith("paper"):
            paper_id = paper_id[5:]  # Remove 'paper' prefix
        else:
            # Fallback to extracting from PDF filename
            pdf_filename = pdf_url.split("/")[-1]
            paper_id = re.sub(r"\.pdf$", "", pdf_filename)

        # Generate full paper ID
        full_paper_id = f"ijcai_{year}_{paper_id}"

        return SimplePaper(
            paper_id=full_paper_id,
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            pdf_urls=[pdf_url],
            source_scraper="ijcai",
            source_url=pdf_url,
            metadata_completeness=self._calculate_completeness(title, authors),
            extraction_confidence=0.95,  # High confidence for structured extraction
        )

    def _extract_paper_from_pdf_link(
        self, pdf_link, venue: str, year: int
    ) -> Optional[SimplePaper]:
        """Extract paper metadata from PDF link and surrounding elements"""
        pdf_url = pdf_link.get("href", "")
        if not pdf_url:
            return None

        # Make URL absolute - construct proper proceedings URL
        if not pdf_url.startswith("http"):
            # For IJCAI, PDFs are under /proceedings/YEAR/
            base_proceedings_url = f"{self.base_url}proceedings/{year}/"
            pdf_url = urljoin(base_proceedings_url, pdf_url)

        # Validate URL - must be a valid URL AND end with .pdf
        if not self._is_valid_url(pdf_url) or not pdf_url.lower().endswith(".pdf"):
            self.logger.warning(f"Invalid PDF URL: {pdf_url}")
            return None

        # Extract paper ID from PDF filename
        pdf_filename = pdf_url.split("/")[-1]
        paper_number = re.sub(r"\.pdf$", "", pdf_filename)

        # Get title - usually the link text or nearby text
        title = pdf_link.get_text(strip=True)
        if not title or len(title) < 10:
            # Look for title in parent elements
            parent = pdf_link.parent
            if parent:
                title_candidates = parent.find_all(string=True)
                title = " ".join(
                    [t.strip() for t in title_candidates if len(t.strip()) > 10]
                )[:200]

        # Extract authors - look for patterns near the PDF link
        authors = self._extract_authors_near_element(pdf_link)

        # For paper ID, check if there's an actual ID in the parent element
        # Otherwise use the PDF number
        actual_paper_id = self._extract_paper_id_from_container(
            pdf_link.parent, paper_number
        )

        # Generate paper ID - use actual ID if found, otherwise use paper number
        full_paper_id = f"ijcai_{year}_{actual_paper_id}"

        return SimplePaper(
            paper_id=full_paper_id,
            title=title.strip(),
            authors=authors,
            venue=venue,
            year=year,
            pdf_urls=[pdf_url],
            source_scraper="ijcai",
            source_url=pdf_url,
            metadata_completeness=self._calculate_completeness(title, authors),
            extraction_confidence=0.9,  # High confidence for direct PDF links
        )

    def _extract_authors_near_element(self, element) -> List[str]:
        """Extract author information from elements near the PDF link"""
        authors = []
        seen_authors = set()  # Track unique authors

        # Look for author information in specific patterns
        if element.parent:
            # Check parent and its siblings for author information
            search_elements = []

            # Add next sibling if exists
            if element.parent.find_next_sibling():
                search_elements.append(element.parent.find_next_sibling())

            # Also check parent's parent children for p, span, div tags
            if element.parent.parent:
                for tag in element.parent.parent.find_all(["p", "span", "div"]):
                    if tag != element.parent:
                        search_elements.append(tag)

            # Process each element for author names
            for elem in search_elements:
                if hasattr(elem, "get_text"):
                    text = elem.get_text(strip=True)

                    # Pattern for author names (First Last, First Last, ...)
                    # This pattern looks for comma-separated names
                    if "," in text and not re.search(
                        r"\d{4}", text
                    ):  # Has commas but no years
                        # Split by comma and check each part
                        parts = text.split(",")
                        for part in parts:
                            part = part.strip()
                            # Enhanced validation to accept names with initials, hyphens, apostrophes
                            if (
                                self._is_valid_author_name(part)
                                and part not in seen_authors
                            ):
                                authors.append(part)
                                seen_authors.add(part)

            # Also check parent's text for author patterns
            parent_text = (
                element.parent.get_text(strip=True)
                if hasattr(element.parent, "get_text")
                else ""
            )

            # Look for pattern like "Author1, Author2" right after the title
            title_text = element.get_text(strip=True)
            if title_text in parent_text:
                # Get text after the title
                idx = parent_text.find(title_text) + len(title_text)
                remaining_text = parent_text[idx:].strip()

                # Enhanced pattern for author names with initials, hyphens, apostrophes
                # Matches patterns like: John Smith, J. A. Smith, Mary-Jane O'Brien, etc.
                author_pattern = r"^([A-Z][a-z\-']+ (?:[A-Z]\. )*[A-Z][a-z\-']+(?:, [A-Z][a-z\-']+ (?:[A-Z]\. )*[A-Z][a-z\-']+)*)"
                author_match = re.match(author_pattern, remaining_text)
                if author_match:
                    author_string = author_match.group(1)
                    for name in author_string.split(","):
                        name = name.strip()
                        if (
                            self._is_valid_author_name(name)
                            and name not in seen_authors
                        ):
                            authors.append(name)
                            seen_authors.add(name)

        return authors[:10]  # Limit to reasonable number

    def _extract_paper_id_from_container(self, container, default_id: str) -> str:
        """Try to extract actual paper ID from the container element"""
        if not container:
            return default_id

        # Look for patterns like "Paper ID: 6581" or "#6581" in the container
        container_text = (
            container.get_text() if hasattr(container, "get_text") else str(container)
        )

        # Try various ID patterns
        id_patterns = [
            r"Paper\s*ID[:\s]*(\d{4,5})",
            r"ID[:\s]*(\d{4,5})",
            r"#(\d{4,5})",
            r"\b(\d{4,5})\b",  # Any 4-5 digit number
        ]

        for pattern in id_patterns:
            match = re.search(pattern, container_text, re.IGNORECASE)
            if match:
                return match.group(1)

        # If no ID found, return the default (paper number from filename)
        return default_id

    def _is_valid_author_name(self, name: str) -> bool:
        """Validate if a string looks like a valid author name"""
        if not name or len(name) < 3:
            return False

        # Split into words
        words = name.split()
        if len(words) < 2:
            return False

        # Check each word/initial
        for word in words:
            # Accept single letter initials with dots (e.g., "J.")
            if len(word) == 2 and word[1] == "." and word[0].isupper():
                continue
            # Accept capitalized words with hyphens/apostrophes
            elif word and (word[0].isupper() or word[0] in ["'", "-"]):
                # Ensure it contains at least one letter
                if any(c.isalpha() for c in word):
                    continue
            else:
                return False

        return True

    def _is_valid_url(self, url: str) -> bool:
        """Validate if URL is well-formed"""
        if not url:
            return False

        # Basic URL validation
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        return bool(url_pattern.match(url))

    def _calculate_completeness(self, title: str, authors: List[str]) -> float:
        """Calculate metadata completeness score"""
        score = 0.0

        if title and len(title) > 10:
            score += 0.4
        if authors:
            score += 0.4
        if len(authors) > 1:
            score += 0.2

        return min(1.0, score)
