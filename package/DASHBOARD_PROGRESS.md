# Real-Time Dashboard Implementation Plan

## Technical Plan for Real-Time Log Streaming

### 1. **Core Architecture**
- Keep the existing Rich Layout from `collection_with_progress.py` (progress bars + domain statistics + logs panel)
- Replace the current `OutputCapture` class with a thread-safe, streaming-capable log handler
- Use a circular buffer to store log lines efficiently
- Implement proper stdout/stderr redirection that feeds directly into the Rich panel

### 2. **Log Streaming Implementation**
```python
class StreamingLogCapture:
    def __init__(self, max_lines=50):
        self.lines = collections.deque(maxlen=max_lines)  # Thread-safe circular buffer
        self.lock = threading.Lock()  # Thread safety for concurrent access
        
    def write(self, text):
        with self.lock:
            if text.strip():
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Millisecond precision
                self.lines.append(f"[{timestamp}] {text.strip()}")
    
    def get_recent_lines(self):
        with self.lock:
            return list(self.lines)  # Return copy for thread safety
```

### 3. **Rich Panel Integration**
- Create a custom `Text` object that gets refreshed from the log buffer
- Use `Live.update()` method to push new log content to the panel
- Set refresh rate to 4-8 times per second for near real-time feel
- Ensure the logs panel scrolls automatically (show most recent lines)

### 4. **stdout/stderr Redirection Strategy**
- Redirect `sys.stdout` and `sys.stderr` to the `StreamingLogCapture` instance
- Maintain original streams for emergency output (errors outside Rich context)
- Use context managers to ensure proper restoration of streams

### 5. **Thread-Safe Updates**
- Collection operations run in main thread, writing to redirected stdout
- Rich Live display updates at regular intervals (4-8 Hz)
- Log buffer is thread-safe and handles concurrent reads/writes
- No blocking operations in the display refresh cycle

### 6. **Layout Structure**
```
┌─ Progress Bars Panel (top, fixed height) ─┐
├─ Domain Statistics Panels (middle, grid) ─┤  
└─ Real-time Activity Log (bottom, expand) ─┘
```

### 7. **Key Implementation Details**
- **Buffering**: Use `collections.deque` with `maxlen` for O(1) operations
- **Timing**: Millisecond timestamps for precise log timing
- **Scrolling**: Always show the most recent 25-30 lines in the panel
- **Performance**: Minimize string operations in the tight refresh loop
- **Error Handling**: Graceful fallback if Rich display fails

### 8. **Integration Points**
- Replace all `tracker.log()` calls with regular `print()` statements
- The redirected stdout automatically feeds into the Rich panel
- Keep existing collection logic unchanged
- Maintain the same progress bar and statistics updates

### 9. **Real-Time Characteristics**
- **Latency**: < 250ms from print() to panel display
- **Refresh Rate**: 4-8 FPS for smooth updates without CPU overhead
- **Capacity**: 50 log lines in memory (auto-scroll older lines out)
- **Thread Safety**: Full concurrent access support

### 10. **Testing Strategy**
- Start with a simple test that prints messages every 500ms
- Verify logs appear in the panel with proper timestamps
- Test with rapid message bursts (simulating API responses)
- Ensure smooth scrolling and no display artifacts

This approach leverages Rich's Live display capabilities while providing true streaming logs through proper stdout redirection. The key insight is using a thread-safe circular buffer that Rich can read from at regular intervals, creating the real-time effect you want.