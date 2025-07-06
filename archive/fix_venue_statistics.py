#!/usr/bin/env python3
"""
Data Quality Fix Script for Venue Statistics
Addresses issues identified in the completion review
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict, Counter
import re

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VenueStatisticsFixer:
    """Fix data quality issues in venue statistics"""

    def __init__(self, input_file: str = "data/mila_venue_statistics.json"):
        self.input_file = Path(input_file)
        self.fixed_data = None

        # Enhanced venue normalization patterns
        self.additional_venue_patterns = [
            # ICML variations
            (r"ICML\.cc/\d+/Conference", "ICML"),
            (r"ICML\.cc/\d+/.*", "ICML"),
            # AAAI variations
            (
                r"Proceedings of the \d+th AAAI Conference on Artificial Intelligence",
                "AAAI",
            ),
            (r"AAAI-\d+", "AAAI"),
            # General proceedings cleanup
            (
                r"Proceedings of the .*Conference on Computer Vision and Pattern Recognition",
                "CVPR",
            ),
            (
                r"Proceedings of the .*International Conference on Computer Vision",
                "ICCV",
            ),
            (r"Proceedings of the .*European Conference on Computer Vision", "ECCV"),
        ]

        # Target years (exclude future data)
        self.valid_years = ["2019", "2020", "2021", "2022", "2023", "2024"]

    def load_data(self) -> Dict[str, Any]:
        """Load the venue statistics data"""
        logger.info(f"Loading venue statistics from {self.input_file}")

        with open(self.input_file, "r") as f:
            data = json.load(f)

        logger.info(f"Loaded data with {len(data.get('venue_counts', {}))} venues")
        return data

    def normalize_venue_name_enhanced(self, venue: str) -> str:
        """Enhanced venue name normalization"""
        if not venue:
            return venue

        venue = venue.strip()

        # Apply additional normalization patterns
        for pattern, replacement in self.additional_venue_patterns:
            if re.search(pattern, venue, re.IGNORECASE):
                return replacement

        return venue

    def fix_venue_normalization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix venue name inconsistencies and consolidate venues"""
        logger.info("Fixing venue name normalization issues")

        venue_counts = data["venue_counts"]
        venue_by_domain = data["venue_by_domain"]
        venue_metadata = data["venue_metadata"]

        # Create mapping of old names to new names
        venue_mappings = {}
        for old_venue in list(venue_counts.keys()):
            new_venue = self.normalize_venue_name_enhanced(old_venue)
            if new_venue != old_venue:
                venue_mappings[old_venue] = new_venue

        logger.info(f"Found {len(venue_mappings)} venues to normalize")

        # Consolidate venue counts
        new_venue_counts = {}
        for old_venue, venue_data in venue_counts.items():
            new_venue = venue_mappings.get(old_venue, old_venue)

            if new_venue not in new_venue_counts:
                new_venue_counts[new_venue] = {
                    "total": 0,
                    "by_year": defaultdict(int),
                    "domains": set(),
                    "paper_count": 0,
                    "unique_paper_count": 0,
                }

            # Consolidate data
            new_venue_counts[new_venue]["total"] += venue_data["total"]
            new_venue_counts[new_venue]["paper_count"] += venue_data["paper_count"]
            new_venue_counts[new_venue]["unique_paper_count"] += venue_data[
                "unique_paper_count"
            ]
            new_venue_counts[new_venue]["domains"].update(venue_data["domains"])

            for year, count in venue_data["by_year"].items():
                new_venue_counts[new_venue]["by_year"][year] += count

        # Convert sets back to lists
        for venue_data in new_venue_counts.values():
            venue_data["domains"] = list(venue_data["domains"])
            venue_data["by_year"] = dict(venue_data["by_year"])

        # Update domain mappings
        new_venue_by_domain = {}
        for domain, venues in venue_by_domain.items():
            new_venues = defaultdict(int)
            for old_venue, count in venues.items():
                new_venue = venue_mappings.get(old_venue, old_venue)
                new_venues[new_venue] += count
            new_venue_by_domain[domain] = dict(new_venues)

        # Update metadata mappings
        new_metadata = {}
        for metadata_type, venue_dict in venue_metadata.items():
            new_metadata[metadata_type] = {}
            for old_venue, value in venue_dict.items():
                new_venue = venue_mappings.get(old_venue, old_venue)
                new_metadata[metadata_type][new_venue] = value

        data["venue_counts"] = new_venue_counts
        data["venue_by_domain"] = new_venue_by_domain
        data["venue_metadata"] = new_metadata

        logger.info(
            f"Normalized venues from {len(venue_counts)} to {len(new_venue_counts)}"
        )
        return data

    def filter_future_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove 2025 and other future year data"""
        logger.info("Filtering out future year data (keeping 2019-2024)")

        venue_counts = data["venue_counts"]
        removed_entries = 0

        for venue, venue_data in venue_counts.items():
            # Filter by_year data
            filtered_by_year = {}
            for year, count in venue_data["by_year"].items():
                if year in self.valid_years:
                    filtered_by_year[year] = count
                else:
                    removed_entries += count

            venue_data["by_year"] = filtered_by_year

        logger.info(f"Removed {removed_entries} entries from future years")
        return data

    def fix_count_discrepancies(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix total vs by_year sum discrepancies"""
        logger.info("Fixing count discrepancies between total and by_year sums")

        venue_counts = data["venue_counts"]
        fixed_venues = 0

        for venue, venue_data in venue_counts.items():
            by_year_sum = sum(venue_data["by_year"].values())
            current_total = venue_data["total"]

            if by_year_sum != current_total:
                # Use by_year_sum as the authoritative total since it reflects
                # the data after filtering out future years
                venue_data["total"] = by_year_sum
                fixed_venues += 1

        logger.info(f"Fixed count discrepancies for {fixed_venues} venues")
        return data

    def enhance_worker3_interface(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance venue_metadata section for Worker 3 consumption"""
        logger.info("Enhancing Worker 3 interface format")

        venue_counts = data["venue_counts"]
        venue_metadata = data["venue_metadata"]

        # Ensure all required metadata sections exist
        required_sections = [
            "computational_scores",
            "citation_averages",
            "venue_types",
            "year_coverage",
            "domain_diversity",
        ]

        for section in required_sections:
            if section not in venue_metadata:
                venue_metadata[section] = {}

        # Add venue ranking information
        venue_rankings = {}
        sorted_venues = sorted(
            venue_counts.items(), key=lambda x: x[1]["total"], reverse=True
        )

        for rank, (venue, venue_data) in enumerate(sorted_venues, 1):
            venue_rankings[venue] = {
                "rank": rank,
                "percentile": round(
                    (len(sorted_venues) - rank + 1) / len(sorted_venues) * 100, 1
                ),
                "tier": "top"
                if rank <= 10
                else "high"
                if rank <= 50
                else "medium"
                if rank <= 150
                else "low",
            }

        venue_metadata["venue_rankings"] = venue_rankings

        # Add summary statistics for Worker 3
        venue_metadata["summary_stats"] = {
            "total_venues": len(venue_counts),
            "top_10_venues": [venue for venue, _ in sorted_venues[:10]],
            "major_conferences": [
                venue
                for venue in venue_counts.keys()
                if any(
                    conf in venue.upper()
                    for conf in ["NEURIPS", "ICML", "ICLR", "CVPR", "ICCV", "AAAI"]
                )
            ],
            "venue_type_distribution": dict(
                Counter(venue_metadata["venue_types"].values())
            ),
            "years_with_data": sorted(
                list(
                    set().union(
                        *[
                            venue_data["by_year"].keys()
                            for venue_data in venue_counts.values()
                        ]
                    )
                )
            ),
        }

        logger.info("Enhanced venue_metadata for Worker 3 interface")
        return data

    def update_analysis_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update analysis summary statistics"""
        logger.info("Updating analysis summary statistics")

        venue_counts = data["venue_counts"]
        venue_by_domain = data["venue_by_domain"]

        # Recalculate summary statistics
        total_venues = len(venue_counts)
        total_papers = sum(venue_data["total"] for venue_data in venue_counts.values())
        active_venues = sum(
            1 for venue_data in venue_counts.values() if venue_data["total"] > 1
        )

        # Get year coverage
        all_years = set()
        for venue_data in venue_counts.values():
            all_years.update(venue_data["by_year"].keys())
        years_covered = sorted([year for year in all_years if year in self.valid_years])

        # Update summary
        data["analysis_summary"].update(
            {
                "total_venues": total_venues,
                "total_papers": total_papers,
                "years_covered": years_covered,
                "venue_coverage_rate": round(active_venues / total_venues, 3)
                if total_venues > 0
                else 0,
                "total_domains": len(venue_by_domain),
                "active_venues": active_venues,
                "data_quality_fixes_applied": True,
                "normalization_completed": True,
            }
        )

        logger.info("Updated analysis summary")
        return data

    def validate_data_integrity(self, data: Dict[str, Any]) -> bool:
        """Comprehensive data integrity validation"""
        logger.info("Running comprehensive data integrity validation")

        venue_counts = data["venue_counts"]
        issues = []

        # Check 1: Total vs by_year consistency
        for venue, venue_data in venue_counts.items():
            by_year_sum = sum(venue_data["by_year"].values())
            if by_year_sum != venue_data["total"]:
                issues.append(
                    f"Count mismatch for {venue}: total={venue_data['total']}, by_year_sum={by_year_sum}"
                )

        # Check 2: Future data
        for venue, venue_data in venue_counts.items():
            invalid_years = [
                year
                for year in venue_data["by_year"].keys()
                if year not in self.valid_years
            ]
            if invalid_years:
                issues.append(f"Invalid years for {venue}: {invalid_years}")

        # Check 3: Major venues presence
        major_venues = ["NeurIPS", "ICML", "ICLR", "CVPR"]
        missing_major = [venue for venue in major_venues if venue not in venue_counts]
        if missing_major:
            issues.append(f"Missing major venues: {missing_major}")

        # Check 4: Required metadata sections
        required_sections = ["computational_scores", "citation_averages", "venue_types"]
        missing_sections = [
            section
            for section in required_sections
            if section not in data["venue_metadata"]
        ]
        if missing_sections:
            issues.append(f"Missing metadata sections: {missing_sections}")

        if issues:
            logger.warning(f"Found {len(issues)} data integrity issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
            return False
        else:
            logger.info("✅ All data integrity checks passed")
            return True

    def run_fixes(self) -> Dict[str, Any]:
        """Execute all data quality fixes"""
        logger.info("Starting venue statistics data quality fixes")

        # Load data
        data = self.load_data()

        # Apply fixes in order
        data = self.fix_venue_normalization(data)
        data = self.filter_future_data(data)
        data = self.fix_count_discrepancies(data)
        data = self.enhance_worker3_interface(data)
        data = self.update_analysis_summary(data)

        # Validate
        is_valid = self.validate_data_integrity(data)
        if not is_valid:
            logger.warning("Data integrity issues remain after fixes")

        self.fixed_data = data
        return data

    def save_fixed_data(self, output_file: str = None) -> None:
        """Save the fixed data"""
        if self.fixed_data is None:
            raise ValueError("No fixed data to save. Run run_fixes() first.")

        if output_file is None:
            output_file = self.input_file

        logger.info(f"Saving fixed data to {output_file}")

        with open(output_file, "w") as f:
            json.dump(self.fixed_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Fixed data saved ({Path(output_file).stat().st_size} bytes)")


def main():
    """Main execution function"""
    fixer = VenueStatisticsFixer()

    # Run all fixes
    fixed_data = fixer.run_fixes()

    # Save fixed data
    fixer.save_fixed_data()

    # Print summary
    summary = fixed_data["analysis_summary"]
    print(f"\n{'=' * 60}")
    print("VENUE STATISTICS DATA QUALITY FIXES COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total venues: {summary['total_venues']}")
    print(f"Total papers: {summary['total_papers']}")
    print(
        f"Years covered: {summary['years_covered'][0]} - {summary['years_covered'][-1]}"
    )
    print(f"Active venues: {summary['active_venues']}")
    print(
        f"Data quality fixes applied: {summary.get('data_quality_fixes_applied', False)}"
    )
    print(f"{'=' * 60}\n")

    return fixed_data


if __name__ == "__main__":
    main()
