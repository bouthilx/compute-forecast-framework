#!/usr/bin/env python3
"""
Debug dashboard display issues
"""
import sys
import time
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout

def test_basic_rich_display():
    """Test if Rich displays work at all"""
    console = Console()
    console.print("🧪 Testing basic Rich display capabilities")
    
    # Test 1: Basic console output
    console.print("✅ Basic console.print() works", style="green")
    
    # Test 2: Panel display
    panel = Panel("Test panel content", title="Test Panel")
    console.print(panel)
    
    # Test 3: Layout display
    layout = Layout()
    layout.split_column(
        Layout(Panel("Top panel", title="Top")),
        Layout(Panel("Bottom panel", title="Bottom"))
    )
    console.print(layout)
    
    print("🔍 Now testing Live display...")

def test_live_display():
    """Test Rich Live display behavior"""
    console = Console()
    console.print("🧪 Testing Rich Live display")
    
    try:
        with Live(Panel("Initial content", title="Live Test"), refresh_per_second=2) as live:
            for i in range(5):
                content = f"Update {i+1}/5 - {time.strftime('%H:%M:%S')}"
                live.update(Panel(content, title="Live Test"))
                print(f"Updated to: {content}")  # This goes to stderr, should be visible
                time.sleep(1)
        
        console.print("✅ Live display test completed")
        
    except Exception as e:
        console.print(f"❌ Live display error: {e}")

def test_dashboard_components():
    """Test individual dashboard components"""
    console = Console()
    console.print("🧪 Testing dashboard components")
    
    from collection_realtime_final import CollectionTracker, create_layout
    
    # Create tracker
    tracker = CollectionTracker()
    tracker.update_stats(total_papers=305, new_papers=5, api_calls=10)
    
    # Test layout creation
    layout = create_layout(tracker)
    console.print("✅ Layout creation works")
    console.print(layout)

if __name__ == "__main__":
    print("🚀 DEBUGGING DASHBOARD DISPLAY ISSUES")
    print("=" * 50)
    
    test_basic_rich_display()
    print()
    
    test_live_display()
    print()
    
    test_dashboard_components()
    print()
    
    print("🎯 Debug completed - check output above")