# Download Command Implementation Plan

**Date**: 2025-01-21
**Task**: Detailed implementation plan for `cf download` command

## Executive Summary

The `cf download` command is responsible for downloading PDFs using URLs discovered by the consolidate command, with Google Drive storage and local caching capabilities. This plan outlines the implementation approach, breaking down the work into manageable components.

## Command Overview

### Purpose
Download PDFs from URLs discovered during consolidation, managing:
- Parallel downloads with rate limiting
- Google Drive storage integration
- Local caching with permanent storage
- Retry mechanisms with exponential backoff
- Resume capability for interrupted downloads

### Core Usage
```bash
cf download --papers papers.json
cf download --papers papers.json --retry-failed
cf download --papers papers.json --resume --parallel 10
```

## Additional Design Considerations

### Operation Flow per Paper

1. **Check Local Cache**
   - No progress bar needed (instant check)
   - If exists, mark as complete

2. **Download from Source**
   - Show progress bar: "Downloading"
   - Chunked download with real-time progress
   - Validate content (PDF vs HTML)

3. **Save to Local Cache**
   - No progress bar (usually instant)
   - Atomic write to avoid corruption

4. **Upload to Google Drive**
   - Show progress bar: "Uploading to Drive"
   - Use resumable upload API
   - Handle quota limits gracefully

5. **Special Case: Download from Drive**
   - If local cache missing but Drive has file
   - Show progress bar: "Downloading from Drive"
   - Used during resume or cache recovery

### Progress Bar Lifecycle

- Progress bars appear when operation starts
- Update continuously during transfer
- Disappear immediately on completion/failure
- Maximum concurrent bars = --parallel setting
- Failed operations log error and free up slot for next paper

## Implementation Components

### 1. Command Structure & CLI Integration

**File**: `compute_forecast/cli/commands/download.py`

```python
# Command structure
@click.command()
@click.option('--papers', required=True, type=click.Path(exists=True))
@click.option('--parallel', default=5, type=int)
@click.option('--rate-limit', type=float)
@click.option('--timeout', default=30, type=int)
@click.option('--retry-failed', is_flag=True)
@click.option('--max-retries', default=3, type=int)
@click.option('--retry-delay', default=5, type=int)
@click.option('--exponential-backoff', is_flag=True)
@click.option('--resume', is_flag=True)
@click.option('--no-progress', is_flag=True)
def download(papers, parallel, rate_limit, timeout, retry_failed,
            max_retries, retry_delay, exponential_backoff, resume, no_progress):
    """Download PDFs using URLs discovered by consolidate command."""
```

### 2. Core Download Orchestrator

**File**: `compute_forecast/orchestration/download_orchestrator.py`

Key responsibilities:
- Load papers with PDF URLs from input file
- Filter papers based on download status and retry flags
- Manage parallel download workers
- Track progress and handle resumption
- Coordinate between local cache and Google Drive storage

### 3. Storage Backend Integration

**Files**:
- `compute_forecast/storage/google_drive.py` - Google Drive API integration
- `compute_forecast/storage/local_cache.py` - Local file cache management
- `compute_forecast/storage/storage_manager.py` - Unified storage interface

Key features:
- Check if PDF already exists in cache/storage
- Upload to Google Drive with progress tracking using resumable uploads
- Download from Google Drive with progress tracking using chunked downloads
- Maintain local cache for fast access
- Handle storage credentials from .env configuration
- Progress callbacks integration for all transfer operations

### 4. Download Worker Implementation

**File**: `compute_forecast/workers/pdf_downloader.py`

Key responsibilities:
- Download individual PDFs with timeout handling
- Implement retry logic with exponential backoff
- Validate downloaded content (not HTML error pages)
- Update paper metadata with download status
- Handle rate limiting between requests

### 5. Progress Tracking & Resume

**Files**:
- `compute_forecast/monitoring/download_progress.py` - Progress tracking
- `compute_forecast/state/download_state.py` - State persistence

#### Progress Bar System Design

**Visual Layout**:
```
[Log messages flow here - scrolling region]
[2025-01-21 10:15:23] INFO: Starting download of 150 papers...
[2025-01-21 10:15:24] SUCCESS: Downloaded paper_123.pdf (2.3 MB)
[2025-01-21 10:15:25] ERROR: Failed to download paper_456.pdf - 404 Not Found
...

[Fixed progress bar region - bottom of terminal]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paper 1: arxiv_2024_123 [####      ] 42% • 2.3/5.5 MB • 1.2 MB/s • Downloading
Paper 2: neurips_2024_456 [#######   ] 73% • 4.1/5.6 MB • 2.1 MB/s • Downloading
Paper 3: icml_2024_789 [##        ] 15% • 0.8/5.2 MB • 0.9 MB/s • Uploading to Drive
Paper 4: cvpr_2024_321 [#####     ] 52% • 3.2/6.1 MB • 1.8 MB/s • Downloading from Drive
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall: 45/150 papers [30%] • Success: 42 • Failed: 3 • ETA: 00:12:34
```

**Key Features**:

1. **Two-Level Progress System**:
   - **Global Progress Bar**: Fixed at the very bottom showing overall completion
   - **Per-Paper Progress Bars**: Above global bar, one for each concurrent download
   - Progress bars disappear when individual papers complete
   - Maximum of N progress bars visible (matching --parallel setting)

2. **Rich Console Integration**:
   ```python
   from rich.console import Console
   from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
   from rich.live import Live
   from rich.layout import Layout
   from rich.panel import Panel

   # Create layout with scrolling log region and fixed progress region
   layout = Layout()
   layout.split_column(
       Layout(name="logs", ratio=1),  # Scrolling log area
       Layout(name="progress", size=parallel + 2)  # Fixed progress area
   )
   ```

3. **Progress Bar Components**:
   - **Per-Paper Progress**:
     - Paper ID (truncated if needed)
     - Progress bar with percentage
     - Current/Total size in MB
     - Transfer speed in MB/s
     - Operation type: "Downloading", "Uploading to Drive", "Downloading from Drive"
     - Auto-remove on completion

   - **Global Progress**:
     - Current/Total papers with percentage
     - Success count in green
     - Failed count in red
     - Estimated time remaining

4. **Log Message Handling**:
   - All log messages flow in the upper scrolling region
   - Console.print() for log messages (not logger.info)
   - Color coding: INFO (white), SUCCESS (green), ERROR (red), WARNING (yellow)
   - Timestamps included in log messages

5. **State Management**:
   - Track active downloads with their progress
   - Update progress bars in real-time using callbacks
   - Clean up completed progress bars
   - Maintain statistics for global progress

**Implementation Example**:
```python
class DownloadProgressManager:
    def __init__(self, total_papers: int, max_parallel: int):
        self.console = Console()
        self.total_papers = total_papers
        self.max_parallel = max_parallel
        self.active_operations = {}
        self.completed = 0
        self.failed = 0

    def start_operation(self, paper_id: str, total_size: int, operation_type: str):
        """Register a new operation with its own progress bar"""
        task = self.add_task(
            f"Paper: {paper_id[:20]} • {operation_type}",
            total=total_size
        )
        self.active_operations[paper_id] = {
            'task': task,
            'operation': operation_type
        }

    def update_progress(self, paper_id: str, transferred: int, speed: float):
        """Update progress for a specific operation"""
        if paper_id in self.active_operations:
            op = self.active_operations[paper_id]
            self.update(op['task'],
                       completed=transferred,
                       description=f"Paper: {paper_id[:20]} • {speed:.1f} MB/s • {op['operation']}")

    def complete_operation(self, paper_id: str, success: bool):
        """Mark operation as complete and remove progress bar"""
        if paper_id in self.active_operations:
            op = self.active_operations[paper_id]
            self.remove_task(op['task'])
            del self.active_operations[paper_id]

        if success:
            self.completed += 1
            self.log_success(f"Completed {op['operation']} for {paper_id}")
        else:
            self.failed += 1
            self.log_error(f"Failed {op['operation']} for {paper_id}")

        self.update_global_progress()
```

**Google Drive Progress Integration**:
```python
class GoogleDriveStorage:
    def upload_with_progress(self, file_path: Path, paper_id: str,
                           progress_callback: Callable):
        """Upload file to Google Drive with progress tracking"""
        file_size = file_path.stat().st_size

        # Initialize progress for upload
        progress_callback.start_operation(paper_id, file_size, "Uploading to Drive")

        # Use resumable upload for progress tracking
        media = MediaFileUpload(str(file_path), resumable=True)
        request = self.service.files().create(
            body={'name': file_path.name, 'parents': [self.folder_id]},
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress_callback.update_progress(
                    paper_id,
                    int(status.resumable_progress),
                    status.resumable_progress / status.total_size / elapsed_time
                )

    def download_with_progress(self, file_id: str, paper_id: str,
                             output_path: Path, progress_callback: Callable):
        """Download file from Google Drive with progress tracking"""
        # Get file metadata for size
        file_metadata = self.service.files().get(fileId=file_id).execute()
        file_size = int(file_metadata.get('size', 0))

        # Initialize progress for download
        progress_callback.start_operation(paper_id, file_size, "Downloading from Drive")

        request = self.service.files().get_media(fileId=file_id)
        with open(output_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress_callback.update_progress(
                        paper_id,
                        int(status.resumable_progress),
                        status.resumable_progress / elapsed_time
                    )
```

6. **Resume Capability**:
   - State saved to `.cf_state/download/download_progress.json`
   - Tracks completed, failed, and pending papers
   - On resume, skip completed papers and retry failed ones if --retry-failed

### 6. Error Handling & Retry Logic

**File**: `compute_forecast/utils/retry_handler.py`

Key features:
- Configurable retry attempts
- Exponential backoff strategy
- Different handling for various error types:
  - Network timeouts
  - 404 errors (no retry)
  - 503 errors (retry with backoff)
  - SSL errors

## Implementation Steps

### Step 1: CLI Command Setup (2-3 hours)
1. Create `compute_forecast/cli/commands/download.py`
2. Add command to CLI registry in `compute_forecast/cli/main.py`
3. Implement basic argument parsing and validation
4. Add configuration loading from .env file

### Step 2: Storage Backend (4-6 hours)
1. Implement Google Drive client wrapper
   - Authentication using service account credentials
   - Upload functionality with folder organization
   - Check if file exists functionality
2. Implement local cache manager
   - Cache directory structure
   - File existence checking
   - Cache path generation from paper ID
3. Create unified storage manager interface

### Step 3: Download Orchestrator (6-8 hours)
1. Implement paper loading and filtering logic
   - Load papers from JSON
   - Filter by PDF URL presence
   - Filter by existing downloads (unless retry-failed)
2. Implement parallel download coordination
   - Worker pool management
   - Rate limiting implementation
   - Progress aggregation
3. Add resume functionality
   - State saving after each batch
   - State loading on resume
   - Graceful interruption handling

### Step 4: Download Worker (4-6 hours)
1. Implement core download logic
   - HTTP client with timeout and chunked downloads for progress
   - Content validation (PDF vs HTML)
   - Temporary file handling
2. Add retry mechanism
   - Configurable retry attempts
   - Exponential backoff calculation
   - Error classification
3. Integrate with storage backends
   - Save to local cache first
   - Upload to Google Drive with progress tracking
   - Update paper metadata
   - Handle all three operation types with progress bars:
     - PDF download from source URL
     - Upload to Google Drive
     - Download from Google Drive (if needed)

### Step 5: Progress & Monitoring (4-5 hours)
1. Implement progress tracking system
   - Create DownloadProgressManager class
   - Implement two-level progress bar system:
     - Global progress bar (fixed at bottom)
     - Per-paper progress bars (above global, auto-remove on completion)
   - Set up Rich console with Layout for log scrolling region
   - Real-time download speed calculation
   - ETA calculation for overall progress
2. Integrate progress callbacks with download workers
   - Pass progress callback to each worker
   - Update progress on chunk downloads
   - Handle progress bar lifecycle (create/update/remove)
3. Add logging and error reporting
   - Route all logs through Rich console
   - Color-coded log messages
   - Summary statistics on completion
   - Failed downloads report with reasons

### Step 6: Testing & Integration (4-6 hours)
1. Unit tests for each component
   - Mock HTTP responses
   - Mock storage backends
   - Test error scenarios
2. Integration tests
   - End-to-end download flow
   - Resume functionality
   - Retry mechanisms
3. Manual testing with real papers

## Technical Considerations

### Configuration Management
- Google Drive credentials from `.env`:
  - `GOOGLE_DRIVE_FOLDER_ID`
  - `GOOGLE_DRIVE_CREDENTIALS_PATH`
- Local cache configuration:
  - `LOCAL_CACHE_DIR` (default: `.cache/pdfs/`)
- Processing defaults:
  - `DEFAULT_PARALLEL_WORKERS` (default: 5)
  - `DEFAULT_RATE_LIMIT` (requests/second)

### Data Flow
1. Input: `papers.json` with PDF URLs from consolidation
2. Processing:
   - Check local cache first
   - If not cached, download from source URL (with progress)
   - Save to local cache
   - Upload to Google Drive (with progress)
3. Storage: Local cache + Google Drive
4. Output: Updated `papers.json` with download status and storage locations

### Error Recovery
- Network errors: Retry with backoff
- Storage errors: Log and continue
- Invalid PDFs: Mark as failed, no retry
- Interrupted downloads: Resume from checkpoint

### Performance Optimization
- Parallel downloads with configurable workers
- Rate limiting to avoid overwhelming servers
- Local cache to avoid re-downloads
- Batch uploads to Google Drive

## Dependencies

### Existing Components
- `compute_forecast.core.config.ConfigManager` - Configuration loading
- `compute_forecast.monitoring` - Progress tracking utilities
- `compute_forecast.utils.logging` - Logging infrastructure

### New Dependencies
- `httpx` or `requests` - HTTP client library
- `google-api-python-client` - Google Drive API
- `tenacity` - Retry logic implementation
- `rich` - Progress bar display

## Success Criteria

1. **Reliability**: Successfully downloads 95%+ of available PDFs
2. **Performance**: Processes 100 papers in under 10 minutes (with good connection)
3. **Robustness**: Handles interruptions gracefully with full resume capability
4. **Storage**: Seamless integration with Google Drive and local cache
5. **User Experience**:
   - Clear progress indication for all operations (download, upload, cache)
   - Separate progress bars for concurrent operations
   - Clean separation of logs and progress display

## Risk Mitigation

1. **API Rate Limits**: Configurable rate limiting with sensible defaults
2. **Large Files**: Streaming downloads with progress indication
3. **Storage Failures**: Fallback to local-only mode if Google Drive fails
4. **Network Issues**: Comprehensive retry logic with exponential backoff
5. **Data Loss**: Atomic operations and checkpoint saving

## Timeline Estimate

Total estimated time: 26-36 hours (3-4 days)

1. Day 1: CLI setup + Storage backend (6-9 hours)
2. Day 2: Download orchestrator + Worker (10-14 hours)
3. Day 3: Progress/monitoring + Testing (8-11 hours)
4. Day 4: Integration, bug fixes, documentation (2-3 hours)

This plan provides a comprehensive approach to implementing the download command while maintaining the project's focus on pragmatic, research-oriented development.
