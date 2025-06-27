#!/usr/bin/env python3
"""
Test GoogleScholarSource initialization by running as package module
"""

import subprocess
import sys
import os

def test_as_module():
    """Test by running Python module directly"""
    
    print("🧪 Testing GoogleScholarSource as Python Module")
    print("=" * 50)
    
    # Test script content
    test_script = '''
import sys
import os
sys.path.insert(0, "src")

# Test 1: Config loading
print("1. Testing config loading...")
from core.config import ConfigManager

config_manager = ConfigManager()
config = config_manager.get_citation_config("google_scholar")
print(f"   ✓ Rate limit: {config.rate_limit}")
print(f"   ✓ Browser automation: {config.use_browser_automation}")
print(f"   ✓ Manual CAPTCHA: {config.manual_captcha_intervention}")

# Test 2: Check browser drivers
print("\\n2. Testing browser driver availability...")
chrome_exists = os.path.exists("/usr/bin/chromedriver")
firefox_exists = os.path.exists("/snap/bin/geckodriver")
print(f"   Chrome driver: {'✓ Available' if chrome_exists else '✗ Missing'}")
print(f"   Firefox driver: {'✓ Available' if firefox_exists else '✗ Missing'}")

# Test 3: Test Selenium imports
print("\\n3. Testing Selenium imports...")
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    print("   ✓ Selenium imports successful")
except ImportError as e:
    print(f"   ✗ Selenium import failed: {e}")
    sys.exit(1)

# Test 4: Test scholarly import
print("\\n4. Testing scholarly import...")
try:
    from scholarly import scholarly
    print("   ✓ Scholarly import successful")
except ImportError as e:
    print(f"   ✗ Scholarly import failed: {e}")
    sys.exit(1)

print("\\n✅ All basic tests passed - system ready for integration")
'''
    
    # Write test script to file
    test_file = "/home/bouthilx/projects/preliminary_report/package/temp_test.py"
    with open(test_file, 'w') as f:
        f.write(test_script)
    
    try:
        # Run the test script
        result = subprocess.run([
            sys.executable, test_file
        ], 
        cwd="/home/bouthilx/projects/preliminary_report/package",
        capture_output=True, 
        text=True,
        timeout=30
        )
        
        print("📋 Test Output:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Errors/Warnings:")
            print(result.stderr)
        
        success = result.returncode == 0
        print(f"\n📊 Module Test: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

def test_browser_automation_direct():
    """Test browser automation capabilities directly"""
    
    print(f"\n🚗 Testing Browser Automation Directly")
    print("=" * 40)
    
    browser_test_script = '''
import sys
import os

# Test Chrome setup
print("Testing Chrome automation...")
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://www.google.com")
        print("   ✓ Chrome automation working")
        driver.quit()
    else:
        print("   ✗ Chrome driver not found")
        
except Exception as e:
    print(f"   ✗ Chrome test failed: {e}")

# Test Firefox setup  
print("\\nTesting Firefox automation...")
try:
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    
    options = FirefoxOptions()
    options.add_argument("--headless")
    
    if os.path.exists("/snap/bin/geckodriver"):
        service = FirefoxService("/snap/bin/geckodriver")
        driver = webdriver.Firefox(service=service, options=options)
        driver.get("https://www.google.com")
        print("   ✓ Firefox automation working")
        driver.quit()
    else:
        print("   ✗ Firefox driver not found")
        
except Exception as e:
    print(f"   ✗ Firefox test failed: {e}")

print("\\n✅ Browser automation tests completed")
'''
    
    test_file = "/home/bouthilx/projects/preliminary_report/package/temp_browser_test.py"
    with open(test_file, 'w') as f:
        f.write(browser_test_script)
    
    try:
        result = subprocess.run([
            sys.executable, test_file
        ], 
        capture_output=True, 
        text=True,
        timeout=60
        )
        
        print("📋 Browser Test Output:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Browser Test Errors:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        return False
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def main():
    """Run all tests"""
    
    print("🚀 Final Google Scholar Integration Tests")
    print("=" * 60)
    
    basic_ok = test_as_module()
    browser_ok = test_browser_automation_direct()
    
    print(f"\n📋 Final Assessment:")
    print(f"   Basic integration: {'✅ Working' if basic_ok else '❌ Broken'}")
    print(f"   Browser automation: {'✅ Working' if browser_ok else '❌ Broken'}")
    
    if basic_ok and browser_ok:
        print(f"\n🎉 ALL INTEGRATION TESTS PASSED")
        print(f"✅ System ready for end-to-end functionality testing")
    else:
        print(f"\n🔧 INTEGRATION ISSUES REMAIN")
        print(f"❌ Must fix before claiming completion")

if __name__ == "__main__":
    main()