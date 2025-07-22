"""Unit tests for DownloadOrchestrator."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import Future

from compute_forecast.orchestration.download_orchestrator import (
    DownloadOrchestrator,
    FailedPaper,
)
from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.consolidation.models import URLRecord


class TestDownloadOrchestrator:
    """Test DownloadOrchestrator functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_storage_manager(self):
        """Create mock storage manager."""
        mock = Mock()
        mock.exists.return_value = (False, None)
        mock.save_pdf.return_value = (True, None)
        return mock

    @pytest.fixture
    def mock_progress_manager(self):
        """Create mock progress manager."""
        mock = Mock()
        mock.get_progress_callback.return_value = Mock()
        mock.start_download = Mock()
        mock.complete_download = Mock()
        mock.log = Mock()
        mock.stop = Mock()
        return mock

    @pytest.fixture
    def orchestrator(self, temp_dir, mock_storage_manager, mock_progress_manager):
        """Create DownloadOrchestrator instance."""
        orchestrator = DownloadOrchestrator(
            parallel_workers=2,
            rate_limit=None,
            timeout=30,
            max_retries=3,
            retry_delay=1,
            exponential_backoff=True,
            cache_dir=str(temp_dir / "cache"),
            progress_manager=mock_progress_manager,
            state_path=temp_dir / "state.json",
        )
        # Replace the storage manager with our mock
        orchestrator.storage_manager = mock_storage_manager
        return orchestrator

    @pytest.fixture
    def sample_paper(self):
        """Create sample paper for testing."""
        return Paper(
            paper_id="test_paper_1",
            title="Test Paper 1",
            authors=[Author(name="Author 1", affiliations=[], email="")],
            venue="Test Conference",
            year=2024,
            urls=[
                URLRecord(
                    source="test",
                    timestamp="2024-01-01T00:00:00",
                    original=True,
                    data={"url": "https://example.com/paper1.pdf"},
                )
            ],
            processing_flags={"selected_pdf_url": "https://example.com/paper1.pdf"},
        )

    def test_categorize_error(self, orchestrator):
        """Test error categorization logic."""
        # Test 404 errors
        error_type, is_permanent = orchestrator._categorize_error("HTTP 404 Not Found")
        assert error_type == "http_404"
        assert is_permanent is True

        # Test 403 errors
        error_type, is_permanent = orchestrator._categorize_error("HTTP 403 Forbidden")
        assert error_type == "http_403"
        assert is_permanent is True

        # Test server errors
        error_type, is_permanent = orchestrator._categorize_error(
            "HTTP 503 Service Unavailable"
        )
        assert error_type == "http_server_error"
        assert is_permanent is False

        # Test timeout errors
        error_type, is_permanent = orchestrator._categorize_error("Connection timeout")
        assert error_type == "timeout"
        assert is_permanent is False

        # Test connection errors
        error_type, is_permanent = orchestrator._categorize_error("Connection refused")
        assert error_type == "connection_error"
        assert is_permanent is False

        # Test validation errors
        error_type, is_permanent = orchestrator._categorize_error("Invalid PDF file")
        assert error_type == "validation_error"
        assert is_permanent is True

        # Test unknown errors
        error_type, is_permanent = orchestrator._categorize_error(
            "Something went wrong"
        )
        assert error_type == "other"
        assert is_permanent is False

    def test_update_state(self, orchestrator, sample_paper):
        """Test state update logic."""
        # Test marking as in progress
        orchestrator._update_state("test_paper_1", "in_progress")
        assert "test_paper_1" in orchestrator.state.in_progress

        # Test marking as completed
        orchestrator._update_state("test_paper_1", "completed")
        assert "test_paper_1" in orchestrator.state.completed
        assert "test_paper_1" not in orchestrator.state.in_progress

        # Test marking as failed with error details
        paper_info = {
            "title": sample_paper.title,
            "pdf_url": sample_paper.processing_flags["selected_pdf_url"],
        }
        orchestrator._update_state("test_paper_1", "failed", "HTTP 404", paper_info)
        assert "test_paper_1" in orchestrator.state.failed
        assert orchestrator.state.failed["test_paper_1"] == "HTTP 404"
        assert len(orchestrator.state.failed_papers) == 1
        assert orchestrator.state.failed_papers[0].paper_id == "test_paper_1"
        assert orchestrator.state.failed_papers[0].error_type == "http_404"
        assert orchestrator.state.failed_papers[0].permanent_failure is True

    def test_filter_papers_for_download(self, orchestrator, mock_storage_manager):
        """Test paper filtering logic."""
        papers = [
            Paper(
                paper_id="paper1",
                title="Paper 1",
                authors=[],
                venue="Test",
                year=2024,
                processing_flags={"selected_pdf_url": "url1"},
            ),
            Paper(
                paper_id="paper2",
                title="Paper 2",
                authors=[],
                venue="Test",
                year=2024,
                processing_flags={"selected_pdf_url": "url2"},
            ),
            Paper(
                paper_id="paper3",
                title="Paper 3",
                authors=[],
                venue="Test",
                year=2024,
                processing_flags={"selected_pdf_url": "url3"},
            ),
        ]

        # Test with empty state - all papers should be included
        filtered = orchestrator.filter_papers_for_download(papers)
        assert len(filtered) == 3

        # Test with completed papers that exist in storage
        orchestrator.state.completed = ["paper1"]
        mock_storage_manager.exists.return_value = (True, "local")
        filtered = orchestrator.filter_papers_for_download(papers)
        assert len(filtered) == 2
        assert all(p.paper_id != "paper1" for p in filtered)

        # Test with completed papers that don't exist in storage (re-download)
        orchestrator.state.completed = ["paper1"]
        mock_storage_manager.exists.return_value = (False, None)
        filtered = orchestrator.filter_papers_for_download(papers)
        assert len(filtered) == 3  # paper1 is re-added since not found

        # Reset state for next tests
        orchestrator.state.completed = []

        # Test with failed papers (no retry)
        orchestrator.state.failed = {"paper2": "Some error"}
        filtered = orchestrator.filter_papers_for_download(papers, retry_failed=False)
        assert len(filtered) == 2  # paper1 and paper3
        assert set(p.paper_id for p in filtered) == {"paper1", "paper3"}

        # Test with failed papers (with retry)
        filtered = orchestrator.filter_papers_for_download(papers, retry_failed=True)
        assert len(filtered) == 3  # All papers including failed paper2

    def test_download_single_paper_success(
        self, orchestrator, sample_paper, mock_storage_manager
    ):
        """Test successful single paper download."""
        mock_downloader = Mock()
        mock_downloader.download_pdf.return_value = (True, None)

        # Paper doesn't exist in storage
        mock_storage_manager.exists.return_value = (False, None)

        # Use a simpler paper without urls to avoid the url.data.url issue
        simple_paper = Paper(
            paper_id="test_paper",
            title="Test Paper",
            authors=[],
            venue="Test",
            year=2024,
            processing_flags={"selected_pdf_url": "https://example.com/paper.pdf"},
        )

        success, error = orchestrator._download_single_paper(
            simple_paper, mock_downloader
        )

        assert success is True
        assert error is None
        mock_downloader.download_pdf.assert_called_once()

        # Check progress callback was passed
        call_args = mock_downloader.download_pdf.call_args
        assert "progress_callback" in call_args.kwargs

    def test_download_single_paper_already_exists(
        self, orchestrator, sample_paper, mock_storage_manager
    ):
        """Test download when paper already exists."""
        mock_downloader = Mock()

        # Paper exists in storage
        mock_storage_manager.exists.return_value = (True, "local")

        success, error = orchestrator._download_single_paper(
            sample_paper, mock_downloader
        )

        assert success is True
        assert error is None
        mock_downloader.download_pdf.assert_not_called()

    def test_download_single_paper_failure(
        self, orchestrator, sample_paper, mock_storage_manager
    ):
        """Test failed single paper download."""
        mock_downloader = Mock()
        mock_downloader.download_pdf.return_value = (False, "HTTP 404 Not Found")

        # Use a simpler paper without urls
        simple_paper = Paper(
            paper_id="test_paper",
            title="Test Paper",
            authors=[],
            venue="Test",
            year=2024,
            processing_flags={"selected_pdf_url": "https://example.com/paper.pdf"},
        )

        success, error = orchestrator._download_single_paper(
            simple_paper, mock_downloader
        )

        assert success is False
        assert error == "HTTP 404 Not Found"

    def test_download_single_paper_no_url(self, orchestrator, mock_storage_manager):
        """Test download with missing URL."""
        paper = Paper(
            paper_id="test",
            title="Test",
            authors=[],
            venue="Test",
            year=2024,
            processing_flags={},
        )
        mock_downloader = Mock()

        success, error = orchestrator._download_single_paper(paper, mock_downloader)

        assert success is False
        assert error == "No PDF URL found"
        mock_downloader.download_pdf.assert_not_called()

    @patch("compute_forecast.orchestration.download_orchestrator.as_completed")
    @patch("compute_forecast.orchestration.download_orchestrator.PDFDownloader")
    @patch("compute_forecast.orchestration.download_orchestrator.ThreadPoolExecutor")
    def test_concurrent_downloads(
        self,
        mock_executor_class,
        mock_downloader_class,
        mock_as_completed,
        orchestrator,
        mock_storage_manager,
        mock_progress_manager,
    ):
        """Test concurrent download execution."""
        # Create papers
        papers = [
            Paper(
                paper_id=f"paper{i}",
                title=f"Paper {i}",
                authors=[],
                venue="Test",
                year=2024,
                processing_flags={"selected_pdf_url": f"url{i}"},
            )
            for i in range(3)
        ]

        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_pdf.return_value = (True, None)
        mock_downloader_class.return_value = mock_downloader

        # Mock executor and futures
        submitted_futures = []

        def mock_submit(func, *args):
            future = Mock(spec=Future)
            future.result.return_value = (True, None)
            submitted_futures.append(future)
            return future

        mock_executor = MagicMock()
        mock_executor.submit.side_effect = mock_submit
        mock_executor.__enter__.return_value = mock_executor
        mock_executor_class.return_value = mock_executor

        # Mock as_completed to return the submitted futures
        def mock_as_completed_func(futures_dict):
            return futures_dict.keys()

        mock_as_completed.side_effect = mock_as_completed_func

        successful, failed = orchestrator.download_papers(papers)

        assert successful == 3
        assert failed == 0
        assert mock_executor.submit.call_count == 3
        mock_progress_manager.stop.assert_called_once()

    def test_rate_limiting(self, orchestrator):
        """Test rate limiting enforcement."""
        import time

        orchestrator.rate_limit = 2.0  # 2 requests per second
        orchestrator._min_request_interval = 0.5  # Should wait 0.5s between requests
        orchestrator._last_request_time = time.time()

        start_time = time.time()
        orchestrator._enforce_rate_limit()  # First call should not wait
        orchestrator._enforce_rate_limit()  # Second call should wait 0.5s
        end_time = time.time()

        # Should have delayed at least 0.5 seconds
        elapsed = end_time - start_time
        assert elapsed >= 0.45  # Allow small margin for timing variance

    def test_export_failed_papers(self, orchestrator, temp_dir):
        """Test failed papers export functionality."""
        # Add some failed papers
        orchestrator.state.failed_papers = [
            FailedPaper(
                paper_id="paper1",
                title="Paper 1",
                pdf_url="url1",
                error_message="HTTP 404",
                error_type="http_404",
                attempts=1,
                last_attempt=datetime.now().isoformat(),
                permanent_failure=True,
            ),
            FailedPaper(
                paper_id="paper2",
                title="Paper 2",
                pdf_url="url2",
                error_message="Timeout",
                error_type="timeout",
                attempts=3,
                last_attempt=datetime.now().isoformat(),
                permanent_failure=False,
            ),
        ]

        output_path = temp_dir / "failed_papers.json"
        result = orchestrator.export_failed_papers(output_path)

        assert result == output_path
        assert output_path.exists()

        # Check content
        with open(output_path) as f:
            data = json.load(f)

        assert data["total_failed_papers"] == 2
        assert data["permanent_failures"] == 1
        assert data["temporary_failures"] == 1
        assert len(data["failed_papers"]) == 2
        assert "summary_by_error_type" in data

    def test_export_failed_papers_empty(self, orchestrator, temp_dir):
        """Test export with no failed papers."""
        result = orchestrator.export_failed_papers()
        assert result is None

    def test_save_and_load_state(self, orchestrator, temp_dir):
        """Test state persistence."""
        # Set up some state
        orchestrator.state.completed = ["paper1", "paper2"]
        orchestrator.state.failed = {"paper3": "Error"}
        orchestrator.state.in_progress = ["paper4"]

        # Save state
        orchestrator._save_state()

        # Create new orchestrator and load state
        new_orchestrator = DownloadOrchestrator(
            parallel_workers=2, state_path=orchestrator.state_path
        )

        loaded_state = new_orchestrator._load_state()

        assert loaded_state.completed == ["paper1", "paper2"]
        assert loaded_state.failed == {"paper3": "Error"}
        assert loaded_state.in_progress == ["paper4"]

    def test_state_thread_safety(self, orchestrator):
        """Test thread-safe state updates."""
        import threading

        def update_state(paper_id, status):
            orchestrator._update_state(paper_id, status)

        # Create multiple threads updating state
        threads = []
        for i in range(10):
            t = threading.Thread(target=update_state, args=(f"paper{i}", "completed"))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All updates should be recorded
        assert len(orchestrator.state.completed) == 10

    @patch("compute_forecast.orchestration.download_orchestrator.PDFDownloader")
    def test_download_papers_with_save_callback(
        self, mock_downloader_class, orchestrator
    ):
        """Test download with periodic save callback."""
        papers = [
            Paper(
                paper_id=f"paper{i}",
                title=f"Paper {i}",
                authors=[],
                venue="Test",
                year=2024,
                processing_flags={"selected_pdf_url": f"url{i}"},
            )
            for i in range(12)  # More than 10 to trigger periodic save
        ]

        mock_downloader = Mock()
        mock_downloader.download_pdf.return_value = (True, None)
        mock_downloader_class.return_value = mock_downloader

        save_callback = Mock()

        with patch.object(
            orchestrator, "_download_single_paper", return_value=(True, None)
        ):
            orchestrator.download_papers(papers, save_papers_callback=save_callback)

        # Should have called save callback at least once (after 10 papers)
        assert save_callback.call_count >= 1
