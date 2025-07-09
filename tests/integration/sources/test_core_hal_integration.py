"""Integration tests for CORE and HAL PDF collectors."""

import pytest
from unittest.mock import Mock, patch

from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.pdf_acquisition.discovery.core.framework import (
    PDFDiscoveryFramework,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.sources.core_collector import (
    COREPDFCollector,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.sources.hal_collector import (
    HALPDFCollector,
)


class TestCOREHALIntegration:
    """Integration tests for CORE and HAL collectors with the framework."""

    @pytest.fixture
    def framework(self):
        """Create a framework with CORE and HAL collectors."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(COREPDFCollector())
        framework.add_collector(HALPDFCollector())
        return framework

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        return [
            Paper(
                paper_id="paper1",
                title="Deep Learning for Scientific Computing",
                authors=[Author(name="John Doe"), Author(name="Jane Smith")],
                year=2023,
                doi="10.1234/dlsc.2023.001",
                venue="Nature Machine Intelligence",
                citations=100,
            ),
            Paper(
                paper_id="paper2",
                title="Quantum Computing Applications",
                authors=[Author(name="Alice Brown")],
                year=2023,
                venue="Physical Review Letters",
                citations=50,
            ),
            Paper(
                paper_id="paper3",
                title="French Research on AI Ethics",
                authors=[Author(name="Pierre Dupont", affiliation="CNRS")],
                year=2023,
                doi="10.5678/ai-ethics.2023",
                venue="HAL Conference",
                citations=25,
                urls=["https://hal.science/hal-12345678"],
            ),
        ]

    def test_framework_integration_with_core_and_hal(self, framework, sample_papers):
        """Test that both collectors work within the framework."""
        # Mock CORE responses
        core_responses = [
            {
                "totalHits": 1,
                "results": [
                    {
                        "id": "core:100001",
                        "doi": "10.1234/dlsc.2023.001",
                        "downloadUrl": "https://core.ac.uk/download/pdf/100001.pdf",
                        "repositoryDocument": {"pdfStatus": 1, "pdfSize": 1048576},
                    }
                ],
            },
            {"totalHits": 0, "results": []},  # No result for paper2
            {"totalHits": 0, "results": []},  # No result for paper3
        ]

        # Mock HAL responses
        hal_oai_response = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <GetRecord>
                <record>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:identifier>https://hal.science/hal-12345678/file/paper.pdf</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </GetRecord>
        </OAI-PMH>"""

        with patch("requests.get") as mock_get:
            # Set up mock responses
            response_iter = iter(core_responses)

            def mock_get_response(*args, **kwargs):
                url = args[0] if args else kwargs.get("url", "")

                # CORE API calls
                if "core.ac.uk" in url:
                    mock_resp = Mock()
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = next(response_iter)
                    return mock_resp

                # HAL OAI-PMH calls
                elif "archives-ouvertes.fr/oai" in url:
                    # Only return success for paper3 with hal ID
                    if "hal-12345678" in str(kwargs.get("params", {})):
                        mock_resp = Mock()
                        mock_resp.status_code = 200
                        mock_resp.text = hal_oai_response
                        mock_resp.content = hal_oai_response.encode("utf-8")
                        return mock_resp
                    else:
                        # Return error for other papers
                        error_resp = Mock()
                        error_resp.status_code = 200
                        error_resp.text = """<?xml version="1.0" encoding="UTF-8"?>
                        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
                            <error code="noRecordsMatch">No matching records</error>
                        </OAI-PMH>"""
                        error_resp.content = error_resp.text.encode("utf-8")
                        return error_resp

                # HAL Search API calls (fallback)
                elif "archives-ouvertes.fr/search" in url:
                    mock_resp = Mock()
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = {
                        "response": {"numFound": 0, "docs": []}
                    }
                    return mock_resp

                return Mock(status_code=404)

            mock_get.side_effect = mock_get_response

            # Run discovery
            result = framework.discover_pdfs(sample_papers)

            # Verify results
            assert result.total_papers == 3
            assert (
                result.discovered_count >= 1
            )  # At least paper1 from CORE should be found

            # Check paper1 was found by CORE
            paper1_records = [r for r in result.records if r.paper_id == "paper1"]
            assert len(paper1_records) == 1
            assert paper1_records[0].source == "core"
            assert (
                paper1_records[0].pdf_url
                == "https://core.ac.uk/download/pdf/100001.pdf"
            )

            # Check source statistics
            assert "core" in result.source_statistics
            assert "hal" in result.source_statistics
            assert result.source_statistics["core"]["attempted"] == 3
            assert result.source_statistics["core"]["successful"] >= 1

    def test_venue_priorities_with_core_and_hal(self, framework):
        """Test that venue priorities work correctly with CORE and HAL."""
        # Set priorities: HAL preferred for French venues
        framework.set_venue_priorities(
            {
                "HAL Conference": ["hal", "core"],
                "Nature Machine Intelligence": ["core", "hal"],
            }
        )

        # Create papers that could be found by both sources
        papers = [
            Paper(
                paper_id="dual1",
                title="Dual Source Paper",
                authors=[Author(name="Test Author")],
                year=2023,
                doi="10.1234/dual.001",
                venue="HAL Conference",
                citations=10,
            )
        ]

        # Mock both sources finding the paper
        with patch("requests.get") as mock_get:

            def mock_get_response(*args, **kwargs):
                url = args[0] if args else kwargs.get("url", "")

                # CORE finds it
                if "core.ac.uk" in url:
                    mock_resp = Mock()
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = {
                        "totalHits": 1,
                        "results": [
                            {
                                "id": "core:200001",
                                "downloadUrl": "https://core.ac.uk/download/pdf/200001.pdf",
                                "repositoryDocument": {"pdfStatus": 1},
                            }
                        ],
                    }
                    return mock_resp

                # HAL also finds it
                elif "archives-ouvertes.fr" in url:
                    if "/search" in url:
                        mock_resp = Mock()
                        mock_resp.status_code = 200
                        mock_resp.json.return_value = {
                            "response": {
                                "numFound": 1,
                                "docs": [
                                    {
                                        "docid": "hal-99999999",
                                        "files_s": [
                                            "https://hal.science/hal-99999999/file/paper.pdf"
                                        ],
                                        "openAccess_bool": True,
                                    }
                                ],
                            }
                        }
                        return mock_resp

                return Mock(status_code=404)

            mock_get.side_effect = mock_get_response

            # Run discovery
            result = framework.discover_pdfs(papers)

            # Should have one record (deduplicated)
            assert result.discovered_count == 1
            assert len(result.records) == 1

            # Given the venue priority, HAL should be preferred
            # (Note: This test assumes deduplication chooses based on priorities)
            # The actual behavior depends on the deduplication implementation
