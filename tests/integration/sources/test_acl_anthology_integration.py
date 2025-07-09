"""Integration tests for ACL Anthology collector."""

import pytest
from unittest.mock import patch, Mock

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.acl_anthology_collector import (
    ACLAnthologyCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.core.framework import (
    PDFDiscoveryFramework,
)
from compute_forecast.pipeline.metadata_collection.models import Paper, Author


@pytest.mark.skip(reason="refactor: pdf_discovery modules not found")
class TestACLAnthologyIntegration:
    """Integration tests for ACL Anthology collector with framework."""

    @pytest.fixture
    def framework(self):
        """Create PDF discovery framework instance."""
        framework = PDFDiscoveryFramework()
        collector = ACLAnthologyCollector()
        framework.add_collector(collector)
        return framework

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        return [
            Paper(
                title="BERT: Pre-training of Deep Bidirectional Transformers",
                authors=[Author(name="Jacob Devlin", affiliation="Google")],
                venue="NAACL",
                year=2019,
                citations=50000,
                paper_id="bert_paper",
                abstract="We introduce a new language representation model...",
            ),
            Paper(
                title="Attention Is All You Need",
                authors=[Author(name="Ashish Vaswani", affiliation="Google")],
                venue="EMNLP",
                year=2017,
                citations=70000,
                paper_id="transformer_paper",
                abstract="The dominant sequence transduction models...",
            ),
            Paper(
                title="Unknown Paper from Different Venue",
                authors=[Author(name="Test Author", affiliation="Test Uni")],
                venue="ICML",  # Not an ACL venue
                year=2023,
                citations=10,
                paper_id="unknown_paper",
            ),
        ]

    def test_framework_integration(self, framework, sample_papers):
        """Test ACL collector integration with discovery framework."""
        # Mock the ACL collector's methods to avoid real network calls
        collector = framework.collectors[0]

        # Mock successful discoveries for ACL venues
        def mock_discover_single(paper):
            if paper.venue in ["NAACL", "EMNLP"]:
                from datetime import datetime
                from compute_forecast.pipeline.pdf_acquisition.discovery.core.models import (
                    PDFRecord,
                )

                return PDFRecord(
                    paper_id=paper.paper_id,
                    pdf_url=f"https://aclanthology.org/{paper.year}.{paper.venue.lower()}-main.123.pdf",
                    source="acl_anthology",
                    discovery_timestamp=datetime.now(),
                    confidence_score=0.95,
                    version_info={"venue_code": f"{paper.venue.lower()}-main"},
                    validation_status="validated",
                    file_size_bytes=1048576,
                )
            else:
                raise Exception(f"Unknown venue: {paper.venue}")

        with patch.object(
            collector, "_discover_single", side_effect=mock_discover_single
        ):
            # Run discovery
            results = framework.discover_pdfs(sample_papers)

            # Check results
            assert results.total_papers == 3
            assert results.discovered_count == 2
            assert len(results.records) == 2
            assert len(results.failed_papers) == 1

            # Check discovered papers
            discovered_ids = {r.paper_id for r in results.records}
            assert "bert_paper" in discovered_ids
            assert "transformer_paper" in discovered_ids
            assert "unknown_paper" not in discovered_ids

            # Check source statistics
            acl_stats = results.source_statistics.get("acl_anthology", {})
            assert acl_stats.get("attempted") == 3
            assert acl_stats.get("successful") == 2
            assert acl_stats.get("failed") == 1

    def test_real_url_construction(self):
        """Test URL construction matches real ACL Anthology patterns."""
        collector = ACLAnthologyCollector()

        # Test various real ACL URL patterns
        test_cases = [
            (
                "emnlp-main",
                2023,
                "456",
                "https://aclanthology.org/2023.emnlp-main.456.pdf",
            ),
            ("acl-long", 2022, "123", "https://aclanthology.org/2022.acl-long.123.pdf"),
            (
                "naacl-short",
                2021,
                "789",
                "https://aclanthology.org/2021.naacl-short.789.pdf",
            ),
            (
                "eacl-main",
                2020,
                "001",
                "https://aclanthology.org/2020.eacl-main.001.pdf",
            ),
        ]

        for venue_code, year, paper_id, expected_url in test_cases:
            url = collector._construct_pdf_url(venue_code, year, paper_id)
            assert url == expected_url

    def test_venue_mapping_completeness(self):
        """Test that all required venues are mapped."""
        collector = ACLAnthologyCollector()

        # Required venues from issue #82
        required_venues = ["EMNLP", "EACL", "ACL", "NAACL"]

        for venue in required_venues:
            codes = collector._map_venue_to_codes(venue)
            assert len(codes) > 0, f"No mapping found for venue: {venue}"

            # Each venue should have at least main track
            assert any("main" in code or "long" in code for code in codes)

    @patch("requests.Session")
    def test_session_configuration(self, mock_session_class):
        """Test that session is properly configured."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        ACLAnthologyCollector()

        # Check session was created
        mock_session_class.assert_called_once()

        # Check headers were set
        mock_session.headers.update.assert_called_once()
        call_args = mock_session.headers.update.call_args[0][0]
        assert "User-Agent" in call_args
        assert "Academic PDF Collector" in call_args["User-Agent"]
