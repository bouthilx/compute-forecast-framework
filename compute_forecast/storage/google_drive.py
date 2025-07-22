"""Enhanced Google Drive storage with progress tracking for downloads."""

import logging
from pathlib import Path
from typing import Dict, Optional, Callable
import time

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import warnings

# Suppress the file_cache warning since we're using service accounts
warnings.filterwarnings(
    "ignore", message="file_cache is only supported with oauth2client<4.0.0"
)

logger = logging.getLogger(__name__)


class GoogleDriveStorage:
    """Google Drive storage backend for PDFs with progress tracking."""

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    PDF_MIME_TYPE = "application/pdf"
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for progress tracking

    def __init__(self, credentials_path: str, folder_id: str):
        """Initialize Google Drive storage.

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
                self._credentials_path, scopes=self.SCOPES
            )
            self._service = build("drive", "v3", credentials=credentials)
            logger.info("Successfully initialized Google Drive service")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise

    def upload_with_progress(
        self,
        file_path: Path,
        paper_id: str,
        progress_callback: Optional[Callable[[str, int, str, float], None]] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """Upload file to Google Drive with progress tracking.

        Args:
            file_path: Path to the file to upload
            paper_id: Unique identifier for the paper
            progress_callback: Callback function(paper_id, bytes_transferred, operation_type, speed)
            metadata: Optional metadata to store with the file

        Returns:
            Google Drive file ID or None if failed
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        file_size = file_path.stat().st_size
        filename = f"{paper_id}.pdf"

        # Prepare file metadata
        file_metadata = {
            "name": filename,
            "parents": [self.folder_id],
        }

        if metadata:
            file_metadata["properties"] = metadata

        # Initialize progress tracking
        if progress_callback:
            progress_callback(paper_id, file_size, "Uploading to Drive", 0.0)

        try:
            # Use resumable upload for progress tracking
            media = MediaFileUpload(
                str(file_path),
                mimetype=self.PDF_MIME_TYPE,
                resumable=True,
                chunksize=self.CHUNK_SIZE,
            )

            request = self._service.files().create(
                body=file_metadata, media_body=media, fields="id"
            )

            # Upload with progress
            response = None
            start_time = time.time()
            bytes_uploaded = 0

            while response is None:
                status, response = request.next_chunk()
                if status:
                    bytes_uploaded = int(status.resumable_progress)
                    elapsed_time = time.time() - start_time
                    speed = bytes_uploaded / elapsed_time if elapsed_time > 0 else 0

                    if progress_callback:
                        progress_callback(
                            paper_id, bytes_uploaded, "Uploading to Drive", speed
                        )

            file_id = response.get("id")
            logger.info(f"Successfully uploaded {filename} to Google Drive: {file_id}")
            return file_id

        except HttpError as e:
            logger.error(f"Failed to upload {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading {filename}: {e}")
            return None

    def download_with_progress(
        self,
        file_id: str,
        paper_id: str,
        output_path: Path,
        progress_callback: Optional[Callable[[str, int, str, float], None]] = None,
    ) -> Optional[Path]:
        """Download file from Google Drive with progress tracking.

        Args:
            file_id: Google Drive file ID
            paper_id: Paper identifier for progress tracking
            output_path: Path to save the downloaded file
            progress_callback: Callback function(paper_id, bytes_transferred, operation_type, speed)

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Get file metadata for size
            file_metadata = (
                self._service.files().get(fileId=file_id, fields="size").execute()
            )
            file_size = int(file_metadata.get("size", 0))

            # Initialize progress
            if progress_callback:
                progress_callback(paper_id, file_size, "Downloading from Drive", 0.0)

            # Create download request
            request = self._service.files().get_media(fileId=file_id)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            start_time = time.time()
            bytes_downloaded = 0

            with open(output_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request, chunksize=self.CHUNK_SIZE)
                done = False

                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        bytes_downloaded = int(status.resumable_progress)
                        elapsed_time = time.time() - start_time
                        speed = (
                            bytes_downloaded / elapsed_time if elapsed_time > 0 else 0
                        )

                        if progress_callback:
                            progress_callback(
                                paper_id,
                                bytes_downloaded,
                                "Downloading from Drive",
                                speed,
                            )

            logger.info(f"Successfully downloaded file {file_id} to {output_path}")
            return output_path

        except HttpError as e:
            logger.error(f"Failed to download {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {file_id}: {e}")
            return None

    def file_exists(self, paper_id: str) -> bool:
        """Check if a PDF exists in Google Drive.

        Args:
            paper_id: Paper identifier

        Returns:
            True if file exists
        """
        filename = f"{paper_id}.pdf"

        try:
            query = (
                f"name='{filename}' and parents in '{self.folder_id}' and trashed=false"
            )
            results = (
                self._service.files()
                .list(q=query, pageSize=1, fields="files(id)")
                .execute()
            )

            files = results.get("files", [])
            return len(files) > 0

        except HttpError as e:
            logger.error(f"Failed to check file existence for {paper_id}: {e}")
            return False

    def get_file_id(self, paper_id: str) -> Optional[str]:
        """Get Google Drive file ID for a paper.

        Args:
            paper_id: Paper identifier

        Returns:
            File ID or None if not found
        """
        filename = f"{paper_id}.pdf"

        try:
            query = (
                f"name='{filename}' and parents in '{self.folder_id}' and trashed=false"
            )
            results = (
                self._service.files()
                .list(q=query, pageSize=1, fields="files(id)")
                .execute()
            )

            files = results.get("files", [])
            if files:
                return files[0]["id"]
            return None

        except HttpError as e:
            logger.error(f"Failed to get file ID for {paper_id}: {e}")
            return None

    def test_connection(self) -> bool:
        """Test the Google Drive connection.

        Returns:
            True if connection is working
        """
        try:
            # Test basic API access
            self._service.files().list(pageSize=1, fields="files(id)").execute()

            # For shared folders, we can't directly get folder metadata with drive.file scope
            # Instead, try to list contents of the folder to verify access
            try:
                # Try to list files in the folder (this works with shared folders)
                results = (
                    self._service.files()
                    .list(
                        q=f"'{self.folder_id}' in parents and trashed=false",
                        pageSize=1,
                        fields="files(id)",
                    )
                    .execute()
                )

                # If we can list contents, we have access
                logger.info(
                    f"Successfully connected to Google Drive folder: {self.folder_id}"
                )
                return True

            except HttpError as e:
                if e.resp.status == 404:
                    # Folder doesn't exist or not shared
                    logger.error(
                        f"Folder not found or not accessible: {self.folder_id}"
                    )
                    logger.error(
                        "Please ensure the folder is shared with the service account"
                    )
                else:
                    logger.error(f"Failed to access folder: {e}")
                return False

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

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
