#!/usr/bin/env python3
"""
Simple test of Google Scholar with enhanced rate limiting
"""

from scholarly import scholarly
import time
import random

def test_scholar_with_enhanced_rate_limiting():
    """Test Google Scholar with enhanced rate limiting to avoid CAPTCHAs"""
    
    print("🚀 Google Scholar Enhanced Rate Limiting Test")
    print("=" * 60)
    
    # Configure very conservative rate limiting
    base_delay = 5.0  # 5 second base delay
    max_results = 5   # Small number of results
    
    print(f"📋 Configuration:")
    print(f"   Base delay: {base_delay}s")
    print(f"   Max results: {max_results}")
    print(f"   Strategy: Conservative rate limiting + randomization")
    
    try:
        # Test simple search with heavy rate limiting
        search_query = "machine learning"
        print(f"\n🔍 Searching: {search_query}")
        
        search_results = scholarly.search_pubs(search_query)
        
        papers_found = []
        
        for i, result in enumerate(search_results):
            if i >= max_results:
                break
            
            try:
                title = result.get('title', 'N/A')
                citations = result.get('num_citations', 0)
                
                papers_found.append({
                    'title': title,
                    'citations': citations
                })
                
                print(f"   ✅ Result {i+1}: {title[:60]}... (citations: {citations})")
                
                # Aggressive rate limiting with randomization
                if i < max_results - 1:  # Don't delay after last result
                    # Random delay between 5-10 seconds
                    delay = random.uniform(base_delay, base_delay * 2)
                    print(f"   ⏱️  Waiting {delay:.1f}s before next request...")
                    time.sleep(delay)
                
            except Exception as e:
                print(f"   ⚠️  Failed to parse result {i+1}: {e}")
        
        # Results summary
        success = len(papers_found) > 0
        print(f"\n📊 Results Summary:")
        print(f"   Papers retrieved: {len(papers_found)}")
        print(f"   Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        if success:
            print("\n🎉 Conservative rate limiting approach is working!")
            print("💡 Recommendations:")
            print("   - Use 5-10 second delays between requests")
            print("   - Limit to small batches (5-10 papers at a time)")
            print("   - Add randomization to avoid patterns")
            print("   - Consider daily quotas to stay under radar")
        else:
            print("\n🔧 Still encountering issues. Consider:")
            print("   - Even longer delays (10-20 seconds)")
            print("   - Using VPN or different IP")
            print("   - Manual CAPTCHA solving")
        
        return success
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Search failed: {error_msg}")
        
        if 'captcha' in error_msg.lower():
            print("🛑 CAPTCHA detected even with conservative rate limiting")
            print("💡 Solutions:")
            print("   1. Wait 30-60 minutes before retry")
            print("   2. Use manual browser intervention")
            print("   3. Consider alternative data sources")
        elif 'cannot fetch' in error_msg.lower():
            print("🛑 Connection blocked")
            print("💡 This IP may be temporarily blocked by Google Scholar")
            
        return False

def main():
    """Run the test"""
    
    success = test_scholar_with_enhanced_rate_limiting()
    
    print(f"\n📋 Final Assessment:")
    if success:
        print("✅ Google Scholar can work with proper rate limiting")
        print("🔧 Ready to integrate into main collection system")
    else:
        print("❌ Google Scholar requires manual intervention or alternative approach")
        print("🔧 Consider using Semantic Scholar as primary source")

if __name__ == "__main__":
    main()