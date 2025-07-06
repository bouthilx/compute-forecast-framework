#!/usr/bin/env python3
"""
Fixed domain extraction that handles both old and new analysis formats.
Extracts all research domains from papers with proper format handling.
"""

import json
import sys
from collections import defaultdict


def load_research_taxonomy():
    """Load the research domain taxonomy."""

    try:
        with open("mila_domain_taxonomy.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: mila_domain_taxonomy.json not found, creating basic taxonomy")
        # Create a basic taxonomy for common domains
        basic_taxonomy = {
            "classification": {
                "Computer Vision": {"category": "Computer Vision & Medical Imaging"},
                "Medical Imaging": {"category": "Computer Vision & Medical Imaging"},
                "Natural Language Processing": {
                    "category": "Natural Language Processing"
                },
                "NLP": {"category": "Natural Language Processing"},
                "Reinforcement Learning": {
                    "category": "Reinforcement Learning & Robotics"
                },
                "Robotics": {"category": "Reinforcement Learning & Robotics"},
                "Graph Learning": {"category": "Graph Learning & Network Analysis"},
                "Network Analysis": {"category": "Graph Learning & Network Analysis"},
                "Machine Learning": {"category": "Other research domains"},
                "Deep Learning": {"category": "Other research domains"},
                "Psychology and Neuroscience": {"category": "Other research domains"},
                "Cognitive Science": {"category": "Other research domains"},
                "Optimization": {"category": "Other research domains"},
                "Statistics": {"category": "Other research domains"},
            }
        }

        with open("mila_domain_taxonomy.json", "w") as f:
            json.dump(basic_taxonomy, f, indent=2)

        return basic_taxonomy


def extract_analysis_data(query_file_path):
    """Extract analysis data from query file, handling both old and new formats."""

    try:
        with open(query_file_path, "r") as f:
            query_data = json.load(f)

        # Check for new format (extractions field)
        if "extractions" in query_data:
            extractions = query_data["extractions"]
            if extractions:  # Non-empty extractions
                return extractions, "new"

        # Check for old format (analysis field)
        if "analysis" in query_data:
            analysis = query_data["analysis"]
            if analysis:  # Non-empty analysis
                return analysis, "old"

        # No valid analysis data found
        return None, "none"

    except Exception as e:
        print(f"Error reading query file {query_file_path}: {e}")
        return None, "error"


def extract_domains_from_analysis(analysis_data, format_type):
    """Extract research domains from analysis data based on format."""

    domains = []

    if format_type == "new":
        # New format: extractions.primary_research_field.data
        primary_field = analysis_data.get("primary_research_field", {})
        if isinstance(primary_field, dict) and "data" in primary_field:
            field_name = primary_field["data"]
            if field_name:
                domains.append(field_name)

        # New format: extractions.sub_research_fields.data (list)
        sub_fields = analysis_data.get("sub_research_fields", {})
        if isinstance(sub_fields, dict) and "data" in sub_fields:
            sub_list = sub_fields["data"]
            if isinstance(sub_list, list):
                for field in sub_list:
                    if field:
                        domains.append(field)

    elif format_type == "old":
        # Old format: analysis.primary_research_field.name.value
        primary_field = analysis_data.get("primary_research_field", {})
        if isinstance(primary_field, dict):
            name_obj = primary_field.get("name", {})
            if isinstance(name_obj, dict) and "value" in name_obj:
                field_name = name_obj["value"]
                if field_name:
                    domains.append(field_name)

        # Old format: analysis.sub_research_fields (list of objects)
        sub_fields = analysis_data.get("sub_research_fields", [])
        if isinstance(sub_fields, list):
            for field_obj in sub_fields:
                if isinstance(field_obj, dict):
                    name_obj = field_obj.get("name", {})
                    if isinstance(name_obj, dict) and "value" in name_obj:
                        field_name = name_obj["value"]
                        if field_name:
                            domains.append(field_name)

    # Clean and deduplicate domains
    cleaned_domains = []
    for domain in domains:
        if isinstance(domain, str) and domain.strip():
            cleaned_domains.append(domain.strip())

    return list(set(cleaned_domains))  # Remove duplicates


def extract_all_domains_fixed():
    """Extract all research domains with fixed format handling."""

    print("FIXED DOMAIN EXTRACTION")
    print("=" * 50)

    # Load papers data
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    # Load taxonomy
    load_research_taxonomy()

    sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
    from paperext.utils import Paper

    print(f"Processing {len(papers_data)} papers...")

    # Statistics
    stats = {
        "total_papers": 0,
        "papers_with_queries": 0,
        "papers_with_analysis": 0,
        "old_format": 0,
        "new_format": 0,
        "no_format": 0,
        "error_format": 0,
        "domains_extracted": 0,
    }

    all_domains = []
    format_distribution = defaultdict(int)

    for i, paper_json in enumerate(papers_data):
        if i % 500 == 0:
            print(f"  Processed {i}/{len(papers_data)} papers")

        stats["total_papers"] += 1
        paper_id = paper_json.get("paper_id", "")
        title = paper_json.get("title", "Unknown")

        # Extract year
        year = None
        for release in paper_json.get("releases", []):
            venue = release.get("venue", {})
            venue_date = venue.get("date", {})
            if isinstance(venue_date, dict) and "text" in venue_date:
                try:
                    year = int(venue_date["text"][:4])
                    break
                except:
                    continue

        if not year or not (2019 <= year <= 2024):
            continue

        # Check for queries
        try:
            paper = Paper(paper_json)
            if not paper.queries:
                continue

            stats["papers_with_queries"] += 1

            # Process each query file
            paper_domains = set()

            for query_path in paper.queries:
                analysis_data, format_type = extract_analysis_data(query_path)

                if format_type == "old":
                    stats["old_format"] += 1
                    format_distribution["old"] += 1
                elif format_type == "new":
                    stats["new_format"] += 1
                    format_distribution["new"] += 1
                elif format_type == "none":
                    stats["no_format"] += 1
                    format_distribution["none"] += 1
                elif format_type == "error":
                    stats["error_format"] += 1
                    format_distribution["error"] += 1
                    continue

                if analysis_data:
                    stats["papers_with_analysis"] += 1

                    # Extract domains
                    domains = extract_domains_from_analysis(analysis_data, format_type)
                    paper_domains.update(domains)

            # Add all domains found for this paper
            for domain in paper_domains:
                all_domains.append(
                    {
                        "paper_id": paper_id,
                        "title": title,
                        "year": year,
                        "domain_name": domain,
                    }
                )
                stats["domains_extracted"] += 1

        except Exception:
            continue

    print("\nEXTRACTION STATISTICS:")
    print(f"  Total papers: {stats['total_papers']:,}")
    print(f"  Papers with queries: {stats['papers_with_queries']:,}")
    print(f"  Papers with analysis: {stats['papers_with_analysis']:,}")
    print(f"  Old format: {stats['old_format']:,}")
    print(f"  New format: {stats['new_format']:,}")
    print(f"  No analysis data: {stats['no_format']:,}")
    print(f"  Error reading: {stats['error_format']:,}")
    print(f"  Total domains extracted: {stats['domains_extracted']:,}")

    print("\nFORMAT DISTRIBUTION:")
    for format_type, count in format_distribution.items():
        print(f"  {format_type}: {count:,}")

    # Save results
    with open("all_domains_fixed.json", "w") as f:
        json.dump(all_domains, f, indent=2)

    print("\nResults saved to all_domains_fixed.json")
    print(
        f"Found {len(all_domains)} domain entries from {len(set(d['paper_id'] for d in all_domains))} unique papers"
    )

    return all_domains, stats


def main():
    """Run the fixed domain extraction."""

    domains, stats = extract_all_domains_fixed()

    # Show sample domains by year
    print("\nSAMPLE DOMAINS BY YEAR:")
    year_domains = defaultdict(list)
    for domain in domains:
        year_domains[domain["year"]].append(domain)

    for year in sorted(year_domains.keys()):
        count = len(year_domains[year])
        print(f"  {year}: {count} domain entries")
        if count > 0:
            sample_domains = year_domains[year][:3]
            for domain in sample_domains:
                print(f"    {domain['domain_name']} - {domain['title'][:50]}...")

    return domains, stats


if __name__ == "__main__":
    main()
