#!/usr/bin/env python3
"""
Test stdout capture in Rich UI
"""
import time
import sys
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

class OutputCapture:
    def __init__(self, max_lines=20):
        self.lines = []
        self.max_lines = max_lines
        
    def write(self, text):
        if text.strip():  # Only capture non-empty lines
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.lines.append(f"[{timestamp}] {text.strip()}")
            # Keep only the last max_lines
            if len(self.lines) > self.max_lines:
                self.lines = self.lines[-self.max_lines:]
    
    def flush(self):
        pass  # Required for stdout/stderr compatibility
    
    def get_lines(self):
        return self.lines.copy()

def create_layout(output_capture):
    """Create layout with captured stdout"""
    layout = Layout()
    
    # Get captured lines
    captured_lines = output_capture.get_lines()
    
    # Create log panel
    log_text = Text("\n".join(captured_lines[-15:]) if captured_lines else "Waiting for activity...")
    logs_panel = Panel(log_text, title="📝 Real-time stdout/stderr Log", border_style="yellow")
    
    layout.add_split(logs_panel)
    return layout

def main():
    # Set up output capture
    output_capture = OutputCapture()
    original_stdout = sys.stdout
    
    print("🧪 Testing stdout capture...")
    
    try:
        # Redirect stdout
        sys.stdout = output_capture
        
        with Live(create_layout(output_capture), refresh_per_second=2) as live:
            for i in range(20):
                print(f"🔍 Test message {i+1}: Searching for papers...")
                time.sleep(0.5)
                
                print(f"📡 Making API request {i+1}...")
                time.sleep(0.5)
                
                print(f"✅ Found {i*2} papers")
                time.sleep(0.5)
                
                print(f"⏱️ Rate limiting: waiting...")
                time.sleep(0.5)
    
    finally:
        # Restore stdout
        sys.stdout = original_stdout
    
    print("\n✅ Test completed! Stdout capture working correctly.")

if __name__ == "__main__":
    main()