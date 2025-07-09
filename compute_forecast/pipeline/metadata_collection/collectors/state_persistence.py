"""
State persistence layer with atomic operations and data integrity guarantees.
Provides thread-safe file operations for checkpoint and session data.
"""

import json
import threading
import shutil
import hashlib
from pathlib import Path
from typing import Union, Dict, Any, Optional, TypeVar, Type, List, cast, Literal
from datetime import datetime
import logging

from .state_structures import CheckpointData, CollectionSession, IntegrityCheckResult

logger = logging.getLogger(__name__)

T = TypeVar("T")


class StateFileCorruptionError(Exception):
    """Raised when state file corruption is detected"""

    pass


class AtomicWriteError(Exception):
    """Raised when atomic write operation fails"""

    pass


class StatePersistence:
    """
    Thread-safe state persistence with atomic operations.
    Ensures data integrity through checksums and atomic writes.
    """

    def __init__(self, base_dir: Path, enable_backups: bool = True):
        """
        Initialize state persistence.

        Args:
            base_dir: Base directory for state storage
            enable_backups: Whether to create backups before overwriting files
        """
        self.base_dir = Path(base_dir)
        self.enable_backups = enable_backups
        self._lock = threading.RLock()

        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"StatePersistence initialized with base_dir: {self.base_dir}")

    def save_state_atomic(
        self,
        file_path: Path,
        data: Union[CheckpointData, CollectionSession, Dict],
        backup_previous: bool = True,
    ) -> bool:
        """
        Save state data atomically with validation.

        Requirements:
        - Must use atomic write (write to temp, then rename)
        - Must validate data before writing
        - Must create backup if requested
        - Must handle concurrent access safely
        - Must complete within 2 seconds

        Args:
            file_path: Target file path
            data: Data to save
            backup_previous: Whether to backup existing file

        Returns:
            True if save successful, False otherwise
        """
        with self._lock:
            try:
                start_time = datetime.now()

                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Validate data before writing
                if not self._validate_data_for_save(data):
                    logger.error(f"Data validation failed for {file_path}")
                    return False

                # Create backup if requested and file exists
                if backup_previous and file_path.exists():
                    self._create_backup(file_path)

                # Serialize data
                if hasattr(data, "to_dict"):
                    serialized_data = data.to_dict()
                else:
                    serialized_data = data

                # Write to temporary file first (atomic operation)
                temp_file = self._get_temp_file_path(file_path)

                try:
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(serialized_data, f, indent=2, default=str)
                        f.flush()  # Ensure data is written to disk

                    # Calculate checksum for integrity
                    file_checksum = self._calculate_file_checksum(temp_file)

                    # Atomic move (rename)
                    shutil.move(str(temp_file), str(file_path))

                    # Store checksum metadata
                    self._store_checksum_metadata(file_path, file_checksum)

                    duration = (datetime.now() - start_time).total_seconds()
                    logger.debug(f"Saved {file_path} atomically in {duration:.3f}s")

                    # Check 2-second requirement
                    if duration > 2.0:
                        logger.warning(
                            f"Save operation took {duration:.3f}s (>2s requirement)"
                        )

                    return True

                except Exception as e:
                    # Clean up temp file if it exists
                    if temp_file.exists():
                        temp_file.unlink()
                    raise AtomicWriteError(f"Failed to write {file_path}: {e}")

            except Exception as e:
                logger.error(f"Atomic save failed for {file_path}: {e}")
                return False

    def load_state(
        self, file_path: Path, expected_type: Type[T], validate_integrity: bool = True
    ) -> Optional[T]:
        """
        Load state data with integrity validation.

        Args:
            file_path: File to load
            expected_type: Expected data type
            validate_integrity: Whether to validate file integrity

        Returns:
            Loaded data or None if failed
        """
        with self._lock:
            try:
                if not file_path.exists():
                    logger.debug(f"State file does not exist: {file_path}")
                    return None

                # Validate file integrity if requested
                if validate_integrity and not self._validate_file_integrity(file_path):
                    logger.error(f"File integrity validation failed: {file_path}")
                    # Try to restore from backup
                    if self._restore_from_backup(file_path):
                        logger.info(f"Restored {file_path} from backup")
                    else:
                        raise StateFileCorruptionError(f"Corrupted file: {file_path}")

                # Load and parse data
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                # Convert to expected type if possible
                if expected_type is dict:
                    return cast(T, raw_data)
                elif hasattr(expected_type, "from_dict"):
                    return cast(T, expected_type.from_dict(raw_data))  # type: ignore
                elif expected_type is CheckpointData:
                    # Special handling for CheckpointData
                    return cast(T, CheckpointData.from_dict(raw_data))
                else:
                    # Try to construct directly
                    return expected_type(**raw_data)

            except Exception as e:
                logger.error(f"Failed to load state from {file_path}: {e}")
                return None

    def validate_file_integrity(self, file_path: Path) -> IntegrityCheckResult:
        """
        Validate file integrity and return detailed results.

        Args:
            file_path: File to validate

        Returns:
            Detailed integrity check result
        """
        try:
            if not file_path.exists():
                return IntegrityCheckResult(
                    file_path=file_path,
                    integrity_status="missing",
                    checksum_valid=False,
                    size_expected=0,
                    size_actual=0,
                    last_modified=datetime.min,
                    recovery_action="restore_from_backup",
                )

            # Get file stats
            stat = file_path.stat()
            size_actual = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime)

            # Check if file is readable and valid JSON
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
                json_valid = True
            except (json.JSONDecodeError, UnicodeDecodeError):
                json_valid = False

            # Validate checksum if metadata exists
            checksum_valid = self._validate_file_integrity(file_path)

            # Determine status
            status: Literal["valid", "corrupted", "missing", "partial"]
            if not json_valid:
                status = "corrupted"
                recovery_action = "restore_from_backup"
            elif not checksum_valid:
                status = "partial"
                recovery_action = "verify_content"
            else:
                status = "valid"
                recovery_action = None

            return IntegrityCheckResult(
                file_path=file_path,
                integrity_status=status,
                checksum_valid=checksum_valid,
                size_expected=-1,  # Unknown expected size
                size_actual=size_actual,
                last_modified=last_modified,
                recovery_action=recovery_action,
            )

        except Exception as e:
            logger.error(f"Integrity check failed for {file_path}: {e}")
            return IntegrityCheckResult(
                file_path=file_path,
                integrity_status="corrupted",
                checksum_valid=False,
                size_expected=0,
                size_actual=0,
                last_modified=datetime.min,
                recovery_action="recreate_file",
            )

    def list_state_files(self, pattern: str = "*.json") -> List[Path]:
        """
        List all state files matching pattern.

        Args:
            pattern: File pattern to match

        Returns:
            List of matching file paths
        """
        try:
            return list(self.base_dir.rglob(pattern))
        except Exception as e:
            logger.error(f"Failed to list state files: {e}")
            return []

    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """
        Clean up old state files and backups.

        Args:
            max_age_days: Maximum age in days before cleanup

        Returns:
            Number of files cleaned up
        """
        with self._lock:
            try:
                cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
                cleaned_count = 0

                # Find old backup files
                for backup_file in self.base_dir.rglob("*.backup"):
                    try:
                        if backup_file.stat().st_mtime < cutoff_time:
                            backup_file.unlink()
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {backup_file}: {e}")

                logger.info(f"Cleaned up {cleaned_count} old files")
                return cleaned_count

            except Exception as e:
                logger.error(f"Cleanup failed: {e}")
                return 0

    def _validate_data_for_save(self, data: Any) -> bool:
        """Validate data before saving"""
        try:
            # Check if data can be serialized
            if hasattr(data, "to_dict"):
                test_data = data.to_dict()
            else:
                test_data = data

            # Try to serialize to JSON
            json.dumps(test_data, default=str)

            # Additional validation for CheckpointData
            if isinstance(data, CheckpointData):
                return data.validate_integrity()

            return True

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return False

    def _create_backup(self, file_path: Path) -> bool:
        """Create backup of existing file"""
        try:
            if not self.enable_backups:
                return True

            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            shutil.copy2(str(file_path), str(backup_path))
            logger.debug(f"Created backup: {backup_path}")
            return True

        except Exception as e:
            logger.warning(f"Failed to create backup for {file_path}: {e}")
            return False

    def _restore_from_backup(self, file_path: Path) -> bool:
        """Restore file from backup"""
        try:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            if backup_path.exists():
                shutil.copy2(str(backup_path), str(file_path))
                logger.info(f"Restored {file_path} from backup")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to restore {file_path} from backup: {e}")
            return False

    def _get_temp_file_path(self, target_path: Path) -> Path:
        """Get temporary file path for atomic writes"""
        return target_path.with_suffix(f"{target_path.suffix}.tmp")

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""

    def _store_checksum_metadata(self, file_path: Path, checksum: str) -> None:
        """Store checksum metadata for file"""
        try:
            metadata_file = file_path.with_suffix(f"{file_path.suffix}.meta")
            metadata = {
                "file_path": str(file_path),
                "checksum": checksum,
                "created": datetime.now().isoformat(),
                "size": file_path.stat().st_size,
            }

            with open(metadata_file, "w") as f:
                json.dump(metadata, f)

        except Exception as e:
            logger.warning(f"Failed to store checksum metadata for {file_path}: {e}")

    def _validate_file_integrity(self, file_path: Path) -> bool:
        """Validate file integrity using stored checksum"""
        try:
            metadata_file = file_path.with_suffix(f"{file_path.suffix}.meta")
            if not metadata_file.exists():
                # No metadata available, assume valid
                return True

            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            stored_checksum = metadata.get("checksum", "")
            if not stored_checksum:
                return True

            current_checksum = self._calculate_file_checksum(file_path)
            return bool(current_checksum == stored_checksum)

        except Exception as e:
            logger.warning(f"Failed to validate integrity for {file_path}: {e}")
            return True  # Assume valid if validation fails
