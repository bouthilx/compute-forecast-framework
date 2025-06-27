#!/usr/bin/env python3
"""
Simple dashboard test to verify display
"""
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

def main():
    console = Console()
    console.print("🧪 Simple Dashboard Test")
    
    def create_panel(counter):
        text = Text()
        text.append(f"Dashboard Update #{counter}\n", style="bold green")
        text.append(f"Time: {time.strftime('%H:%M:%S')}\n")
        text.append("📊 Papers collected: 207\n")
        text.append("🎯 Target: 800\n")
        text.append("📈 Progress: 25.9%\n")
        text.append("\nRecent Activity:\n", style="bold yellow")
        text.append("🔍 Searching for 'deep learning'...\n")
        text.append("📡 Making API request...\n")
        text.append("✅ Found 5 papers\n")
        text.append("➕ Added new paper: 'Deep Learning for CV'\n")
        text.append(f"⏱️ Update cycle: {counter}/10")
        
        return Panel(text, title="📝 Paper Collection Dashboard", border_style="blue")
    
    print("Starting Live dashboard (10 updates)...")
    
    with Live(create_panel(0), refresh_per_second=1) as live:
        for i in range(1, 11):
            time.sleep(1)
            live.update(create_panel(i))
    
    print("Dashboard test completed!")

if __name__ == "__main__":
    main()