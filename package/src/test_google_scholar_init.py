#!/usr/bin/env python3
"""
Test GoogleScholarSource initialization within package structure
"""

from data.sources.google_scholar import GoogleScholarSource
from core.config import ConfigManager
import os

def test_initialization():
    """Test GoogleScholarSource initialization"""
    
    print("🧪 Testing GoogleScholarSource Initialization")
    print("=" * 50)
    
    try:
        # Test config loading first
        print("1. Testing config loading...")
        config_manager = ConfigManager()
        config = config_manager.get_citation_config('google_scholar')
        
        print(f"   ✅ Config loaded:")
        print(f"   - Rate limit: {config.rate_limit}")
        print(f"   - Browser automation: {config.use_browser_automation}")
        print(f"   - Manual CAPTCHA: {config.manual_captcha_intervention}")
        
        # Test GoogleScholarSource creation
        print("\n2. Testing GoogleScholarSource creation...")
        scholar = GoogleScholarSource()
        
        print(f"   ✅ GoogleScholarSource created successfully")
        print(f"   - Browser automation: {scholar.use_browser}")
        print(f"   - Manual CAPTCHA: {scholar.manual_captcha}")
        print(f"   - Base rate limit: {scholar.base_rate_limit}")
        print(f"   - Max requests per session: {scholar.max_requests_per_session}")
        
        # Test browser capabilities
        print("\n3. Testing browser driver availability...")
        chrome_available = os.path.exists('/usr/bin/chromedriver')
        firefox_available = os.path.exists('/snap/bin/geckodriver')
        
        print(f"   Chrome driver: {'✅ Available' if chrome_available else '❌ Missing'}")
        print(f"   Firefox driver: {'✅ Available' if firefox_available else '❌ Missing'}")
        
        # Test browser setup (dry run)
        print("\n4. Testing browser setup method...")
        if scholar.use_browser:
            # Test the setup method exists and is callable
            setup_method = getattr(scholar, '_setup_browser', None)
            if setup_method:
                print(f"   ✅ Browser setup method available")
            else:
                print(f"   ❌ Browser setup method missing")
        
        # Clean up
        scholar.close_browser()
        
        print(f"\n📊 Initialization Test: ✅ SUCCESS")
        return True
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_initialization()
    exit(0 if success else 1)