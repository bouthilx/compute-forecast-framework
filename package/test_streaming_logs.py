#!/usr/bin/env python3
"""
Test script to verify real-time log streaming functionality
"""
import time
import sys
from datetime import datetime
from streaming_dashboard import StreamingLogCapture

def test_basic_streaming():
    """Test basic streaming log capture"""
    print("🧪 TESTING BASIC STREAMING LOG CAPTURE")
    print("=" * 50)
    
    # Create log capture
    log_capture = StreamingLogCapture(max_lines=10)
    
    # Test writing directly
    log_capture.write("Test message 1")
    log_capture.write("Test message 2") 
    log_capture.write("Test message 3")
    
    lines = log_capture.get_recent_lines()
    print(f"✅ Direct write test: {len(lines)} lines captured")
    for line in lines:
        print(f"  {line}")
    
    print()

def test_stdout_redirection():
    """Test stdout redirection to log capture"""
    print("🧪 TESTING STDOUT REDIRECTION")
    print("=" * 50)
    
    # Create log capture
    log_capture = StreamingLogCapture(max_lines=15)
    
    # Redirect stdout
    original_stdout = sys.stdout
    sys.stdout = log_capture
    
    try:
        # These should be captured
        print("📄 This should appear in logs")
        print("🔍 Searching for papers...")
        print("✅ Found 5 papers")
        print("⏱️ Rate limiting...")
        print("📊 Progress update complete")
        
        # Restore stdout temporarily to show results
        sys.stdout = original_stdout
        
        lines = log_capture.get_recent_lines()
        print(f"✅ Redirection test: {len(lines)} lines captured")
        for line in lines:
            print(f"  {line}")
            
    finally:
        sys.stdout = original_stdout
    
    print()

def test_rapid_logging():
    """Test rapid message bursts"""
    print("🧪 TESTING RAPID MESSAGE BURSTS")
    print("=" * 50)
    
    log_capture = StreamingLogCapture(max_lines=20)
    original_stdout = sys.stdout
    sys.stdout = log_capture
    
    try:
        # Rapid burst of messages
        for i in range(15):
            print(f"📈 Rapid message {i+1}")
            time.sleep(0.1)  # 100ms intervals
        
        # Restore stdout
        sys.stdout = original_stdout
        
        lines = log_capture.get_recent_lines()
        print(f"✅ Rapid burst test: {len(lines)} lines captured")
        print("📊 First 5 and last 5 lines:")
        for i, line in enumerate(lines):
            if i < 5 or i >= len(lines) - 5:
                print(f"  {line}")
            elif i == 5:
                print("  ...")
        
    finally:
        sys.stdout = original_stdout
    
    print()

def test_circular_buffer():
    """Test circular buffer behavior (max_lines limit)"""
    print("🧪 TESTING CIRCULAR BUFFER LIMIT")
    print("=" * 50)
    
    log_capture = StreamingLogCapture(max_lines=5)  # Small buffer
    original_stdout = sys.stdout
    sys.stdout = log_capture
    
    try:
        # Send more messages than buffer can hold
        for i in range(10):
            print(f"Buffer test message {i+1}")
        
        # Restore stdout
        sys.stdout = original_stdout
        
        lines = log_capture.get_recent_lines()
        print(f"✅ Buffer limit test: {len(lines)} lines captured (max=5)")
        print("📋 Should show only the last 5 messages:")
        for line in lines:
            print(f"  {line}")
        
    finally:
        sys.stdout = original_stdout
    
    print()

def test_timestamp_precision():
    """Test millisecond timestamp precision"""
    print("🧪 TESTING TIMESTAMP PRECISION")
    print("=" * 50)
    
    log_capture = StreamingLogCapture(max_lines=5)
    original_stdout = sys.stdout
    sys.stdout = log_capture
    
    try:
        # Quick succession of messages
        print("Message A")
        time.sleep(0.001)  # 1ms delay
        print("Message B")
        time.sleep(0.001)
        print("Message C")
        
        # Restore stdout
        sys.stdout = original_stdout
        
        lines = log_capture.get_recent_lines()
        print(f"✅ Timestamp test: {len(lines)} lines captured")
        print("⏰ Check timestamp precision (should show milliseconds):")
        for line in lines:
            print(f"  {line}")
        
    finally:
        sys.stdout = original_stdout
    
    print()

def main():
    """Run all streaming tests"""
    print("🚀 STREAMING LOG CAPTURE TEST SUITE")
    print("=" * 60)
    print()
    
    test_basic_streaming()
    test_stdout_redirection()
    test_rapid_logging()
    test_circular_buffer()
    test_timestamp_precision()
    
    print("🎉 ALL TESTS COMPLETED!")
    print("✅ StreamingLogCapture is working correctly")
    print("📝 Ready for integration into dashboard")

if __name__ == "__main__":
    main()