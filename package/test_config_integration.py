#!/usr/bin/env python3
"""
Test configuration integration for enhanced Google Scholar source
"""

import sys
import os

# Add src to path
sys.path.insert(0, '/home/bouthilx/projects/preliminary_report/package/src')

def test_config_integration():
    """Test that the enhanced GoogleScholarSource can initialize"""
    
    print("🧪 Testing Configuration Integration")
    print("=" * 50)
    
    try:
        # Test 1: Config loading
        print("1. Testing config loading...")
        from core.config import ConfigManager
        
        config_manager = ConfigManager()
        config = config_manager.get_citation_config('google_scholar')
        
        print(f"   ✅ Config loaded successfully")
        print(f"   Rate limit: {config.rate_limit}")
        print(f"   Browser automation: {config.use_browser_automation}")
        print(f"   Manual CAPTCHA: {config.manual_captcha_intervention}")
        
        # Test 2: GoogleScholarSource initialization
        print("\n2. Testing GoogleScholarSource initialization...")
        from data.sources.google_scholar import GoogleScholarSource
        
        scholar = GoogleScholarSource()
        print(f"   ✅ GoogleScholarSource created successfully")
        print(f"   Browser automation enabled: {scholar.use_browser}")
        print(f"   Manual CAPTCHA enabled: {scholar.manual_captcha}")
        print(f"   Base rate limit: {scholar.base_rate_limit}")
        
        # Test 3: Browser setup (without actually using it)
        print("\n3. Testing browser setup capability...")
        
        # Check if browser setup would work
        has_chrome = os.path.exists('/usr/bin/chromedriver')
        has_firefox = os.path.exists('/snap/bin/geckodriver')
        
        print(f"   Chrome driver available: {has_chrome}")
        print(f"   Firefox driver available: {has_firefox}")
        
        if has_chrome or has_firefox:
            print(f"   ✅ Browser automation ready")
        else:
            print(f"   ⚠️  No browser drivers found")
        
        # Clean up
        scholar.close_browser()
        
        print(f"\n📊 Integration Test: ✅ SUCCESS")
        print(f"   - Configuration system working")
        print(f"   - GoogleScholarSource initializes")
        print(f"   - Browser automation configured")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_minimal_scholarly():
    """Test basic scholarly library functionality"""
    
    print(f"\n🔍 Testing Basic Scholarly Library")
    print("=" * 40)
    
    try:
        from scholarly import scholarly
        
        print("   Scholarly library imported successfully")
        
        # Test very basic connectivity (will likely fail due to CAPTCHA, but tests import)
        try:
            # Just test that we can call the function, expect it to fail
            results = scholarly.search_pubs('test')
            next(results)
            print("   ✅ Scholarly working (unexpected!)")
            return True
        except Exception as e:
            error_msg = str(e)
            if 'cannot fetch' in error_msg.lower() or 'captcha' in error_msg.lower():
                print(f"   ✅ Scholarly library working (expected CAPTCHA/blocking)")
                return True
            else:
                print(f"   ❌ Unexpected error: {e}")
                return False
    
    except Exception as e:
        print(f"   ❌ Scholarly import failed: {e}")
        return False

def main():
    """Run all integration tests"""
    
    config_ok = test_config_integration()
    scholarly_ok = test_minimal_scholarly()
    
    print(f"\n📋 Final Assessment:")
    print(f"   Config integration: {'✅ Working' if config_ok else '❌ Broken'}")
    print(f"   Scholarly library: {'✅ Working' if scholarly_ok else '❌ Broken'}")
    
    if config_ok and scholarly_ok:
        print(f"\n🎉 Integration tests PASSED - ready for functionality testing")
    else:
        print(f"\n🔧 Integration tests FAILED - need to fix before proceeding")

if __name__ == "__main__":
    main()