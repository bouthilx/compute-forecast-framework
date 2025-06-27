#!/usr/bin/env python3
"""
Test Google Scholar with proper browser automation setup
"""

from scholarly import scholarly, ProxyGenerator
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
import time
import random

def setup_chrome_automation():
    """Set up Chrome browser automation for scholarly"""
    try:
        # Configure Chrome options
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Randomize user agent
        user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Create driver
        service = ChromeService('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Configure scholarly to use Chrome
        pg = ProxyGenerator()
        pg._webdriver = driver
        scholarly.use_proxy(pg)
        
        print("✅ Chrome automation configured successfully")
        return driver, pg
        
    except Exception as e:
        print(f"❌ Chrome setup failed: {e}")
        return None, None

def setup_firefox_automation():
    """Set up Firefox browser automation for scholarly"""
    try:
        # Configure Firefox options
        firefox_options = FirefoxOptions()
        firefox_options.add_argument("--headless")
        firefox_options.binary_location = "/usr/bin/firefox"
        
        # Create driver with explicit binary location
        service = FirefoxService("/snap/bin/geckodriver")
        driver = webdriver.Firefox(service=service, options=firefox_options)
        
        # Configure scholarly to use Firefox
        pg = ProxyGenerator()
        pg._webdriver = driver
        scholarly.use_proxy(pg)
        
        print("✅ Firefox automation configured successfully")
        return driver, pg
        
    except Exception as e:
        print(f"❌ Firefox setup failed: {e}")
        return None, None

def test_scholar_with_browser(driver, pg):
    """Test Google Scholar search with browser automation"""
    
    print("\n🔍 Testing Google Scholar with browser automation...")
    
    try:
        # Test simple search
        search_query = "machine learning 2024"
        print(f"   Query: {search_query}")
        
        search_results = scholarly.search_pubs(search_query)
        
        # Try to get first few results
        results = []
        for i, result in enumerate(search_results):
            if i >= 3:  # Just get first 3 results
                break
            results.append(result)
            print(f"   Result {i+1}: {result.get('title', 'N/A')[:60]}...")
            
            # Randomized delay
            delay = random.uniform(2.0, 4.0)
            time.sleep(delay)
        
        if results:
            print(f"✅ Successfully retrieved {len(results)} results with browser automation")
            return True
        else:
            print("⚠️  Search returned no results")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error with browser automation: {error_msg}")
        
        if 'captcha' in error_msg.lower():
            print("🛑 Still getting CAPTCHA - may need longer delays or different approach")
        
        return False

def main():
    """Main test function"""
    
    print("🚀 Google Scholar Browser Automation Test (Fixed)")
    print("=" * 60)
    
    driver = None
    pg = None
    
    try:
        # Try Chrome first
        print("Trying Chrome automation...")
        driver, pg = setup_chrome_automation()
        
        if not driver:
            print("Trying Firefox automation...")
            driver, pg = setup_firefox_automation()
        
        if not driver:
            print("❌ Could not set up any browser automation")
            return
        
        # Test the configured browser
        success = test_scholar_with_browser(driver, pg)
        
        print(f"\n📊 Final Result: {'✅ Working' if success else '❌ Still blocked'}")
        
    finally:
        # Clean up
        if driver:
            driver.quit()
            print("\n🧹 Browser session closed")

if __name__ == "__main__":
    main()