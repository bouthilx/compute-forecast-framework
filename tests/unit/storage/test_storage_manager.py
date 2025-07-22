"""Unit tests for StorageManager."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from compute_forecast.storage.storage_manager import StorageManager


class TestStorageManager:
    """Test StorageManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_google_drive(self):
        """Create mock Google Drive storage."""
        mock = Mock()
        mock.file_exists.return_value = False
        mock.upload_file.return_value = "file_id_123"
        mock.download_pdf.return_value = Path("/tmp/downloaded.pdf")
        mock.test_connection.return_value = True
        return mock

    @pytest.fixture
    def storage_manager_local_only(self, temp_dir):
        """Create storage manager with local storage only."""
        return StorageManager(
            cache_dir=str(temp_dir / "cache"),
            google_drive_credentials=None,
            google_drive_folder_id=None,
        )

    @pytest.fixture
    def storage_manager_drive_only(self, mock_google_drive, temp_dir):
        """Create storage manager with Google Drive only."""
        # Create with minimal cache dir but replace google_drive
        manager = StorageManager(
            cache_dir=str(temp_dir / "minimal_cache"),
            google_drive_credentials=None,
            google_drive_folder_id=None,
        )
        # Replace with our mock
        manager.google_drive = mock_google_drive
        manager.local_cache = None  # Disable local cache for drive-only test
        return manager

    @pytest.fixture
    def storage_manager_both(self, temp_dir, mock_google_drive):
        """Create storage manager with both storages."""
        manager = StorageManager(
            cache_dir=str(temp_dir / "cache"),
            google_drive_credentials=None,
            google_drive_folder_id=None,
        )
        # Replace with our mock
        manager.google_drive = mock_google_drive
        return manager

    def test_local_only_mode(self, storage_manager_local_only, temp_dir):
        """Test storage manager with only local cache."""
        # Test save
        pdf_content = b"%PDF-1.4\nTest content"
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(pdf_content)

        success = storage_manager_local_only.save_pdf(
            paper_id="test_paper", source_path=pdf_path
        )

        assert success is True

        # Test exists
        exists, location = storage_manager_local_only.exists("test_paper")
        assert exists is True
        assert location == "cache"

        # Test get
        retrieved_path = storage_manager_local_only.get_pdf_path("test_paper")
        assert retrieved_path is not None
        assert retrieved_path.exists()
        assert retrieved_path.read_bytes() == pdf_content

    def test_google_drive_only_mode(
        self, storage_manager_drive_only, mock_google_drive, temp_dir
    ):
        """Test storage manager with only Google Drive."""
        # Test save
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest content")

        success, error = storage_manager_drive_only.save_pdf(
            paper_id="test_paper", pdf_path=pdf_path
        )

        assert success is True
        assert error is None
        mock_google_drive.upload_file.assert_called_once()

        # Test exists
        mock_google_drive.file_exists.return_value = True
        exists, location = storage_manager_drive_only.exists("test_paper")
        assert exists is True
        assert location == "google_drive"

        # Test get
        mock_google_drive.download_pdf.return_value = pdf_path
        retrieved_path = storage_manager_drive_only.get_pdf("test_paper")
        assert retrieved_path == pdf_path
        mock_google_drive.download_pdf.assert_called_once()

    def test_both_storages(self, storage_manager_both, mock_google_drive, temp_dir):
        """Test storage manager with both local and Google Drive."""
        # Test save - should save to both
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest content")

        success, error = storage_manager_both.save_pdf(
            paper_id="test_paper", pdf_path=pdf_path
        )

        assert success is True
        assert error is None
        mock_google_drive.upload_file.assert_called_once()

        # Check local cache exists
        cache_path = Path(storage_manager_both.cache_dir) / "test_paper.pdf"
        assert cache_path.exists()

    def test_save_pdf_local_success(self, storage_manager_local_only, temp_dir):
        """Test successful local PDF save."""
        pdf_content = b"%PDF-1.4\nTest PDF content"
        pdf_path = temp_dir / "source.pdf"
        pdf_path.write_bytes(pdf_content)

        success, error = storage_manager_local_only.save_pdf("paper123", pdf_path)

        assert success is True
        assert error is None

        # Verify file was copied to cache
        cache_path = Path(storage_manager_local_only.cache_dir) / "paper123.pdf"
        assert cache_path.exists()
        assert cache_path.read_bytes() == pdf_content

    def test_save_pdf_google_drive_success(
        self, storage_manager_drive_only, mock_google_drive, temp_dir
    ):
        """Test successful Google Drive upload."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")

        # Test with progress callback
        progress_callback = Mock()

        success, error = storage_manager_drive_only.save_pdf(
            paper_id="paper123",
            pdf_path=pdf_path,
            metadata={"title": "Test Paper"},
            progress_callback=progress_callback,
        )

        assert success is True
        assert error is None
        mock_google_drive.upload_file.assert_called_once_with(
            pdf_path,
            "paper123.pdf",
            metadata={"title": "Test Paper"},
            progress_callback=progress_callback,
        )

    def test_save_pdf_fallback(self, storage_manager_both, mock_google_drive, temp_dir):
        """Test fallback to local when Google Drive fails."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")

        # Make Google Drive fail
        mock_google_drive.upload_file.side_effect = Exception("Upload failed")

        success, error = storage_manager_both.save_pdf("paper123", pdf_path)

        # Should still succeed with local save
        assert success is True
        assert error is None

        # Local file should exist
        cache_path = Path(storage_manager_both.cache_dir) / "paper123.pdf"
        assert cache_path.exists()

    def test_save_pdf_both_fail(
        self, storage_manager_both, mock_google_drive, temp_dir
    ):
        """Test when both local and Drive fail."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")

        # Make Google Drive fail
        mock_google_drive.upload_file.side_effect = Exception("Upload failed")

        # Make local save fail by making cache dir read-only
        cache_dir = Path(storage_manager_both.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.chmod(0o444)  # Read-only

        try:
            success, error = storage_manager_both.save_pdf("paper123", pdf_path)
            assert success is False
            assert "Failed to save" in error
        finally:
            # Restore permissions for cleanup
            cache_dir.chmod(0o755)

    def test_exists_check(self, storage_manager_both, mock_google_drive, temp_dir):
        """Test existence checking in both storages."""
        # Not in either
        exists, location = storage_manager_both.exists("paper123")
        assert exists is False
        assert location is None

        # Add to local cache
        cache_path = Path(storage_manager_both.cache_dir) / "paper123.pdf"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"test")

        exists, location = storage_manager_both.exists("paper123")
        assert exists is True
        assert location == "local"

        # Remove from local, add to Drive
        cache_path.unlink()
        mock_google_drive.file_exists.return_value = True

        exists, location = storage_manager_both.exists("paper123")
        assert exists is True
        assert location == "google_drive"

    def test_get_pdf_from_cache(self, storage_manager_both, temp_dir):
        """Test retrieving PDF from local cache."""
        # Add file to cache
        cache_dir = Path(storage_manager_both.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "paper123.pdf"
        cache_path.write_bytes(b"%PDF-1.4\nCached content")

        retrieved = storage_manager_both.get_pdf("paper123")
        assert retrieved == cache_path
        assert retrieved.read_bytes() == b"%PDF-1.4\nCached content"

    def test_get_pdf_from_drive(
        self, storage_manager_both, mock_google_drive, temp_dir
    ):
        """Test retrieving PDF from Google Drive when not in cache."""
        # Not in cache, but in Drive
        mock_google_drive.file_exists.return_value = True

        # Create a file to return
        downloaded_file = temp_dir / "downloaded.pdf"
        downloaded_file.write_bytes(b"%PDF-1.4\nDrive content")
        mock_google_drive.download_pdf.return_value = downloaded_file

        retrieved = storage_manager_both.get_pdf("paper123")
        assert retrieved == downloaded_file
        mock_google_drive.download_pdf.assert_called_once()

    def test_get_pdf_not_found(self, storage_manager_both, mock_google_drive):
        """Test get_pdf when file doesn't exist anywhere."""
        mock_google_drive.file_exists.return_value = False

        retrieved = storage_manager_both.get_pdf("nonexistent")
        assert retrieved is None

    def test_save_with_metadata(
        self, storage_manager_both, mock_google_drive, temp_dir
    ):
        """Test saving with metadata passes through correctly."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")

        metadata = {"title": "Test Paper", "authors": "John Doe", "year": 2024}

        storage_manager_both.save_pdf("paper123", pdf_path, metadata=metadata)

        # Check metadata was passed to Google Drive
        mock_google_drive.upload_file.assert_called_once()
        call_args = mock_google_drive.upload_file.call_args
        assert call_args[1]["metadata"] == metadata

    def test_create_cache_directory(self, temp_dir):
        """Test that cache directory is created if it doesn't exist."""
        cache_dir = temp_dir / "new_cache"
        assert not cache_dir.exists()

        storage_manager = StorageManager(cache_dir=str(cache_dir))

        # Save a file to trigger directory creation
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"test")
        storage_manager.save_pdf("test", pdf_path)

        assert cache_dir.exists()

    def test_invalid_pdf_path(self, storage_manager_local_only, temp_dir):
        """Test handling of invalid PDF path."""
        non_existent = temp_dir / "does_not_exist.pdf"

        success, error = storage_manager_local_only.save_pdf("paper123", non_existent)

        assert success is False
        assert "not found" in error.lower()

    def test_progress_callback_propagation(
        self, storage_manager_both, mock_google_drive, temp_dir
    ):
        """Test that progress callback is properly propagated."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")

        progress_callback = Mock()

        storage_manager_both.save_pdf(
            "paper123", pdf_path, progress_callback=progress_callback
        )

        # Verify callback was passed to Google Drive
        mock_google_drive.upload_file.assert_called_once()
        call_kwargs = mock_google_drive.upload_file.call_args.kwargs
        assert call_kwargs.get("progress_callback") == progress_callback
