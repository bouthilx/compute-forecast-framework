#!/usr/bin/env python3
"""
Test script for Google Scholar browser automation setup
"""

import logging
from scholarly import scholarly, ProxyGenerator
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import random

def setup_browser_automation():
    """Configure scholarly library to use browser automation"""
    
    # Configure Chrome options for automation
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Randomize user agent
    user_agents = [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    try:
        # Create browser instance
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Try to configure scholarly to use the browser via internal methods
        pg = ProxyGenerator()
        
        # Check if the ProxyGenerator has webdriver setup methods
        if hasattr(pg, '_get_chrome_webdriver'):
            # Use internal method to set up webdriver
            pg._webdriver = driver
            scholarly.use_proxy(pg)
            print("✅ Browser automation configured successfully (internal method)")
            return driver
        else:
            print("⚠️  No direct webdriver support found, trying without proxy")
            driver.quit()
            return None
            
    except Exception as e:
        print(f"❌ Browser setup failed: {e}")
        return None

def test_captcha_detection():
    """Test CAPTCHA detection and handling"""
    
    print("\n🔍 Testing Google Scholar connectivity with browser automation...")
    
    try:
        # Test simple search
        search_query = "machine learning test"
        search_results = scholarly.search_pubs(search_query)
        
        # Try to get first result
        first_result = next(search_results, None)
        
        if first_result:
            print("✅ Successfully retrieved search results")
            print(f"   Title: {first_result.get('title', 'N/A')[:80]}...")
            print(f"   Citations: {first_result.get('num_citations', 'N/A')}")
            return True
        else:
            print("⚠️  Search returned no results")
            return False
            
    except Exception as e:
        error_msg = str(e).lower()
        if 'captcha' in error_msg:
            print(f"🛑 CAPTCHA detected: {e}")
            return False
        else:
            print(f"❌ Other error: {e}")
            return False

def test_rate_limiting():
    """Test different rate limiting approaches"""
    
    print("\n⏱️  Testing rate limiting strategies...")
    
    delays = [1.5, 2.0, 3.0, 4.0]
    
    for delay in delays:
        print(f"   Testing {delay}s delay...")
        try:
            # Random delay between 1.5x and 2x the base delay
            actual_delay = random.uniform(delay * 1.5, delay * 2.0)
            time.sleep(actual_delay)
            
            # Simple test search
            search_results = scholarly.search_pubs("reinforcement learning")
            result = next(search_results, None)
            
            if result:
                print(f"   ✅ Success with {delay}s base delay")
            else:
                print(f"   ⚠️  No results with {delay}s delay")
                
        except Exception as e:
            if 'captcha' in str(e).lower():
                print(f"   🛑 CAPTCHA with {delay}s delay: {e}")
            else:
                print(f"   ❌ Error with {delay}s delay: {e}")

def main():
    """Main test function"""
    
    print("🚀 Google Scholar Browser Automation Test")
    print("=" * 50)
    
    # Setup browser automation
    driver = setup_browser_automation()
    
    if not driver:
        print("❌ Cannot proceed without browser automation")
        return
    
    try:
        # Test basic connectivity
        success = test_captcha_detection()
        
        if success:
            # Test rate limiting if basic test succeeds
            test_rate_limiting()
        
        print("\n📊 Test Summary:")
        print(f"   Browser automation: {'✅ Working' if driver else '❌ Failed'}")
        print(f"   CAPTCHA avoidance: {'✅ Working' if success else '❌ Still blocked'}")
        
    finally:
        # Clean up
        if driver:
            driver.quit()
            print("\n🧹 Browser session closed")

if __name__ == "__main__":
    main()