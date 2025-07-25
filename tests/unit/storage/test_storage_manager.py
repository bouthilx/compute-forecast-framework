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
        mock.upload_with_progress.return_value = "file_id_123"
        # download_pdf and download_with_progress should return paths within temp_dir
        # They will be dynamically set in the test based on the actual cache directory
        mock.download_pdf.return_value = None
        mock.download_with_progress.return_value = None
        mock.get_file_id.return_value = "file_id_123"
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
        # Mock the local cache to fail saves to simulate drive-only mode
        mock_local_cache = Mock()
        mock_local_cache.save.return_value = None  # Simulate failed save
        mock_local_cache.get_path.return_value = None  # Simulate file not in cache
        mock_local_cache.exists.return_value = (
            False  # Simulate file not existing in cache
        )
        mock_local_cache.cache_dir = temp_dir / "minimal_cache"
        mock_local_cache.metadata = {}  # Add metadata dict
        mock_local_cache._get_cache_path = Mock(
            return_value=temp_dir / "minimal_cache" / "test_paper.pdf"
        )
        mock_local_cache._save_metadata = Mock()
        manager.local_cache = mock_local_cache
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

        success = storage_manager_drive_only.save_pdf(
            paper_id="test_paper", source_path=pdf_path
        )

        assert success is True
        mock_google_drive.upload_with_progress.assert_called_once()

        # Test exists
        mock_google_drive.file_exists.return_value = True
        exists, location = storage_manager_drive_only.exists("test_paper")
        assert exists is True
        assert location == "drive"

        # Test get
        mock_google_drive.get_file_id.return_value = "file123"
        # Set the download return to be the expected cache path
        expected_cache_path = storage_manager_drive_only.local_cache._get_cache_path(
            "test_paper"
        )
        expected_cache_path.parent.mkdir(parents=True, exist_ok=True)
        expected_cache_path.write_bytes(b"downloaded content")
        mock_google_drive.download_with_progress.return_value = expected_cache_path
        retrieved_path = storage_manager_drive_only.get_pdf_path("test_paper")
        assert retrieved_path == expected_cache_path
        mock_google_drive.get_file_id.assert_called_once()
        mock_google_drive.download_with_progress.assert_called_once()

    def test_both_storages(self, storage_manager_both, mock_google_drive, temp_dir):
        """Test storage manager with both local and Google Drive."""
        # Test save - should save to both
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest content")

        success = storage_manager_both.save_pdf(
            paper_id="test_paper", source_path=pdf_path
        )

        assert success is True
        mock_google_drive.upload_with_progress.assert_called_once()

        # Check local cache exists
        # LocalCache uses subdirectory structure based on first 2 chars of paper_id
        cache_path = (
            Path(storage_manager_both.local_cache.cache_dir) / "te" / "test_paper.pdf"
        )
        assert cache_path.exists()

    def test_save_pdf_local_success(self, storage_manager_local_only, temp_dir):
        """Test successful local PDF save."""
        pdf_content = b"%PDF-1.4\nTest PDF content"
        pdf_path = temp_dir / "source.pdf"
        pdf_path.write_bytes(pdf_content)

        success = storage_manager_local_only.save_pdf("paper123", source_path=pdf_path)

        assert success is True

        # Verify file was copied to cache
        cache_path = (
            Path(storage_manager_local_only.local_cache.cache_dir)
            / "pa"
            / "paper123.pdf"
        )
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

        success = storage_manager_drive_only.save_pdf(
            paper_id="paper123",
            source_path=pdf_path,
            metadata={"title": "Test Paper"},
            progress_callback=progress_callback,
        )

        assert success is True
        mock_google_drive.upload_with_progress.assert_called_once_with(
            pdf_path,
            "paper123",
            progress_callback,
            {"title": "Test Paper"},
        )

    def test_save_pdf_fallback(self, storage_manager_both, mock_google_drive, temp_dir):
        """Test fallback to local when Google Drive fails."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")

        # Make Google Drive fail
        mock_google_drive.upload_with_progress.return_value = None

        success = storage_manager_both.save_pdf("paper123", source_path=pdf_path)

        # Should still succeed with local save
        assert success is True

        # Local file should exist
        cache_path = (
            Path(storage_manager_both.local_cache.cache_dir) / "pa" / "paper123.pdf"
        )
        assert cache_path.exists()

    def test_save_pdf_both_fail(
        self, storage_manager_both, mock_google_drive, temp_dir
    ):
        """Test when both local and Drive fail."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")

        # Make Google Drive fail
        mock_google_drive.upload_with_progress.return_value = None

        # Make local save fail by making cache dir read-only
        cache_dir = Path(storage_manager_both.local_cache.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.chmod(0o444)  # Read-only

        try:
            success = storage_manager_both.save_pdf("paper123", source_path=pdf_path)
            assert success is False
        finally:
            # Restore permissions for cleanup
            cache_dir.chmod(0o755)

    def test_exists_check(self, storage_manager_both, mock_google_drive, temp_dir):
        """Test existence checking in both storages."""
        # Not in either
        exists, location = storage_manager_both.exists("paper123")
        assert exists is False
        assert location == ""

        # Add to local cache
        cache_path = (
            Path(storage_manager_both.local_cache.cache_dir) / "pa" / "paper123.pdf"
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"test")

        exists, location = storage_manager_both.exists("paper123")
        assert exists is True
        assert location == "cache"

        # Remove from local, add to Drive
        cache_path.unlink()
        mock_google_drive.file_exists.return_value = True

        exists, location = storage_manager_both.exists("paper123")
        assert exists is True
        assert location == "drive"

    def test_get_pdf_from_cache(self, storage_manager_both, temp_dir):
        """Test retrieving PDF from local cache."""
        # Add file to cache using LocalCache's subdirectory structure
        cache_path = storage_manager_both.local_cache._get_cache_path("paper123")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"%PDF-1.4\nCached content")

        # Update metadata so LocalCache knows about it
        storage_manager_both.local_cache.metadata["paper123"] = {
            "path": str(
                cache_path.relative_to(storage_manager_both.local_cache.cache_dir)
            ),
            "size": cache_path.stat().st_size,
            "cached_at": "2024-01-01T00:00:00",
        }

        retrieved = storage_manager_both.get_pdf_path("paper123")
        assert retrieved == cache_path
        assert retrieved.read_bytes() == b"%PDF-1.4\nCached content"

    def test_get_pdf_from_drive(
        self, storage_manager_both, mock_google_drive, temp_dir
    ):
        """Test retrieving PDF from Google Drive when not in cache."""
        # Make sure it's not in cache
        assert storage_manager_both.local_cache.get_path("paper123") is None

        # Not in cache, but in Drive
        mock_google_drive.file_exists.return_value = True
        mock_google_drive.get_file_id.return_value = "file123"

        # Set the download return to be the expected cache path
        expected_cache_path = storage_manager_both.local_cache._get_cache_path(
            "paper123"
        )

        # Configure the mock to create the file when called
        def mock_download(*args):
            expected_cache_path.parent.mkdir(parents=True, exist_ok=True)
            expected_cache_path.write_bytes(b"%PDF-1.4\nDrive content")
            return expected_cache_path

        mock_google_drive.download_with_progress.side_effect = mock_download

        retrieved = storage_manager_both.get_pdf_path("paper123")
        assert retrieved == expected_cache_path
        assert retrieved.read_bytes() == b"%PDF-1.4\nDrive content"
        mock_google_drive.download_with_progress.assert_called_once()

    def test_get_pdf_not_found(self, storage_manager_both, mock_google_drive):
        """Test get_pdf when file doesn't exist anywhere."""
        mock_google_drive.file_exists.return_value = False
        mock_google_drive.get_file_id.return_value = None

        retrieved = storage_manager_both.get_pdf_path("nonexistent")
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
        mock_google_drive.upload_with_progress.assert_called_once()
        call_args = mock_google_drive.upload_with_progress.call_args
        # upload_with_progress(source_path, paper_id, progress_callback, metadata)
        assert call_args[0][3] == metadata

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

        success = storage_manager_local_only.save_pdf(
            "paper123", source_path=non_existent
        )

        assert success is False

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
        mock_google_drive.upload_with_progress.assert_called_once()
        # Check that the callback was passed in the call
        call_args = mock_google_drive.upload_with_progress.call_args
        assert (
            progress_callback in call_args[0]
            or progress_callback in call_args[1].values()
        )
