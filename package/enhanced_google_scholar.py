#!/usr/bin/env python3
"""
Enhanced Google Scholar source with custom browser automation
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import random
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode, quote_plus

class EnhancedGoogleScholarSource:
    """Enhanced Google Scholar source with browser automation for CAPTCHA avoidance"""
    
    def __init__(self, rate_limit: float = 3.0):
        self.rate_limit = rate_limit
        self.driver = None
        self.session_start_time = None
        self.request_count = 0
        self.max_requests_per_session = 50  # Limit requests per browser session
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"
        ]
    
    def _setup_browser(self, browser_type: str = "chrome") -> bool:
        """Set up browser with anti-detection measures"""
        
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
            
            print(f"✅ {browser_type.title()} browser initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to set up {browser_type} browser: {e}")
            return False
    
    def _should_refresh_session(self) -> bool:
        """Check if we should refresh the browser session"""
        
        if not self.driver or not self.session_start_time:
            return True
        
        # Refresh after too many requests
        if self.request_count >= self.max_requests_per_session:
            print(f"🔄 Refreshing session after {self.request_count} requests")
            return True
        
        # Refresh after too much time (1 hour)
        if time.time() - self.session_start_time > 3600:
            print("🔄 Refreshing session after 1 hour")
            return True
        
        return False
    
    def _refresh_session(self):
        """Refresh the browser session"""
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        # Try Chrome first, then Firefox
        if not self._setup_browser("chrome"):
            if not self._setup_browser("firefox"):
                raise Exception("Could not initialize any browser")
    
    def _wait_rate_limit(self):
        """Apply rate limiting with randomization"""
        
        # Base delay plus random jitter
        delay = random.uniform(self.rate_limit * 0.8, self.rate_limit * 1.5)
        
        # Add extra delay if we've made many requests recently
        if self.request_count > 20:
            delay += random.uniform(1.0, 3.0)
        
        print(f"   ⏱️  Rate limit delay: {delay:.1f}s")
        time.sleep(delay)
    
    def _check_for_captcha(self, page_source: str) -> bool:
        """Check if the page contains a CAPTCHA"""
        
        captcha_indicators = [
            "captcha",
            "unusual traffic",
            "automated queries",
            "verify you're not a robot",
            "sorry/index"
        ]
        
        page_lower = page_source.lower()
        for indicator in captcha_indicators:
            if indicator in page_lower:
                return True
        return False
    
    def _handle_captcha_manually(self, max_wait_time: int = 300) -> bool:
        """Handle CAPTCHA with manual intervention option"""
        
        print("🛑 CAPTCHA detected!")
        print("Options:")
        print("1. [RECOMMENDED] Wait and retry with longer delays")
        print("2. Manual intervention (opens visible browser)")
        print("3. Abort")
        
        choice = input("Choose option (1/2/3): ").strip()
        
        if choice == "1":
            # Implement exponential backoff
            wait_time = 30
            print(f"⏳ Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
            return True
            
        elif choice == "2":
            print("🖥️  Opening visible browser for manual CAPTCHA solving...")
            print(f"You have {max_wait_time} seconds to solve the CAPTCHA...")
            print("Press Enter when done or Ctrl+C to abort.")
            
            # Switch to non-headless mode
            self._switch_to_visible_browser()
            
            try:
                input("Press Enter when CAPTCHA is solved...")
                return True
            except KeyboardInterrupt:
                print("\n❌ Manual intervention aborted")
                return False
                
        else:
            print("❌ Aborting...")
            return False
    
    def _switch_to_visible_browser(self):
        """Switch to a visible browser for manual CAPTCHA solving"""
        
        current_url = self.driver.current_url if self.driver else None
        
        # Close headless browser
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        # Open visible browser
        try:
            options = ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
            # Note: not adding --headless for manual intervention
            
            service = ChromeService('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=options)
            
            if current_url:
                self.driver.get(current_url)
                
        except Exception as e:
            print(f"Failed to switch to visible browser: {e}")
            # Fall back to headless
            self._setup_browser("chrome")
    
    def search_papers(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google Scholar for papers"""
        
        # Refresh session if needed
        if self._should_refresh_session():
            self._refresh_session()
        
        results = []
        
        try:
            # Build search URL
            search_params = {
                'hl': 'en',
                'q': query,
                'as_vis': '0',
                'as_sdt': '0,33'
            }
            
            base_url = "https://scholar.google.com/scholar"
            search_url = f"{base_url}?{urlencode(search_params)}"
            
            print(f"🔍 Searching: {query}")
            print(f"   URL: {search_url}")
            
            # Apply rate limiting
            self._wait_rate_limit()
            
            # Load the search page
            self.driver.get(search_url)
            self.request_count += 1
            
            # Check for CAPTCHA
            page_source = self.driver.page_source
            if self._check_for_captcha(page_source):
                if not self._handle_captcha_manually():
                    raise Exception("CAPTCHA handling failed or aborted")
                
                # Retry the search after CAPTCHA handling
                print("🔄 Retrying search after CAPTCHA handling...")
                self.driver.get(search_url)
                page_source = self.driver.page_source
                
                # Check again for CAPTCHA
                if self._check_for_captcha(page_source):
                    raise Exception("CAPTCHA still present after handling")
            
            # Wait for results to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-lid]"))
                )
            except TimeoutException:
                print("⚠️  No results found or page load timeout")
                return results
            
            # Extract paper results
            paper_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-lid]")
            
            for i, element in enumerate(paper_elements[:max_results]):
                try:
                    paper_data = self._extract_paper_data(element)
                    if paper_data:
                        results.append(paper_data)
                        print(f"   ✅ Result {len(results)}: {paper_data.get('title', 'N/A')[:60]}...")
                    
                    # Small delay between extractions
                    if i < len(paper_elements) - 1:
                        time.sleep(random.uniform(0.5, 1.5))
                        
                except Exception as e:
                    print(f"   ⚠️  Failed to extract paper {i+1}: {e}")
            
            print(f"✅ Successfully extracted {len(results)} papers")
            return results
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            raise
    
    def _extract_paper_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract paper data from a result element"""
        
        try:
            paper_data = {}
            
            # Extract title
            title_elem = element.find_element(By.CSS_SELECTOR, "h3 a")
            paper_data['title'] = title_elem.text.strip()
            paper_data['url'] = title_elem.get_attribute('href')
            
            # Extract authors and venue info
            meta_elem = element.find_element(By.CSS_SELECTOR, ".gs_a")
            meta_text = meta_elem.text
            paper_data['meta'] = meta_text
            
            # Try to parse authors and venue from meta text
            # Format is usually: "Author1, Author2 - Venue, Year - Publisher"
            if ' - ' in meta_text:
                parts = meta_text.split(' - ')
                paper_data['authors_raw'] = parts[0].strip()
                if len(parts) > 1:
                    venue_year = parts[1].strip()
                    paper_data['venue_year'] = venue_year
            
            # Extract citation count
            try:
                cited_elem = element.find_element(By.CSS_SELECTOR, ".gs_fl a")
                if "Cited by" in cited_elem.text:
                    citations_text = cited_elem.text
                    citations_match = re.search(r'Cited by (\d+)', citations_text)
                    if citations_match:
                        paper_data['citations'] = int(citations_match.group(1))
            except:
                paper_data['citations'] = 0
            
            # Extract snippet/abstract
            try:
                snippet_elem = element.find_element(By.CSS_SELECTOR, ".gs_rs")
                paper_data['snippet'] = snippet_elem.text.strip()
            except:
                paper_data['snippet'] = ""
            
            return paper_data
            
        except Exception as e:
            print(f"   Error extracting paper data: {e}")
            return None
    
    def test_connectivity(self) -> bool:
        """Test if we can connect to Google Scholar"""
        
        try:
            # Refresh session for clean test
            self._refresh_session()
            
            # Try a simple search
            results = self.search_papers("test", max_results=1)
            
            return len(results) > 0
            
        except Exception as e:
            print(f"Connectivity test failed: {e}")
            return False
    
    def close(self):
        """Clean up browser resources"""
        
        if self.driver:
            try:
                self.driver.quit()
                print("🧹 Browser session closed")
            except:
                pass


def main():
    """Test the enhanced Google Scholar functionality"""
    
    print("🚀 Enhanced Google Scholar Test")
    print("=" * 50)
    
    scholar = EnhancedGoogleScholarSource(rate_limit=4.0)
    
    try:
        # Test connectivity
        print("Testing connectivity...")
        if not scholar.test_connectivity():
            print("❌ Connectivity test failed")
            return
        
        print("✅ Connectivity test passed")
        
        # Test actual search
        print("\nTesting search functionality...")
        results = scholar.search_papers("machine learning 2024", max_results=3)
        
        print(f"\n📊 Retrieved {len(results)} papers:")
        for i, paper in enumerate(results, 1):
            print(f"{i}. {paper.get('title', 'N/A')}")
            print(f"   Citations: {paper.get('citations', 0)}")
            print(f"   Authors: {paper.get('authors_raw', 'N/A')}")
            print()
        
        print("🎉 Enhanced Google Scholar is working!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        scholar.close()


if __name__ == "__main__":
    main()