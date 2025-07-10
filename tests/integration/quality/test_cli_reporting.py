"""Integration tests for CLI command and reporting functionality."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from typer.testing import CliRunner
import json

from compute_forecast.cli.main import app


class TestCLIReporting:
    """Test CLI command with reporting features."""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    def test_cli_with_custom_thresholds(self, sample_collection_data):
        """Test CLI with custom threshold options."""
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text(json.dumps(sample_collection_data))
            
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--min-completeness", "0.95",
                "--min-coverage", "0.85",
                "--verbose"
            ])
            
            assert result.exit_code == 0
            assert "COLLECTION QUALITY REPORT" in result.output
            # Custom thresholds should be reflected in the assessment
    
    def test_cli_output_formats(self, sample_collection_data):
        """Test different output formats."""
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text(json.dumps(sample_collection_data))
            
            # Test JSON format
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--format", "json"
            ])
            
            assert result.exit_code == 0
            # Should be valid JSON - strip any leading/trailing whitespace
            try:
                output_data = json.loads(result.output.strip())
                assert "report_info" in output_data
                assert output_data["report_info"]["stage"] == "collection"
            except json.JSONDecodeError:
                # Might have additional output, try to find JSON part
                lines = result.output.split('\n')
                json_start = None
                for i, line in enumerate(lines):
                    if line.strip().startswith('{'):
                        json_start = i
                        break
                if json_start is not None:
                    json_content = '\n'.join(lines[json_start:])
                    output_data = json.loads(json_content)
                    assert "report_info" in output_data
                    assert output_data["report_info"]["stage"] == "collection"
                else:
                    pytest.fail(f"No valid JSON found in output: {result.output}")
            
            # Test Markdown format
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--format", "markdown"
            ])
            
            assert result.exit_code == 0
            assert "# Collection Quality Report" in result.output
            assert "## Overall Quality Score" in result.output
    
    def test_cli_output_to_file(self, sample_collection_data):
        """Test output to file functionality."""
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            output_file = Path(tmp_dir) / "report.md"
            data_file.write_text(json.dumps(sample_collection_data))
            
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--format", "markdown",
                "--output", str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            assert "Report saved to" in result.output
            
            # Verify file content
            content = output_file.read_text()
            assert "# Collection Quality Report" in content
    
    def test_cli_progress_tracking(self, sample_collection_data):
        """Test progress tracking displays correctly."""
        # Progress tracking is harder to test in CLI
        # We mainly verify it doesn't break the command
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text(json.dumps(sample_collection_data))
            
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection"
            ])
            
            assert result.exit_code == 0
            # Progress indicators should not appear in non-TTY output
    
    def test_cli_all_stages(self, sample_collection_data):
        """Test running all applicable stages."""
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text(json.dumps(sample_collection_data))
            
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--all"
            ])
            
            assert result.exit_code == 0
            # Should include collection report
            assert "COLLECTION QUALITY REPORT" in result.output or "collection" in result.output.lower()
    
    def test_cli_skip_checks(self, sample_collection_data):
        """Test skipping specific checks."""
        with TemporaryDirectory() as tmp_dir:
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text(json.dumps(sample_collection_data))
            
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--skip-checks", "accuracy,coverage"
            ])
            
            assert result.exit_code == 0
            # Verify skipped checks don't appear
            assert "Accuracy_Check" not in result.output
            assert "Coverage_Check" not in result.output
    
    def test_cli_fail_on_critical(self):
        """Test fail-on-critical flag."""
        with TemporaryDirectory() as tmp_dir:
            # Create data with critical issues (empty collection)
            data_file = Path(tmp_dir) / "test_data.json"
            data_file.write_text("[]")
            
            # Should fail with default fail-on-critical=True
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection"
            ])
            
            assert result.exit_code == 1
            assert "critical issues" in result.output.lower()
            
            # Should succeed with --no-fail-on-critical
            result = self.runner.invoke(app, [
                "quality",
                str(data_file),
                "--stage", "collection",
                "--no-fail-on-critical"
            ])
            
            assert result.exit_code == 0
    
    def test_cli_list_options(self):
        """Test list-stages and list-checks options."""
        # Test list stages
        result = self.runner.invoke(app, ["quality", "--list-stages"])
        assert result.exit_code == 0
        assert "collection" in result.output
        
        # Test list checks
        result = self.runner.invoke(app, ["quality", "--list-checks", "collection"])
        assert result.exit_code == 0
        assert "completeness" in result.output
        assert "consistency" in result.output
        assert "accuracy" in result.output
        assert "coverage" in result.output


@pytest.fixture
def sample_collection_data():
    """Sample collection data for testing."""
    return [
        {
            "title": "Test Paper 1: Machine Learning",
            "authors": ["John Doe", "Jane Smith"],
            "venue": "NeurIPS",
            "year": 2023,
            "abstract": "This paper presents advances in ML.",
            "pdf_url": "https://example.com/paper1.pdf",
            "doi": "10.1234/paper1",
            "scraper_source": "neurips_scraper"
        },
        {
            "title": "Test Paper 2: Deep Learning",
            "authors": ["Alice Johnson"],
            "venue": "ICML",
            "year": 2023,
            "abstract": "This paper explores DL techniques.",
            "pdf_url": "https://example.com/paper2.pdf",
            "scraper_source": "icml_scraper"
        }
    ]