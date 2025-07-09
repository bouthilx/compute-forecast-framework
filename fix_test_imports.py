#!/usr/bin/env python3
"""Fix import statements in test files to reflect new directory structure."""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Define import mappings
IMPORT_MAPPINGS = {
    # Data models and collectors
    r'compute_forecast\.data\.models': 'compute_forecast.pipeline.metadata_collection.models',
    r'compute_forecast\.data\.collectors\.': 'compute_forecast.pipeline.metadata_collection.collectors.',
    r'compute_forecast\.data\.sources\.': 'compute_forecast.pipeline.metadata_collection.sources.',
    r'compute_forecast\.data\.processors\.': 'compute_forecast.pipeline.metadata_collection.processors.',
    
    # Filtering
    r'compute_forecast\.filtering\.': 'compute_forecast.pipeline.paper_filtering.selectors.',
    
    # PDF modules
    r'compute_forecast\.pdf_discovery\.': 'compute_forecast.pipeline.pdf_acquisition.discovery.',
    r'compute_forecast\.pdf_download\.': 'compute_forecast.pipeline.pdf_acquisition.download.',
    r'compute_forecast\.pdf_storage\.': 'compute_forecast.pipeline.pdf_acquisition.storage.',
    r'compute_forecast\.pdf_parser\.': 'compute_forecast.pipeline.content_extraction.parser.',
    
    # Extraction
    r'compute_forecast\.extraction\.': 'compute_forecast.pipeline.content_extraction.templates.',
    
    # Analysis
    r'compute_forecast\.analysis\.': 'compute_forecast.pipeline.analysis.',
    
    # Quality
    r'compute_forecast\.quality\.contracts\.': 'compute_forecast.core.contracts.',
    r'compute_forecast\.quality\.extraction\.': 'compute_forecast.pipeline.content_extraction.quality.',
    
    # These need special handling based on subdirectories
    # r'compute_forecast\.orchestration\.': 'compute_forecast.orchestration.',
    # r'compute_forecast\.monitoring\.': 'compute_forecast.monitoring.',
}

# Special mappings for orchestration subdirectories
ORCHESTRATION_MAPPINGS = {
    r'compute_forecast\.orchestration\.collectors\.': 'compute_forecast.pipeline.metadata_collection.collectors.',
    r'compute_forecast\.orchestration\.sources\.': 'compute_forecast.pipeline.metadata_collection.sources.',
    r'compute_forecast\.orchestration\.processors\.': 'compute_forecast.pipeline.metadata_collection.processors.',
}

# Special mappings for monitoring subdirectories
MONITORING_MAPPINGS = {
    r'compute_forecast\.monitoring\.dashboard_server': 'compute_forecast.monitoring.server.dashboard_server',
    r'compute_forecast\.monitoring\.dashboard_metrics': 'compute_forecast.monitoring.server.dashboard_metrics',
    r'compute_forecast\.monitoring\.advanced_dashboard_server': 'compute_forecast.monitoring.server.advanced_dashboard_server',
    r'compute_forecast\.monitoring\.advanced_analytics_engine': 'compute_forecast.monitoring.server.advanced_analytics_engine',
    r'compute_forecast\.monitoring\.integration_utils': 'compute_forecast.monitoring.server.integration_utils',
    r'compute_forecast\.monitoring\.alert_': 'compute_forecast.monitoring.alerting.alert_',
    r'compute_forecast\.monitoring\.alerting_engine': 'compute_forecast.monitoring.alerting.alerting_engine',
    r'compute_forecast\.monitoring\.intelligent_alerting_system': 'compute_forecast.monitoring.alerting.intelligent_alerting_system',
    r'compute_forecast\.monitoring\.notification_channels': 'compute_forecast.monitoring.alerting.notification_channels',
    r'compute_forecast\.monitoring\.metrics_collector': 'compute_forecast.monitoring.metrics.metrics_collector',
}


def find_test_files(root_dir: Path) -> List[Path]:
    """Find all Python test files."""
    test_files = []
    for path in root_dir.rglob("*.py"):
        if path.is_file() and not str(path).endswith('__pycache__'):
            test_files.append(path)
    return test_files


def update_imports_in_file(file_path: Path, dry_run: bool = False) -> List[Tuple[str, str]]:
    """Update imports in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Apply standard mappings
    for old_pattern, new_pattern in IMPORT_MAPPINGS.items():
        # Handle both 'from' and 'import' statements
        from_pattern = rf'(from\s+){old_pattern}'
        from_replacement = rf'\1{new_pattern}'
        
        # Check if pattern exists
        if re.search(from_pattern, content):
            new_content = re.sub(from_pattern, from_replacement, content)
            if new_content != content:
                # Extract actual changes for reporting
                for match in re.finditer(from_pattern, content):
                    old_import = match.group(0)
                    new_import = re.sub(from_pattern, from_replacement, old_import)
                    changes.append((old_import, new_import))
                content = new_content
    
    # Apply orchestration mappings
    for old_pattern, new_pattern in ORCHESTRATION_MAPPINGS.items():
        from_pattern = rf'(from\s+){old_pattern}'
        from_replacement = rf'\1{new_pattern}'
        
        if re.search(from_pattern, content):
            new_content = re.sub(from_pattern, from_replacement, content)
            if new_content != content:
                for match in re.finditer(from_pattern, content):
                    old_import = match.group(0)
                    new_import = re.sub(from_pattern, from_replacement, old_import)
                    changes.append((old_import, new_import))
                content = new_content
    
    # Apply monitoring mappings
    for old_pattern, new_pattern in MONITORING_MAPPINGS.items():
        from_pattern = rf'(from\s+){old_pattern}'
        from_replacement = rf'\1{new_pattern}'
        
        if re.search(from_pattern, content):
            new_content = re.sub(from_pattern, from_replacement, content)
            if new_content != content:
                for match in re.finditer(from_pattern, content):
                    old_import = match.group(0)
                    new_import = re.sub(from_pattern, from_replacement, old_import)
                    changes.append((old_import, new_import))
                content = new_content
    
    # Write back if changes were made
    if content != original_content and not dry_run:
        with open(file_path, 'w') as f:
            f.write(content)
    
    return changes


def main():
    """Main function to update all test imports."""
    # Find test directories
    test_dirs = [
        Path("tests"),
        Path("compute_forecast/testing"),
        Path("compute_forecast/core/contracts"),  # contract_tests.py
        Path("compute_forecast/pipeline/analysis/computational"),  # filter_tests.py, pattern_tests.py
    ]
    
    # Also check for any test files in the main package
    test_files_in_package = [
        Path("compute_forecast/test_google_scholar_init.py"),
    ]
    
    all_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            all_files.extend(find_test_files(test_dir))
    
    for test_file in test_files_in_package:
        if test_file.exists():
            all_files.append(test_file)
    
    print(f"Found {len(all_files)} test files to process")
    
    # Process each file
    total_changes = 0
    files_with_changes = []
    
    for file_path in all_files:
        changes = update_imports_in_file(file_path, dry_run=False)
        if changes:
            files_with_changes.append(file_path)
            total_changes += len(changes)
            print(f"\n{file_path}:")
            for old, new in changes:
                print(f"  {old} -> {new}")
    
    print(f"\nSummary:")
    print(f"  Total files processed: {len(all_files)}")
    print(f"  Files with changes: {len(files_with_changes)}")
    print(f"  Total import changes: {total_changes}")


if __name__ == "__main__":
    main()