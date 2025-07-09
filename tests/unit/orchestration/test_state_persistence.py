"""
Unit tests for StatePersistence class.
Tests atomic operations, data integrity, and error handling.
"""

import pytest
import json
import tempfile
import shutil
import threading
import time
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from compute_forecast.pipeline.metadata_collection.collectors.state_persistence import (
    StatePersistence,
)
from compute_forecast.pipeline.metadata_collection.collectors.state_structures import (
    CheckpointData,
    CollectionSession,
    VenueConfig,
)

# Add package root to Python path
package_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(package_root))


class TestStatePersistence:
    """Test StatePersistence atomic operations and integrity"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def persistence(self, temp_dir):
        """Create StatePersistence instance for testing"""
        return StatePersistence(temp_dir, enable_backups=True)

    @pytest.fixture
    def sample_checkpoint(self):
        """Create sample checkpoint data"""
        return CheckpointData(
            checkpoint_id="test_001",
            session_id="session_123",
            checkpoint_type="venue_completed",
            timestamp=datetime.now(),
            venues_completed=[("CVPR", 2023)],
            venues_in_progress=[("ICLR", 2024)],
            venues_not_started=[("NeurIPS", 2024)],
            papers_collected=100,
            papers_by_venue={"CVPR": {2023: 100}},
            last_successful_operation="venue_cvpr_completed",
            api_health_status={},
            rate_limit_status={},
        )

    @pytest.fixture
    def sample_session(self):
        """Create sample session data"""
        venue_configs = [
            VenueConfig(
                venue_name="CVPR", target_years=[2023, 2024], max_papers_per_year=50
            )
        ]

        return CollectionSession(
            session_id="session_123",
            creation_time=datetime.now(),
            last_activity_time=datetime.now(),
            status="active",
            target_venues=venue_configs,
            target_years=[2023, 2024],
            collection_config={"max_retries": 3},
            venues_completed=[],
            venues_in_progress=[("CVPR", 2023)],
            venues_failed=[],
        )

    def test_persistence_initialization(self, temp_dir):
        """Test StatePersistence initialization"""
        persistence = StatePersistence(temp_dir, enable_backups=True)

        assert persistence.base_dir == temp_dir
        assert persistence.enable_backups is True
        assert temp_dir.exists()

    def test_save_checkpoint_atomic(self, persistence, sample_checkpoint, temp_dir):
        """Test atomic saving of checkpoint data"""
        file_path = temp_dir / "checkpoints" / "test_001.json"

        # Save checkpoint
        result = persistence.save_state_atomic(file_path, sample_checkpoint)

        assert result is True
        assert file_path.exists()
        assert file_path.parent.exists()

        # Verify content
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["checkpoint_id"] == "test_001"
        assert saved_data["session_id"] == "session_123"
        assert saved_data["papers_collected"] == 100

    def test_save_session_atomic(self, persistence, sample_session, temp_dir):
        """Test atomic saving of session data"""
        file_path = temp_dir / "sessions" / "session_123.json"

        # Save session
        result = persistence.save_state_atomic(file_path, sample_session)

        assert result is True
        assert file_path.exists()

        # Verify content
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["session_id"] == "session_123"
        assert saved_data["status"] == "active"

    def test_save_dict_data(self, persistence, temp_dir):
        """Test saving plain dictionary data"""
        file_path = temp_dir / "test_dict.json"
        test_data = {
            "key1": "value1",
            "key2": 42,
            "key3": [1, 2, 3],
            "key4": {"nested": "data"},
        }

        result = persistence.save_state_atomic(file_path, test_data)

        assert result is True
        assert file_path.exists()

        # Verify content
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data == test_data

    def test_backup_creation(self, persistence, sample_checkpoint, temp_dir):
        """Test backup creation during save"""
        file_path = temp_dir / "test_backup.json"

        # Create initial file
        initial_data = {"version": 1}
        persistence.save_state_atomic(file_path, initial_data, backup_previous=False)

        # Save new data with backup
        result = persistence.save_state_atomic(
            file_path, sample_checkpoint, backup_previous=True
        )

        assert result is True
        assert file_path.exists()

        # Check backup was created
        backup_path = file_path.with_suffix(".json.backup")
        assert backup_path.exists()

        # Verify backup contains original data
        with open(backup_path, "r") as f:
            backup_data = json.load(f)
        assert backup_data == initial_data

    def test_load_checkpoint(self, persistence, sample_checkpoint, temp_dir):
        """Test loading checkpoint data"""
        file_path = temp_dir / "test_load.json"

        # Save first
        persistence.save_state_atomic(file_path, sample_checkpoint)

        # Load back
        loaded_checkpoint = persistence.load_state(file_path, CheckpointData)

        assert loaded_checkpoint is not None
        assert loaded_checkpoint.checkpoint_id == "test_001"
        assert loaded_checkpoint.session_id == "session_123"
        assert loaded_checkpoint.papers_collected == 100
        assert isinstance(loaded_checkpoint, CheckpointData)

    def test_load_session(self, persistence, sample_session, temp_dir):
        """Test loading session data"""
        file_path = temp_dir / "test_session.json"

        # Save first
        persistence.save_state_atomic(file_path, sample_session)

        # Load back
        loaded_session = persistence.load_state(file_path, CollectionSession)

        assert loaded_session is not None
        assert loaded_session.session_id == "session_123"
        assert loaded_session.status == "active"
        assert isinstance(loaded_session, CollectionSession)

    def test_load_dict(self, persistence, temp_dir):
        """Test loading dictionary data"""
        file_path = temp_dir / "test_dict.json"
        test_data = {"test": "data", "number": 42}

        # Save first
        persistence.save_state_atomic(file_path, test_data)

        # Load back
        loaded_data = persistence.load_state(file_path, dict)

        assert loaded_data == test_data

    def test_load_nonexistent_file(self, persistence, temp_dir):
        """Test loading non-existent file"""
        file_path = temp_dir / "nonexistent.json"

        result = persistence.load_state(file_path, dict)

        assert result is None

    def test_atomic_write_failure_cleanup(self, persistence, temp_dir):
        """Test cleanup on atomic write failure"""
        file_path = temp_dir / "test_failure.json"

        # Mock file write to fail
        with patch("builtins.open", side_effect=OSError("Disk full")):
            result = persistence.save_state_atomic(file_path, {"test": "data"})

        assert result is False
        assert not file_path.exists()

        # Check no temp files left behind
        temp_files = list(temp_dir.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_file_integrity_validation(self, persistence, sample_checkpoint, temp_dir):
        """Test file integrity validation"""
        file_path = temp_dir / "test_integrity.json"

        # Save file with metadata
        persistence.save_state_atomic(file_path, sample_checkpoint)

        # Validate integrity
        integrity_result = persistence.validate_file_integrity(file_path)

        assert integrity_result.integrity_status == "valid"
        assert integrity_result.checksum_valid is True
        assert integrity_result.file_path == file_path
        assert integrity_result.size_actual > 0

    def test_corrupted_file_detection(self, persistence, sample_checkpoint, temp_dir):
        """Test detection of corrupted files"""
        file_path = temp_dir / "test_corrupt.json"

        # Save file normally
        persistence.save_state_atomic(file_path, sample_checkpoint)

        # Corrupt the file content
        with open(file_path, "w") as f:
            f.write("corrupted json content")

        # Validate integrity
        integrity_result = persistence.validate_file_integrity(file_path)

        assert integrity_result.integrity_status == "corrupted"
        assert integrity_result.recovery_action == "restore_from_backup"

    def test_missing_file_detection(self, persistence, temp_dir):
        """Test detection of missing files"""
        file_path = temp_dir / "missing.json"

        integrity_result = persistence.validate_file_integrity(file_path)

        assert integrity_result.integrity_status == "missing"
        assert integrity_result.checksum_valid is False
        assert integrity_result.recovery_action == "restore_from_backup"

    def test_concurrent_saves(self, persistence, temp_dir):
        """Test thread safety of concurrent saves"""
        file_path = temp_dir / "concurrent.json"
        results = []

        def save_data(data_id):
            data = {"id": data_id, "timestamp": datetime.now().isoformat()}
            result = persistence.save_state_atomic(file_path, data)
            results.append(result)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=save_data, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All saves should succeed
        assert all(results)
        assert file_path.exists()

        # File should be valid JSON
        with open(file_path, "r") as f:
            final_data = json.load(f)
        assert "id" in final_data

    def test_backup_restore(self, persistence, temp_dir):
        """Test restoring from backup"""
        file_path = temp_dir / "test_restore.json"
        backup_path = file_path.with_suffix(".json.backup")

        # Create backup manually
        backup_data = {"backup": "data"}
        with open(backup_path, "w") as f:
            json.dump(backup_data, f)

        # Restore using internal method
        result = persistence._restore_from_backup(file_path)

        assert result is True
        assert file_path.exists()

        # Verify restored content
        with open(file_path, "r") as f:
            restored_data = json.load(f)
        assert restored_data == backup_data

    def test_list_state_files(self, persistence, temp_dir):
        """Test listing state files"""
        # Create some test files
        test_files = [
            temp_dir / "test1.json",
            temp_dir / "subdir" / "test2.json",
            temp_dir / "test3.txt",  # Non-JSON file
        ]

        for file_path in test_files:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("{}")

        # List JSON files
        json_files = persistence.list_state_files("*.json")

        assert len(json_files) == 2
        assert all(f.suffix == ".json" for f in json_files)

    def test_cleanup_old_files(self, persistence, temp_dir):
        """Test cleanup of old backup files"""
        import os

        # Create old backup files
        old_backup = temp_dir / "old.json.backup"
        recent_backup = temp_dir / "recent.json.backup"

        old_backup.write_text("{}")
        recent_backup.write_text("{}")

        # Make one file old by modifying its timestamp
        old_time = time.time() - (31 * 24 * 3600)  # 31 days ago
        os.utime(old_backup, (old_time, old_time))

        # Cleanup files older than 30 days
        cleaned_count = persistence.cleanup_old_files(max_age_days=30)

        assert cleaned_count == 1
        assert not old_backup.exists()
        assert recent_backup.exists()

    def test_performance_requirement(self, persistence, sample_checkpoint, temp_dir):
        """Test that save operations complete within 2 seconds"""
        file_path = temp_dir / "performance_test.json"

        start_time = time.time()
        result = persistence.save_state_atomic(file_path, sample_checkpoint)
        duration = time.time() - start_time

        assert result is True
        assert duration < 2.0  # Must complete within 2 seconds


if __name__ == "__main__":
    pytest.main([__file__])
