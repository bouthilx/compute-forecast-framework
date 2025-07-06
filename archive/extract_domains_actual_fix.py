#!/usr/bin/env python3
"""
ACTUAL FIX: Extract domains with correct understanding of the new format structure.
The 'extractions' field contains nested dictionaries, not direct 'data' fields.
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
                "Software Engineering": {"category": "Other research domains"},
            }
        }

        with open("mila_domain_taxonomy.json", "w") as f:
            json.dump(basic_taxonomy, f, indent=2)

        return basic_taxonomy


def extract_domains_from_new_format(extractions):
    """Extract research domains from NEW format - corrected structure understanding."""

    domains = []

    # New format: extractions.primary_research_field.name.value
    primary_field = extractions.get("primary_research_field", {})
    if isinstance(primary_field, dict):
        name_obj = primary_field.get("name", {})
        if isinstance(name_obj, dict) and "value" in name_obj:
            field_name = name_obj["value"]
            if field_name and isinstance(field_name, str):
                domains.append(field_name.strip())

    # New format: extractions.sub_research_fields (list of objects with name.value)
    sub_fields = extractions.get("sub_research_fields", [])
    if isinstance(sub_fields, list):
        for field_obj in sub_fields:
            if isinstance(field_obj, dict):
                name_obj = field_obj.get("name", {})
                if isinstance(name_obj, dict) and "value" in name_obj:
                    field_name = name_obj["value"]
                    if field_name and isinstance(field_name, str):
                        domains.append(field_name.strip())

    return domains


def extract_domains_from_old_format(analysis):
    """Extract research domains from old format (analysis field)."""

    domains = []

    # Old format: analysis.primary_research_field.name.value
    primary_field = analysis.get("primary_research_field", {})
    if isinstance(primary_field, dict):
        name_obj = primary_field.get("name", {})
        if isinstance(name_obj, dict) and "value" in name_obj:
            field_name = name_obj["value"]
            if field_name and isinstance(field_name, str):
                domains.append(field_name.strip())

    # Old format: analysis.sub_research_fields (list of objects)
    sub_fields = analysis.get("sub_research_fields", [])
    if isinstance(sub_fields, list):
        for field_obj in sub_fields:
            if isinstance(field_obj, dict):
                name_obj = field_obj.get("name", {})
                if isinstance(name_obj, dict) and "value" in name_obj:
                    field_name = name_obj["value"]
                    if field_name and isinstance(field_name, str):
                        domains.append(field_name.strip())

    return domains


def extract_all_domains_from_query(query_file_path):
    """Extract ALL domains from a query file, checking both old and new formats."""

    try:
        with open(query_file_path, "r") as f:
            query_data = json.load(f)

        all_domains = []
        formats_found = []

        # Try new format (extractions field)
        if "extractions" in query_data:
            extractions = query_data["extractions"]
            if extractions and isinstance(extractions, dict):
                new_domains = extract_domains_from_new_format(extractions)
                if new_domains:
                    all_domains.extend(new_domains)
                    formats_found.append("new")

        # Try old format (analysis field)
        if "analysis" in query_data:
            analysis = query_data["analysis"]
            if analysis and isinstance(analysis, dict):
                old_domains = extract_domains_from_old_format(analysis)
                if old_domains:
                    all_domains.extend(old_domains)
                    formats_found.append("old")

        # Remove duplicates while preserving order
        unique_domains = []
        seen = set()
        for domain in all_domains:
            if domain and domain not in seen:
                unique_domains.append(domain)
                seen.add(domain)

        format_used = "+".join(formats_found) if formats_found else "none"
        return unique_domains, format_used

    except Exception as e:
        print(f"Error reading query file {query_file_path}: {e}")
        return [], "error"


def extract_all_domains_actual_fix():
    """Extract all research domains with ACTUAL FIX - correct new format structure."""

    print("ACTUAL FIX DOMAIN EXTRACTION")
    print("=" * 50)

    # Load papers data
    data_path = "/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json"
    with open(data_path, "r") as f:
        papers_data = json.load(f)

    # Load taxonomy
    taxonomy = load_research_taxonomy()

    sys.path.insert(0, "/home/bouthilx/projects/paperext/src")
    from paperext.utils import Paper

    print(f"Processing {len(papers_data)} papers...")

    # Statistics
    stats = {
        "total_papers": 0,
        "papers_with_queries": 0,
        "papers_with_analysis": 0,
        "old_only": 0,
        "new_only": 0,
        "both_formats": 0,
        "no_format": 0,
        "error_format": 0,
        "domains_extracted": 0,
        "papers_with_domains": 0,
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

            # Process each query file and collect ALL domains
            paper_domains = set()
            paper_formats = set()

            for query_path in paper.queries:
                domains, format_used = extract_all_domains_from_query(query_path)

                if format_used == "old":
                    paper_formats.add("old")
                elif format_used == "new":
                    paper_formats.add("new")
                elif format_used == "old+new":
                    paper_formats.add("both")
                elif format_used == "error":
                    stats["error_format"] += 1
                    continue

                if domains:
                    paper_domains.update(domains)

            # Count format statistics per paper
            if paper_formats:
                stats["papers_with_analysis"] += 1
                if "both" in paper_formats or (
                    "old" in paper_formats and "new" in paper_formats
                ):
                    stats["both_formats"] += 1
                    format_distribution["both"] += 1
                elif "old" in paper_formats:
                    stats["old_only"] += 1
                    format_distribution["old"] += 1
                elif "new" in paper_formats:
                    stats["new_only"] += 1
                    format_distribution["new"] += 1
            else:
                stats["no_format"] += 1
                format_distribution["none"] += 1

            # Add all domains found for this paper
            if paper_domains:
                stats["papers_with_domains"] += 1
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

    print("\nACTUAL FIX EXTRACTION STATISTICS:")
    print(f"  Total papers: {stats['total_papers']:,}")
    print(f"  Papers with queries: {stats['papers_with_queries']:,}")
    print(f"  Papers with analysis: {stats['papers_with_analysis']:,}")
    print(f"  Papers with domains: {stats['papers_with_domains']:,}")
    print(f"  Old format only: {stats['old_only']:,}")
    print(f"  New format only: {stats['new_only']:,}")
    print(f"  Both formats: {stats['both_formats']:,}")
    print(f"  No analysis data: {stats['no_format']:,}")
    print(f"  Error reading: {stats['error_format']:,}")
    print(f"  Total domains extracted: {stats['domains_extracted']:,}")

    print("\nFORMAT DISTRIBUTION:")
    for format_type, count in format_distribution.items():
        print(f"  {format_type}: {count:,}")

    # Save results
    with open("all_domains_actual_fix.json", "w") as f:
        json.dump(all_domains, f, indent=2)

    print("\nResults saved to all_domains_actual_fix.json")
    print(
        f"Found {len(all_domains)} domain entries from {len(set(d['paper_id'] for d in all_domains))} unique papers"
    )

    return all_domains, stats


def main():
    """Run the actual fixed domain extraction."""

    domains, stats = extract_all_domains_actual_fix()

    # Show sample domains by year
    print("\nSAMPLE DOMAINS BY YEAR:")
    year_domains = defaultdict(list)
    for domain in domains:
        year_domains[domain["year"]].append(domain)

    for year in sorted(year_domains.keys()):
        count = len(year_domains[year])
        unique_papers = len(set(d["paper_id"] for d in year_domains[year]))
        print(f"  {year}: {count} domain entries from {unique_papers} papers")
        if count > 0:
            sample_domains = year_domains[year][:3]
            for domain in sample_domains:
                print(f"    {domain['domain_name']} - {domain['title'][:50]}...")

    return domains, stats


if __name__ == "__main__":
    main()
