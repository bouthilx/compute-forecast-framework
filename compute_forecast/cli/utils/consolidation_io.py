"""Shared utilities for consolidation commands - I/O operations."""

import json
from pathlib import Path
from datetime import datetime
from typing import List

from compute_forecast.pipeline.metadata_collection.models import Paper


def load_papers(input_path: Path) -> List[Paper]:
    """Load papers from collected JSON file"""
    with open(input_path) as f:
        data = json.load(f)

    papers = []
    for i, paper_data in enumerate(data.get("papers", [])):
        # Convert to Paper object
        paper = Paper.from_dict(paper_data)

        # Generate a unique ID if none exists
        if not paper.paper_id:
            # Use a combination of venue, year, and index as temporary ID
            paper.paper_id = f"{paper.venue}_{paper.year}_{i:04d}"

        papers.append(paper)

    return papers


def save_papers(papers: List[Paper], output_path: Path, stats: dict):
    """Save enriched papers to JSON file"""
    # Convert papers to dict format with proper serialization
    papers_data = []
    for p in papers:
        # to_dict() now handles all serialization including provenance records
        paper_dict = p.to_dict()
        papers_data.append(paper_dict)

    output_data = {
        "consolidation_metadata": {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "method": "two-phase",
            "phases": [
                "openalex_id_harvesting",
                "semantic_scholar_batch_enrichment",
                "openalex_full_enrichment",
            ],
        },
        "papers": papers_data,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)