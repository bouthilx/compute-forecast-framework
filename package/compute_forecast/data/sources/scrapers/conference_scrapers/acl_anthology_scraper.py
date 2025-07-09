"""Scraper for ACL Anthology proceedings"""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin
from datetime import datetime

from ..base import ConferenceProceedingsScraper, ScrapingConfig, ScrapingResult
from ..models import SimplePaper
from ..error_handling import retry_on_error


class ACLAnthologyScraper(ConferenceProceedingsScraper):
    """Scraper for ACL Anthology proceedings"""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        super().__init__("acl_anthology", config or ScrapingConfig())
        self.base_url = "https://aclanthology.org/"
        self.venue_mappings = self._load_venue_mappings()
        
    def _load_venue_mappings(self) -> Dict[str, str]:
        """Map common venue names to ACL Anthology codes"""
        return {
            "ACL": "acl",
            "EMNLP": "emnlp", 
            "NAACL": "naacl",
            "COLING": "coling",
            "EACL": "eacl",
            "CoNLL": "conll",
            "SemEval": "semeval",
            "WMT": "wmt",
            "TACL": "tacl",
            "CL": "cl",
            "AACL": "aacl",
            "IJCNLP": "ijcnlp",
            "RANLP": "ranlp",
            "ANLP": "anlp"
        }
        
    def get_supported_venues(self) -> List[str]:
        return list(self.venue_mappings.keys())
        
    def get_available_years(self, venue: str) -> List[int]:
        """Get years available for a venue from ACL Anthology"""
        if venue not in self.venue_mappings:
            return []
            
        venue_code = self.venue_mappings[venue]
        # Try venues page first
        venue_url = urljoin(self.base_url, f"venues/{venue_code}/")
        
        try:
            response = self._make_request(venue_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            years = set()
            
            # Look for year-based links in various patterns
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Multiple patterns: events/acl-2024/, volumes/2024.acl-main/, P24-1234
                year_patterns = [
                    r'events/.*-(\d{4})/?$',
                    r'volumes/(\d{4})\.',
                    r'/[A-Z](\d{2})-\d+',  # Paper IDs like P24-1234 (year 2024)
                ]
                
                for pattern in year_patterns:
                    year_match = re.search(pattern, href)
                    if year_match:
                        year_str = year_match.group(1)
                        # Handle 2-digit years
                        if len(year_str) == 2:
                            year = 2000 + int(year_str) if int(year_str) < 50 else 1900 + int(year_str)
                        else:
                            year = int(year_str)
                        years.add(year)
                        
            return sorted(list(years), reverse=True)
            
        except Exception as e:
            self.logger.warning(f"Failed to get {venue} years from venue page: {e}")
            # Fallback to recent years
            current_year = datetime.now().year
            return list(range(current_year, 2017, -1))
    
    def get_proceedings_url(self, venue: str, year: int) -> str:
        """Construct ACL Anthology event URL"""
        venue_code = self.venue_mappings.get(venue, venue.lower())
        # Primary pattern is events page
        return urljoin(self.base_url, f"events/{venue_code}-{year}/")
        
    @retry_on_error(max_retries=3, delay=1.0)
    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Scrape ACL Anthology papers for venue/year"""
        if venue not in self.venue_mappings:
            return ScrapingResult.failure_result(
                errors=[f"Venue {venue} not supported"],
                metadata={"venue": venue, "year": year}
            )
            
        try:
            # Try events page first
            event_url = self.get_proceedings_url(venue, year)
            all_papers = []
            
            try:
                event_response = self._make_request(event_url)
                volume_urls = self._extract_volume_urls(event_response.text, venue, year)
                
                # If we found volume URLs, scrape each one
                if volume_urls:
                    for vol_name, vol_url in volume_urls.items():
                        try:
                            self.logger.info(f"Scraping {venue} {year} {vol_name} from {vol_url}")
                            papers = self._scrape_volume_page(vol_url, venue, year)
                            all_papers.extend(papers)
                        except Exception as e:
                            self.logger.warning(f"Failed to scrape volume {vol_name}: {e}")
                            continue
                else:
                    # No volume links found, try to parse papers directly from event page
                    all_papers = self._parse_event_page(event_response.text, venue, year, event_url)
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Event page not found, trying volume URLs directly: {e}")
                # Fallback to trying volume URLs directly
                all_papers = self._try_direct_volume_urls(venue, year)
            
            return ScrapingResult.success_result(
                papers_count=len(all_papers),
                metadata={
                    "venue": venue, 
                    "year": year, 
                    "papers": all_papers
                }
            )
            
        except Exception as e:
            error_msg = f"Failed to scrape {venue} {year}: {str(e)}"
            self.logger.error(error_msg)
            return ScrapingResult.failure_result(
                errors=[error_msg],
                metadata={"venue": venue, "year": year}
            )
    
    def _extract_volume_urls(self, html: str, venue: str, year: int) -> Dict[str, str]:
        """Extract volume URLs from event page"""
        soup = BeautifulSoup(html, 'html.parser')
        venue_code = self.venue_mappings.get(venue, venue.lower())
        volumes = {}
        
        # Look for volume links
        volume_patterns = [
            rf"volumes/{year}\.{venue_code}-(\w+)",
            r"volumes/[A-Z]\d{2}-(\w+)",  # New paper ID format
        ]
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            for pattern in volume_patterns:
                match = re.search(pattern, href)
                if match:
                    volume_type = match.group(1)
                    full_url = urljoin(self.base_url, href)
                    volumes[volume_type] = full_url
                    
        return volumes
    
    def _try_direct_volume_urls(self, venue: str, year: int) -> List[SimplePaper]:
        """Try common volume URL patterns directly"""
        venue_code = self.venue_mappings.get(venue, venue.lower())
        papers = []
        
        # Common volume suffixes
        volume_suffixes = ["main", "long", "short", "demo", "findings", "srw", "tutorial", "industry"]
        
        for suffix in volume_suffixes:
            # Try different URL patterns
            url_patterns = [
                f"volumes/{year}.{venue_code}-{suffix}/",
                f"volumes/{venue_code}-{year}-{suffix}/",
            ]
            
            for pattern in url_patterns:
                url = urljoin(self.base_url, pattern)
                try:
                    self.logger.debug(f"Trying direct URL: {url}")
                    papers.extend(self._scrape_volume_page(url, venue, year))
                    break  # If successful, don't try other patterns
                except Exception:
                    continue
                    
        return papers
    
    def _scrape_volume_page(self, url: str, venue: str, year: int) -> List[SimplePaper]:
        """Scrape papers from a volume page"""
        response = self._make_request(url)
        return self._parse_volume_page(response.text, venue, year, url)
        
    def parse_proceedings_page(self, html: str, venue: str, year: int) -> List[SimplePaper]:
        """Parse proceedings page HTML (required by base class)"""
        # This method is called by the base class scrape_venue_year
        # We'll redirect to our event page parser
        return self._parse_event_page(html, venue, year, self.get_proceedings_url(venue, year))
        
    def _parse_event_page(self, html: str, venue: str, year: int, source_url: str) -> List[SimplePaper]:
        """Parse ACL Anthology event page"""
        soup = BeautifulSoup(html, 'html.parser')
        papers = []
        
        # Look for paper entries - ACL Anthology uses various structures
        # Try multiple selectors
        paper_selectors = [
            'span.d-block',  # Common paper entry container
            'p.d-sm-flex',   # Alternative container
            'div.paper-entry',  # Another possible container
            'li.paper'  # List-based layout
        ]
        
        paper_entries = []
        for selector in paper_selectors:
            paper_entries = soup.select(selector)
            if paper_entries:
                break
                
        if not paper_entries:
            # Fallback: look for any links to paper pages
            paper_links = soup.find_all('a', href=re.compile(r'/[A-Z]\d{2}-\d+/?$'))
            for link in paper_links:
                paper = self._extract_paper_from_link(link, venue, year, source_url)
                if paper:
                    papers.append(paper)
        else:
            for entry in paper_entries:
                try:
                    paper = self._extract_paper_from_entry(entry, venue, year, source_url)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.debug(f"Failed to extract paper from entry: {e}")
                    continue
                    
        self.logger.info(f"Extracted {len(papers)} papers from {venue} {year}")
        return papers
    
    def _parse_volume_page(self, html: str, venue: str, year: int, source_url: str) -> List[SimplePaper]:
        """Parse ACL Anthology volume page"""
        # Volume pages often have similar structure to event pages
        return self._parse_event_page(html, venue, year, source_url)
        
    def _extract_paper_from_entry(self, entry, venue: str, year: int, source_url: str) -> Optional[SimplePaper]:
        """Extract paper from an entry element"""
        
        # Get paper URL - look for the entry itself if it's a BeautifulSoup object
        if hasattr(entry, 'name') and entry.name == 'div':
            # Entry is the container, look inside
            paper_link = entry.find('a', href=re.compile(r'/\d{4}\.\w+-\w+\.\d+/?$|/[A-Z]\d{2}-\d+/?$'))
        else:
            paper_link = entry.find('a', href=re.compile(r'/\d{4}\.\w+-\w+\.\d+/?$|/[A-Z]\d{2}-\d+/?$'))
            
        if not paper_link:
            # Try alternative patterns
            paper_link = entry.find('a', href=re.compile(r'/(anthology|papers)/'))
            
        if not paper_link:
            return None
            
        paper_url = paper_link['href']
        if not paper_url.startswith('http'):
            paper_url = urljoin(self.base_url, paper_url)
            
        # Extract paper ID from URL
        paper_id_match = re.search(r'/([A-Z]\d{2}-\d+)/?$', paper_url)
        if paper_id_match:
            paper_id = paper_id_match.group(1)
        else:
            # Try to extract from other patterns
            paper_id = paper_url.split('/')[-1] or paper_url.split('/')[-2]
        
        # Get title
        title = paper_link.get_text(strip=True)
        if not title:
            # Look for title in nearby elements
            title_elem = entry.find(['strong', 'b', 'h3', 'h4', 'h5'])
            title = title_elem.get_text(strip=True) if title_elem else ""
            
        # Get authors
        authors = self._extract_authors_from_entry(entry)
        
        # Get PDF URL
        pdf_url = self._extract_pdf_url(entry, paper_url)
                
        return SimplePaper(
            paper_id=f"acl_{paper_id}",
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            pdf_urls=[pdf_url] if pdf_url else [],
            source_scraper="acl_anthology",
            source_url=paper_url,
            metadata_completeness=self._calculate_completeness(title, authors, pdf_url),
            extraction_confidence=0.95  # High confidence for ACL Anthology
        )
        
    def _extract_paper_from_link(self, link, venue: str, year: int, source_url: str) -> Optional[SimplePaper]:
        """Extract paper from just a link element"""
        # Create a minimal entry container
        entry = BeautifulSoup(f'<div>{link}</div>', 'html.parser')
        return self._extract_paper_from_entry(entry, venue, year, source_url)
        
    def _extract_authors_from_entry(self, entry) -> List[str]:
        """Extract authors from ACL Anthology entry"""
        authors = []
        
        # Multiple strategies for finding authors
        # 1. Look for explicit author container
        author_container = entry.find(['span', 'div'], class_=re.compile(r'(author|by)'))
        if author_container:
            author_text = author_container.get_text()
        else:
            # 2. Look for italic text (common pattern)
            italic = entry.find('i')
            if italic:
                author_text = italic.get_text()
            else:
                # 3. Look for text pattern after title
                # Often authors are after title, before other metadata
                text_nodes = [node.strip() for node in entry.stripped_strings]
                author_text = ""
                
                # Look through all text nodes for author patterns
                for text in text_nodes:
                    # Common author patterns - must have at least 2 parts and contain names
                    if (re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', text) and 
                        not re.search(r'^\d{4}$', text) and
                        text != entry.find('a').get_text(strip=True) if entry.find('a') else True):
                        author_text = text
                        break
                        
        if author_text:
            # Clean and split authors
            author_text = re.sub(r'\s+', ' ', author_text).strip()
            
            # Split by common separators
            author_parts = re.split(r'[,;]|\s+and\s+|\s+AND\s+|\s*&\s*', author_text)
            
            for part in author_parts:
                part = part.strip()
                # Basic validation - at least two words
                if len(part.split()) >= 2 and not part.isdigit():
                    authors.append(part)
                    
        return authors
        
    def _extract_pdf_url(self, entry, paper_url: str) -> Optional[str]:
        """Extract PDF URL from entry"""
        # Look for explicit PDF link
        pdf_link = entry.find('a', href=re.compile(r'\.pdf$'))
        if pdf_link:
            pdf_url = pdf_link['href']
            if not pdf_url.startswith('http'):
                pdf_url = urljoin(self.base_url, pdf_url)
            return pdf_url
            
        # ACL Anthology often has predictable PDF URLs based on paper ID
        paper_id_match = re.search(r'/([A-Z]\d{2}-\d+)/?$', paper_url)
        if paper_id_match:
            paper_id = paper_id_match.group(1)
            # Common PDF URL pattern
            return f"https://aclanthology.org/{paper_id}.pdf"
            
        return None
        
    def _calculate_completeness(self, title: str, authors: List[str], pdf_url: Optional[str]) -> float:
        """Calculate metadata completeness score"""
        has_good_title = title and len(title) > 10
        has_authors = bool(authors)
        has_pdf = bool(pdf_url)
        
        # Score based on what we have
        if has_good_title and has_authors and has_pdf:
            return 1.0
        elif has_good_title and (has_authors or has_pdf):
            return 0.7
        elif has_good_title and not has_authors and not has_pdf:
            return 0.8  # Good title alone is valuable
        elif has_authors and has_pdf:
            return 0.6
        elif has_good_title:
            return 0.4
        elif has_authors or has_pdf:
            return 0.3
        else:
            return 0.0