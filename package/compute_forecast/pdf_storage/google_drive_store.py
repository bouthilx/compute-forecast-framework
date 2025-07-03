"""Google Drive storage backend for PDFs."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io
import warnings

# Suppress the file_cache warning since we're using service accounts
warnings.filterwarnings('ignore', message='file_cache is only supported with oauth2client<4.0.0')

logger = logging.getLogger(__name__)


class GoogleDriveStore:
    """Google Drive storage backend for PDF files."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    PDF_MIME_TYPE = 'application/pdf'
    
    def __init__(self, credentials_path: str, folder_id: str):
        """Initialize Google Drive store.
        
        Args:
            credentials_path: Path to service account credentials JSON
            folder_id: Google Drive folder ID to store PDFs
        """
        self.folder_id = folder_id
        self._service = None
        self._credentials_path = credentials_path
        self._initialize_service()
        
    def _initialize_service(self):
        """Initialize Google Drive API service."""
        try:
            credentials = Credentials.from_service_account_file(
                self._credentials_path,
                scopes=self.SCOPES
            )
            self._service = build('drive', 'v3', credentials=credentials)
            logger.info("Successfully initialized Google Drive service")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise
            
    def upload_pdf(self, paper_id: str, pdf_path: Path, metadata: Optional[Dict] = None) -> str:
        """Upload a PDF to Google Drive.
        
        Args:
            paper_id: Unique identifier for the paper
            pdf_path: Path to the PDF file
            metadata: Optional metadata to store with the file
            
        Returns:
            Google Drive file ID
            
        Raises:
            HttpError: If upload fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        # Prepare file metadata
        file_metadata = {
            'name': f'{paper_id}.pdf',
            'parents': [self.folder_id],
            'description': json.dumps({
                'paper_id': paper_id,
                'upload_timestamp': datetime.utcnow().isoformat(),
                **(metadata or {})
            })
        }
        
        media = MediaFileUpload(
            str(pdf_path),
            mimetype=self.PDF_MIME_TYPE,
            resumable=True
        )
        
        try:
            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Successfully uploaded {paper_id} to Google Drive: {file_id}")
            return file_id
            
        except HttpError as e:
            logger.error(f"Failed to upload {paper_id}: {e}")
            raise
            
    def download_pdf(self, file_id: str, destination_path: Path) -> Path:
        """Download a PDF from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            destination_path: Path to save the downloaded file
            
        Returns:
            Path to the downloaded file
            
        Raises:
            HttpError: If download fails
        """
        try:
            request = self._service.files().get_media(fileId=file_id)
            
            # Ensure destination directory exists
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            with open(destination_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.debug(f"Download progress: {int(status.progress() * 100)}%")
                        
            logger.info(f"Successfully downloaded file {file_id} to {destination_path}")
            return destination_path
            
        except HttpError as e:
            logger.error(f"Failed to download {file_id}: {e}")
            raise
            
    def list_files(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """List all PDF files in the Drive folder.
        
        Args:
            page_size: Number of files per page
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            results = []
            page_token = None
            
            while True:
                response = self._service.files().list(
                    q=f"'{self.folder_id}' in parents and mimeType='{self.PDF_MIME_TYPE}'",
                    pageSize=page_size,
                    fields="nextPageToken, files(id, name, size, createdTime, modifiedTime, description)",
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken')
                
                if not page_token:
                    break
                    
            logger.info(f"Found {len(results)} PDFs in Google Drive")
            return results
            
        except HttpError as e:
            logger.error(f"Failed to list files: {e}")
            raise
            
    def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            True if successful
        """
        try:
            self._service.files().delete(fileId=file_id).execute()
            logger.info(f"Successfully deleted file {file_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to delete {file_id}: {e}")
            return False
            
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific file.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata or None if not found
        """
        try:
            file = self._service.files().get(
                fileId=file_id,
                fields='id, name, size, createdTime, modifiedTime, description'
            ).execute()
            
            # Parse description JSON if present
            if 'description' in file:
                try:
                    file['parsed_description'] = json.loads(file['description'])
                except json.JSONDecodeError:
                    file['parsed_description'] = {}
                    
            return file
            
        except HttpError as e:
            logger.error(f"Failed to get metadata for {file_id}: {e}")
            return None
            
    def batch_upload(self, files: Dict[str, Path], show_progress: bool = True) -> Dict[str, str]:
        """Upload multiple PDFs to Google Drive.
        
        Args:
            files: Dictionary mapping paper_id to PDF path
            show_progress: Whether to show progress
            
        Returns:
            Dictionary mapping paper_id to file_id
        """
        results = {}
        total = len(files)
        
        for i, (paper_id, pdf_path) in enumerate(files.items(), 1):
            if show_progress:
                logger.info(f"Uploading {i}/{total}: {paper_id}")
                
            try:
                file_id = self.upload_pdf(paper_id, pdf_path)
                results[paper_id] = file_id
            except Exception as e:
                logger.error(f"Failed to upload {paper_id}: {e}")
                
        return results
        
    def test_connection(self) -> bool:
        """Test the Google Drive connection.
        
        Returns:
            True if connection is working
        """
        try:
            # First test basic API access by listing files (doesn't require folder access)
            test_response = self._service.files().list(
                pageSize=1,
                fields="files(id)"
            ).execute()
            
            # Now try to access the specific folder
            try:
                folder = self._service.files().get(
                    fileId=self.folder_id,
                    fields='id, name, mimeType'
                ).execute()
                
                # Verify it's actually a folder
                if folder.get('mimeType') != 'application/vnd.google-apps.folder':
                    logger.error(f"ID {self.folder_id} is not a folder, it's a {folder.get('mimeType')}")
                    return False
                
                logger.info(f"Successfully connected to Google Drive folder: {folder.get('name')}")
                return True
                
            except HttpError as e:
                if e.resp.status == 404:
                    logger.error(f"Folder not found or not accessible: {self.folder_id}")
                    logger.error("Please ensure:")
                    logger.error("1. The folder ID is correct")
                    logger.error("2. The folder is shared with the service account email")
                    logger.error("3. The service account has at least 'Viewer' permission")
                else:
                    logger.error(f"Failed to access folder: {e}")
                return False
                
        except HttpError as e:
            logger.error(f"Google Drive API connection failed: {e}")
            logger.error("Please ensure the Google Drive API is enabled in your project")
            return False
        except Exception as e:
            logger.error(f"Connection test failed with unexpected error: {e}")
            return False