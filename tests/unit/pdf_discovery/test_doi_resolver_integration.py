"""Integration tests for DOI resolver components."""

import pytest
from unittest.mock import patch
from datetime import datetime

from compute_forecast.pdf_discovery.sources.doi_resolver_collector import (
    DOIResolverCollector,
)
from compute_forecast.pdf_discovery.core.framework import PDFDiscoveryFramework
from compute_forecast.pdf_discovery.core.models import PDFRecord, DiscoveryResult
from compute_forecast.data.models import Paper, Author


class TestDOIResolverIntegration:
    """Test DOI resolver integration with PDF discovery framework."""

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers with and without DOIs."""
        return [
            Paper(
                title="Paper with DOI",
                authors=[Author(name="John Doe")],
                venue="Test Journal",
                year=2021,
                citations=10,
                doi="10.1038/nature12373",
                paper_id="paper_1",
            ),
            Paper(
                title="Paper without DOI",
                authors=[Author(name="Jane Smith")],
                venue="Test Journal",
                year=2021,
                citations=5,
                doi="",  # No DOI
                paper_id="paper_2",
            ),
            Paper(
                title="Another paper with DOI",
                authors=[Author(name="Bob Wilson")],
                venue="Test Journal",
                year=2021,
                citations=15,
                doi="10.1126/science.123456",
                paper_id="paper_3",
            ),
        ]

    def test_framework_integration(self, sample_papers):
        """Test DOI resolver integration with PDF discovery framework."""
        # Create framework and add DOI resolver collector
        framework = PDFDiscoveryFramework()
        collector = DOIResolverCollector(email="test@example.com")
        framework.add_collector(collector)

        # Mock the API responses
        with patch.object(
            collector.crossref_client, "lookup_doi"
        ) as mock_crossref, patch.object(
            collector.unpaywall_client, "find_open_access"
        ) as mock_unpaywall:
            # Setup mock responses for successful lookups
            def crossref_side_effect(doi):
                from compute_forecast.data.models import APIResponse, ResponseMetadata

                if doi in ["10.1038/nature12373", "10.1126/science.123456"]:
                    return APIResponse(
                        success=True,
                        papers=[
                            Paper(
                                title="Mock Paper",
                                authors=[Author(name="Mock Author")],
                                venue="Mock Journal",
                                year=2021,
                                citations=0,
                                doi=doi,
                                urls=[f"https://publisher.com/{doi}.pdf"],
                                paper_id=f"crossref_{doi}",
                            )
                        ],
                        metadata=ResponseMetadata(
                            total_results=1,
                            returned_count=1,
                            query_used=doi,
                            response_time_ms=100,
                            api_name="crossref",
                            timestamp=datetime.now(),
                        ),
                        errors=[],
                    )
                return APIResponse(success=False, papers=[], metadata=None, errors=[])

            def unpaywall_side_effect(doi):
                from compute_forecast.data.models import APIResponse, ResponseMetadata

                if doi == "10.1038/nature12373":  # Only first DOI has OA
                    return APIResponse(
                        success=True,
                        papers=[
                            Paper(
                                title="Mock Paper",
                                authors=[Author(name="Mock Author")],
                                venue="Mock Journal",
                                year=2021,
                                citations=0,
                                doi=doi,
                                urls=[f"https://arxiv.org/pdf/{doi}.pdf"],
                                paper_id=f"unpaywall_{doi}",
                            )
                        ],
                        metadata=ResponseMetadata(
                            total_results=1,
                            returned_count=1,
                            query_used=doi,
                            response_time_ms=150,
                            api_name="unpaywall",
                            timestamp=datetime.now(),
                        ),
                        errors=[],
                    )
                return APIResponse(success=False, papers=[], metadata=None, errors=[])

            mock_crossref.side_effect = crossref_side_effect
            mock_unpaywall.side_effect = unpaywall_side_effect

            # Run discovery
            result = framework.discover_pdfs(sample_papers)

            # Verify results
            assert isinstance(result, DiscoveryResult)
            assert result.total_papers == 3

            # Should find PDFs for 2 papers (the ones with DOIs)
            assert result.discovered_count == 2

            # Check that we have records for papers with DOIs
            found_paper_ids = {record.paper_id for record in result.records}
            assert "paper_1" in found_paper_ids
            assert "paper_3" in found_paper_ids
            assert "paper_2" not in found_paper_ids  # No DOI

            # Verify that both CrossRef and Unpaywall were called for papers with DOIs
            assert mock_crossref.call_count == 2
            assert mock_unpaywall.call_count == 2

    def test_collector_statistics(self, sample_papers):
        """Test that collector statistics are properly tracked."""
        collector = DOIResolverCollector(email="test@example.com")

        # Mock successful discovery for one paper
        with patch.object(collector, "_discover_single") as mock_discover:
            mock_discover.return_value = PDFRecord(
                paper_id="paper_1",
                pdf_url="https://example.com/paper.pdf",
                source="doi_resolver",
                discovery_timestamp=datetime.now(),
                confidence_score=0.8,
                version_info={},
                validation_status="high_confidence",
            )

            # Only pass papers with DOIs
            papers_with_dois = [p for p in sample_papers if p.doi]
            collector.discover_pdfs(papers_with_dois)

            # Check statistics
            stats = collector.get_statistics()
            assert stats["attempted"] == 2  # Two papers with DOIs
            assert stats["successful"] == 2
            assert stats["failed"] == 0

    def test_rate_limiting_configuration(self):
        """Test that rate limiting is properly configured."""
        collector = DOIResolverCollector(email="test@example.com")

        # Verify timeout is set appropriately for combined API calls
        assert collector.timeout == 120  # 2 minutes for both APIs

        # Verify individual clients have appropriate retry settings
        assert collector.crossref_client.max_retries == 3
        assert collector.unpaywall_client.max_retries == 3
        assert (
            collector.crossref_client.retry_delay == 2.0
        )  # CrossRef prefers slower requests
        assert (
            collector.unpaywall_client.retry_delay == 1.0
        )  # Unpaywall is more lenient
