#!/usr/bin/env python3
"""Quick test of the quality CLI enhancements."""

import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner
from compute_forecast.cli.app import app

runner = CliRunner()

# Create test data
test_data = {
    "papers": [
        {
            "title": "Test Paper 1",
            "authors": ["Author A", "Author B"],
            "venue": "Test Conference",
            "year": 2023,
            "abstract": "This is a test abstract.",
            "doi": "10.1234/test1",
            "pdf_url": "http://example.com/paper1.pdf",
            "_source": "test_scraper",
        },
        {
            "title": "Test Paper 2",
            "authors": ["Author C"],
            "venue": "Test Conference",
            "year": 2023,
            "abstract": None,  # Missing abstract
            "doi": None,  # Missing DOI
            "pdf_url": None,  # Missing PDF
            "_source": "test_scraper",
        },
        {
            "title": "Test Paper 3",
            "authors": ["Author D", "Author E"],
            "venue": "Another Conference",
            "year": "invalid",  # Invalid year
            "abstract": "Another test abstract.",
            "doi": "10.1234/test3",
            "pdf_url": "not-a-valid-url",  # Invalid URL
            "_source": "test_scraper",
        },
    ],
    "metadata": {
        "scraped_at": "2023-12-01T00:00:00",
        "scraper": "test_scraper",
        "version": "1.0",
    },
}

# Create temporary test file
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(test_data, f)
    test_file = Path(f.name)

try:
    print("Testing quality command with various options...\n")

    # Test 1: Basic text output
    print("1. Basic text output:")
    result = runner.invoke(app, ["quality", str(test_file), "--stage", "collection"])
    print(result.output[:500] + "...\n" if len(result.output) > 500 else result.output)

    # Test 2: JSON output
    print("2. JSON output:")
    result = runner.invoke(
        app, ["quality", str(test_file), "--stage", "collection", "--format", "json"]
    )
    if result.exit_code == 0:
        try:
            parsed = json.loads(result.output)
            print(f"  - Stage: {parsed['report_info']['stage']}")
            print(f"  - Overall Score: {parsed['report_info']['overall_score']}")
            print(f"  - Check Results: {len(parsed['check_results'])} checks")
        except Exception:
            print(result.output[:200] + "...")
    else:
        print(f"  Error: {result.output}")

    # Test 3: Markdown output with file save
    print("\n3. Markdown output to file:")
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        output_file = Path(f.name)

    result = runner.invoke(
        app,
        [
            "quality",
            str(test_file),
            "--stage",
            "collection",
            "--format",
            "markdown",
            "--output",
            str(output_file),
        ],
    )
    if result.exit_code == 0 and output_file.exists():
        print("  - File saved successfully")
        print(f"  - File size: {output_file.stat().st_size} bytes")
        content = output_file.read_text()
        print(f"  - First line: {content.split('\\n')[0]}")
        output_file.unlink()
    else:
        print(f"  Error: {result.output}")

    # Test 4: Custom thresholds
    print("\n4. Custom thresholds:")
    result = runner.invoke(
        app,
        [
            "quality",
            str(test_file),
            "--stage",
            "collection",
            "--min-completeness",
            "0.9",
            "--min-accuracy",
            "0.8",
            "--verbose",
        ],
    )
    if "threshold" in result.output.lower() or "score" in result.output.lower():
        print("  - Custom thresholds applied")
    print(result.output[:300] + "...\n" if len(result.output) > 300 else result.output)

    # Test 5: List available stages
    print("5. List available stages:")
    result = runner.invoke(app, ["quality", "--list-stages"])
    print(result.output)

    # Test 6: List checks for collection stage
    print("6. List checks for collection stage:")
    result = runner.invoke(app, ["quality", "--list-checks", "collection"])
    print(result.output)

finally:
    # Cleanup
    if test_file.exists():
        test_file.unlink()
    print("\nTest completed!")
