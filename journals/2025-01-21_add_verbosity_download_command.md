# Add Verbosity to Download Command

**Date**: 2025-01-21
**Time**: 17:25
**Task**: Add verbosity argument to download command for better debugging

## Implementation

Added verbosity support to the `cf download` command following the same pattern as the consolidate command:

### 1. CLI Argument
```python
verbose: int = typer.Option(
    0,
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity level (-v for INFO, -vv for DEBUG)",
),
```

### 2. Logging Configuration
```python
# Configure logging based on verbosity
log_level = logging.WARNING
if verbose >= 2:
    log_level = logging.DEBUG
elif verbose >= 1:
    log_level = logging.INFO

# Configure root logger with stderr handler for Rich compatibility
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
```

### 3. Enhanced Logging Throughout Components

Added detailed logging to key components:

#### Download Command (`download.py`):
- Paper loading statistics
- URL extraction details
- Paper filtering information

#### Download Orchestrator (`download_orchestrator.py`):
- Parallel worker initialization
- Task submission details
- Success/failure logging

#### PDF Downloader (`pdf_downloader.py`):
- HTTP request details
- Response status codes
- Content type and size information
- File validation steps
- Storage operations

#### Storage Manager (`storage_manager.py`):
- Cache operations
- Google Drive upload attempts
- Storage location confirmations

#### Progress Manager (`simple_download_progress.py`):
- Logs both to console and standard logger
- Maintains Rich display while providing verbose output

## Usage Examples

```bash
# Normal operation (WARNING level only)
cf download --papers papers.json

# INFO level logging (-v)
cf download --papers papers.json -v

# DEBUG level logging (-vv)
cf download --papers papers.json -vv
```

## Testing Results

With `-vv` (DEBUG) level, the output now shows:
- Paper loading: "Loaded 4 papers from file, Found 4 with PDF URLs, 0 without"
- HTTP details: "Making HTTP request to URL", "HTTP response status: 404"
- Storage operations: "Saving PDF to storage", "Google Drive not configured"
- Download flow: Step-by-step progression including cache hits
- Detailed error information for failed downloads

The verbose output is sent to stderr so it doesn't interfere with Rich progress bars on stdout.

## Benefits

1. **Debugging**: Detailed visibility into download process
2. **Error Analysis**: Clear understanding of why downloads fail (HTTP 404, validation errors, etc.)
3. **Performance Monitoring**: See cache hits vs actual downloads
4. **Storage Debugging**: Track local cache vs Google Drive operations
5. **URL Validation**: Verify which URLs are being used for downloads

This significantly improves the ability to diagnose download issues and understand the system behavior during operation.
