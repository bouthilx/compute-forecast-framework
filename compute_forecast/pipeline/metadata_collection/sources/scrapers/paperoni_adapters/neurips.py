"""NeurIPS paperoni adapter - simplified implementation."""

from typing import List, Any, Optional
from datetime import datetime
import re
import time
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag

from .base import BasePaperoniAdapter
from ..models import SimplePaper


class NeurIPSAdapter(BasePaperoniAdapter):
    """Simplified adapter for NeurIPS papers - scrapes directly from proceedings."""

    def __init__(self, config=None):
        super().__init__("neurips", config)
        self.base_url = "https://proceedings.neurips.cc"
        # Add configurable request delay for PDF fetching
        self.pdf_request_delay = getattr(config, 'pdf_request_delay', 0.1) if config else 0.1
        # Override rate limit for NeurIPS to 0.1s (since no documented rate limit exists)
        if self.config:
            self.config.rate_limit_delay = 0.1

    def get_supported_venues(self) -> List[str]:
        return ["neurips", "NeurIPS", "NIPS"]

    def _create_paperoni_scraper(self):
        """No paperoni scraper needed for simplified implementation."""
        return None

    def estimate_paper_count(self, venue: str, year: int) -> Optional[int]:
        """Estimate the number of papers for NeurIPS year."""
        try:
            url = f"{self.base_url}/paper_files/paper/{year}"
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Count paper entries
            paper_count = 0
            for li in soup.find_all("li"):
                if isinstance(li, Tag):
                    link = li.find("a", href=lambda x: x and "hash" in x)
                    if link:
                        paper_count += 1

            self.logger.info(f"NeurIPS {year} has approximately {paper_count} papers")
            return paper_count

        except Exception as e:
            self.logger.warning(
                f"Could not estimate paper count for NeurIPS {year}: {e}"
            )
            return None

    def _call_paperoni_scraper(self, scraper: Any, venue: str, year: int) -> List[Any]:
        """Direct implementation instead of using paperoni."""
        papers = []
        
        self.logger.info(f"Starting NeurIPS scraper for {venue} {year}")
        self.logger.debug(f"Batch size: {self.config.batch_size}")
        self.logger.debug(f"PDF request delay: {self.pdf_request_delay}s")

        try:
            # Fetch the proceedings page for the given year
            url = f"{self.base_url}/paper_files/paper/{year}"
            self.logger.info(f"Fetching proceedings page: {url}")
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Find all paper entries - look for li elements that contain paper links
            # NeurIPS papers have links with 'hash' in the URL
            all_li = soup.find_all("li")
            paper_entries = []

            for li in all_li:
                if isinstance(li, Tag):
                    link = li.find("a", href=lambda x: x and "hash" in x)
                    if link:
                        paper_entries.append(li)

            self.logger.info(
                f"Found {len(paper_entries)} paper entries on NeurIPS {year} page"
            )

            # Apply batch size limit if batch_size is reasonable (not unlimited)
            limit = (
                self.config.batch_size
                if self.config.batch_size < 10000
                else len(paper_entries)
            )
            
            self.logger.info(f"Processing {limit} papers (batch_size={self.config.batch_size})")
            
            processed_count = 0
            for i, entry in enumerate(paper_entries[:limit]):
                try:
                    self.logger.debug(f"Processing paper {i+1}/{limit}")
                    # Extract paper link
                    if isinstance(entry, Tag):
                        link_elem = entry.find("a")
                        if not link_elem or not isinstance(link_elem, Tag):
                            continue

                        href_attr = link_elem.get("href", "")
                        if not isinstance(href_attr, str) or "hash" not in href_attr:
                            continue

                        paper_url = href_attr
                        if not paper_url.startswith("http"):
                            paper_url = self.base_url + paper_url

                        # Extract title
                        title = link_elem.text.strip()
                    else:
                        continue

                    # Extract authors
                    authors = []
                    if isinstance(entry, Tag):
                        authors_elem = entry.find("i")
                        if authors_elem and isinstance(authors_elem, Tag):
                            authors_text = authors_elem.text
                            # Simple split by comma - more sophisticated parsing could be added
                            authors = [a.strip() for a in authors_text.split(",")]

                    # Extract hash for PDF URL
                    hash_match = re.search(r"hash/([^-]+)", paper_url)
                    if hash_match:
                        paper_hash = hash_match.group(1)
                        
                        # Try to fetch actual PDF URL from page
                        self.logger.debug(f"Fetching PDF URL for paper: {paper_url}")
                        pdf_url = self._fetch_pdf_url_from_page(paper_url, paper_hash)
                        
                        if not pdf_url:
                            # Fall back to pattern-based URL (with year-aware logic)
                            year_int = int(year)
                            if year_int >= 2022:
                                # Use Conference pattern for 2022+
                                pdf_url = f"{self.base_url}/paper_files/paper/{year}/file/{paper_hash}-Paper-Conference.pdf"
                            else:
                                # Use standard pattern for 2021 and earlier
                                pdf_url = f"{self.base_url}/paper_files/paper/{year}/file/{paper_hash}-Paper.pdf"
                            
                            self.logger.debug(
                                f"Using pattern-based PDF URL for {paper_hash}: {pdf_url}"
                            )
                    else:
                        # Fallback for unexpected URL format
                        pdf_url = paper_url.replace("/hash/", "/file/").replace(".html", ".pdf")
                        self.logger.warning(f"Could not extract hash from URL: {paper_url}")

                    # Create SimplePaper object
                    paper = SimplePaper(
                        title=title,
                        authors=authors,
                        venue="NeurIPS",
                        year=year,
                        pdf_urls=[pdf_url],
                        source_scraper=self.source_name,
                        source_url=paper_url,
                        scraped_at=datetime.now(),
                        extraction_confidence=0.9,
                    )

                    papers.append(paper)
                    processed_count += 1
                    
                    if processed_count % 10 == 0:
                        self.logger.info(f"Processed {processed_count}/{limit} papers")

                except Exception as e:
                    self.logger.warning(f"Failed to parse paper entry {i+1}: {e}")
                    if self.logger.isEnabledFor(logging.DEBUG):
                        import traceback
                        self.logger.debug(traceback.format_exc())
                    continue

            self.logger.info(
                f"Successfully extracted {len(papers)} papers from {limit} processed entries"
            )

        except Exception as e:
            self.logger.error(f"Failed to fetch NeurIPS {year} proceedings: {e}")
            raise

        return papers

    def _fetch_pdf_url_from_page(self, html_url: str, paper_hash: str) -> Optional[str]:
        """
        Fetch the actual PDF URL from the paper's HTML page.
        
        Args:
            html_url: The URL of the paper's HTML page
            paper_hash: The paper's hash identifier
            
        Returns:
            The PDF URL if found, None otherwise
        """
        self.logger.debug(f"_fetch_pdf_url_from_page called with: {html_url}")
        
        try:
            # Add delay before fetching to be respectful to the server
            if self.pdf_request_delay > 0:
                time.sleep(self.pdf_request_delay)
            
            # Fetch the paper page
            response = self._make_request(html_url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Look for PDF links using button classes - much safer than searching all links
            main_paper_url = None
            other_pdfs = []
            
            # Strategy 1: For 2022+, look for btn-primary (exactly one per page, always the main paper)
            btn_primary = soup.find("a", class_="btn-primary")
            if btn_primary and btn_primary.get("href", "").endswith(".pdf"):
                href = btn_primary["href"]
                if paper_hash in href:
                    main_paper_url = href
                    self.logger.debug(f"Found main paper via btn-primary: {btn_primary.text.strip()}")
            
            # Strategy 2: If no btn-primary (2019-2021), look for button with text "Paper"
            if not main_paper_url:
                pdf_buttons = soup.find_all("a", class_="btn")
                
                for button in pdf_buttons:
                    href = button.get("href", "")
                    text = button.text.strip()
                    
                    # Check if this is a PDF link for this paper
                    if paper_hash in href and href.endswith(".pdf"):
                        # Use text to identify the PDF type - most reliable method
                        if text == "Paper":
                            # This is the main paper
                            main_paper_url = href
                            self.logger.debug(f"Found main paper button via text: {text}")
                            break
                        elif text == "Supplemental":
                            other_pdfs.append((href, "supplemental"))
                        elif text == "AuthorFeedback":
                            other_pdfs.append((href, "feedback"))
                        else:
                            # Unknown button text
                            self.logger.warning(f"Unknown PDF button text: '{text}' for {href}")
                            other_pdfs.append((href, f"unknown-{text}"))
            
            # Use main paper if found, otherwise log what we skipped
            if main_paper_url:
                pdf_url = main_paper_url
                if not pdf_url.startswith("http"):
                    pdf_url = urljoin(self.base_url, pdf_url)
                
                self.logger.debug(f"Selected main paper PDF: {pdf_url}")
            elif other_pdfs:
                self.logger.warning(
                    f"No main paper PDF found for {paper_hash}. "
                    f"Skipped PDFs: {[(url, type) for url, type in other_pdfs]}"
                )
                return None
            else:
                return None
            
            # Validate the URL pattern
            self._validate_pdf_url_pattern(pdf_url, html_url)
            
            return pdf_url
            
        except Exception as e:
            self.logger.warning(
                f"Failed to fetch PDF URL from page {html_url}: {e}"
            )
        
        return None

    def _validate_pdf_url_pattern(self, pdf_url: str, html_url: str) -> None:
        """
        Validate that the PDF URL matches a known pattern for main papers.
        Log a warning if an unknown pattern is detected.
        """
        main_paper_patterns = [
            "-Paper.pdf",
            "-Paper-Conference.pdf"
        ]
        
        non_paper_patterns = [
            "-AuthorFeedback.pdf",
            "-Supplemental.pdf",
            "-Supplemental-Conference.pdf"
        ]
        
        # Extract the suffix after the hash - need to handle the full URL properly
        if "/file/" in pdf_url and "-" in pdf_url:
            # Get the filename part after the last /
            filename = pdf_url.split("/")[-1]
            # Extract suffix after the hash
            if "-" in filename:
                suffix = "-" + filename.split("-", 1)[1]
            else:
                suffix = filename
            
            if suffix in main_paper_patterns:
                self.logger.debug(f"Confirmed main paper pattern: {suffix}")
            elif suffix in non_paper_patterns:
                self.logger.error(
                    f"Non-paper PDF pattern detected but being used: {suffix} "
                    f"This should not happen! (from HTML: {html_url})"
                )
            else:
                self.logger.warning(
                    f"Unknown PDF URL pattern detected: {suffix} "
                    f"(from HTML: {html_url})"
                )
