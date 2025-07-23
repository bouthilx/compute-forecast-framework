"""NeurIPS paperoni adapter - simplified implementation."""

from typing import List, Any, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup, Tag

from .base import BasePaperoniAdapter
from ..models import SimplePaper


class NeurIPSAdapter(BasePaperoniAdapter):
    """Simplified adapter for NeurIPS papers - scrapes directly from proceedings."""

    def __init__(self, config=None):
        super().__init__("neurips", config)
        self.base_url = "https://proceedings.neurips.cc"

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

        try:
            # Fetch the proceedings page for the given year
            url = f"{self.base_url}/paper_files/paper/{year}"
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
            for entry in paper_entries[:limit]:
                try:
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
                        pdf_url = f"{self.base_url}/paper_files/paper/{year}/file/{paper_hash}-Paper.pdf"
                    else:
                        pdf_url = paper_url.replace("/hash/", "/file/").replace(
                            ".html", ".pdf"
                        )

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

                except Exception as e:
                    self.logger.warning(f"Failed to parse paper entry: {e}")
                    continue

            self.logger.info(
                f"Successfully extracted {len(papers)} papers from {len(paper_entries)} entries"
            )

        except Exception as e:
            self.logger.error(f"Failed to fetch NeurIPS {year} proceedings: {e}")
            raise

        return papers
