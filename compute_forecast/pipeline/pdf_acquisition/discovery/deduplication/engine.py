"""Main deduplication engine for PDF discovery."""

import logging
from typing import Dict, List, Union, Optional
from dataclasses import dataclass

from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
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

    def deduplicate_records(
        self,
        all_records: Dict[str, List[PDFRecord]],
        record_to_paper: Optional[Dict[str, Paper]] = None,
    ) -> Dict[str, PDFRecord]:
        """Select best PDF for each paper from all discovered records.

        This is the main entry point that handles the complete deduplication process:
        1. Flatten all records into a single list
        2. Find exact matches (by DOI, arXiv ID, etc.)
        3. Find fuzzy matches (by title/author similarity)
        4. Group duplicate records together
        5. Select best version from each group

        Args:
            all_records: Dict mapping paper_id to list of PDFRecord from different sources
            record_to_paper: Optional mapping from record paper_id to Paper objects

        Returns:
            Dict mapping unique paper identifier to the best PDFRecord for that paper
        """
        if not all_records:
            return {}

        # Clear previous log
        self.dedup_log.clear()

        # Store the mapping for the matcher to use
        self._record_to_paper = record_to_paper or {}

        # If no record_to_paper mapping provided, build it from paper_data attributes
        if not self._record_to_paper:
            for paper_group_id, records in all_records.items():
                for record in records:
                    if hasattr(record, "paper_data") and record.paper_data:
                        self._record_to_paper[record.paper_id] = record.paper_data

        # Flatten all records
        all_flat_records = []
        for paper_group_id, records in all_records.items():
            for record in records:
                all_flat_records.append(record)

        if not all_flat_records:
            return {}

        logger.info(f"Starting deduplication of {len(all_flat_records)} records")

        # Step 1: Find exact matches
        exact_matches = self.fuzzy_matcher.find_duplicates_exact(
            all_flat_records, self._record_to_paper
        )

        # Step 2: Find fuzzy matches on remaining records
        fuzzy_matches = self.fuzzy_matcher.find_duplicates_fuzzy(
            all_flat_records, self._record_to_paper
        )

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
                self._log_deduplication_decision(
                    group_records, best_record, "version_selection"
                )

        logger.info(
            f"Deduplication complete: {len(all_flat_records)} -> {len(result)} unique papers"
        )

        return result

    def _build_duplicate_groups(
        self,
        all_records: List[PDFRecord],
        exact_matches: List[ExactMatch],
        fuzzy_matches: List[FuzzyMatch],
    ) -> Dict[str, List[PDFRecord]]:
        """Build groups of duplicate records based on exact and fuzzy matches.

        Args:
            all_records: All PDF records to group
            exact_matches: List of exact matches found
            fuzzy_matches: List of fuzzy matches found

        Returns:
            Dict mapping group_id to list of records in that group
        """
        # Create a mapping from paper_id to list of records
        # This allows us to handle multiple records with the same paper_id
        paper_id_to_records: Dict[str, List[PDFRecord]] = {}
        for record in all_records:
            if record.paper_id not in paper_id_to_records:
                paper_id_to_records[record.paper_id] = []
            paper_id_to_records[record.paper_id].append(record)

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
                if record_id in paper_id_to_records:
                    # Add all records with this paper_id to the group
                    for record in paper_id_to_records[record_id]:
                        if record.paper_id not in grouped_records:
                            group_records.append(record)
                            grouped_records.add(record.paper_id)

            if group_records:
                groups[group_id] = group_records
                self._log_deduplication_decision(
                    group_records,
                    group_records[0],
                    f"exact_match_{match.match_field}:{match.match_value}",
                )

        # Process fuzzy matches (only for ungrouped records)
        for fuzzy_match in fuzzy_matches:
            if any(rid in grouped_records for rid in fuzzy_match.record_ids):
                continue  # Skip if any record already grouped

            group_id = f"fuzzy_group_{group_counter}"
            group_counter += 1

            group_records = []
            for record_id in fuzzy_match.record_ids:
                if record_id in paper_id_to_records:
                    # Add all records with this paper_id to the group
                    for record in paper_id_to_records[record_id]:
                        if record.paper_id not in grouped_records:
                            group_records.append(record)
                            grouped_records.add(record.paper_id)

            if group_records:
                groups[group_id] = group_records
                self._log_deduplication_decision(
                    group_records,
                    group_records[0],
                    f"fuzzy_match_confidence:{fuzzy_match.confidence:.3f}",
                )

        # Add remaining ungrouped records as individual groups
        for record in all_records:
            if record.paper_id not in grouped_records:
                group_id = f"individual_{record.paper_id}_{record.source}"
                groups[group_id] = [record]

        return groups

    def _log_deduplication_decision(
        self, group_records: List[PDFRecord], selected_record: PDFRecord, reason: str
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
            "merge_rate": merge_decisions / total_decisions
            if total_decisions > 0
            else 0.0,
        }
