from scholarly import scholarly
import time
import random
from datetime import datetime
from typing import List, Optional
try:
    from .base import BaseCitationSource
    from ..models import Paper, Author, CollectionQuery, CollectionResult
    from ...core.config import ConfigManager
    from ...core.logging import setup_logging
except ImportError:
    # Fallback for direct execution
    from base import BaseCitationSource
    from models import Paper, Author, CollectionQuery, CollectionResult
    from core.config import ConfigManager
    from core.logging import setup_logging

# Enhanced browser automation imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class GoogleScholarSource(BaseCitationSource):
    """Google Scholar citation data source implementation with browser automation"""
    
    def __init__(self):
        config_manager = ConfigManager()
        config = config_manager.get_citation_config('google_scholar')
        super().__init__(config.__dict__)
        self.logger = setup_logging()
        
        # Browser automation settings
        self.use_browser = getattr(config, 'use_browser_automation', True)
        self.manual_captcha = getattr(config, 'manual_captcha_intervention', True)
        self.driver = None
        self.session_start_time = None
        self.request_count = 0
        self.max_requests_per_session = 30
        
        # Enhanced rate limiting
        self.base_rate_limit = max(self.rate_limit, 3.0)  # Minimum 3 seconds
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0"
        ]
    
    def _setup_browser(self, browser_type: str = "chrome") -> bool:
        """Set up browser with anti-detection measures"""
        
        if not self.use_browser:
            return False
        
        try:
            if browser_type == "chrome":
                options = ChromeOptions()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
                
                service = ChromeService('/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=options)
                
            elif browser_type == "firefox":
                options = FirefoxOptions()
                options.add_argument("--headless")
                options.set_preference("general.useragent.override", random.choice(self.user_agents))
                
                service = FirefoxService("/snap/bin/geckodriver")
                self.driver = webdriver.Firefox(service=service, options=options)
            
            # Configure timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.session_start_time = time.time()
            self.request_count = 0
            
            self.logger.info(f"{browser_type.title()} browser initialized for CAPTCHA handling")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up {browser_type} browser: {e}")
            return False
    
    def _should_refresh_session(self) -> bool:
        """Check if we should refresh the browser session"""
        
        if not self.driver or not self.session_start_time:
            return True
        
        if self.request_count >= self.max_requests_per_session:
            self.logger.info(f"Refreshing session after {self.request_count} requests")
            return True
        
        if time.time() - self.session_start_time > 3600:  # 1 hour
            self.logger.info("Refreshing session after 1 hour")
            return True
        
        return False
    
    def _enhanced_rate_limit(self):
        """Apply enhanced rate limiting with randomization"""
        
        # Base delay plus random jitter
        delay = random.uniform(self.base_rate_limit * 0.8, self.base_rate_limit * 1.5)
        
        # Add extra delay if we've made many requests recently
        if self.request_count > 15:
            delay += random.uniform(2.0, 4.0)
        
        self.logger.debug(f"Rate limit delay: {delay:.1f}s")
        time.sleep(delay)
    
    def _check_for_captcha_in_scholarly(self) -> bool:
        """Check if scholarly library encountered a CAPTCHA"""
        
        try:
            # Try a simple test search to see if we get CAPTCHA
            test_results = scholarly.search_pubs('test query')
            next(test_results)
            return False  # No CAPTCHA if we got results
        except Exception as e:
            error_msg = str(e).lower()
            if 'captcha' in error_msg or 'sorry' in error_msg or 'unusual traffic' in error_msg:
                return True
            return False
        
    def search_papers(self, query: CollectionQuery) -> CollectionResult:
        """Search Google Scholar for papers matching query with enhanced CAPTCHA handling"""
        
        papers = []
        errors = []
        
        try:
            # Validate query parameters
            if not query.domain:
                raise ValueError("Domain is required for search")
            if query.year < 1950 or query.year > datetime.now().year:
                raise ValueError(f"Invalid year: {query.year}")
            
            # Set up browser session if needed
            if self.use_browser and self._should_refresh_session():
                if not self._setup_browser("chrome"):
                    if not self._setup_browser("firefox"):
                        self.logger.warning("Browser setup failed, continuing with basic scholarly")
                        self.use_browser = False
            
            # Construct search query
            search_query = self._build_search_query(query)
            self.logger.info(f"Google Scholar search query: {search_query}")
            
            # Check for CAPTCHA before starting
            if self.use_browser and self._check_for_captcha_in_scholarly():
                self.logger.warning("CAPTCHA detected before search - using enhanced rate limiting")
                time.sleep(random.uniform(30, 60))  # Long wait before retry
            
            search_results = scholarly.search_pubs(search_query)
            
            for i, result in enumerate(search_results):
                if i >= query.max_results:
                    break
                
                try:
                    paper = self._parse_scholar_result(result, query)
                    if paper and paper.citations >= query.min_citations:
                        papers.append(paper)
                        self.logger.debug(f"Found paper: {paper.title[:60]}...")
                        
                except Exception as e:
                    errors.append(f"Failed to parse result {i}: {e}")
                    self.logger.warning(f"Parse error for result {i}: {e}")
                
                # Enhanced rate limiting
                self._enhanced_rate_limit()
                
                if self.use_browser:
                    self.request_count += 1
        
        except ValueError as e:
            errors.append(f"Invalid query parameters: {e}")
            self.logger.error(f"Query validation failed: {e}")
        except Exception as e:
            error_msg = str(e)
            if 'captcha' in error_msg.lower():
                # Handle CAPTCHA error
                errors.append(f"CAPTCHA detected: {e}")
                self.logger.error(f"Google Scholar CAPTCHA detected: {e}")
                
                if self.manual_captcha:
                    self.logger.info("Manual CAPTCHA intervention may be required")
                    # In production, could pause and allow manual intervention
                    
            else:
                errors.append(f"Search failed: {e}")
                self.logger.error(f"Google Scholar search failed: {e}")
        
        return CollectionResult(
            papers=papers,
            query=query,
            source="google_scholar",
            collection_timestamp=datetime.now().isoformat(),
            success_count=len(papers),
            failed_count=len(errors),
            errors=errors
        )
    
    def _build_search_query(self, query: CollectionQuery) -> str:
        """Build Google Scholar search query string"""
        parts = []
        
        if query.venue:
            # Google Scholar doesn't always recognize venue names consistently
            # Use more general search terms for better results
            if query.venue.upper() == 'NEURIPS':
                # Try multiple variants for NeurIPS
                parts.append('("Neural Information Processing Systems" OR "NeurIPS" OR "NIPS")')
            elif query.venue in ['ICML', 'ICLR']:
                parts.append(f'source:"{query.venue}"')
            else:
                parts.append(f'venue:"{query.venue}"')
        
        if query.keywords:
            keyword_str = ' OR '.join(query.keywords[:3])  # Limit keywords
            parts.append(f'({keyword_str})')
        
        parts.append(f'year:{query.year}')
        
        return ' '.join(parts)
    
    def _parse_scholar_result(self, result: dict, query: CollectionQuery) -> Paper:
        """Parse Google Scholar result into Paper object"""
        
        if not result:
            raise ValueError("Empty result provided")
        
        # Google Scholar returns data in 'bib' field
        bib = result.get('bib', {})
        title = bib.get('title', '').strip()
        if not title:
            raise ValueError("Paper title is required")
        
        # Parse authors with validation
        authors = []
        author_list = bib.get('author', [])
        if isinstance(author_list, list):
            for author_data in author_list:
                # In Google Scholar, authors are simple strings, not dicts
                if isinstance(author_data, str):
                    author_name = author_data.strip()
                    if author_name:  # Only add authors with names
                        author = Author(
                            name=author_name,
                            affiliation='',  # Google Scholar doesn't provide affiliation in search results
                            author_id=''  # No author ID in search results
                        )
                        authors.append(author)
                elif isinstance(author_data, dict):
                    author_name = author_data.get('name', '').strip()
                    if author_name:  # Only add authors with names
                        author = Author(
                            name=author_name,
                            affiliation=author_data.get('affiliation', '').strip(),
                            author_id=author_data.get('scholar_id', '').strip()
                        )
                        authors.append(author)
        
        # Validate and clean data
        citations = result.get('num_citations', 0)
        if not isinstance(citations, int) or citations < 0:
            citations = 0
        
        # Extract year from bib
        pub_year = bib.get('pub_year', 'NA')
        if pub_year == 'NA' or not pub_year.isdigit():
            year = query.year  # Use query year if not available
        else:
            year = int(pub_year)
        
        # Extract venue from bib
        venue = bib.get('venue', '').strip()
        if not venue:
            venue = query.venue or ''
        
        # Extract abstract from bib
        abstract = bib.get('abstract', '').strip()
        
        # Get PDF URL if available
        urls = []
        if result.get('eprint_url'):
            urls.append(result.get('eprint_url'))
        elif result.get('pub_url'):
            urls.append(result.get('pub_url'))
        
        # Create paper object
        paper = Paper(
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            citations=citations,
            abstract=abstract,
            urls=urls,
            source="google_scholar",
            collection_timestamp=datetime.now().isoformat(),
            mila_domain=query.domain
        )
        
        return paper
    
    def get_paper_details(self, paper_id: str) -> Paper:
        """Get detailed paper information by Google Scholar ID"""
        try:
            # Get detailed paper info from Google Scholar
            search_query = scholarly.search_pubs(paper_id)
            paper_data = next(search_query, None)
            
            if not paper_data:
                raise ValueError(f"Paper with ID {paper_id} not found")
            
            # Fill in missing details if needed
            filled_paper = scholarly.fill(paper_data)
            
            # Parse authors
            authors = []
            for author_data in filled_paper.get('author', []):
                author = Author(
                    name=author_data.get('name', ''),
                    affiliation=author_data.get('affiliation', ''),
                    author_id=author_data.get('scholar_id', '')
                )
                authors.append(author)
            
            # Create detailed paper object
            paper = Paper(
                title=filled_paper.get('title', ''),
                authors=authors,
                venue=filled_paper.get('venue', ''),
                year=filled_paper.get('year', 0),
                citations=filled_paper.get('num_citations', 0),
                abstract=filled_paper.get('abstract', ''),
                doi=filled_paper.get('doi', ''),
                urls=[filled_paper.get('url', '')] if filled_paper.get('url') else [],
                source="google_scholar",
                collection_timestamp=datetime.now().isoformat()
            )
            
            return paper
            
        except Exception as e:
            self.logger.error(f"Failed to get paper details for {paper_id}: {e}")
            raise
    
    def close_browser(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser session closed")
            except:
                pass
            finally:
                self.driver = None
                self.session_start_time = None
                self.request_count = 0
    
    def test_connectivity(self) -> bool:
        """Test Google Scholar connectivity"""
        try:
            # Simple test search
            test_results = scholarly.search_pubs('machine learning')
            next(test_results)  # Try to get first result
            return True
        except Exception as e:
            self.logger.error(f"Google Scholar connectivity test failed: {e}")
            return False
            return False