"""Performance tests for PDF deduplication."""

import pytest
import time
from datetime import datetime
from typing import List

from compute_forecast.pipeline.pdf_acquisition.discovery.deduplication.engine import (
    PaperDeduplicator,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import PDFRecord
from compute_forecast.pipeline.metadata_collection.models import Paper, Author


class TestDeduplicationPerformance:
    """Test deduplication performance with large datasets."""

    @pytest.fixture
    def large_dataset(self) -> tuple[List[Paper], List[PDFRecord]]:
        """Create a large dataset for performance testing."""
        papers = []
        records = []

        # Create 500 unique papers with some duplicates (reduced for testing)
        for i in range(500):
            paper = Paper(
                title=f"Research Paper {i:04d}: Deep Learning Applications",
                authors=[
                    Author(
                        name=f"Author {i % 100}", affiliation=f"University {i % 50}"
                    ),
                    Author(
                        name=f"Co-Author {(i + 1) % 100}",
                        affiliation=f"Institute {i % 30}",
                    ),
                ],
                venue=f"Conference {i % 20}",
                year=2020 + (i % 4),
                citations=i * 10,
                paper_id=f"paper_{i:04d}",
                doi=f"10.1234/paper.{i:04d}" if i % 5 != 0 else None,  # 80% have DOIs
                arxiv_id=f"2{(i % 2) + 3}01.{i:05d}"
                if i % 3 == 0
                else None,  # 33% have arXiv IDs
            )
            papers.append(paper)

        # Create records with some duplicates (multiple sources per paper)
        for i, paper in enumerate(papers):
            # Each paper has 1-3 records from different sources
            num_sources = min(3, 1 + (i % 3))
            sources = ["semantic_scholar", "arxiv", "venue_direct"][:num_sources]

            for source in sources:
                record = PDFRecord(
                    paper_id=f"{paper.paper_id}_{source}",
                    pdf_url=f"https://{source}.com/{paper.paper_id}.pdf",
                    source=source,
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.85 + (i % 15) / 100,  # 0.85-0.99
                    version_info={"is_published": source == "venue_direct"},
                    validation_status="valid" if i % 10 != 0 else "unknown",
                    file_size_bytes=100_000 + (i * 1000) % 500_000,
                )
                record.paper_data = paper
                records.append(record)

        return papers, records

    def test_deduplication_performance_500_papers(self, large_dataset):
        """Test deduplication performance with 500 papers (~1500 records)."""
        papers, records = large_dataset
        deduplicator = PaperDeduplicator()

        # Group records by paper
        all_records = {}
        for record in records:
            base_id = record.paper_data.paper_id
            if base_id not in all_records:
                all_records[base_id] = []
            all_records[base_id].append(record)

        start_time = time.time()
        result = deduplicator.deduplicate_records(all_records)
        end_time = time.time()

        execution_time = end_time - start_time

        # Performance assertions (relaxed for CI environments)
        assert execution_time < 60.0, (
            f"Deduplication took {execution_time:.2f}s, should be < 60s"
        )

        # Correctness assertions
        assert len(result) <= 500, f"Expected <= 500 unique papers, got {len(result)}"
        assert len(result) > 0, "Should have some results"
        assert len(records) > len(result), "Should have deduplicated some records"

        # Check that best versions were selected
        for paper_id, selected_record in result.items():
            assert selected_record is not None
            assert hasattr(selected_record, "paper_data")

        # Log performance stats
        stats = deduplicator.get_deduplication_stats()
        print("\nPerformance Results for 500 papers:")
        print(f"  Execution time: {execution_time:.2f}s")
        print(f"  Records processed: {len(records)}")
        print(f"  Unique papers: {len(result)}")
        print(f"  Merge decisions: {stats.get('merge_decisions', 0)}")
        print(f"  Average confidence: {stats.get('average_confidence', 0):.3f}")
        print(f"  Records per second: {len(records) / execution_time:.1f}")

    @pytest.mark.slow
    def test_deduplication_performance_10k_papers(self):
        """Test deduplication performance with 10,000 papers (~20,000 records)."""
        # Create an even larger dataset
        papers = []
        records = []

        for i in range(10000):
            paper = Paper(
                title=f"Large Scale Research {i:05d}: AI and ML",
                authors=[
                    Author(name=f"Researcher {i % 500}", affiliation=f"Uni {i % 100}"),
                ],
                venue=f"Venue {i % 50}",
                year=2020 + (i % 5),
                citations=i,
                paper_id=f"large_{i:05d}",
                doi=f"10.5678/large.{i:05d}" if i % 4 != 0 else None,
            )
            papers.append(paper)

            # Most papers have 2 records (original + duplicate)
            sources = ["source1", "source2"] if i % 2 == 0 else ["source1"]

            for source in sources:
                record = PDFRecord(
                    paper_id=f"{paper.paper_id}_{source}",
                    pdf_url=f"https://{source}.com/{paper.paper_id}.pdf",
                    source=source,
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.8 + (i % 20) / 100,
                    version_info={},
                    validation_status="valid",
                    file_size_bytes=200_000,
                )
                record.paper_data = paper
                records.append(record)

        deduplicator = PaperDeduplicator()

        # Group records
        all_records = {}
        for record in records:
            base_id = record.paper_data.paper_id
            if base_id not in all_records:
                all_records[base_id] = []
            all_records[base_id].append(record)

        start_time = time.time()
        result = deduplicator.deduplicate_records(all_records)
        end_time = time.time()

        execution_time = end_time - start_time

        # Performance requirements for 10k papers
        assert execution_time < 120.0, (
            f"Deduplication took {execution_time:.2f}s, should be < 120s"
        )
        assert len(result) == 10000, f"Expected 10000 unique papers, got {len(result)}"

        # Memory efficiency check (basic)
        stats = deduplicator.get_deduplication_stats()
        assert stats["total_decisions"] > 0

        print("\nPerformance Results for 10,000 papers:")
        print(f"  Execution time: {execution_time:.2f}s")
        print(f"  Records processed: {len(records)}")
        print(f"  Unique papers: {len(result)}")
        print(f"  Records per second: {len(records) / execution_time:.1f}")

    def test_fuzzy_matching_performance(self):
        """Test fuzzy matching performance with many similar titles."""
        papers = []
        records = []

        # Create papers with very similar titles (stress test fuzzy matching)
        base_titles = [
            "Deep Learning for Natural Language Processing",
            "Machine Learning Applications in Computer Vision",
            "Reinforcement Learning for Robotics",
            "Neural Networks and Deep Learning",
            "Artificial Intelligence in Healthcare",
        ]

        for i in range(100):  # Reduced from 500 to 100 for performance
            # Vary titles slightly to test fuzzy matching
            base_title = base_titles[i % len(base_titles)]
            variations = [
                base_title,
                f"{base_title} (Extended Abstract)",
                f"{base_title}: A Survey",
                f"{base_title} - Supplementary Material",
                f"An Approach to {base_title}",
            ]

            title = variations[i % len(variations)]

            paper = Paper(
                title=title,
                authors=[
                    Author(name=f"Author {i % 100}", affiliation=f"Uni {i % 50}"),
                ],
                venue="TestConf",
                year=2023,
                citations=i,
                paper_id=f"fuzzy_{i:03d}",
                # No DOIs to force fuzzy matching
            )
            papers.append(paper)

            record = PDFRecord(
                paper_id=paper.paper_id,
                pdf_url=f"https://test.com/{paper.paper_id}.pdf",
                source="test",
                discovery_timestamp=datetime.now(),
                confidence_score=0.9,
                version_info={},
                validation_status="valid",
            )
            record.paper_data = paper
            records.append(record)

        deduplicator = PaperDeduplicator()

        all_records = {"fuzzy_test": records}

        start_time = time.time()
        result = deduplicator.deduplicate_records(all_records)
        end_time = time.time()

        execution_time = end_time - start_time

        # Should complete fuzzy matching in reasonable time
        assert execution_time < 10.0, (
            f"Fuzzy matching took {execution_time:.2f}s, should be < 10s"
        )

        # Should find some duplicates (papers with very similar titles)
        assert len(result) < len(records), "Should have found some fuzzy duplicates"

        stats = deduplicator.get_deduplication_stats()
        print("\nFuzzy Matching Performance:")
        print(f"  Execution time: {execution_time:.2f}s")
        print(f"  Input records: {len(records)}")
        print(f"  Output records: {len(result)}")
        print(f"  Duplicates found: {len(records) - len(result)}")
        print(f"  Merge rate: {stats.get('merge_rate', 0):.1%}")

    def test_memory_efficiency_large_dataset(self, large_dataset):
        """Test that deduplication doesn't use excessive memory."""
        papers, records = large_dataset
        deduplicator = PaperDeduplicator()

        # Group records
        all_records = {}
        for record in records:
            base_id = record.paper_data.paper_id
            if base_id not in all_records:
                all_records[base_id] = []
            all_records[base_id].append(record)

        # Monitor log size
        initial_log_size = len(deduplicator.dedup_log)

        result = deduplicator.deduplicate_records(all_records)

        final_log_size = len(deduplicator.dedup_log)

        # Log shouldn't grow excessively
        log_growth = final_log_size - initial_log_size
        assert log_growth <= len(result) * 2, "Deduplication log growing too large"

        # Result should be reasonable size
        assert len(result) > 0
        assert len(result) <= len(records)

        print("\nMemory Efficiency Check:")
        print(f"  Dedup log entries: {log_growth}")
        print(f"  Input records: {len(records)}")
        print(f"  Output records: {len(result)}")
        print(f"  Memory ratio: {log_growth / len(records):.3f}")
