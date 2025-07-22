"""Integration tests for PubMed Central collector with PDF discovery framework."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from compute_forecast.pipeline.pdf_acquisition.discovery.core.framework import (
    PDFDiscoveryFramework,
)
from compute_forecast.pipeline.pdf_acquisition.discovery.sources.pubmed_central_collector import (
    PubMedCentralCollector,
)
from compute_forecast.pipeline.metadata_collection.models import Paper
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


class TestPubMedCentralIntegration:
    """Test PubMed Central collector integration with framework."""

    @pytest.fixture
    def framework(self):
        """Create PDF discovery framework with PubMed Central collector."""
        framework = PDFDiscoveryFramework()
        collector = PubMedCentralCollector()
        framework.add_collector(collector)
        return framework

    @pytest.fixture
    def medical_papers(self):
        """Create sample medical papers."""
        return [
            create_test_paper(
                paper_id="med_1",
                title="COVID-19 Vaccine Efficacy Study",
                authors=["Dr. Smith", "Dr. Jones"],
                year=2023,
                citation_count=100,
                venue="Journal of Medical Research",
            ),
            create_test_paper(
                paper_id="med_2",
                title="Machine Learning in Medical Imaging",
                authors=["Dr. Brown", "Dr. Davis"],
                year=2023,
                citation_count=50,
                venue="Medical AI Journal",
            ),
            create_test_paper(
                paper_id="med_3",
                title="Deep Learning for Cancer Detection",
                authors=["Dr. Wilson"],
                year=2022,
                citation_count=75,
                venue="Oncology Research",
            ),
        ]

    def test_framework_with_pubmed_central(self, framework, medical_papers):
        """Test framework discovers PDFs using PubMed Central."""
        # Mock successful PMC responses
        with patch(
            "compute_forecast.pdf_discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            # Setup responses for paper 1
            search_resp1 = Mock()
            search_resp1.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSearchResult>
                <Count>1</Count>
                <IdList><Id>11111111</Id></IdList>
            </eSearchResult>"""
            search_resp1.status_code = 200

            summary_resp1 = Mock()
            summary_resp1.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSummaryResult>
                <DocSum>
                    <Id>11111111</Id>
                    <Item Name="pmc" Type="String">PMC1111111</Item>
                </DocSum>
            </eSummaryResult>"""
            summary_resp1.status_code = 200

            # Setup responses for paper 2
            search_resp2 = Mock()
            search_resp2.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSearchResult>
                <Count>1</Count>
                <IdList><Id>22222222</Id></IdList>
            </eSearchResult>"""
            search_resp2.status_code = 200

            summary_resp2 = Mock()
            summary_resp2.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSummaryResult>
                <DocSum>
                    <Id>22222222</Id>
                    <Item Name="pmc" Type="String">PMC2222222</Item>
                </DocSum>
            </eSummaryResult>"""
            summary_resp2.status_code = 200

            # Paper 3 has no PMC ID (failure case)
            no_results = Mock()
            no_results.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSearchResult><Count>0</Count><IdList></IdList></eSearchResult>"""
            no_results.status_code = 200

            mock_get.side_effect = [
                search_resp1,
                summary_resp1,  # Paper 1 DOI search
                search_resp2,
                summary_resp2,  # Paper 2 DOI search
                no_results,
                no_results,  # Paper 3 searches fail
            ]

            # Run discovery
            result = framework.discover_pdfs(medical_papers)

            # Verify results
            assert result.total_papers == 3
            assert result.discovered_count == 2
            assert len(result.records) == 2
            assert len(result.failed_papers) == 1
            assert "med_3" in result.failed_papers

            # Check discovered PDFs
            pdf_ids = {record.paper_id for record in result.records}
            assert "med_1" in pdf_ids
            assert "med_2" in pdf_ids

            # Verify URLs
            urls = {record.pdf_url for record in result.records}
            assert "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1111111/pdf/" in urls
            assert "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2222222/pdf/" in urls

            # Check source statistics
            assert "pubmed_central" in result.source_statistics
            stats = result.source_statistics["pubmed_central"]
            assert stats["attempted"] == 3
            assert stats["successful"] == 2
            assert stats["failed"] == 1

    def test_venue_specific_prioritization(self, framework):
        """Test that PubMed Central is prioritized for medical venues."""
        # Set venue priorities
        framework.set_venue_priorities(
            {
                "Journal of Medical Research": ["pubmed_central", "arxiv"],
                "Medical AI Journal": ["pubmed_central", "openreview"],
            }
        )

        # Priorities are set internally in the deduplication engine

        # Test with a medical paper
        paper = create_test_paper(
            paper_id="med_test",
            title="Test Medical Paper",
            authors=["Dr. Test"],
            year=2023,
            citation_count=10,
            venue="Journal of Medical Research",
        )

        # Mock response
        with patch(
            "compute_forecast.pdf_discovery.sources.pubmed_central_collector.requests.get"
        ) as mock_get:
            search_resp = Mock()
            search_resp.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSearchResult>
                <Count>1</Count>
                <IdList><Id>99999999</Id></IdList>
            </eSearchResult>"""
            search_resp.status_code = 200

            summary_resp = Mock()
            summary_resp.text = """<?xml version="1.0" encoding="UTF-8"?>
            <eSummaryResult>
                <DocSum>
                    <Id>99999999</Id>
                    <Item Name="pmc" Type="String">PMC9999999</Item>
                </DocSum>
            </eSummaryResult>"""
            summary_resp.status_code = 200

            mock_get.side_effect = [search_resp, summary_resp]

            result = framework.discover_pdfs([paper])

            assert result.discovered_count == 1
            assert result.records[0].source == "pubmed_central"
