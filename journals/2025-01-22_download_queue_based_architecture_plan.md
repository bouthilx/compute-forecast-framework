# Download Queue-Based Architecture Plan

**Date**: 2025-01-22
**Task**: Plan refactoring of download command to use queue-based architecture like consolidate

## Problem

Current download implementation has thread safety issues:
- Multiple worker threads directly modify shared state
- Local cache metadata dictionary gets modified during iteration
- Error: "dictionary changed size during iteration"

## Current Architecture Issues

1. **Shared State Mutations**
   - Workers directly update orchestrator state
   - Multiple threads access storage manager concurrently
   - Cache metadata is not thread-safe

2. **Direct Callbacks**
   - Progress updates happen inline from worker threads
   - State persistence happens from multiple threads
   - Paper status updates modify shared lists/dicts

## Proposed Solution: Queue-Based Architecture

Follow the same pattern as the consolidate command:

### 1. Download Workers (Producers)
- Each worker downloads PDFs independently
- Push results to a thread-safe queue
- No direct state modifications
- Message types:
  ```python
  {
      "type": "download_complete",
      "paper_id": "...",
      "success": True,
      "cached_path": "...",
      "timestamp": "..."
  }
  
  {
      "type": "download_failed", 
      "paper_id": "...",
      "error": "...",
      "permanent": True/False
  }
  
  {
      "type": "progress_update",
      "paper_id": "...",
      "bytes": 1234,
      "speed": 5.2
  }
  ```

### 2. Result Processor (Consumer)
Single thread that:
- Pops messages from queue
- Updates orchestrator state safely
- Updates progress manager
- Persists state periodically
- Updates paper objects with download status
- Handles storage manager metadata updates

### 3. Architecture Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Download       │     │  Download       │     │  Download       │
│  Worker 1       │     │  Worker 2       │     │  Worker N       │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ push                  │ push                  │ push
         ▼                       ▼                       ▼
    ┌────────────────────────────────────────────────────┐
    │              Thread-Safe Queue                      │
    └────────────────────────┬───────────────────────────┘
                             │ pop
                             ▼
                   ┌─────────────────┐
                   │ Result Processor │
                   │   (Single Thread) │
                   └─────────┬───────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
         ┌──────────────┐         ┌──────────────┐
         │ State Update │         │Progress Mgr  │
         │ & Persistence│         │   Update     │
         └──────────────┘         └──────────────┘
```

### 4. Implementation Steps

#### Step 1: Create Message Queue
```python
from queue import Queue
download_queue = Queue()
```

#### Step 2: Modify Workers
- Remove direct state updates
- Push all events to queue
- Keep download logic unchanged

#### Step 3: Create Result Processor
```python
def process_results(queue, orchestrator, progress_mgr):
    while True:
        message = queue.get()
        if message["type"] == "stop":
            break
            
        if message["type"] == "download_complete":
            orchestrator._update_state(...)
            progress_mgr.complete_download(...)
            
        elif message["type"] == "download_failed":
            orchestrator._update_state(...)
            progress_mgr.complete_download(...)
            
        # Periodic state save
        if processed % 10 == 0:
            orchestrator._save_state()
```

#### Step 4: Update Orchestrator
- Start result processor thread
- Modify worker submission to use queue
- Ensure clean shutdown

### 5. Benefits

1. **Thread Safety**: Single point of state modification
2. **Consistency**: No race conditions
3. **Performance**: Workers don't block on state updates  
4. **Reliability**: Centralized error handling
5. **Maintainability**: Clear separation of concerns

### 6. Estimated Changes

- `download_orchestrator.py`: 
  - Add queue initialization
  - Create result processor
  - Modify `_download_single_paper` to push to queue
  - Update `download_papers` to manage processor thread

- `pdf_downloader.py`:
  - No changes needed (already returns results)

- `storage_manager.py`:
  - Ensure thread-safe file operations only
  - Remove any shared state updates

### 7. Testing Considerations

- Verify queue doesn't fill up (backpressure)
- Test graceful shutdown
- Ensure no messages lost
- Validate state consistency

## Timeline

Estimated 2-3 hours to implement:
- 1 hour: Core queue architecture
- 0.5 hour: Update workers and processor
- 0.5 hour: Testing and validation

## Next Steps

1. Implement queue-based message passing
2. Create single-threaded result processor
3. Remove all direct state mutations from workers
4. Test with concurrent downloads
5. Verify thread safety issue is resolved