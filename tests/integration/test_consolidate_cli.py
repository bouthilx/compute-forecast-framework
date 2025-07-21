import json
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
                "citations": 0,
            }
        ]
    }

    with open(input_file, "w") as f:
        json.dump(input_data, f)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "consolidate",
            "--input",
            str(input_file),
            "--output",
            str(tmp_path / "output.json"),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    assert "1 papers" in result.output


def test_consolidate_command_with_scraper_format(tmp_path):
    """Test consolidate CLI command with new format"""
    # Create test input with new format
    input_file = tmp_path / "papers.json"
    input_data = {
        "collection_metadata": {
            "timestamp": "2025-01-10T10:00:00",
            "venues": ["ICML", "NeurIPS"],
            "years": [2023],
            "total_papers": 3,
        },
        "papers": [
            {
                "title": "Paper with string authors",
                "authors": ["John Doe", "Jane Smith"],  # String authors
                "venue": "ICML",
                "year": 2023,
                "citations": [],
                "abstracts": [],
                "urls": [],
                "keywords": [],
                "doi": "",
                "arxiv_id": None,
                "paper_id": None,  # No ID
            },
            {
                "title": "Paper with author objects",
                "authors": [{"name": "Alice Brown", "affiliations": ["MIT"]}],
                "venue": "NeurIPS",
                "year": 2023,
                "citations": [],
                "abstracts": [
                    {
                        "source": "original",
                        "timestamp": "2025-01-10T09:30:00",
                        "original": True,
                        "data": {"text": "Existing abstract", "language": "en"},
                    }
                ],
                "urls": [],
                "keywords": ["machine learning"],
                "doi": "10.1234/test",
                "arxiv_id": None,
                "paper_id": None,
            },
            {
                "title": "Complete paper",
                "authors": [{"name": "Bob Wilson", "affiliations": ["Stanford"]}],
                "venue": "ICML",
                "year": 2023,
                "citations": [
                    {
                        "source": "original",
                        "timestamp": "2025-01-10T08:00:00",
                        "original": True,
                        "data": {"count": 5},
                    }
                ],
                "abstracts": [],
                "urls": [
                    {
                        "source": "original",
                        "timestamp": "2025-01-10T08:00:00",
                        "original": True,
                        "data": {"url": "https://example.com/paper3.pdf"},
                    }
                ],
                "keywords": [],
                "doi": "",
                "arxiv_id": "",
                "paper_id": "existing-id",
                "collection_timestamp": "2025-01-10T08:00:00",
            },
        ],
    }

    with open(input_file, "w") as f:
        json.dump(input_data, f)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "consolidate",
            "--input",
            str(input_file),
            "--output",
            str(tmp_path / "output.json"),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    assert "3 papers" in result.output

    # Test actual run (not dry-run)
    output_file = tmp_path / "enriched.json"
    result = runner.invoke(
        app,
        [
            "consolidate",
            "--input",
            str(input_file),
            "--output",
            str(output_file),
            "--sources",
            "semantic_scholar",  # Only one source to avoid rate limits in tests
        ],
    )

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
    assert papers[0]["abstracts"] == []  # Empty list
    assert papers[0]["doi"] == ""
    assert papers[0]["urls"] == []  # Empty list
    assert papers[0]["citations"] == []  # Empty list
    assert len(papers[0]["authors"]) == 2
    assert papers[0]["authors"][0]["name"] == "John Doe"
    assert papers[0]["authors"][0]["affiliations"] == []

    # Second paper should have abstract
    assert papers[1]["paper_id"].startswith("NeurIPS_2023_")
    assert papers[1]["authors"][0]["affiliations"] == ["MIT"]
    assert len(papers[1]["abstracts"]) == 1
    assert papers[1]["abstracts"][0]["data"]["text"] == "Existing abstract"

    # Third paper should keep existing ID
    assert papers[2]["paper_id"] == "existing-id"
    assert len(papers[2]["urls"]) == 1
    assert papers[2]["urls"][0]["data"]["url"] == "https://example.com/paper3.pdf"
    # Should have original citation plus any from enrichment
    assert len(papers[2]["citations"]) >= 1
    # First citation should be the original
    original_citations = [c for c in papers[2]["citations"] if c["original"]]
    assert len(original_citations) == 1
    assert original_citations[0]["data"]["count"] == 5


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
                "citations": [],
                "collection_timestamp": "2025-01-10T12:00:00",  # ISO datetime string
            }
        ]
    }

    with open(input_file, "w") as f:
        json.dump(input_data, f)

    output_file = tmp_path / "output.json"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "consolidate",
            "--input",
            str(input_file),
            "--output",
            str(output_file),
            "--enrich",
            "citations",  # Just citations to run faster
        ],
    )

    assert result.exit_code == 0

    # Verify output is valid JSON
    with open(output_file) as f:
        output_data = json.load(f)  # Should not raise

    # Check datetime was preserved as string
    assert isinstance(output_data["papers"][0]["collection_timestamp"], str)
    assert output_data["papers"][0]["collection_timestamp"] == "2025-01-10T12:00:00"
