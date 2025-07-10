import json
from typer.testing import CliRunner

from compute_forecast.cli.main import app


def test_consolidate_command(tmp_path):
    """Test consolidate CLI command"""
    # Create test input
    input_file = tmp_path / "test_papers.json"
    input_data = {
        "papers": [
            {
                "title": "Test Paper",
                "authors": [{"name": "John Doe", "affiliations": []}],
                "venue": "ICML",
                "year": 2023,
                "paper_id": "test1",
                "citations": 0
            }
        ]
    }
    
    with open(input_file, "w") as f:
        json.dump(input_data, f)
    
    # Run command
    runner = CliRunner()
    result = runner.invoke(app, [
        "consolidate",
        "--input", str(input_file),
        "--output", str(tmp_path / "output.json"),
        "--dry-run"
    ])
    
    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    assert "1 papers" in result.output