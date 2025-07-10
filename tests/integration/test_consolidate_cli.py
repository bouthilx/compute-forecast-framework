import json
from pathlib import Path
from typer.testing import CliRunner

from compute_forecast.cli.main import app


def test_consolidate_command(tmp_path):
    """Test consolidate CLI command with minimal data"""
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


def test_consolidate_command_with_scraper_format(tmp_path):
    """Test consolidate CLI command with scraper data format"""
    # Create test input with scraper format
    input_file = tmp_path / "scraper_papers.json"
    input_data = {
        "collection_metadata": {
            "timestamp": "2025-01-10T10:00:00",
            "venues": ["ICML", "NeurIPS"],
            "years": [2023],
            "total_papers": 3,
            "scrapers_used": ["pmlr", "paperoni_neurips"],
            "errors": []
        },
        "papers": [
            {
                "title": "Paper with string authors",
                "authors": ["John Doe", "Jane Smith"],  # String authors
                "venue": "ICML",
                "year": 2023,
                "abstract": None,  # None abstract
                "pdf_urls": ["https://example.com/paper1.pdf"],  # pdf_urls field
                "keywords": [],
                "doi": None,
                "arxiv_id": None,
                "paper_id": None,  # No ID
                "source_scraper": "pmlr",
                "source_url": "https://proceedings.mlr.press/",
                "scraped_at": "2025-01-10T09:00:00",
                "extraction_confidence": 0.95,
                "metadata_completeness": 0.8
            },
            {
                "title": "Paper with mixed data",
                "authors": [{"name": "Alice Brown", "affiliation": "MIT"}],  # Old author format
                "venue": "NeurIPS",
                "year": 2023,
                "abstract": "Existing abstract",
                "pdf_urls": [],
                "keywords": ["machine learning"],
                "doi": "10.1234/test",
                "arxiv_id": None,
                "paper_id": None,
                "source_scraper": "paperoni_neurips",
                "source_url": "https://neurips.cc/",
                "scraped_at": "2025-01-10T09:30:00",
                "extraction_confidence": 0.9,
                "metadata_completeness": 0.7
            },
            {
                "title": "Complete paper",
                "authors": [{"name": "Bob Wilson", "affiliations": ["Stanford"]}],  # New format
                "venue": "ICML",
                "year": 2023,
                "abstract": "",
                "urls": ["https://example.com/paper3.pdf"],  # Already has urls field
                "keywords": [],
                "doi": "",
                "arxiv_id": "",
                "paper_id": "existing-id",
                "citations": 5,
                "collection_timestamp": "2025-01-10T08:00:00"
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
    assert "3 papers" in result.output
    
    # Test actual run (not dry-run)
    output_file = tmp_path / "enriched.json"
    result = runner.invoke(app, [
        "consolidate",
        "--input", str(input_file),
        "--output", str(output_file),
        "--sources", "semantic_scholar"  # Only one source to avoid rate limits in tests
    ])
    
    assert result.exit_code == 0
    assert output_file.exists()
    
    # Verify output format
    with open(output_file) as f:
        output_data = json.load(f)
    
    assert "consolidation_metadata" in output_data
    assert "papers" in output_data
    assert len(output_data["papers"]) == 3
    
    # Check paper conversions
    papers = output_data["papers"]
    
    # First paper should have generated ID
    assert papers[0]["paper_id"] is not None
    assert papers[0]["paper_id"].startswith("ICML_2023_")
    assert papers[0]["abstract"] == ""  # None converted to empty string
    assert papers[0]["doi"] == ""  # None converted to empty string
    assert papers[0]["urls"] == ["https://example.com/paper1.pdf"]  # pdf_urls mapped
    assert papers[0]["citations"] == 0  # Default added
    assert len(papers[0]["authors"]) == 2
    assert papers[0]["authors"][0]["name"] == "John Doe"
    assert papers[0]["authors"][0]["affiliations"] == []
    
    # Second paper should have affiliation converted
    assert papers[1]["paper_id"].startswith("NeurIPS_2023_")
    assert papers[1]["authors"][0]["affiliations"] == ["MIT"]
    
    # Third paper should keep existing ID
    assert papers[2]["paper_id"] == "existing-id"
    assert papers[2]["urls"] == ["https://example.com/paper3.pdf"]  # Kept as-is


def test_consolidate_command_json_serialization(tmp_path):
    """Test consolidate handles datetime serialization correctly"""
    input_file = tmp_path / "datetime_test.json"
    input_data = {
        "papers": [
            {
                "title": "Test Paper",
                "authors": [],
                "venue": "ICML",
                "year": 2023,
                "paper_id": "test1",
                "citations": 0,
                "collection_timestamp": "2025-01-10T12:00:00"  # ISO datetime string
            }
        ]
    }
    
    with open(input_file, "w") as f:
        json.dump(input_data, f)
    
    output_file = tmp_path / "output.json"
    
    runner = CliRunner()
    result = runner.invoke(app, [
        "consolidate",
        "--input", str(input_file),
        "--output", str(output_file),
        "--enrich", "citations"  # Just citations to run faster
    ])
    
    assert result.exit_code == 0
    
    # Verify output is valid JSON
    with open(output_file) as f:
        output_data = json.load(f)  # Should not raise
    
    # Check datetime was preserved as string
    assert isinstance(output_data["papers"][0]["collection_timestamp"], str)
    assert output_data["papers"][0]["collection_timestamp"] == "2025-01-10T12:00:00"