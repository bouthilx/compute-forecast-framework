#!/usr/bin/env python3
"""
Extract research domains with justifications and quotes from Mila papers.
"""

import json
import sys
import pandas as pd

sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
from paperext.utils import Paper


def extract_domain_data():
    """Extract all domain information with context from Mila papers."""

    # Load papers
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    print(f"Processing {len(papers_data)} papers...")

    # Storage for domain data
    primary_domains = []
    sub_domains = []
    papers_processed = 0

    for i, paper_json in enumerate(papers_data[:100]):  # Test with first 100 papers
        if i % 25 == 0:
            print(f"Processing paper {i}...")

        try:
            paper = Paper(paper_json)
            if not paper.queries:
                continue

            # Load analysis
            with open(paper.queries[0], "r") as f:
                analysis_data = json.load(f)

            extractions = analysis_data.get("extractions", {})
            if not extractions:
                continue

            papers_processed += 1

            # Extract paper metadata
            paper_id = paper_json.get("paper_id", "")
            title = paper_json.get("title", "")

            # Extract year
            year = None
            for release in paper_json.get("releases", []):
                venue = release.get("venue", {})
                venue_date = venue.get("date", {})
                if isinstance(venue_date, dict) and "text" in venue_date:
                    year = venue_date["text"][:4]
                    break

            # Extract primary research field
            primary_field = extractions.get("primary_research_field", {})
            if isinstance(primary_field, dict) and "name" in primary_field:
                name_data = primary_field["name"]
                if isinstance(name_data, dict):
                    domain_entry = {
                        "paper_id": paper_id,
                        "title": title,
                        "year": year,
                        "domain_type": "primary",
                        "domain_name": name_data.get("value", ""),
                        "justification": name_data.get("justification", ""),
                        "quote": name_data.get("quote", ""),
                        "aliases": primary_field.get("aliases", []),
                    }
                    primary_domains.append(domain_entry)

            # Extract sub research fields
            sub_fields = extractions.get("sub_research_fields", [])
            for sub_field in sub_fields:
                if isinstance(sub_field, dict) and "name" in sub_field:
                    name_data = sub_field["name"]
                    if isinstance(name_data, dict):
                        domain_entry = {
                            "paper_id": paper_id,
                            "title": title,
                            "year": year,
                            "domain_type": "sub",
                            "domain_name": name_data.get("value", ""),
                            "justification": name_data.get("justification", ""),
                            "quote": name_data.get("quote", ""),
                            "aliases": sub_field.get("aliases", []),
                        }
                        sub_domains.append(domain_entry)

        except Exception as e:
            print(
                f"Error processing paper {paper_json.get('paper_id', 'unknown')}: {e}"
            )
            continue

    print(f"\\nProcessed {papers_processed} papers successfully")
    print(f"Extracted {len(primary_domains)} primary domains")
    print(f"Extracted {len(sub_domains)} sub domains")

    # Combine and save
    all_domains = primary_domains + sub_domains

    # Save to JSON
    with open("domain_extraction_raw.json", "w") as f:
        json.dump(
            {
                "primary_domains": primary_domains,
                "sub_domains": sub_domains,
                "all_domains": all_domains,
                "stats": {
                    "papers_processed": papers_processed,
                    "primary_domains_count": len(primary_domains),
                    "sub_domains_count": len(sub_domains),
                },
            },
            f,
            indent=2,
        )

    # Create DataFrame for analysis
    df = pd.DataFrame(all_domains)
    df.to_csv("domain_extraction_raw.csv", index=False)

    # Show sample data
    print("\\n=== SAMPLE DOMAIN EXTRACTIONS ===")
    for i, domain in enumerate(all_domains[:5]):
        print(f"\\n--- Domain {i+1} ---")
        print(f"Paper: {domain['title'][:60]}...")
        print(f"Domain: {domain['domain_name']}")
        print(f"Type: {domain['domain_type']}")
        print(f"Justification: {domain['justification'][:100]}...")
        if domain["quote"]:
            print(f"Quote: {domain['quote'][:100]}...")

    # Show unique domain names
    unique_domains = set(d["domain_name"] for d in all_domains if d["domain_name"])
    print(f"\\n=== UNIQUE DOMAIN NAMES ({len(unique_domains)}) ===")
    for domain in sorted(unique_domains)[:20]:
        print(f"  - {domain}")
    if len(unique_domains) > 20:
        print(f"  ... and {len(unique_domains) - 20} more")

    return all_domains


if __name__ == "__main__":
    domains = extract_domain_data()
    print("\\nDomain extraction complete. Files saved:")
    print("  - domain_extraction_raw.json")
    print("  - domain_extraction_raw.csv")
