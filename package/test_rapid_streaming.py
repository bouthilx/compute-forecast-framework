#!/usr/bin/env python3
"""
Test rapid message bursts and smooth scrolling
"""
import time
import sys
from datetime import datetime
from collection_realtime_final import StreamingLogCapture, create_layout, CollectionTracker
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

def test_rapid_bursts_with_dashboard():
    """Test rapid message bursts in live dashboard"""
    console = Console()
    console.print("🧪 Testing rapid message bursts with live dashboard", style="bold green")
    
    # Initialize tracker
    tracker = CollectionTracker()
    
    # Redirect stdout
    original_stdout = sys.stdout
    sys.stdout = tracker.log_capture
    
    try:
        print("🚀 Starting rapid burst test...")
        print("📊 Dashboard should show smooth scrolling")
        
        with Live(create_layout(tracker), refresh_per_second=8) as live:  # High refresh rate
            
            # Test 1: Rapid API simulation
            print("🧪 Test 1: Simulating rapid API responses...")
            for i in range(15):
                print(f"📡 API call {i+1}: Searching papers...")
                print(f"📄 Found paper: 'Research Paper {i+1}'")
                print(f"✅ Added to collection")
                time.sleep(0.2)  # 200ms intervals - very rapid
            
            print("⏸️ Pause between tests...")
            time.sleep(2)
            
            # Test 2: Burst of errors/warnings
            print("🧪 Test 2: Simulating error bursts...")
            for i in range(10):
                if i % 3 == 0:
                    print(f"⚠️ Rate limit warning {i+1}")
                elif i % 3 == 1:
                    print(f"❌ API error {i+1}: Connection timeout")
                else:
                    print(f"🔄 Retry attempt {i+1}")
                time.sleep(0.1)  # 100ms - even faster
            
            print("⏸️ Pause between tests...")
            time.sleep(2)
            
            # Test 3: Mixed activity simulation
            print("🧪 Test 3: Mixed activity simulation...")
            activities = [
                "🔍 Searching Computer Vision papers...",
                "📡 API request to Semantic Scholar...",
                "📄 Processing 10 results...",
                "➕ Added: 'Deep Learning in Medical Imaging'",
                "⏱️ Rate limiting: waiting 3 seconds...",
                "🔍 Searching NLP papers...",
                "📡 API request to OpenAlex...",
                "📄 Processing 8 results...",
                "➕ Added: 'Transformer Networks for Text'",
                "📊 Progress: 305/800 papers collected",
                "💾 Saving progress to file...",
                "✅ Progress saved successfully",
                "🔍 Searching Graph Learning papers...",
                "📡 Multiple API calls in progress...",
                "📄 Large batch processing...",
                "➕ Added multiple papers to collection",
                "🎯 Target progress: 38% complete"
            ]
            
            for activity in activities:
                print(activity)
                time.sleep(0.3)  # 300ms intervals
            
            print("✅ All rapid burst tests completed!")
            print("📊 Dashboard should show smooth scrolling behavior")
            print("🎯 Logs should display most recent 25 lines")
            
            # Show final state
            time.sleep(3)
    
    except KeyboardInterrupt:
        print("⚠️ Test interrupted by user")
    finally:
        sys.stdout = original_stdout
    
    console.print("\\n✅ Rapid burst test completed!")
    console.print("📊 Check that logs scrolled smoothly and showed recent activity")

if __name__ == "__main__":
    test_rapid_bursts_with_dashboard()