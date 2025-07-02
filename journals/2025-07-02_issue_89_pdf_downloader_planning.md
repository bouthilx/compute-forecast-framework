# Journal Entry: 2025-07-02 - Issue #89 PDF Downloader Planning

## Analysis Summary

### Issue Overview
**Issue #89**: [PDF-Download] Implement Simple PDF Download Manager
- **Objective**: Create a simple, robust PDF downloader with caching, retry logic, and progress tracking
- **Time Estimate**: S (2-3h) - Straightforward implementation
- **Priority**: High
- **Milestone**: 02-B PDF Handling Pipeline
- **Worker**: W2

### Current Codebase Assessment

#### Existing Infrastructure
1. **PDF Discovery Module** (`src/pdf_discovery/`)
   - Already has `PDFRecord` model with all necessary fields
   - Discovery framework exists for finding PDFs
   - Deduplication engine exists

2. **Data Models** (`src/pdf_discovery/core/models.py`)
   - `PDFRecord` dataclass with:
     - `paper_id`: Unique identifier
     - `pdf_url`: URL to download
     - `source`: Where it was discovered
     - Additional metadata fields

3. **Dependencies**
   - `requests` already available for HTTP downloads
   - Need to add `tqdm` for progress bars
   - Python 3.13+ requirement

#### Missing Components
1. **PDF Download Module** (`src/pdf_download/`)
   - Directory doesn't exist yet
   - Need to create downloader.py and cache_manager.py

2. **Progress Tracking**
   - `tqdm` not in dependencies yet

### Implementation Plan

#### 1. Directory Structure
```
src/pdf_download/
├── __init__.py
├── downloader.py      # Main SimplePDFDownloader class
└── cache_manager.py   # Caching utilities
```

#### 2. Core Components
- **SimplePDFDownloader**: Main class handling downloads
- **Cache Manager**: Handle local file caching by paper_id
- **Retry Logic**: Exponential backoff with 3 attempts
- **Batch Processing**: ThreadPoolExecutor for parallel downloads
- **Validation**: Content-type and file size checks

#### 3. Integration Points
- Use existing `PDFRecord` model from pdf_discovery
- Integrate with discovery results
- Follow existing code patterns (dataclasses, type hints)

### Success Criteria Verification
- ✅ 95%+ download success rate (implement robust retry)
- ✅ No re-download of cached files (check cache first)
- ✅ Clear progress indication (tqdm for batch operations)
- ✅ Graceful error handling (comprehensive try/except)
- ✅ <5s average download time (parallel downloads)

### Next Steps
1. Create directory structure
2. Implement SimplePDFDownloader class
3. Add caching logic
4. Implement retry mechanism
5. Add batch download functionality
6. Create comprehensive tests
7. Update dependencies (add tqdm)

### Time Allocation
- Setup & structure: 15 minutes
- Core downloader implementation: 45 minutes
- Caching logic: 30 minutes
- Retry & batch processing: 45 minutes
- Testing: 30 minutes
- Documentation & cleanup: 15 minutes
**Total**: ~3 hours (within S estimate)

### Dependencies & Blockers
- **Dependencies**: None - can start immediately
- **Blocks**: PDF Parser (#92) - they will need our download functionality