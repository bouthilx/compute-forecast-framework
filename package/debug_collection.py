#!/usr/bin/env python3
"""
Debug version of collection with guaranteed display time
"""
import sys
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

def main():
    console = Console()
    
    # Test 1: Basic console output
    console.print("🔧 DEBUG: Starting collection debug...", style="bold yellow")
    
    # Test 2: Basic panel
    panel = Panel("Debug test content", title="Debug Panel")
    console.print(panel)
    
    # Test 3: Check if Live works with minimal content
    console.print("🔧 DEBUG: Testing Live display...")
    
    try:
        def create_debug_panel():
            current_time = datetime.now().strftime("%H:%M:%S")
            text = Text()
            text.append(f"DEBUG MODE - Time: {current_time}\n", style="bold green")
            text.append("If you can see this updating, the dashboard works!\n")
            text.append("Press Ctrl+C to stop\n")
            text.append("\nWaiting for collection to start...\n")
            return Panel(text, title="🔧 Collection Debug", border_style="red")
        
        console.print("Starting Live display (will run for 30 seconds minimum)...")
        
        with Live(create_debug_panel(), refresh_per_second=2) as live:
            for i in range(60):  # Run for 30 seconds minimum
                time.sleep(0.5)
                live.update(create_debug_panel())
                
                if i == 10:
                    # Simulate some activity
                    console.print("🔧 DEBUG: 5 seconds passed - Live is working!")
    
    except KeyboardInterrupt:
        console.print("\n🔧 DEBUG: Interrupted by user")
    except Exception as e:
        console.print(f"\n🔧 DEBUG: Error in Live display: {e}")
        import traceback
        traceback.print_exc()
    
    console.print("\n🔧 DEBUG: Test completed")
    return True

if __name__ == "__main__":
    print("🔧 DEBUG: Starting debug collection...")
    print("🔧 DEBUG: If you see a red panel updating with time, the dashboard works!")
    print("🔧 DEBUG: Press Ctrl+C to stop early")
    print()
    
    main()
    
    print("\n🔧 DEBUG: Debug session completed")
    print("🔧 DEBUG: If you saw the updating panel, your environment supports Rich dashboards!")