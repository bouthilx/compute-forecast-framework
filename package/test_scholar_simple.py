#!/usr/bin/env python3
"""
Simple test of current Google Scholar functionality
"""

from scholarly import scholarly
import time

def test_basic_search():
    """Test basic Google Scholar search without browser automation"""
    
    print("🔍 Testing basic Google Scholar search...")
    
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
            time.sleep(2.0)  # 2 second delay between requests
        
        if results:
            print(f"✅ Successfully retrieved {len(results)} results")
            return True
        else:
            print("⚠️  Search returned no results")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        
        if 'captcha' in error_msg.lower():
            print("🛑 CAPTCHA detected - need browser automation")
        elif 'blocked' in error_msg.lower():
            print("🛑 IP blocked - need different approach") 
        elif 'timeout' in error_msg.lower():
            print("⏱️  Timeout - might need longer delays")
        
        return False

def main():
    print("🚀 Simple Google Scholar Test")
    print("=" * 40)
    
    success = test_basic_search()
    
    print(f"\n📊 Result: {'✅ Working' if success else '❌ Blocked/Failed'}")

if __name__ == "__main__":
    main()