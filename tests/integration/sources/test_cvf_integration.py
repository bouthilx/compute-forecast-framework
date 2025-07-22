"""Integration tests for CVF collector with PDF discovery framework."""

import pytest
from datetime import datetime
from unittest.mock import patch, Mock

from compute_forecast.pipeline.pdf_acquisition.discovery import PDFDiscoveryFramework
from compute_forecast.pipeline.pdf_acquisition.discovery.sources import CVFCollector
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


class TestCVFIntegration:
    """Integration tests for CVF collector."""

    @pytest.fixture
    def framework(self):
        """Create framework with CVF collector."""
        framework = PDFDiscoveryFramework()
        framework.add_collector(CVFCollector())
        return framework

    @pytest.fixture
    def cvf_papers(self):
        """Create sample CVF conference papers."""
        return [
            create_test_paper(
                paper_id="cvpr_2023_1",
                title="Deep Learning for Object Detection",
                authors=["John Doe", "Jane Smith"],
                year=2023,
                citation_count=50,
                venue="CVPR",
            ),
            create_test_paper(
                paper_id="iccv_2023_1",
                title="Vision Transformers for Image Classification",
                authors=["Alice Brown"],
                year=2023,
                citation_count=30,
                venue="ICCV",
            ),
            create_test_paper(
                paper_id="eccv_2022_1",
                title="Neural Rendering Techniques",
                authors=["Bob Wilson"],
                year=2022,
                citation_count=25,
                venue="ECCV",
            ),
            create_test_paper(
                paper_id="icml_2023_1",
                title="Machine Learning Theory",
                authors=["Charlie Davis"],
                year=2023,
                citation_count=40,
                venue="ICML",  # Not a CVF venue
            ),
        ]

    @patch("requests.get")
    def test_framework_discovery_with_cvf(self, mock_get, framework, cvf_papers):
        """Test PDF discovery through framework with CVF collector."""

        # Mock successful proceedings fetch for each venue
        def mock_response(url, **kwargs):
            response = Mock()
            response.status_code = 200

            if "CVPR2023" in url:
                response.text = """
                <html><body>
                <a href="/content/CVPR2023/papers/Doe23_Deep_Learning_Object_Detection_CVPR_2023_paper.pdf">
                    Deep Learning for Object Detection
                </a>
                </body></html>
                """
            elif "ICCV2023" in url:
                response.text = """
                <html><body>
                <a href="/content/ICCV2023/papers/Brown23_Vision_Transformers_ICCV_2023_paper.pdf">
                    Vision Transformers for Image Classification
                </a>
                </body></html>
                """
            elif "ECCV2022" in url:
                response.text = """
                <html><body>
                <a href="/content/ECCV2022/papers/Wilson22_Neural_Rendering_ECCV_2022_paper.pdf">
                    Neural Rendering Techniques
                </a>
                </body></html>
                """
            else:
                response.text = "<html><body>No papers</body></html>"

            return response

        mock_get.side_effect = mock_response

        # Run discovery
        result = framework.discover_pdfs(cvf_papers)

        # Verify results
        assert result.total_papers == 4
        assert result.discovered_count == 3  # 3 CVF papers found
        assert len(result.records) == 3
        assert len(result.failed_papers) == 1
        assert "icml_2023_1" in result.failed_papers

        # Check discovered PDFs
        pdf_by_id = {r.paper_id: r for r in result.records}

        # CVPR paper
        assert "cvpr_2023_1" in pdf_by_id
        cvpr_pdf = pdf_by_id["cvpr_2023_1"]
        assert cvpr_pdf.source == "cvf"
        assert (
            "CVPR2023/papers/Doe23_Deep_Learning_Object_Detection_CVPR_2023_paper.pdf"
            in cvpr_pdf.pdf_url
        )
        assert cvpr_pdf.confidence_score == 0.95

        # ICCV paper
        assert "iccv_2023_1" in pdf_by_id
        iccv_pdf = pdf_by_id["iccv_2023_1"]
        assert (
            "ICCV2023/papers/Brown23_Vision_Transformers_ICCV_2023_paper.pdf"
            in iccv_pdf.pdf_url
        )

        # ECCV paper
        assert "eccv_2022_1" in pdf_by_id
        eccv_pdf = pdf_by_id["eccv_2022_1"]
        assert (
            "ECCV2022/papers/Wilson22_Neural_Rendering_ECCV_2022_paper.pdf"
            in eccv_pdf.pdf_url
        )

    def test_cvf_venue_priority(self, framework):
        """Test that CVF collector can be prioritized for CV venues."""
        # Set CVF as priority for computer vision conferences
        framework.set_venue_priorities(
            {
                "CVPR": ["cvf", "semantic_scholar"],
                "ICCV": ["cvf", "semantic_scholar"],
                "ECCV": ["cvf", "semantic_scholar"],
                "WACV": ["cvf", "semantic_scholar"],
            }
        )

        # Verify priorities were set
        assert framework.venue_priorities["CVPR"][0] == "cvf"
        assert framework.venue_priorities["ICCV"][0] == "cvf"

    @patch("requests.get")
    def test_cvf_biannual_conference_validation(self, mock_get, framework):
        """Test that biannual conferences are validated correctly."""
        # ICCV should work for odd years
        paper_2023 = create_test_paper(
            paper_id="test1",
            title="Test Paper",
            authors=[],
            year=2023,
            citation_count=0,
            venue="ICCV",
        )

        # ICCV should fail for even years
        paper_2022 = create_test_paper(
            paper_id="test2",
            title="Test Paper",
            authors=[],
            year=2022,
            citation_count=0,
            venue="ICCV",
        )

        # Mock proceedings
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body>
        <a href="/content/ICCV2023/papers/Test_Paper_ICCV_2023_paper.pdf">Test Paper</a>
        </body></html>
        """
        mock_get.return_value = mock_response

        # Test discovery
        result = framework.discover_pdfs([paper_2023, paper_2022])

        # Should only find the 2023 paper
        assert result.discovered_count == 1
        assert result.records[0].paper_id == "test1"
        assert "test2" in result.failed_papers
