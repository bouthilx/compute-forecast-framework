# PDF Storage Design

## Problem
- Need to store 450-580 PDFs (150-180 Mila + 300-400 benchmark papers)
- Average academic PDF: 1-5MB → Total: ~0.5-3GB
- Repository bloat concern with local storage
- Time-boxed implementation (2-4 hours max)

## Recommended Solution: Google Drive with Metadata Tracking

### Architecture Overview
```
Repository (Git)
├── data/
│   └── pdf_metadata.json     # PDF metadata + Drive IDs
├── src/
│   └── pdf_storage/
│       ├── google_drive_store.py
│       └── pdf_manager.py
└── .env                       # Google credentials (gitignored)

Google Drive
└── Mila_Compute_Analysis/     # Shared folder
    ├── mila_papers/
    └── benchmark_papers/
```

### Implementation

#### 1. Google Drive Integration (Simplest)
```python
# src/pdf_storage/google_drive_store.py
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
from pathlib import Path

class GoogleDriveStore:
    def __init__(self, credentials_file, folder_id):
        creds = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        self.service = build('drive', 'v3', credentials=creds)
        self.folder_id = folder_id
        self.metadata_file = Path('data/pdf_metadata.json')
        self.metadata = self._load_metadata()
    
    def upload_pdf(self, local_path, paper_id):
        """Upload PDF and store metadata"""
        file_metadata = {
            'name': f"{paper_id}.pdf",
            'parents': [self.folder_id]
        }
        media = MediaFileUpload(local_path, mimetype='application/pdf')
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # Store metadata
        self.metadata[paper_id] = {
            'drive_id': file['id'],
            'drive_url': file['webViewLink'],
            'local_path': str(local_path),
            'uploaded_at': datetime.now().isoformat()
        }
        self._save_metadata()
        return file['id']
    
    def get_pdf_url(self, paper_id):
        """Get shareable link for PDF"""
        if paper_id in self.metadata:
            return self.metadata[paper_id]['drive_url']
        return None
    
    def download_pdf(self, paper_id, local_path):
        """Download PDF from Drive"""
        if paper_id not in self.metadata:
            return False
        
        request = self.service.files().get_media(
            fileId=self.metadata[paper_id]['drive_id']
        )
        with open(local_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        return True
```

#### 2. PDF Manager with Local Cache
```python
# src/pdf_storage/pdf_manager.py
class PDFManager:
    def __init__(self, drive_store=None, cache_dir='./temp_pdf_cache'):
        self.drive_store = drive_store
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_pdf(self, paper_id):
        """Get PDF with local caching"""
        cache_path = self.cache_dir / f"{paper_id}.pdf"
        
        # Check cache first
        if cache_path.exists():
            return cache_path
        
        # Download from Drive if available
        if self.drive_store:
            success = self.drive_store.download_pdf(paper_id, cache_path)
            if success:
                return cache_path
        
        return None
    
    def store_pdf(self, local_path, paper_id):
        """Store PDF in Drive and update metadata"""
        if self.drive_store:
            return self.drive_store.upload_pdf(local_path, paper_id)
        return None
    
    def cleanup_cache(self, max_age_days=1):
        """Clean old files from cache"""
        cutoff = time.time() - (max_age_days * 24 * 60 * 60)
        for pdf in self.cache_dir.glob("*.pdf"):
            if pdf.stat().st_mtime < cutoff:
                pdf.unlink()
```

### Setup Instructions

1. **Create Google Service Account**:
   ```bash
   # 1. Go to Google Cloud Console
   # 2. Create project "mila-compute-analysis"
   # 3. Enable Google Drive API
   # 4. Create service account
   # 5. Download credentials JSON
   ```

2. **Create Shared Folder**:
   - Create folder in Google Drive
   - Share with service account email
   - Copy folder ID from URL

3. **Environment Setup**:
   ```bash
   pip install google-api-python-client google-auth
   echo "GOOGLE_CREDENTIALS_FILE=credentials.json" >> .env
   echo "GOOGLE_DRIVE_FOLDER_ID=your_folder_id" >> .env
   ```

## Alternative Options

### Option 2: Git LFS (Simpler but uses repo space)
```bash
# Initialize Git LFS
git lfs install
git lfs track "*.pdf"
git add .gitattributes
```

Pros: Simple, integrated with Git
Cons: Still counts against repo storage limits

### Option 3: Reference-Only Approach
Store only URLs/DOIs in repository:
```json
{
  "paper_id": "smith2023",
  "title": "Large Language Models...",
  "pdf_url": "https://arxiv.org/pdf/2301.00234.pdf",
  "doi": "10.1145/1234567.1234568"
}
```

### Option 4: Local NAS/Shared Drive
If your organization has shared network storage:
```python
PDF_STORAGE_PATH = "/mnt/shared/mila_compute_analysis/pdfs"
```

## Recommendation

**Use Google Drive** for these reasons:
1. Zero repository bloat
2. Shareable with team members
3. Simple Python API
4. Free up to 15GB (enough for this project)
5. Implementation time: 2-3 hours

**Implementation Priority**:
1. Basic Google Drive upload/download (1 hour)
2. Metadata tracking system (30 min)
3. Local cache management (30 min)
4. Integration with existing PDF discovery (1 hour)

## Migration Path
```python
# One-time migration script
def migrate_existing_pdfs():
    store = GoogleDriveStore(credentials, folder_id)
    for pdf_path in Path('./pdf_cache').glob('*.pdf'):
        paper_id = pdf_path.stem
        store.upload_pdf(pdf_path, paper_id)
        pdf_path.unlink()  # Remove local file
```