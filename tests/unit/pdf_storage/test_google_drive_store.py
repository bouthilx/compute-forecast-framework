"""Tests for GoogleDriveStore class."""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import os

from compute_forecast.pdf_storage.google_drive_store import GoogleDriveStore


class TestGoogleDriveStore(unittest.TestCase):
    """Test GoogleDriveStore functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_credentials_path = "/fake/path/to/credentials.json"
        self.mock_folder_id = "fake_folder_id"

    @patch("compute_forecast.pdf_storage.google_drive_store.build")
    @patch(
        "compute_forecast.pdf_storage.google_drive_store.service_account.Credentials.from_service_account_file"
    )
    def test_initialization(self, mock_credentials, mock_build):
        """Test GoogleDriveStore initialization."""
        mock_credentials.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        store = GoogleDriveStore(self.mock_credentials_path, self.mock_folder_id)

        self.assertEqual(store.folder_id, self.mock_folder_id)
        self.assertEqual(store._service, mock_service)
        mock_credentials.assert_called_once_with(
            self.mock_credentials_path,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )

    @patch("compute_forecast.pdf_storage.google_drive_store.build")
    @patch(
        "compute_forecast.pdf_storage.google_drive_store.service_account.Credentials.from_service_account_file"
    )
    def test_test_connection_success(self, mock_credentials, mock_build):
        """Test successful connection test."""
        mock_credentials.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock successful API calls
        mock_service.files().list().execute.return_value = {"files": []}
        mock_service.files().get().execute.return_value = {
            "id": self.mock_folder_id,
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        store = GoogleDriveStore(self.mock_credentials_path, self.mock_folder_id)
        result = store.test_connection()

        self.assertTrue(result)

    @patch("compute_forecast.pdf_storage.google_drive_store.build")
    @patch(
        "compute_forecast.pdf_storage.google_drive_store.service_account.Credentials.from_service_account_file"
    )
    def test_test_connection_failure(self, mock_credentials, mock_build):
        """Test connection test failure."""
        mock_credentials.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock API failure
        mock_service.files().list().execute.side_effect = Exception("API Error")

        store = GoogleDriveStore(self.mock_credentials_path, self.mock_folder_id)
        result = store.test_connection()

        self.assertFalse(result)

    @patch("compute_forecast.pdf_storage.google_drive_store.build")
    @patch(
        "compute_forecast.pdf_storage.google_drive_store.service_account.Credentials.from_service_account_file"
    )
    @patch("compute_forecast.pdf_storage.google_drive_store.MediaFileUpload")
    def test_upload_file_success(self, mock_media_upload, mock_credentials, mock_build):
        """Test successful file upload."""
        mock_credentials.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_media_upload.return_value = Mock()

        # Mock successful upload
        mock_service.files().create().execute.return_value = {
            "id": "uploaded_file_id",
            "name": "test.pdf",
        }

        store = GoogleDriveStore(self.mock_credentials_path, self.mock_folder_id)

        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"mock pdf content")
            temp_path = Path(temp_file.name)

        try:
            result = store.upload_file(temp_path, "test.pdf", {"test": "metadata"})
            self.assertEqual(result, "uploaded_file_id")
        finally:
            os.unlink(temp_path)

    @patch("compute_forecast.pdf_storage.google_drive_store.build")
    @patch(
        "compute_forecast.pdf_storage.google_drive_store.service_account.Credentials.from_service_account_file"
    )
    def test_upload_file_failure(self, mock_credentials, mock_build):
        """Test file upload failure."""
        mock_credentials.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock upload failure
        mock_service.files().create().execute.side_effect = Exception("Upload failed")

        store = GoogleDriveStore(self.mock_credentials_path, self.mock_folder_id)

        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"mock pdf content")
            temp_path = Path(temp_file.name)

        try:
            result = store.upload_file(temp_path, "test.pdf", {"test": "metadata"})
            self.assertIsNone(result)
        finally:
            os.unlink(temp_path)

    @patch("compute_forecast.pdf_storage.google_drive_store.build")
    @patch(
        "compute_forecast.pdf_storage.google_drive_store.service_account.Credentials.from_service_account_file"
    )
    def test_file_exists(self, mock_credentials, mock_build):
        """Test file existence check."""
        mock_credentials.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock file found
        mock_service.files().list().execute.return_value = {
            "files": [{"id": "existing_file_id", "name": "test.pdf"}]
        }

        store = GoogleDriveStore(self.mock_credentials_path, self.mock_folder_id)
        result = store.file_exists("test.pdf")

        self.assertTrue(result)

    @patch("compute_forecast.pdf_storage.google_drive_store.build")
    @patch(
        "compute_forecast.pdf_storage.google_drive_store.service_account.Credentials.from_service_account_file"
    )
    def test_file_not_exists(self, mock_credentials, mock_build):
        """Test file not exists check."""
        mock_credentials.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock no files found
        mock_service.files().list().execute.return_value = {"files": []}

        store = GoogleDriveStore(self.mock_credentials_path, self.mock_folder_id)
        result = store.file_exists("nonexistent.pdf")

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
