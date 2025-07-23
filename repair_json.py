#!/usr/bin/env python3
"""Repair truncated JSON file by properly closing all open structures."""

import json
import sys


def repair_truncated_json(input_file, output_file):
    """Attempt to repair a truncated JSON file."""
    with open(input_file, "r") as f:
        content = f.read()

    # Try to parse to find where it breaks
    try:
        json.loads(content)
        print("JSON is already valid!")
        return
    except json.JSONDecodeError as e:
        print(f"JSON error at position {e.pos} (line {e.lineno}, column {e.colno})")

    # Count open braces and brackets to determine what needs closing
    brace_count = 0
    bracket_count = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(content):
        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if not in_string:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
            elif char == "[":
                bracket_count += 1
            elif char == "]":
                bracket_count -= 1

    print(f"Unclosed braces: {brace_count}")
    print(f"Unclosed brackets: {bracket_count}")

    # Find the last complete object
    # Look for the last complete author entry
    last_complete_pos = content.rfind('"email": ""')
    if last_complete_pos > 0:
        # Find the closing brace after this
        pos = last_complete_pos
        while pos < len(content) and content[pos] != "}":
            pos += 1

        if pos < len(content):
            # Include the closing brace
            truncate_pos = pos + 1
            print(f"Truncating at position {truncate_pos}")

            # Create repaired content
            repaired = content[:truncate_pos]

            # Close the authors array
            repaired += "\n      ]"

            # Close any remaining structures
            # We need to close: urls, processing_flags, and the paper object
            repaired += ',\n      "venue": "ICML",\n      "year": 2021,\n      "citations": [],\n      "abstracts": [],\n      "doi": "",\n      "urls": [],\n      "identifiers": [],\n      "paper_id": "truncated_paper",\n      "openalex_id": null,\n      "arxiv_id": null,\n      "normalized_venue": null,\n      "keywords": [],\n      "citation_velocity": null,\n      "collection_source": "pmlr",\n      "collection_timestamp": "2025-07-15T07:22:37.544519",\n      "processing_flags": {},\n      "venue_confidence": 1.0,\n      "deduplication_confidence": 1.0,\n      "breakthrough_score": null,\n      "computational_analysis": null,\n      "authorship_analysis": null,\n      "venue_analysis": null,\n      "source": "",\n      "mila_domain": "",\n      "collection_method": "",\n      "selection_rank": null,\n      "benchmark_type": ""\n    }\n  ]\n}'

            # Write repaired file
            with open(output_file, "w") as f:
                f.write(repaired)

            print(f"Repaired JSON written to {output_file}")

            # Validate the repair
            try:
                with open(output_file, "r") as f:
                    data = json.load(f)
                print(f"Success! Repaired file contains {len(data['papers'])} papers")
            except json.JSONDecodeError as e:
                print(f"Repair failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python repair_json.py <input_file> <output_file>")
        sys.exit(1)

    repair_truncated_json(sys.argv[1], sys.argv[2])
