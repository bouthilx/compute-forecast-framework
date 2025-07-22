"""Unit tests for PDF downloader."""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import Timeout, ConnectionError

from compute_forecast.workers.pdf_downloader import PDFDownloader
from compute_forecast.storage import StorageManager


class TestPDFDownloader:
    """Test PDF downloader functionality."""

    @pytest.fixture
    def mock_storage_manager(self):
        """Create mock storage manager."""
        mock = Mock(spec=StorageManager)
        mock.exists.return_value = (False, "")
        mock.save_pdf.return_value = True
        return mock

    @pytest.fixture
    def downloader(self, mock_storage_manager):
        """Create PDF downloader instance."""
        return PDFDownloader(
            storage_manager=mock_storage_manager,
            timeout=30,
            max_retries=2,
            retry_delay=1,
            exponential_backoff=True,
        )

    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response."""
        response = Mock()
        response.status_code = 200
        response.headers = {"Content-Type": "application/pdf", "Content-Length": "1000"}
        response.text = ""
        response.reason = "OK"

        # Mock iter_content for chunked download
        pdf_content = b"%PDF-1.4\n%Mock PDF content" + b"\x00" * 1000
        response.iter_content = Mock(
            return_value=[
                pdf_content[i : i + 100] for i in range(0, len(pdf_content), 100)
            ]
        )

        return response

    def test_successful_download(self, downloader, mock_response, mock_storage_manager):
        """Test successful PDF download."""
        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/paper.pdf"
            )

            assert success is True
            assert error is None
            assert mock_storage_manager.save_pdf.called

    def test_download_with_progress_callback(
        self, downloader, mock_response, mock_storage_manager
    ):
        """Test download with progress tracking."""
        progress_calls = []

        def progress_callback(paper_id, bytes_transferred, operation, speed):
            progress_calls.append(
                {
                    "paper_id": paper_id,
                    "bytes": bytes_transferred,
                    "operation": operation,
                    "speed": speed,
                }
            )

        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123",
                "https://example.com/paper.pdf",
                progress_callback=progress_callback,
            )

            assert success is True
            assert len(progress_calls) > 0
            assert progress_calls[0]["operation"] == "Starting"
            assert any(call["operation"] == "Downloading" for call in progress_calls)

    def test_http_404_error(self, downloader, mock_storage_manager):
        """Test handling of 404 errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.reason = "Not Found"

        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/missing.pdf"
            )

            assert success is False
            assert "HTTP 404" in error
            assert "Not Found" in error

    def test_http_403_forbidden(self, downloader, mock_storage_manager):
        """Test handling of 403 forbidden errors."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Access Denied"
        mock_response.reason = "Forbidden"

        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/forbidden.pdf"
            )

            assert success is False
            assert "HTTP 403" in error

    def test_timeout_error(self, downloader, mock_storage_manager):
        """Test handling of timeout errors."""
        with patch.object(
            downloader.session, "get", side_effect=Timeout("Connection timed out")
        ):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/slow.pdf"
            )

            assert success is False
            assert "timeout" in error.lower()
            assert "30s" in error  # Should include timeout duration

    def test_connection_error(self, downloader, mock_storage_manager):
        """Test handling of connection errors."""
        with patch.object(
            downloader.session, "get", side_effect=ConnectionError("Connection failed")
        ):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/unreachable.pdf"
            )

            assert success is False
            assert "Connection error" in error

    def test_retry_on_server_error(self, downloader, mock_storage_manager):
        """Test retry logic for server errors."""
        # First attempt fails with 500, second succeeds
        pdf_content = b"%PDF-1.4\n%Mock PDF content" + b"\x00" * 2000
        mock_responses = [
            Mock(status_code=500, text="Server Error", reason="Internal Server Error"),
            Mock(
                status_code=200,
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Length": str(len(pdf_content)),
                },
                iter_content=Mock(
                    return_value=[
                        pdf_content[i : i + 100]
                        for i in range(0, len(pdf_content), 100)
                    ]
                ),
            ),
        ]

        with patch.object(downloader.session, "get", side_effect=mock_responses):
            with patch("time.sleep"):  # Don't actually sleep in tests
                success, error = downloader.download_pdf(
                    "test_paper_123", "https://example.com/flaky.pdf"
                )

                # Should succeed after retry
                assert success is True
                assert error is None

    def test_max_retries_exceeded(self, downloader, mock_storage_manager):
        """Test that max retries are respected."""
        # All attempts fail with 500
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.reason = "Internal Server Error"

        with patch.object(downloader.session, "get", return_value=mock_response):
            with patch("time.sleep"):  # Don't actually sleep in tests
                success, error = downloader.download_pdf(
                    "test_paper_123", "https://example.com/always_fails.pdf"
                )

                assert success is False
                assert error is not None

    def test_non_retryable_errors(self, downloader, mock_storage_manager):
        """Test that certain errors are not retried."""
        # 404 should not be retried
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.reason = "Not Found"

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(downloader.session, "get", side_effect=mock_get):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/404.pdf"
            )

            assert success is False
            assert "HTTP 404" in error
            assert call_count == 1  # Should not retry

    def test_html_content_detection(self, downloader, mock_storage_manager):
        """Test detection of HTML content instead of PDF."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html", "Content-Length": "2000"}
        mock_response.text = ""

        # Return HTML content with enough size to pass size check
        html_content = (
            b"<!DOCTYPE html><html><body>Error page" + b"x" * 2000 + b"</body></html>"
        )
        mock_response.iter_content = Mock(
            return_value=[
                html_content[i : i + 100] for i in range(0, len(html_content), 100)
            ]
        )

        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/fake.pdf"
            )

            assert success is False
            assert "HTML" in error

    def test_invalid_pdf_header(self, downloader, mock_storage_manager):
        """Test detection of invalid PDF header."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": "2000",
        }
        mock_response.text = ""

        # Return content without PDF header but with sufficient size
        invalid_content = b"This is not a PDF file" + b"\x00" * 2000
        mock_response.iter_content = Mock(
            return_value=[
                invalid_content[i : i + 100]
                for i in range(0, len(invalid_content), 100)
            ]
        )

        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/invalid.pdf"
            )

            assert success is False
            assert "Invalid PDF header" in error

    def test_file_too_small(self, downloader, mock_storage_manager):
        """Test detection of files that are too small."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": "100",
        }
        mock_response.text = ""

        # Return very small content
        mock_response.iter_content = Mock(return_value=[b"%PDF"])

        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/tiny.pdf"
            )

            assert success is False
            assert "too small" in error

    def test_storage_failure(self, downloader, mock_storage_manager):
        """Test handling of storage save failures."""
        mock_storage_manager.save_pdf.return_value = False

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": "1000",
        }
        mock_response.text = ""

        pdf_content = b"%PDF-1.4\n%Mock PDF content" + b"\x00" * 1000
        mock_response.iter_content = Mock(return_value=[pdf_content])

        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/paper.pdf"
            )

            assert success is False
            assert "Failed to save to storage" in error

    def test_already_exists_in_storage(self, downloader, mock_storage_manager):
        """Test behavior when PDF already exists."""
        mock_storage_manager.exists.return_value = (True, "cache")

        with patch.object(downloader.session, "get") as mock_get:
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/paper.pdf"
            )

            assert success is True
            assert error is None
            # Should not attempt download
            assert not mock_get.called

    def test_exponential_backoff(self, downloader, mock_storage_manager):
        """Test exponential backoff calculation."""
        downloader.exponential_backoff = True
        downloader.retry_delay = 2

        sleep_times = []

        def mock_sleep(seconds):
            sleep_times.append(seconds)

        # All attempts fail
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.reason = "Internal Server Error"

        with patch.object(downloader.session, "get", return_value=mock_response):
            with patch("time.sleep", side_effect=mock_sleep):
                success, error = downloader.download_pdf(
                    "test_paper_123", "https://example.com/error.pdf"
                )

                assert success is False
                # Check exponential backoff: 2, 4, 8...
                assert len(sleep_times) == 2  # max_retries = 2
                assert sleep_times[0] == 2
                assert sleep_times[1] == 4

    def test_metadata_passed_to_storage(self, downloader, mock_storage_manager):
        """Test that metadata is passed to storage manager."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": "2000",
        }
        mock_response.text = ""

        pdf_content = b"%PDF-1.4\n%Mock PDF content" + b"\x00" * 2000
        mock_response.iter_content = Mock(
            return_value=[
                pdf_content[i : i + 100] for i in range(0, len(pdf_content), 100)
            ]
        )

        metadata = {"title": "Test Paper", "authors": ["Author 1", "Author 2"]}

        with patch.object(downloader.session, "get", return_value=mock_response):
            success, error = downloader.download_pdf(
                "test_paper_123", "https://example.com/paper.pdf", metadata=metadata
            )

            assert success is True
            # Check that metadata was passed to storage
            # save_pdf is called with positional args: paper_id, source_path, progress_callback, metadata
            call_args = mock_storage_manager.save_pdf.call_args
            assert len(call_args[0]) >= 4 or "metadata" in call_args[1]
            # The metadata is the 4th positional argument or a keyword argument
            if len(call_args[0]) >= 4:
                assert call_args[0][3] == metadata
            else:
                assert call_args[1].get("metadata") == metadata

    def test_session_configuration(self):
        """Test that session is properly configured."""
        mock_storage = Mock(spec=StorageManager)
        downloader = PDFDownloader(
            storage_manager=mock_storage, max_retries=3, exponential_backoff=True
        )

        # Check that session has proper headers
        assert "User-Agent" in downloader.session.headers

        # Check that retry adapter is configured
        assert "http://" in downloader.session.adapters
        assert "https://" in downloader.session.adapters
