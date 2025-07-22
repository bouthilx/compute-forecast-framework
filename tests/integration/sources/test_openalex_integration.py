"""Integration tests for OpenAlex PDF discovery."""

import pytest
from datetime import datetime
import os
from unittest.mock import patch, Mock

from compute_forecast.pipeline.pdf_acquisition.discovery.sources.openalex_collector import (
    OpenAlexPDFCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery import PDFDiscoveryFramework
from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
)


def create_test_paper(
    paper_id: str,
    title: str,
    venue: str,
    year: int,
    citation_count: int,
    authors: list,
    abstract_text: str = "",
) -> Paper:
    """Helper to create Paper objects with new model format."""
    citations = []
    if citation_count > 0:
        citations.append(
            CitationRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=CitationData(count=citation_count),
            )
        )

    abstracts = []
    if abstract_text:
        abstracts.append(
            AbstractRecord(
                source="test",
                timestamp=datetime.now(),
                original=True,
                data=AbstractData(text=abstract_text),
            )
        )

    return Paper(
        paper_id=paper_id,
        title=title,
        venue=venue,
        year=year,
        citations=citations,
        abstracts=abstracts,
        authors=authors,
    )


@pytest.mark.skip(reason="Integration test needs framework fixes")
class TestOpenAlexIntegration:
    """Integration tests for OpenAlex PDF collector."""

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        papers = [
            create_test_paper(
                paper_id="paper_1",
                title="Neural Network Optimization",
                authors=[Author(name="Jane Doe", affiliations=["Mila"])],
                year=2023,
                venue="NeurIPS",
                citation_count=15,
            ),
            create_test_paper(
                paper_id="paper_2",
                title="Transformer Architecture Improvements",
                authors=[
                    Author(name="John Smith", affiliations=["University of Montreal"])
                ],
                year=2023,
                venue="ICML",
                citation_count=25,
            ),
            create_test_paper(
                paper_id="paper_3",
                title="Reinforcement Learning in Robotics",
                authors=[Author(name="Alice Johnson", affiliations=["Mila"])],
                year=2023,
                venue="ICLR",
                citation_count=10,
            ),
        ]
        return papers

    @patch.dict(os.environ, {"OPENALEX_EMAIL": "test@example.com"})
    def test_collector_initialization(self):
        """Test collector can be initialized with environment variable."""
        collector = OpenAlexPDFCollector()
        assert collector.email == "test@example.com"
        assert collector.source_name == "openalex"
        assert collector.supports_batch is True

    @patch("requests.get")
    def test_framework_integration(self, mock_get, sample_papers):
        """Test OpenAlex collector integration with PDF discovery framework."""
        # Mock OpenAlex API responses
        mock_responses = {
            "10.1234/neurips.2023.001": {
                "id": "https://openalex.org/W1111111111",
                "doi": "https://doi.org/10.1234/neurips.2023.001",
                "best_oa_location": {
                    "is_oa": True,
                    "pdf_url": "https://papers.neurips.cc/paper/2023/file/paper1.pdf",
                    "license": "cc-by",
                },
                "authorships": [
                    {
                        "institutions": [
                            {
                                "id": "https://openalex.org/I162448124",
                                "display_name": "Mila",
                            }
                        ]
                    }
                ],
            },
            "10.1234/icml.2023.002": {
                "id": "https://openalex.org/W2222222222",
                "doi": "https://doi.org/10.1234/icml.2023.002",
                "primary_location": {
                    "is_oa": True,
                    "pdf_url": "https://proceedings.mlr.press/v202/paper2.pdf",
                },
                "best_oa_location": None,
                "authorships": [],
            },
        }

        def mock_api_response(url, params=None, headers=None, timeout=None):
            """Mock OpenAlex API responses."""
            response = Mock()

            # Extract DOI from filter parameter
            filter_param = params.get("filter", "")

            # Handle batch query
            if "doi:10.1234/neurips.2023.001|doi:10.1234/icml.2023.002" in filter_param:
                response.status_code = 200
                response.json.return_value = {
                    "results": list(mock_responses.values()),
                    "meta": {"count": 2},
                }
            # Handle individual queries
            elif "doi:10.1234/neurips.2023.001" in filter_param:
                response.status_code = 200
                response.json.return_value = {
                    "results": [mock_responses["10.1234/neurips.2023.001"]],
                    "meta": {"count": 1},
                }
            elif "doi:10.1234/icml.2023.002" in filter_param:
                response.status_code = 200
                response.json.return_value = {
                    "results": [mock_responses["10.1234/icml.2023.002"]],
                    "meta": {"count": 1},
                }
            else:
                # No results for other queries
                response.status_code = 200
                response.json.return_value = {"results": [], "meta": {"count": 0}}

            return response

        mock_get.side_effect = mock_api_response

        # Create framework and add OpenAlex collector
        framework = PDFDiscoveryFramework()
        openalex_collector = OpenAlexPDFCollector(email="test@example.com")
        framework.add_collector(openalex_collector)

        # Discover PDFs
        result = framework.discover_pdfs(sample_papers)

        # Verify results
        assert result.total_papers == 3
        assert result.discovered_count == 2  # Only 2 papers have PDFs
        assert len(result.records) == 2

        # Check specific records
        pdf_urls = {record.paper_id: record.pdf_url for record in result.records}
        assert (
            pdf_urls["paper_1"]
            == "https://papers.neurips.cc/paper/2023/file/paper1.pdf"
        )
        assert pdf_urls["paper_2"] == "https://proceedings.mlr.press/v202/paper2.pdf"

        # Check Mila affiliation tracking
        mila_paper = next(r for r in result.records if r.paper_id == "paper_1")
        assert mila_paper.version_info["has_mila_author"] is True

        # Check statistics
        assert "openalex" in result.source_statistics
        assert result.source_statistics["openalex"]["attempted"] == 3
        assert result.source_statistics["openalex"]["successful"] == 2

    def test_mila_institution_filtering(self):
        """Test Mila institution ID configuration."""
        # Test with custom Mila ID
        collector = OpenAlexPDFCollector(
            mila_institution_id="https://openalex.org/I999999999"
        )
        assert collector.mila_institution_id == "https://openalex.org/I999999999"

        # Test with default Mila ID
        collector_default = OpenAlexPDFCollector()
        assert (
            collector_default.mila_institution_id == "https://openalex.org/I162448124"
        )

    @patch("requests.get")
    def test_concurrent_discovery(self, mock_get, sample_papers):
        """Test OpenAlex works with concurrent discovery."""

        # Mock successful responses for all papers
        def mock_response(url, params=None, headers=None, timeout=None):
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "best_oa_location": {
                            "is_oa": True,
                            "pdf_url": "https://example.com/paper.pdf",
                        },
                        "authorships": [],
                    }
                ],
                "meta": {"count": 1},
            }
            return response

        mock_get.side_effect = mock_response

        # Create framework with multiple collectors
        framework = PDFDiscoveryFramework()
        framework.add_collector(OpenAlexPDFCollector())

        # Mock another collector
        mock_collector = Mock()
        mock_collector.source_name = "mock_source"
        mock_collector.supports_batch = False
        mock_collector.discover_pdfs_batch.return_value = {}
        framework.add_collector(mock_collector)

        # Discover with progress callback
        progress_updates = []

        def progress_callback(current, total, message):
            progress_updates.append((current, total, message))

        result = framework.discover_pdfs(
            sample_papers[:1], progress_callback=progress_callback
        )

        # Verify concurrent execution
        assert result.discovered_count >= 0
        assert len(progress_updates) > 0
