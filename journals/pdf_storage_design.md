# PDF Storage Design - Google Drive Integration

**Date**: 2025-07-02  
**Issue**: PDF storage without repository bloat  
**Time**: ~3 hours

## Analysis Request
User requested simple options for storing PDFs without taking up repository space, mentioning they have Google Suite available.

## Approach
Designed and implemented a Google Drive storage solution with the following components:

### 1. Architecture
- **GoogleDriveStore**: Core Google Drive API integration
- **PDFManager**: Caching layer with Drive backend
- **PDFDiscoveryStorage**: Integration with existing discovery framework
- **Metadata tracking**: JSON file to track Drive IDs and paper metadata

### 2. Key Features
- Simple API for store/retrieve operations
- Local caching to minimize API calls
- Automatic deduplication
- Batch processing support
- Progress tracking
- Team sharing via Google Drive

### 3. Implementation Details
Created complete implementation including:
- Google Drive service account integration
- Local cache management with auto-cleanup
- Migration scripts for existing PDFs
- Setup wizard for easy configuration
- Integration with PDF discovery framework

## Outcomes

### Delivered Components
1. `src/pdf_storage/` module with:
   - `google_drive_store.py`: Drive API operations
   - `pdf_manager.py`: Cache management
   - `discovery_integration.py`: Discovery framework integration

2. Scripts:
   - `setup_google_drive.py`: Interactive setup wizard
   - `migrate_pdfs_to_drive.py`: Migration tool for existing PDFs

3. Documentation:
   - Design document with architecture overview
   - README with quick start guide
   - Example usage patterns

### Benefits
- **Zero repository bloat**: PDFs stored externally
- **Simple setup**: ~30 minutes with interactive wizard
- **Minimal dependencies**: Just Google API client
- **Pragmatic approach**: Focus on "good enough" for research project
- **Time-boxed**: 2-3 hour implementation

## Alternative Options Considered
1. **Git LFS**: Simple but still uses repo quota
2. **Reference-only**: Store URLs/DOIs only
3. **AWS S3**: More complex setup
4. **Local NAS**: Requires infrastructure

## Recommendation
Google Drive is optimal for this use case:
- Free 15GB storage (sufficient for ~3000 PDFs)
- Simple Python API
- Team collaboration built-in
- No infrastructure required
- Aligns with existing Google Suite

## Next Steps
1. Run `pip install -r requirements_pdf_storage.txt`
2. Execute `python scripts/setup_google_drive.py`
3. Optional: Migrate existing PDFs with migration script
4. Integrate with PDF discovery pipeline

The solution prioritizes simplicity and quick implementation while solving the repository bloat concern effectively.