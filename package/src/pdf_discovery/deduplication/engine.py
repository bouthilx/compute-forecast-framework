"""Main deduplication engine for PDF discovery."""

import logging
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict

from src.pdf_discovery.core.models import PDFRecord
from src.data.models import Paper
from .matchers import PaperFuzzyMatcher, IdentifierNormalizer, ExactMatch, FuzzyMatch
from .version_manager import VersionManager

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationDecision:
    """Record of a deduplication decision for audit purposes."""
    merged_records: List[str]
    selected_record: str
    reason: str
    confidence: float
    timestamp: str


class PaperDeduplicator:
    """Main deduplication engine for handling duplicate papers."""
    
    def __init__(self):
        """Initialize the deduplication engine."""
        self.fuzzy_matcher = PaperFuzzyMatcher()
        self.identifier_normalizer = IdentifierNormalizer()
        self.version_manager = VersionManager()
        
        # Track deduplication decisions for audit
        self.dedup_log: List[DeduplicationDecision] = []
    
    def deduplicate_records(self, all_records: Dict[str, List[PDFRecord]]) -> Dict[str, PDFRecord]:
        """Select best PDF for each paper from all discovered records.
        
        This is the main entry point that handles the complete deduplication process:
        1. Flatten all records into a single list
        2. Find exact matches (by DOI, arXiv ID, etc.)
        3. Find fuzzy matches (by title/author similarity)
        4. Group duplicate records together
        5. Select best version from each group
        
        Args:
            all_records: Dict mapping paper_id to list of PDFRecord from different sources
            
        Returns:
            Dict mapping unique paper identifier to the best PDFRecord for that paper
        """
        if not all_records:
            return {}
        
        # Clear previous log
        self.dedup_log.clear()
        
        # Flatten all records and ensure paper_data is attached
        all_flat_records = []
        for paper_group_id, records in all_records.items():
            for record in records:
                # Ensure paper data is available for matching
                if not hasattr(record, 'paper_data'):
                    logger.warning(f"Record {record.paper_id} missing paper_data, skipping")
                    continue
                all_flat_records.append(record)
        
        if not all_flat_records:
            return {}
        
        logger.info(f"Starting deduplication of {len(all_flat_records)} records")
        
        # Step 1: Find exact matches
        exact_matches = self.fuzzy_matcher.find_duplicates_exact(all_flat_records)
        
        # Step 2: Find fuzzy matches on remaining records
        fuzzy_matches = self.fuzzy_matcher.find_duplicates_fuzzy(all_flat_records)
        
        # Step 3: Build groups of duplicate records
        duplicate_groups = self._build_duplicate_groups(
            all_flat_records, exact_matches, fuzzy_matches
        )
        
        # Step 4: Select best version from each group
        result = {}
        for group_id, group_records in duplicate_groups.items():
            if len(group_records) == 1:
                # No duplicates, keep the record
                record = group_records[0]
                result[group_id] = record
            else:
                # Multiple versions, select best
                best_record = self.version_manager.select_best_version(group_records)
                result[group_id] = best_record
                
                # Log the decision
                self._log_deduplication_decision(group_records, best_record, "version_selection")
        
        logger.info(f"Deduplication complete: {len(all_flat_records)} -> {len(result)} unique papers")
        
        return result
    
    def _build_duplicate_groups(
        self, 
        all_records: List[PDFRecord], 
        exact_matches: List[ExactMatch], 
        fuzzy_matches: List[FuzzyMatch]
    ) -> Dict[str, List[PDFRecord]]:
        """Build groups of duplicate records based on exact and fuzzy matches.
        
        Args:
            all_records: All PDF records to group
            exact_matches: List of exact matches found
            fuzzy_matches: List of fuzzy matches found
            
        Returns:
            Dict mapping group_id to list of records in that group
        """
        # Create a mapping from record_id to record
        record_map = {record.paper_id: record for record in all_records}
        
        # Track which records have been grouped
        grouped_records = set()
        groups = {}
        group_counter = 0
        
        # Process exact matches first (higher confidence)
        for match in exact_matches:
            if any(rid in grouped_records for rid in match.record_ids):
                continue  # Skip if any record already grouped
            
            group_id = f"exact_group_{group_counter}"
            group_counter += 1
            
            group_records = []
            for record_id in match.record_ids:
                if record_id in record_map:
                    group_records.append(record_map[record_id])
                    grouped_records.add(record_id)
            
            if group_records:
                groups[group_id] = group_records
                self._log_deduplication_decision(
                    group_records, group_records[0], 
                    f"exact_match_{match.match_field}:{match.match_value}"
                )
        
        # Process fuzzy matches (only for ungrouped records)
        for match in fuzzy_matches:
            if any(rid in grouped_records for rid in match.record_ids):
                continue  # Skip if any record already grouped
            
            group_id = f"fuzzy_group_{group_counter}"
            group_counter += 1
            
            group_records = []
            for record_id in match.record_ids:
                if record_id in record_map:
                    group_records.append(record_map[record_id])
                    grouped_records.add(record_id)
            
            if group_records:
                groups[group_id] = group_records
                self._log_deduplication_decision(
                    group_records, group_records[0], 
                    f"fuzzy_match_confidence:{match.confidence:.3f}"
                )
        
        # Add remaining ungrouped records as individual groups
        for record in all_records:
            if record.paper_id not in grouped_records:
                group_id = f"individual_{record.paper_id}"
                groups[group_id] = [record]
        
        return groups
    
    def _log_deduplication_decision(
        self, 
        group_records: List[PDFRecord], 
        selected_record: PDFRecord, 
        reason: str
    ):
        """Log a deduplication decision for audit purposes."""
        from datetime import datetime
        
        decision = DeduplicationDecision(
            merged_records=[r.paper_id for r in group_records],
            selected_record=selected_record.paper_id,
            reason=reason,
            confidence=selected_record.confidence_score,
            timestamp=datetime.now().isoformat(),
        )
        
        self.dedup_log.append(decision)
        
        if len(group_records) > 1:
            logger.debug(
                f"Merged {len(group_records)} records into {selected_record.paper_id} "
                f"(reason: {reason})"
            )
    
    def get_deduplication_stats(self) -> Dict[str, Union[int, float]]:
        """Get statistics about the last deduplication run."""
        if not self.dedup_log:
            return {}
        
        total_decisions = len(self.dedup_log)
        merge_decisions = len([d for d in self.dedup_log if len(d.merged_records) > 1])
        avg_confidence = sum(d.confidence for d in self.dedup_log) / total_decisions
        
        return {
            "total_decisions": total_decisions,
            "merge_decisions": merge_decisions,
            "individual_records": total_decisions - merge_decisions,
            "average_confidence": avg_confidence,
            "merge_rate": merge_decisions / total_decisions if total_decisions > 0 else 0.0,
        }