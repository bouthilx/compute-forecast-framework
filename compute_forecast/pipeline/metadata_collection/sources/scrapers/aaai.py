"""AAAI scraper using OAI-PMH protocol."""

import re
import time
import xml.etree.ElementTree as ET
from typing import List, Any, Optional
from datetime import datetime

from .base import BaseScraper, ScrapingResult, ScrapingConfig
from .models import SimplePaper


class AAAIScraper(BaseScraper):
    """Scraper for AAAI proceedings using OAI-PMH protocol."""
    
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
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        super().__init__("aaai", config)
        self.base_url = "https://ojs.aaai.org/index.php"
        # XML namespaces for OAI-PMH
        self.namespaces = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        # Configure session headers
        self.session.headers.update({
            'User-Agent': 'ComputeForecast/1.0 (mailto:research@institution.edu)',
            'Accept': 'application/xml'
        })
        # Limit batch size for AAAI to avoid timeouts
        if self.config.batch_size > 50:
            self.logger.warning(f"Reducing batch size from {self.config.batch_size} to 50 for AAAI to avoid timeouts")
            self.config.batch_size = 50
        
        # Enable debug logging if environment variable is set
        import os
        if os.environ.get('CF_DEBUG') or os.environ.get('CF_VERBOSE'):
            import logging
            self.logger.setLevel(logging.DEBUG)
            # Also add console handler to see debug output
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
        
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
        
    def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
        """Scrape papers for a specific venue and year using OAI-PMH."""
        papers = []
        errors = []
        
        venue_lower = venue.lower()
        journal_name = self._get_journal_name(venue_lower)
        
        if not journal_name:
            error_msg = f"Unsupported venue for AAAI: {venue}"
            self.logger.error(error_msg)
            return ScrapingResult(
                success=False,
                papers_collected=0,
                errors=[error_msg],
                metadata={},
                timestamp=datetime.now()
            )
            
        try:
            # OAI-PMH endpoint URL
            oai_url = f"{self.base_url}/{journal_name}/oai"
            
            # For AAAI, use much smaller date ranges to avoid timeouts
            # Conference-specific optimizations: only query months when conferences typically publish
            conference_months = {
                'aaai': [1, 2, 3, 4],     # AAAI is usually in Feb-March, papers appear Jan-Apr
                'aies': list(range(1, 13)),  # AIES varies by year
                'hcomp': [10, 11, 12],    # HCOMP is usually in October
                'icwsm': [5, 6, 7],       # ICWSM is usually in June
            }
            
            # Get relevant months for this venue
            months_to_query = conference_months.get(venue_lower, list(range(1, 13)))
            
            # Build date ranges for relevant months only
            date_ranges = []
            for month in months_to_query:
                if month == 12:
                    # December ends on 31st
                    date_ranges.append((f'{year}-{month:02d}-01', f'{year}-{month:02d}-31'))
                elif month in [4, 6, 9, 11]:
                    # April, June, September, November have 30 days
                    date_ranges.append((f'{year}-{month:02d}-01', f'{year}-{month:02d}-30'))
                elif month == 2:
                    # February - use 28 to avoid leap year issues
                    date_ranges.append((f'{year}-{month:02d}-01', f'{year}-{month:02d}-28'))
                else:
                    # January, March, May, July, August, October have 31 days
                    date_ranges.append((f'{year}-{month:02d}-01', f'{year}-{month:02d}-31'))
            
            for from_date, until_date in date_ranges:
                if len(papers) >= self.config.batch_size:
                    break
                
                # Try weekly ranges if we're having trouble
                use_weekly_ranges = len(errors) > 0  # Switch to weekly after first error
                
                if use_weekly_ranges and from_date != until_date:
                    # Split month into weekly ranges
                    from_day = int(from_date.split('-')[2])
                    until_day = int(until_date.split('-')[2])
                    year_month = from_date[:7]
                    
                    week_ranges = []
                    for week_start in range(from_day, until_day + 1, 7):
                        week_end = min(week_start + 6, until_day)
                        week_ranges.append((f"{year_month}-{week_start:02d}", f"{year_month}-{week_end:02d}"))
                else:
                    week_ranges = [(from_date, until_date)]
                
                for week_from, week_until in week_ranges:
                    if len(papers) >= self.config.batch_size:
                        break
                        
                    # Initial request parameters for this date range
                    params = {
                        'verb': 'ListRecords',
                        'metadataPrefix': 'oai_dc',
                        'from': week_from,
                        'until': week_until
                    }
                
                    resumption_token = None
                    
                    while len(papers) < self.config.batch_size:
                        # Use resumption token if available
                        if resumption_token:
                            params = {
                                'verb': 'ListRecords',
                                'resumptionToken': resumption_token
                            }
                        
                        self.logger.info(f"Querying OAI-PMH for {venue} papers from {week_from} to {week_until}")
                    
                        # Add retry logic for 503 errors
                        max_retries = 3
                        retry_count = 0
                        
                        while retry_count < max_retries:
                            try:
                                # Use very short timeout to fail fast on hanging connections
                                response = self.session.get(oai_url, params=params, timeout=5)
                                if response.status_code == 503:
                                    # Check for Retry-After header
                                    retry_after = response.headers.get('Retry-After', 30)
                                    try:
                                        retry_after = int(retry_after)
                                    except (ValueError, TypeError):
                                        retry_after = 30
                                    
                                    self.logger.warning(f"Got 503 error, retrying after {retry_after} seconds")
                                    time.sleep(min(retry_after, 30))  # Cap wait time
                                    retry_count += 1
                                    continue
                                elif response.status_code != 200:
                                    raise Exception(f"OAI-PMH error: {response.status_code}")
                                break
                            except Exception as e:
                                if retry_count < max_retries - 1:
                                    wait_time = min(5 * (retry_count + 1), 20)  # Shorter backoff
                                    self.logger.warning(f"Request failed for {week_from} to {week_until}, retrying in {wait_time}s: {str(e)[:100]}")
                                    time.sleep(wait_time)
                                    retry_count += 1
                                else:
                                    # Skip this date range instead of failing entirely
                                    self.logger.error(f"Skipping {week_from} to {week_until} after {max_retries} retries: {str(e)[:100]}")
                                    errors.append(f"Timeout for {week_from} to {week_until}")
                                    break  # Continue with next date range
                    
                        # Skip this date range if we couldn't get a response
                        if retry_count >= max_retries:
                            continue
                            
                        # Parse XML response
                        root = ET.fromstring(response.text)
                    
                        # Check for OAI-PMH errors
                        error_elem = root.find('.//oai:error', self.namespaces)
                        if error_elem is not None:
                            error_code = error_elem.get('code', 'unknown')
                            error_msg = error_elem.text or 'Unknown error'
                            if error_code == 'noRecordsMatch':
                                self.logger.info(f"No records found for {venue} from {week_from} to {week_until}")
                                break
                            else:
                                raise Exception(f"OAI-PMH error {error_code}: {error_msg}")
                        
                        # Extract records
                        records = root.findall('.//oai:record', self.namespaces)
                        
                        if not records:
                            self.logger.info(f"No records found for {venue} from {week_from} to {week_until}")
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
            
            # Consider it a success if we got any papers, even with some errors
            success = len(papers) > 0 or (len(errors) < len(date_ranges))
            
            return ScrapingResult(
                success=success,
                papers_collected=len(papers),
                errors=errors if errors else [],
                metadata={"papers": papers},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            error_msg = f"Error fetching AAAI papers for {venue} {year}: {str(e)}"
            self.logger.error(error_msg)
            return ScrapingResult(
                success=False,
                papers_collected=len(papers),
                errors=[error_msg],
                metadata={"papers": papers} if papers else {},
                timestamp=datetime.now()
            )
    
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
    
    def estimate_paper_count(self, venue: str, year: int) -> Optional[int]:
        """Estimate number of papers for a venue/year using fast OAI-PMH queries.
        
        Uses ListIdentifiers verb with a sample month to estimate total papers.
        Falls back to reasonable defaults if API fails.
        """
        import time as timer
        start_time = timer.time()
        
        venue_lower = venue.lower()
        journal_name = self._get_journal_name(venue_lower)
        
        if not journal_name:
            return None
        
        self.logger.info(f"Starting paper count estimation for {venue} {year}")
        
        try:
            # OAI-PMH endpoint URL
            oai_url = f"{self.base_url}/{journal_name}/oai"
            
            # Sample just January to estimate (or first month of conference)
            # For conferences that don't run all year, sample their typical month
            sample_months = {
                'aaai': ('02', '02'),  # AAAI is usually in February
                'aies': ('01', '01'),  # AIES varies
                'hcomp': ('10', '10'),  # HCOMP is usually in October
                'icwsm': ('06', '06'),  # ICWSM is usually in June
            }
            
            start_month, end_month = sample_months.get(venue_lower, ('01', '01'))
            
            params = {
                'verb': 'ListIdentifiers',
                'metadataPrefix': 'oai_dc',
                'from': f'{year}-{start_month}-01',
                'until': f'{year}-{end_month}-28'  # Use 28 to avoid month-end issues
            }
            
            self.logger.debug(f"Estimating papers for {venue} {year} using sample month {start_month}")
            self.logger.debug(f"Request URL: {oai_url} with params: {params}")
            
            request_start = timer.time()
            response = self.session.get(oai_url, params=params, timeout=3)  # Very short timeout for estimation
            request_time = timer.time() - request_start
            self.logger.debug(f"OAI-PMH request took {request_time:.2f}s, status: {response.status_code}")
            
            if response.status_code == 503:
                # Rate limited, fall back to defaults
                self.logger.debug("Got 503 during estimation, using defaults")
                raise Exception("Rate limited")
            elif response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            
            # Parse XML response
            parse_start = timer.time()
            root = ET.fromstring(response.text)
            parse_time = timer.time() - parse_start
            self.logger.debug(f"XML parsing took {parse_time:.2f}s")
            
            # Check for OAI-PMH errors
            error_elem = root.find('.//oai:error', self.namespaces)
            if error_elem is not None:
                error_code = error_elem.get('code', 'unknown')
                if error_code == 'noRecordsMatch':
                    # No papers in this year
                    return 0
                else:
                    raise Exception(f"OAI error: {error_code}")
            
            # Count identifiers in this page
            identifiers = root.findall('.//oai:header/oai:identifier', self.namespaces)
            sample_count = len(identifiers)
            
            # Check if there's a resumption token with total count
            resumption = root.find('.//oai:resumptionToken', self.namespaces)
            if resumption is not None:
                # Some OAI-PMH implementations provide completeListSize
                complete_size = resumption.get('completeListSize')
                if complete_size:
                    try:
                        sample_count = int(complete_size)
                        self.logger.debug(f"Got completeListSize from OAI-PMH: {sample_count}")
                    except (ValueError, TypeError):
                        pass
                elif resumption.text:
                    # There are more pages, estimate based on typical page size
                    # OJS typically returns 100 records per page
                    self.logger.debug("Has resumption token, estimating multiple pages")
                    sample_count = max(sample_count * 2, 100)  # Conservative estimate
            
            # Extrapolate to full year
            # Most conferences publish once a year, so sample month ≈ total
            # Add small buffer for workshops/late additions
            if venue_lower == 'aaai':
                # AAAI has main track + workshops, can be larger
                estimated_total = int(sample_count * 1.2)
            else:
                # Other venues are smaller, mostly single track
                estimated_total = int(sample_count * 1.1)
            
            total_time = timer.time() - start_time
            self.logger.info(f"Estimated {estimated_total} papers for {venue} {year} (sample: {sample_count}) in {total_time:.2f}s")
            return estimated_total
            
        except Exception as e:
            total_time = timer.time() - start_time
            self.logger.debug(f"Failed to estimate count for {venue} {year} after {total_time:.2f}s: {e}")
            
            # Return reasonable defaults based on historical conference sizes
            venue_defaults = {
                'aaai': 1500,   # Large conference with workshops
                'aies': 100,    # Smaller specialized conference  
                'hcomp': 150,   # Medium workshop
                'icwsm': 300,   # Medium conference
            }
            
            default_count = venue_defaults.get(venue_lower, 500)
            self.logger.debug(f"Using default estimate: {default_count}")
            return default_count