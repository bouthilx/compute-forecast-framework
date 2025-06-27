#!/usr/bin/env python3
"""
Test Google Scholar using scholarly's internal webdriver methods
"""

from scholarly import scholarly, ProxyGenerator
import time
import random

def setup_scholarly_with_internal_browser():
    """Use scholarly's internal browser setup methods"""
    
    print("🔧 Setting up browser automation using scholarly's internal methods...")
    
    try:
        # Create proxy generator
        pg = ProxyGenerator()
        
        # Try to use internal Firefox webdriver method
        try:
            print("   Trying internal Firefox setup...")
            driver = pg._get_firefox_webdriver()
            if driver:
                print("   ✅ Firefox webdriver created successfully")
                scholarly.use_proxy(pg)
                return driver, pg
        except Exception as e:
            print(f"   ❌ Firefox failed: {e}")
        
        # Try to use internal Chrome webdriver method  
        try:
            print("   Trying internal Chrome setup...")
            driver = pg._get_chrome_webdriver()
            if driver:
                print("   ✅ Chrome webdriver created successfully")
                scholarly.use_proxy(pg)
                return driver, pg
        except Exception as e:
            print(f"   ❌ Chrome failed: {e}")
        
        print("   ❌ Both browsers failed")
        return None, None
        
    except Exception as e:
        print(f"❌ Browser setup failed: {e}")
        return None, None

def test_scholar_search(max_results=3):
    """Test Google Scholar search with configured browser"""
    
    print(f"\n🔍 Testing Google Scholar search (max {max_results} results)...")
    
    try:
        # Test search with a simple query
        search_query = "reinforcement learning"
        print(f"   Query: {search_query}")
        
        search_results = scholarly.search_pubs(search_query)
        
        results = []
        for i, result in enumerate(search_results):
            if i >= max_results:
                break
            
            try:
                title = result.get('title', 'N/A')[:60]
                citations = result.get('num_citations', 'N/A')
                print(f"   Result {i+1}: {title}... (citations: {citations})")
                results.append(result)
                
                # Randomized delay between requests
                delay = random.uniform(3.0, 6.0)
                print(f"   Waiting {delay:.1f}s before next request...")
                time.sleep(delay)
                
            except Exception as e:
                print(f"   ⚠️  Failed to parse result {i+1}: {e}")
        
        if results:
            print(f"✅ Successfully retrieved {len(results)} results")
            return True
        else:
            print("⚠️  No results retrieved")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Search failed: {error_msg}")
        
        if 'captcha' in error_msg.lower():
            print("🛑 CAPTCHA still detected - may need different approach")
        elif 'too many requests' in error_msg.lower():
            print("🛑 Rate limited - need longer delays")
        
        return False

def main():
    """Main test function"""
    
    print("🚀 Google Scholar Test - Internal Browser Methods")
    print("=" * 60)
    
    driver = None
    
    try:
        # Set up browser automation
        driver, pg = setup_scholarly_with_internal_browser()
        
        if not driver:
            print("\n❌ Cannot proceed without browser automation")
            return
        
        # Test search functionality
        success = test_scholar_search(max_results=2)  # Start small
        
        print(f"\n📊 Final Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        if success:
            print("🎉 Google Scholar browser automation is working!")
        else:
            print("🔄 May need further rate limiting adjustments")
        
    finally:
        # Clean up browser
        if driver:
            try:
                driver.quit()
                print("\n🧹 Browser session closed cleanly")
            except:
                print("\n🧹 Browser cleanup completed")

if __name__ == "__main__":
    main()