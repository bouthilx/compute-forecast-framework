#!/usr/bin/env python3
"""
Final cleanup script to remove all 2025 references and fix remaining issues
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
import re

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FinalVenueCleanup:
    """Final cleanup for venue statistics to remove all 2025 references"""

    def __init__(self, input_file: str = "data/mila_venue_statistics.json"):
        self.input_file = Path(input_file)
        self.valid_years = ["2019", "2020", "2021", "2022", "2023", "2024"]

    def load_data(self) -> Dict[str, Any]:
        """Load the venue statistics data"""
        logger.info(f"Loading venue statistics from {self.input_file}")

        with open(self.input_file, "r") as f:
            data = json.load(f)

        return data

    def remove_future_venue_names(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove venues with 2025 in their names"""
        logger.info("Removing venues with 2025 in their names")

        venue_counts = data["venue_counts"]
        venue_by_domain = data["venue_by_domain"]
        venue_metadata = data["venue_metadata"]

        # Find venues with 2025 in name
        venues_to_remove = []
        for venue_name in venue_counts.keys():
            if "2025" in venue_name:
                venues_to_remove.append(venue_name)

        logger.info(
            f"Found {len(venues_to_remove)} venues with 2025 in name: {venues_to_remove}"
        )

        # Remove from venue_counts
        for venue in venues_to_remove:
            if venue in venue_counts:
                del venue_counts[venue]

        # Remove from domain mappings
        for domain, venues in venue_by_domain.items():
            for venue in venues_to_remove:
                if venue in venues:
                    del venues[venue]

        # Remove from metadata
        for metadata_type, venue_dict in venue_metadata.items():
            if isinstance(venue_dict, dict):
                for venue in venues_to_remove:
                    if venue in venue_dict:
                        del venue_dict[venue]

        logger.info(f"Removed {len(venues_to_remove)} venues with 2025 references")
        return data

    def filter_temporal_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter all temporal metadata to valid years only"""
        logger.info("Filtering temporal metadata to 2019-2024 range")

        venue_metadata = data["venue_metadata"]

        # Fix year_coverage data
        if "year_coverage" in venue_metadata:
            fixed_count = 0
            for venue, year_info in venue_metadata["year_coverage"].items():
                if isinstance(year_info, dict):
                    # Filter years_active to valid years only
                    if "years_active" in year_info:
                        old_years = year_info["years_active"]
                        valid_years_only = [
                            year for year in old_years if year in self.valid_years
                        ]

                        if valid_years_only != old_years:
                            year_info["years_active"] = sorted(valid_years_only)

                            # Recalculate year_span, first_year, last_year
                            if valid_years_only:
                                year_info["first_year"] = min(valid_years_only)
                                year_info["last_year"] = max(valid_years_only)
                                year_info["year_span"] = len(valid_years_only)
                                fixed_count += 1
                            else:
                                # No valid years, mark for removal
                                year_info["first_year"] = None
                                year_info["last_year"] = None
                                year_info["year_span"] = 0
                                year_info["years_active"] = []

            logger.info(f"Fixed temporal metadata for {fixed_count} venues")

        # Fix summary_stats years_with_data
        if "summary_stats" in venue_metadata:
            summary = venue_metadata["summary_stats"]
            if "years_with_data" in summary:
                old_years = summary["years_with_data"]
                valid_years_only = [
                    year for year in old_years if year in self.valid_years
                ]
                summary["years_with_data"] = sorted(valid_years_only)
                logger.info(
                    f"Fixed summary_stats years_with_data: {old_years} -> {valid_years_only}"
                )

        return data

    def fix_venue_type_classifications(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix obvious venue type misclassifications"""
        logger.info("Fixing venue type misclassifications")

        venue_metadata = data["venue_metadata"]
        venue_types = venue_metadata.get("venue_types", {})

        fixed_count = 0

        # Conference patterns that might be misclassified as journals
        conference_patterns = [
            r"Conference",
            r"CVPR",
            r"ICCV",
            r"ECCV",
            r"NeurIPS",
            r"ICML",
            r"ICLR",
            r"AAAI",
            r"IJCAI",
            r"Proceedings of",
            r"Workshop",
        ]

        # Journal patterns that might be misclassified as conferences
        journal_patterns = [
            r"Journal",
            r"Transactions",
            r"Nature",
            r"Science",
            r"Cell",
            r"PLOS",
            r"BMC",
            r"IEEE Trans",
        ]

        for venue, current_type in venue_types.items():
            correct_type = None

            # Check if it should be a conference
            for pattern in conference_patterns:
                if re.search(pattern, venue, re.IGNORECASE):
                    correct_type = "conference"
                    break

            # Check if it should be a journal (higher priority)
            for pattern in journal_patterns:
                if re.search(pattern, venue, re.IGNORECASE):
                    correct_type = "journal"
                    break

            # Apply fix if needed
            if correct_type and correct_type != current_type:
                venue_types[venue] = correct_type
                fixed_count += 1

        logger.info(f"Fixed venue type classifications for {fixed_count} venues")
        return data

    def validate_no_future_data(self, data: Dict[str, Any]) -> bool:
        """Validate that no 2025 or future data remains"""
        logger.info("Validating no future data remains")

        # Convert to string and search for 2025 references
        data_str = json.dumps(data)

        # Count 2025 references (excluding those in venue names we already know about)
        future_refs = []
        lines = data_str.split("\n")
        for i, line in enumerate(lines):
            if "2025" in line:
                future_refs.append(f"Line {i+1}: {line.strip()}")

        if future_refs:
            logger.warning(f"Found {len(future_refs)} remaining 2025 references:")
            for ref in future_refs[:10]:  # Show first 10
                logger.warning(f"  {ref}")
            if len(future_refs) > 10:
                logger.warning(f"  ... and {len(future_refs) - 10} more")
            return False
        else:
            logger.info("✅ No future data found - all clean!")
            return True

    def update_final_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update final statistics after cleanup"""
        logger.info("Updating final statistics")

        venue_counts = data["venue_counts"]
        venue_by_domain = data["venue_by_domain"]

        # Recalculate totals
        total_venues = len(venue_counts)
        total_papers = sum(venue_data["total"] for venue_data in venue_counts.values())
        active_venues = sum(
            1 for venue_data in venue_counts.values() if venue_data["total"] > 1
        )

        # Get clean year coverage
        all_years = set()
        for venue_data in venue_counts.values():
            all_years.update(venue_data["by_year"].keys())
        years_covered = sorted([year for year in all_years if year in self.valid_years])

        # Update analysis summary
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
                "final_cleanup_applied": True,
                "temporal_range_validated": f"{min(years_covered)}-{max(years_covered)}"
                if years_covered
                else "none",
            }
        )

        # Update venue metadata summary stats
        if "venue_metadata" in data and "summary_stats" in data["venue_metadata"]:
            summary = data["venue_metadata"]["summary_stats"]
            summary.update(
                {"total_venues": total_venues, "years_with_data": years_covered}
            )

        logger.info("Updated final statistics")
        return data

    def run_final_cleanup(self) -> Dict[str, Any]:
        """Execute final cleanup"""
        logger.info("Starting final venue statistics cleanup")

        # Load data
        data = self.load_data()

        # Apply cleanup steps
        data = self.remove_future_venue_names(data)
        data = self.filter_temporal_metadata(data)
        data = self.fix_venue_type_classifications(data)
        data = self.update_final_statistics(data)

        # Final validation
        is_clean = self.validate_no_future_data(data)

        if is_clean:
            logger.info("✅ Final cleanup successful - all future data removed")
        else:
            logger.warning("⚠️ Some future data may still remain")

        return data

    def save_clean_data(self, data: Dict[str, Any], output_file: str = None) -> None:
        """Save the cleaned data"""
        if output_file is None:
            output_file = self.input_file

        logger.info(f"Saving cleaned data to {output_file}")

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Cleaned data saved ({Path(output_file).stat().st_size} bytes)")


def main():
    """Main execution function"""
    cleaner = FinalVenueCleanup()

    # Run final cleanup
    clean_data = cleaner.run_final_cleanup()

    # Save cleaned data
    cleaner.save_clean_data(clean_data)

    # Print summary
    summary = clean_data["analysis_summary"]
    print(f"\n{'='*60}")
    print("FINAL VENUE STATISTICS CLEANUP COMPLETE")
    print(f"{'='*60}")
    print(f"Total venues: {summary['total_venues']}")
    print(f"Total papers: {summary['total_papers']}")
    print(f"Temporal range: {summary.get('temporal_range_validated', 'unknown')}")
    print(f"Active venues: {summary['active_venues']}")
    print(f"Final cleanup applied: {summary.get('final_cleanup_applied', False)}")
    print(f"{'='*60}\n")

    return clean_data


if __name__ == "__main__":
    main()
