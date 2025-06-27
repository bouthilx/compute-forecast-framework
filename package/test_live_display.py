#!/usr/bin/env python3
"""
Test Rich Live display
"""
import time
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

def main():
    console = Console()
    console.print("🧪 Testing Rich Live display...")
    
    def generate_content(counter):
        text = Text()
        text.append(f"Counter: {counter}\n", style="bold green")
        text.append(f"Time: {time.strftime('%H:%M:%S')}\n")
        text.append("This should update every second!")
        return Panel(text, title="Live Test")
    
    try:
        print("Starting Live display test (will run for 10 seconds)...")
        
        with Live(generate_content(0), refresh_per_second=2) as live:
            for i in range(10):
                time.sleep(1)
                live.update(generate_content(i + 1))
        
        print("Live display test completed!")
        return True
        
    except Exception as e:
        print(f"Error with Live display: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Rich Live display is working!")
    else:
        print("❌ Rich Live display failed!")