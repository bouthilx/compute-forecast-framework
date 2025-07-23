"""Integration tests for download functionality."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import time

from compute_forecast.orchestration import DownloadOrchestrator
from compute_forecast.pipeline.metadata_collection.models import Paper
from typer.testing import CliRunner
from compute_forecast.cli.main import app


class TestDownloadIntegration:
    """Test download command integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_papers(self, temp_dir):
        """Create sample papers JSON file."""
        papers_data = {
            "papers": [
                {
                    "paper_id": "test_paper_1",
                    "title": "Test Paper 1",
                    "authors": [{"name": "Author 1", "affiliations": [], "email": ""}],
                    "venue": "Test Conference",
                    "year": 2024,
                    "urls": [
                        {
                            "source": "test",
                            "timestamp": "2024-01-01T00:00:00",
                            "original": True,
                            "data": {"url": "https://example.com/paper1.pdf"},
                        }
                    ],
                    "processing_flags": {},
                },
                {
                    "paper_id": "test_paper_2",
                    "title": "Test Paper 2",
                    "authors": [{"name": "Author 2", "affiliations": [], "email": ""}],
                    "venue": "Test Conference",
                    "year": 2024,
                    "urls": [
                        {
                            "source": "test",
                            "timestamp": "2024-01-01T00:00:00",
                            "original": True,
                            "data": {"url": "https://example.com/paper2.pdf"},
                        }
                    ],
                    "processing_flags": {},
                },
            ]
        }

        papers_file = temp_dir / "papers.json"
        with open(papers_file, "w") as f:
            json.dump(papers_data, f)

        return papers_file

    @pytest.fixture
    def mock_pdf_content(self):
        """Generate mock PDF content."""
        return b"%PDF-1.4\n%Mock PDF content\n" + b"0" * 10000 + b"\n%%EOF"

    def test_download_command_basic(self, sample_papers, temp_dir, mock_pdf_content):
        """Test basic download command functionality."""
        runner = CliRunner()

        # Mock HTTP requests
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": str(len(mock_pdf_content)),
        }
        mock_response.text = ""
        mock_response.iter_content = Mock(
            return_value=[
                mock_pdf_content[i : i + 1000]
                for i in range(0, len(mock_pdf_content), 1000)
            ]
        )

        with patch("compute_forecast.workers.pdf_downloader.PDFDownloader._create_session") as mock_create:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_create.return_value = mock_session
            
            with patch.dict("os.environ", {"LOCAL_CACHE_DIR": str(temp_dir / "cache")}):
                result = runner.invoke(
                    app, ["download", "--papers", str(sample_papers), "--no-progress"]
                )

                assert result.exit_code == 0
                assert "Starting download of 2 papers" in result.output
                assert "Successful: 2" in result.output

    def test_download_with_failures(self, sample_papers, temp_dir):
        """Test download with some failures."""
        runner = CliRunner()

        # Mock responses - first succeeds, second fails with 404
        responses = [
            Mock(
                status_code=200,
                headers={"Content-Type": "application/pdf", "Content-Length": "10000"},
                text="",
                iter_content=Mock(return_value=[b"%PDF-1.4\n" + b"0" * 10000 + b"\n%%EOF"]),
            ),
            Mock(status_code=404, text="Not Found", reason="Not Found"),
        ]

        with patch("compute_forecast.workers.pdf_downloader.PDFDownloader._create_session") as mock_create:
            mock_session = Mock()
            mock_session.get.side_effect = responses
            mock_create.return_value = mock_session
            
            with patch.dict("os.environ", {"LOCAL_CACHE_DIR": str(temp_dir / "cache")}):
                result = runner.invoke(
                    app, ["download", "--papers", str(sample_papers), "--no-progress"]
                )

                assert result.exit_code == 0
                assert "Successful: 1" in result.output
                assert "Failed: 1" in result.output
                assert "Failed papers exported to:" in result.output

    def test_resume_functionality(self, sample_papers, temp_dir, mock_pdf_content):
        """Test resume from checkpoint."""
        runner = CliRunner()

        # Create checkpoint with one paper already completed
        checkpoint_dir = temp_dir / ".cf_state" / "download"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_data = {
            "completed": ["test_paper_1"],
            "failed": {},
            "in_progress": [],
            "last_updated": "2024-01-01T00:00:00",
        }

        with open(checkpoint_dir / "download_progress.json", "w") as f:
            json.dump(checkpoint_data, f)

        # Create a file in cache for the first paper so it's truly "completed"
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "test_paper_1.pdf").write_bytes(b"dummy pdf content")
        
        # Mock only one request (for second paper)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": str(len(mock_pdf_content)),
        }
        mock_response.text = ""
        mock_response.iter_content = Mock(return_value=[mock_pdf_content])

        with patch("compute_forecast.workers.pdf_downloader.PDFDownloader._create_session") as mock_create:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_create.return_value = mock_session
            with patch.dict("os.environ", {"LOCAL_CACHE_DIR": str(temp_dir / "cache")}):
                with patch(
                    "compute_forecast.cli.commands.download.get_download_state_path",
                    return_value=checkpoint_dir / "download_progress.json",
                ):
                    result = runner.invoke(
                        app,
                        [
                            "download",
                            "--papers",
                            str(sample_papers),
                            "--resume",
                            "--no-progress",
                        ],
                    )

                    assert result.exit_code == 0
                    # Check that it shows 1 paper to download in the table
                    output_lines = result.output.split('\n')
                    table_found = False
                    for i, line in enumerate(output_lines):
                        if "To Download" in line and i + 2 < len(output_lines):
                            # The table row with counts should be 2 lines down
                            data_line = output_lines[i + 2]
                            # Extract numbers from the table row
                            numbers = [s.strip() for s in data_line.split('│') if s.strip().isdigit()]
                            if len(numbers) >= 2:
                                assert numbers[1] == "1"  # To Download column should be 1
                                table_found = True
                                break
                    assert table_found, "Could not find download plan table"
                    
                    # Should show successful download
                    assert "Successful: 1" in result.output
                    # Should only call get once for the second paper
                    assert mock_session.get.call_count == 1

    def test_retry_failed_with_permanent_failures(self, sample_papers, temp_dir):
        """Test that permanent failures are not retried."""
        runner = CliRunner()

        # Create checkpoint with permanent failure
        checkpoint_dir = temp_dir / ".cf_state" / "download"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_data = {
            "completed": [],
            "failed": {"test_paper_1": "HTTP 404"},
            "in_progress": [],
            "last_updated": "2024-01-01T00:00:00",
            "failed_papers": [
                {
                    "paper_id": "test_paper_1",
                    "title": "Test Paper 1",
                    "pdf_url": "https://example.com/paper1.pdf",
                    "error_message": "HTTP 404",
                    "error_type": "http_404",
                    "attempts": 1,
                    "last_attempt": "2024-01-01T00:00:00",
                    "permanent_failure": True,
                }
            ],
        }

        with open(checkpoint_dir / "download_progress.json", "w") as f:
            json.dump(checkpoint_data, f)

        # Mock response for second paper only
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": "10000",
        }
        mock_response.text = ""
        mock_response.iter_content = Mock(return_value=[b"%PDF-1.4\n" + b"0" * 1000])

        with patch("compute_forecast.workers.pdf_downloader.PDFDownloader._create_session") as mock_create:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_create.return_value = mock_session
            with patch.dict("os.environ", {"LOCAL_CACHE_DIR": str(temp_dir / "cache")}):
                with patch(
                    "compute_forecast.cli.commands.download.get_download_state_path",
                    return_value=checkpoint_dir / "download_progress.json",
                ):
                    result = runner.invoke(
                        app,
                        [
                            "download",
                            "--papers",
                            str(sample_papers),
                            "--retry-failed",
                            "--no-progress",
                        ],
                    )

                    assert result.exit_code == 0
                    # Should only attempt to download the second paper
                    assert mock_get.call_count == 1
                    assert "Starting download of 1 papers" in result.output

    def test_parallel_downloads(self, temp_dir):
        """Test parallel download functionality."""
        # Create papers for parallel test
        papers_data = {
            "papers": [
                {
                    "paper_id": f"test_paper_{i}",
                    "title": f"Test Paper {i}",
                    "authors": [
                        {"name": f"Author {i}", "affiliations": [], "email": ""}
                    ],
                    "venue": "Test Conference",
                    "year": 2024,
                    "urls": [
                        {
                            "source": "test",
                            "timestamp": "2024-01-01T00:00:00",
                            "original": True,
                            "data": {"url": f"https://example.com/paper{i}.pdf"},
                        }
                    ],
                    "processing_flags": {},
                }
                for i in range(5)
            ]
        }

        papers_file = temp_dir / "papers.json"
        with open(papers_file, "w") as f:
            json.dump(papers_data, f)

        # Create orchestrator
        orchestrator = DownloadOrchestrator(
            parallel_workers=3,
            cache_dir=str(temp_dir / "cache"),
            state_path=temp_dir / ".cf_state" / "download" / "progress.json",
        )

        # Load papers
        papers = []
        for paper_data in papers_data["papers"]:
            paper = Paper.from_dict(paper_data)
            paper.processing_flags["selected_pdf_url"] = paper_data["urls"][0]["data"][
                "url"
            ]
            papers.append(paper)

        # Track download times
        download_times = {}

        def mock_download(url, **kwargs):
            paper_num = int(url.split("paper")[1].split(".")[0])
            start_time = time.time()

            # Simulate download time
            time.sleep(0.1)

            download_times[paper_num] = start_time

            response = Mock()
            response.status_code = 200
            response.headers = {
                "Content-Type": "application/pdf",
                "Content-Length": "1000",
            }
            response.text = ""
            response.iter_content = Mock(return_value=[b"%PDF-1.4\n" + b"0" * 10000 + b"\n%%EOF"])
            return response

        with patch("compute_forecast.workers.pdf_downloader.PDFDownloader._create_session") as mock_create:
            mock_session = Mock()
            mock_session.get.side_effect = mock_download
            mock_create.return_value = mock_session
            successful, failed = orchestrator.download_papers(papers)

            assert successful == 5
            assert failed == 0

            # Check that downloads happened in parallel
            # With 3 workers, first 3 should start almost simultaneously
            times = sorted(download_times.values())
            first_batch_spread = times[2] - times[0]
            assert first_batch_spread < 0.05  # First 3 should start within 50ms

    def test_failed_papers_export_format(self, sample_papers, temp_dir):
        """Test the format of failed papers export."""
        runner = CliRunner()

        # All requests fail with different errors
        responses = [
            Mock(status_code=404, text="Not Found", reason="Not Found"),
            Mock(status_code=403, text="Forbidden", reason="Forbidden"),
        ]

        with patch("compute_forecast.workers.pdf_downloader.PDFDownloader._create_session") as mock_create:
            mock_session = Mock()
            mock_session.get.side_effect = responses
            mock_create.return_value = mock_session
            
            with patch.dict("os.environ", {"LOCAL_CACHE_DIR": str(temp_dir / "cache")}):
                result = runner.invoke(
                    app, ["download", "--papers", str(sample_papers), "--no-progress"]
                )

                assert result.exit_code == 0

                # Find the failed papers file
                failed_files = list(Path(".").glob("failed_papers_*.json"))
                assert len(failed_files) == 1

                # Check content
                with open(failed_files[0]) as f:
                    failed_data = json.load(f)

                assert "export_timestamp" in failed_data
                assert failed_data["total_failed_papers"] == 2
                assert failed_data["permanent_failures"] == 2
                assert len(failed_data["failed_papers"]) == 2

                # Check error categorization
                error_types = [fp["error_type"] for fp in failed_data["failed_papers"]]
                assert "http_404" in error_types
                assert "http_403" in error_types

                # Cleanup
                failed_files[0].unlink()

    def test_verbosity_levels(self, sample_papers, temp_dir, mock_pdf_content):
        """Test different verbosity levels."""
        runner = CliRunner()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": str(len(mock_pdf_content)),
        }
        mock_response.text = ""
        mock_response.iter_content = Mock(return_value=[mock_pdf_content])

        with patch("compute_forecast.workers.pdf_downloader.PDFDownloader._create_session") as mock_create:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_create.return_value = mock_session
            with patch.dict("os.environ", {"LOCAL_CACHE_DIR": str(temp_dir / "cache")}):
                # Test with -v (INFO level)
                result = runner.invoke(
                    app,
                    ["download", "--papers", str(sample_papers), "-v", "--no-progress"],
                )

                assert result.exit_code == 0
                # Should see INFO level logs
                assert "INFO" in result.output or "Starting download" in result.output

                # Test with -vv (DEBUG level)
                result = runner.invoke(
                    app,
                    [
                        "download",
                        "--papers",
                        str(sample_papers),
                        "-vv",
                        "--no-progress",
                    ],
                )

                assert result.exit_code == 0
                # Should see DEBUG level logs
                assert (
                    "DEBUG" in result.output or "Making HTTP request" in result.output
                )
