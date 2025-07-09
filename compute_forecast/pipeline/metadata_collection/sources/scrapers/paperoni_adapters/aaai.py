"""AAAI adapter using OAI-PMH protocol."""

import re
import time
import xml.etree.ElementTree as ET
from typing import List, Any, Optional
from datetime import datetime

from .base import BasePaperoniAdapter
from ..models import SimplePaper


class AAAIAdapter(BasePaperoniAdapter):
    """Adapter for AAAI proceedings using OAI-PMH protocol."""
    
    # Venue to OJS journal name mapping
    VENUE_TO_JOURNAL = {
        "aaai": "AAAI",
        "aies": "AIES",  # AI, Ethics, and Society
        "hcomp": "HCOMP",  # Human Computation and Crowdsourcing
        "icwsm": "ICWSM",  # International Conference on Web and Social Media
    }
    
    # Conference start years
    CONFERENCE_START_YEARS = {
        "aaai": 1980,   # AAAI Conference on Artificial Intelligence
        "aies": 2018,   # AAAI/ACM Conference on AI, Ethics, and Society
        "hcomp": 2013,  # AAAI Conference on Human Computation and Crowdsourcing
        "icwsm": 2007,  # International AAAI Conference on Web and Social Media
    }
    
    def __init__(self, config=None):
        super().__init__("aaai", config)
        self.base_url = "https://ojs.aaai.org/index.php"
        # XML namespaces for OAI-PMH
        self.namespaces = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        # Limit batch size for AAAI to avoid timeouts
        if self.config.batch_size > 50:
            self.logger.warning(f"Reducing batch size from {self.config.batch_size} to 50 for AAAI to avoid timeouts")
            self.config.batch_size = 50
        
    def get_supported_venues(self) -> List[str]:
        """Return all supported AAAI venues."""
        return list(self.VENUE_TO_JOURNAL.keys())
    
    def get_available_years(self, venue: str) -> List[int]:
        """Get available years for each venue."""
        venue_lower = venue.lower()
        
        if venue_lower not in self.CONFERENCE_START_YEARS:
            return []
            
        start_year = self.CONFERENCE_START_YEARS[venue_lower]
        current_year = datetime.now().year
        
        return list(range(start_year, current_year + 1))
    
    def _get_journal_name(self, venue: str) -> Optional[str]:
        """Get OJS journal name for a given venue."""
        return self.VENUE_TO_JOURNAL.get(venue.lower())
        
    def _create_paperoni_scraper(self):
        """Create HTTP session for OAI-PMH requests."""
        # Use the session from base class
        self.session.headers.update({
            'User-Agent': 'ComputeForecast/1.0 (mailto:research@institution.edu)',
            'Accept': 'application/xml'
        })
        return self.session
        
    def _call_paperoni_scraper(self, scraper: Any, venue: str, year: int) -> List[SimplePaper]:
        """Use OAI-PMH protocol to get papers."""
        papers = []
        
        venue_lower = venue.lower()
        journal_name = self._get_journal_name(venue_lower)
        
        if not journal_name:
            self.logger.error(f"Unsupported venue for AAAI: {venue}")
            return []
            
        try:
            # Ensure session is configured
            self._create_paperoni_scraper()
            
            # OAI-PMH endpoint URL
            oai_url = f"{self.base_url}/{journal_name}/oai"
            
            # For AAAI, use smaller date ranges to avoid timeouts
            # Split year into quarters
            date_ranges = [
                (f'{year}-01-01', f'{year}-03-31'),
                (f'{year}-04-01', f'{year}-06-30'),
                (f'{year}-07-01', f'{year}-09-30'),
                (f'{year}-10-01', f'{year}-12-31')
            ]
            
            for from_date, until_date in date_ranges:
                if len(papers) >= self.config.batch_size:
                    break
                    
                # Initial request parameters for this date range
                params = {
                    'verb': 'ListRecords',
                    'metadataPrefix': 'oai_dc',
                    'from': from_date,
                    'until': until_date
                }
                
                resumption_token = None
                
                while len(papers) < self.config.batch_size:
                    # Use resumption token if available
                    if resumption_token:
                        params = {
                            'verb': 'ListRecords',
                            'resumptionToken': resumption_token
                        }
                    
                    self.logger.info(f"Querying OAI-PMH for {venue} papers from {from_date} to {until_date}")
                    
                    # Add retry logic for 503 errors
                    max_retries = 3
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            response = self.session.get(oai_url, params=params, timeout=60)
                            if response.status_code == 503:
                                # Check for Retry-After header
                                retry_after = response.headers.get('Retry-After', 30)
                                try:
                                    retry_after = int(retry_after)
                                except (ValueError, TypeError):
                                    retry_after = 30
                                
                                self.logger.warning(f"Got 503 error, retrying after {retry_after} seconds")
                                time.sleep(retry_after)
                                retry_count += 1
                                continue
                            elif response.status_code != 200:
                                raise Exception(f"OAI-PMH error: {response.status_code} - {response.text}")
                            break
                        except Exception as e:
                            if retry_count < max_retries - 1:
                                self.logger.warning(f"Request failed, retrying: {e}")
                                time.sleep(10 * (retry_count + 1))  # Exponential backoff
                                retry_count += 1
                            else:
                                raise
                    
                    # Parse XML response
                    root = ET.fromstring(response.text)
                    
                    # Check for OAI-PMH errors
                    error_elem = root.find('.//oai:error', self.namespaces)
                    if error_elem is not None:
                        error_code = error_elem.get('code', 'unknown')
                        error_msg = error_elem.text or 'Unknown error'
                        if error_code == 'noRecordsMatch':
                            self.logger.info(f"No records found for {venue} from {from_date} to {until_date}")
                            break
                        else:
                            raise Exception(f"OAI-PMH error {error_code}: {error_msg}")
                    
                    # Extract records
                    records = root.findall('.//oai:record', self.namespaces)
                    
                    if not records:
                        self.logger.info(f"No records found for {venue} from {from_date} to {until_date}")
                        break
                    
                    for record in records:
                        if len(papers) >= self.config.batch_size:
                            break
                            
                        try:
                            paper = self._parse_oai_record(record, venue_lower, year)
                            if paper:
                                papers.append(paper)
                        except Exception as e:
                            self.logger.warning(f"Failed to parse OAI record: {e}")
                            continue
                    
                    # Check for resumption token
                    resumption_elem = root.find('.//oai:resumptionToken', self.namespaces)
                    if resumption_elem is not None and resumption_elem.text:
                        resumption_token = resumption_elem.text
                        # Add small delay before next request
                        time.sleep(2)  # Increased delay to be more polite
                    else:
                        # No more records for this date range
                        break
                    
            self.logger.info(f"Collected {len(papers)} papers for {venue} {year}")
            
        except Exception as e:
            self.logger.error(f"Error fetching AAAI papers for {venue} {year}: {e}")
            raise
            
        return papers
    
    def _parse_oai_record(self, record: ET.Element, venue: str, year: int) -> Optional[SimplePaper]:
        """Parse OAI-PMH record into SimplePaper."""
        try:
            # Extract metadata section
            metadata = record.find('.//oai_dc:dc', self.namespaces)
            if metadata is None:
                return None
            
            # Extract title
            title_elem = metadata.find('dc:title', self.namespaces)
            title = title_elem.text if title_elem is not None else ''
            if not title:
                return None
            
            # Extract authors
            authors = []
            for creator in metadata.findall('dc:creator', self.namespaces):
                if creator.text:
                    authors.append(creator.text)
            
            # Extract abstract
            desc_elem = metadata.find('dc:description', self.namespaces)
            abstract = desc_elem.text if desc_elem is not None else ''
            
            # Extract identifiers (URL and DOI)
            paper_url = ''
            doi = ''
            for identifier in metadata.findall('dc:identifier', self.namespaces):
                if identifier.text:
                    if identifier.text.startswith('http'):
                        paper_url = identifier.text
                    elif identifier.text.startswith('10.'):
                        doi = identifier.text
            
            # Extract PDF URL from relation field
            pdf_urls = []
            for relation in metadata.findall('dc:relation', self.namespaces):
                if relation.text and (relation.text.endswith('.pdf') or '/view/' in relation.text):
                    pdf_urls.append(relation.text)
            
            # Extract article ID from OAI identifier
            header = record.find('oai:header', self.namespaces)
            paper_id = ''
            if header is not None:
                identifier_elem = header.find('oai:identifier', self.namespaces)
                if identifier_elem is not None and identifier_elem.text:
                    paper_id = self._extract_article_id(identifier_elem.text)
            
            # Extract publication year from date if available
            date_elem = metadata.find('dc:date', self.namespaces)
            if date_elem is not None and date_elem.text:
                try:
                    pub_date = datetime.strptime(date_elem.text[:10], '%Y-%m-%d')
                    actual_year = pub_date.year
                except (ValueError, TypeError):
                    actual_year = year
            else:
                actual_year = year
            
            return SimplePaper(
                title=title,
                authors=authors,
                venue=venue.upper(),
                year=actual_year,
                abstract=abstract,
                pdf_urls=pdf_urls,
                doi=doi,
                paper_id=paper_id,
                source_scraper=self.source_name,
                source_url=paper_url,
                keywords=[],  # Keywords will be added in consolidation phase
                extraction_confidence=0.95
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing OAI record: {e}")
            return None
    
    def _extract_article_id(self, oai_identifier: str) -> Optional[str]:
        """Extract article ID from OAI identifier.
        
        Example: 'oai:ojs.aaai.org:article/32043' -> '32043'
        """
        match = re.search(r'article/(\d+)', oai_identifier)
        return match.group(1) if match else None