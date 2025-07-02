#!/usr/bin/env python3
"""
Script to clean up the package directory by organizing scripts into appropriate folders.
Based on the classification in journals/package_script_classification.md

Usage: python cleanup_scripts.py [--dry-run] [--execute]
"""

import os
import shutil
from pathlib import Path
import argparse

# Scripts to remove (temporary tests/debug)
TO_REMOVE = [
    "check_recent_paper_query.py",
    "debug_collection.py",
    "debug_dashboard.py", 
    "debug_temporal_classification.py",
    "demo_complete_monitoring.py",
    "demo_dashboard.py",
    "demo_real_logs.py",
    "demo_streaming_working.py",
    "enhanced_google_scholar.py",
    "guaranteed_dashboard.py",
    "investigate_2024_paper.py",
    "investigate_early_years_pattern.py",
    "investigate_missing_analysis.py",
    "investigate_specific_paper.py",
    "quick_environment_check.py",
    "run_enhanced_tests.py",
    "simple_collection.py",
    "simple_collection_test.py",
    "simple_dashboard_test.py",
    "streaming_dashboard.py",
    "test_classification_logic.py",
    "test_collection_setup.py",
    "test_config_integration.py",
    "test_end_to_end.py",
    "test_enhanced_classification.py",
    "test_enhanced_minimal.py",
    "test_enhanced_scholar.py",
    "test_google_scholar_final.py",
    "test_live_display.py",
    "test_rapid_streaming.py",
    "test_realtime.py",
    "test_scholar_browser.py",
    "test_scholar_fixed.py",
    "test_scholar_internal.py",
    "test_scholar_simple.py",
    "test_scholar_simple_final.py",
    "test_small_collection.py",
    "test_stdout_capture.py",
    "test_streaming_logs.py",
    "test_ui.py",
    "working_dashboard.py"
]

# Scripts to archive (past analyses/iterations)
TO_ARCHIVE = [
    "analyze_dataset_structure.py",
    "analyze_datasets.py",
    "analyze_duplicates.py",
    "analyze_overlap.py",
    "calculate_corrections.py",
    "cluster_domains.py",
    "collection_fixed.py",
    "collection_fixed_display.py",
    "collection_validation_report.py",
    "collection_with_dashboard.py",
    "collection_with_progress.py",
    "collection_with_progress_backup.py",
    "collection_with_real_logs.py",
    "complete_paper_accounting.py",
    "continue_collection.py",
    "continue_collection_with_dashboard.py",
    "correct_venue_mergers.py",
    "create_collection_validation.py",
    "dataset_based_corrections.py",
    "detailed_agreement_analysis.py",
    "domain_mapping_sanity_check.py",
    "empirical_correction_analysis.py",
    "environments_analysis.py",
    "examine_other_domains.py",
    "execute_collection.py",
    "execute_fixed_collection.py",
    "execute_paper_collection.py",
    "extract_domains.py",
    "extract_domains_actual_fix.py",
    "extract_domains_completely_fixed.py",
    "extract_domains_final_fix.py",
    "extract_domains_fixed.py",
    "fast_paper_accounting.py",
    "final_cleanup_venues.py",
    "find_venue_duplicates.py",
    "fix_venue_statistics.py",
    "full_corrected_venue_list.py",
    "full_domain_analysis.py",
    "list_merged_venues.py",
    "manual_create_proof_files.py",
    "realtime_collection.py",
    "temporal_analysis_fixed.py",
    "validate_venue_statistics.py",
    "venue_publication_counter.py",
    "venue_statistics_generator.py"
]

def cleanup_package_directory(dry_run=True):
    """Clean up the package directory by organizing scripts."""
    
    package_dir = Path(__file__).parent
    archive_dir = package_dir / "archive"
    
    if not dry_run and not archive_dir.exists():
        archive_dir.mkdir(exist_ok=True)
        print(f"Created archive directory: {archive_dir}")
    
    # Process files to remove
    print("\n=== FILES TO REMOVE ===")
    removed_count = 0
    for filename in TO_REMOVE:
        filepath = package_dir / filename
        if filepath.exists():
            if dry_run:
                print(f"Would remove: {filename}")
            else:
                filepath.unlink()
                print(f"Removed: {filename}")
            removed_count += 1
        else:
            print(f"Not found (skip): {filename}")
    
    # Process files to archive
    print("\n=== FILES TO ARCHIVE ===")
    archived_count = 0
    for filename in TO_ARCHIVE:
        filepath = package_dir / filename
        if filepath.exists():
            if dry_run:
                print(f"Would archive: {filename}")
            else:
                shutil.move(str(filepath), str(archive_dir / filename))
                print(f"Archived: {filename}")
            archived_count += 1
        else:
            print(f"Not found (skip): {filename}")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Files to remove: {removed_count}/{len(TO_REMOVE)}")
    print(f"Files to archive: {archived_count}/{len(TO_ARCHIVE)}")
    
    if dry_run:
        print("\nThis was a DRY RUN. Use --execute to perform actual cleanup.")
    else:
        print("\nCleanup completed!")

def main():
    parser = argparse.ArgumentParser(description="Clean up package directory scripts")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", 
                      help="Show what would be done without making changes")
    group.add_argument("--execute", action="store_true",
                      help="Actually perform the cleanup")
    
    args = parser.parse_args()
    
    cleanup_package_directory(dry_run=args.dry_run)

if __name__ == "__main__":
    main()