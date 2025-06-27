#!/usr/bin/env python3
"""
Test the enhanced Google Scholar source implementation
"""

import sys
import os
sys.path.append('/home/bouthilx/projects/preliminary_report/package/src')

from data.sources.google_scholar import GoogleScholarSource
from data.models import CollectionQuery
from datetime import datetime

def test_enhanced_google_scholar():
    """Test the enhanced Google Scholar implementation"""
    
    print("🚀 Testing Enhanced Google Scholar Implementation")
    print("=" * 60)
    
    # Create the source
    scholar = GoogleScholarSource()
    
    try:
        # Create a test query
        query = CollectionQuery(
            domain="Machine Learning",
            venue="ICML",
            year=2024,
            keywords=["deep learning"],
            max_results=3,
            min_citations=0
        )
        
        print(f"📋 Test Query:")
        print(f"   Domain: {query.domain}")
        print(f"   Venue: {query.venue}")
        print(f"   Year: {query.year}")
        print(f"   Keywords: {query.keywords}")
        print(f"   Max results: {query.max_results}")
        
        # Test connectivity first
        print("\n🔍 Testing connectivity...")
        if scholar.test_connectivity():
            print("✅ Connectivity test passed")
        else:
            print("❌ Connectivity test failed")
            return
        
        # Perform the search
        print("\n🔍 Performing search...")
        result = scholar.search_papers(query)
        
        # Display results
        print(f"\n📊 Search Results:")
        print(f"   Papers found: {result.success_count}")
        print(f"   Errors: {result.failed_count}")
        print(f"   Source: {result.source}")
        
        if result.errors:
            print(f"\n❌ Errors encountered:")
            for error in result.errors:
                print(f"   - {error}")
        
        if result.papers:
            print(f"\n📚 Papers retrieved:")
            for i, paper in enumerate(result.papers, 1):
                print(f"{i}. {paper.title}")
                print(f"   Authors: {', '.join([a.name for a in paper.authors])}")
                print(f"   Citations: {paper.citations}")
                print(f"   Venue: {paper.venue}")
                print()
        else:
            print("\n⚠️  No papers were retrieved")
        
        # Summary
        success = result.success_count > 0
        print(f"📋 Summary: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        if success:
            print("🎉 Enhanced Google Scholar is working!")
        else:
            print("🔧 May need further adjustments or manual intervention")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        scholar.close_browser()

if __name__ == "__main__":
    test_enhanced_google_scholar()