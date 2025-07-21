"""Tests for AAAI scraper using OAI-PMH protocol."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import xml.etree.ElementTree as ET
from compute_forecast.pipeline.metadata_collection.sources.scrapers.aaai import (
    AAAIScraper,
)
from compute_forecast.pipeline.metadata_collection.sources.scrapers.models import (
    SimplePaper,
)


class TestAAAIScraper:
    """Test AAAI scraper functionality."""

    @pytest.fixture
    def scraper(self):
        """Create an AAAI scraper instance."""
        return AAAIScraper()

    def test_get_supported_venues(self, scraper):
        """Test that scraper returns supported AAAI venues."""
        venues = scraper.get_supported_venues()

        assert "aaai" in venues
        assert "aies" in venues  # AI, Ethics, and Society
        assert "hcomp" in venues  # Human Computation and Crowdsourcing
        assert "icwsm" in venues  # Web and Social Media
        assert len(venues) >= 4

    def test_get_available_years(self, scraper):
        """Test available years for different venues."""
        current_year = datetime.now().year

        # AAAI - oldest conference (1980)
        aaai_years = scraper.get_available_years("aaai")
        assert 1980 in aaai_years
        assert current_year in aaai_years
        assert len(aaai_years) > 40

        # AIES - started 2018
        aies_years = scraper.get_available_years("aies")
        assert min(aies_years) == 2018
        assert current_year in aies_years

        # HCOMP - started 2013
        hcomp_years = scraper.get_available_years("hcomp")
        assert min(hcomp_years) == 2013
        assert current_year in hcomp_years

        # ICWSM - started 2007
        icwsm_years = scraper.get_available_years("icwsm")
        assert min(icwsm_years) == 2007
        assert current_year in icwsm_years

        # Unknown venue
        unknown_years = scraper.get_available_years("unknown")
        assert unknown_years == []

    def test_venue_to_journal_mapping(self, scraper):
        """Test that venues map correctly to OJS journal names."""
        assert scraper._get_journal_name("aaai") == "AAAI"
        assert scraper._get_journal_name("aies") == "AIES"
        assert scraper._get_journal_name("hcomp") == "HCOMP"
        assert scraper._get_journal_name("icwsm") == "ICWSM"
        assert scraper._get_journal_name("unknown") is None

    def test_session_configuration(self, scraper):
        """Test that HTTP session is properly configured."""
        assert "User-Agent" in scraper.session.headers
        assert "Accept" in scraper.session.headers
        assert scraper.session.headers["Accept"] == "application/xml"

    def test_parse_oai_record_success(self, scraper):
        """Test parsing of OAI-PMH record."""
        # Mock OAI-PMH XML response with proper namespaces
        xml_response = """<?xml version="1.0"?>
        <record xmlns="http://www.openarchives.org/OAI/2.0/"
                xmlns:oai="http://www.openarchives.org/OAI/2.0/"
                xmlns:dc="http://purl.org/dc/elements/1.1/">
            <header>
                <identifier>oai:ojs.aaai.org:article/32043</identifier>
                <datestamp>2025-04-11T09:18:53Z</datestamp>
            </header>
            <metadata>
                <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/">
                    <dc:title>GoBERT: Gene Ontology Graph Informed BERT</dc:title>
                    <dc:creator>Miao, Yuwei</dc:creator>
                    <dc:creator>Guo, Yuzhi</dc:creator>
                    <dc:description>Abstract text here</dc:description>
                    <dc:date>2025-04-11</dc:date>
                    <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/32043</dc:identifier>
                    <dc:identifier>10.1609/aaai.v39i1.32043</dc:identifier>
                    <dc:relation>https://ojs.aaai.org/index.php/AAAI/article/view/32043/34198</dc:relation>
                    <dc:source>Proceedings of the AAAI Conference on Artificial Intelligence; Vol. 39 No. 1</dc:source>
                </oai_dc:dc>
            </metadata>
        </record>"""

        root = ET.fromstring(xml_response)
        paper = scraper._parse_oai_record(root, "aaai", 2025)

        assert paper is not None
        assert paper.title == "GoBERT: Gene Ontology Graph Informed BERT"
        assert paper.authors == ["Miao, Yuwei", "Guo, Yuzhi"]
        assert paper.venue == "AAAI"
        assert paper.year == 2025
        assert paper.abstract == "Abstract text here"
        assert paper.doi == "10.1609/aaai.v39i1.32043"
        assert paper.paper_id == "32043"
        assert (
            paper.source_url == "https://ojs.aaai.org/index.php/AAAI/article/view/32043"
        )
        assert paper.pdf_urls == [
            "https://ojs.aaai.org/index.php/AAAI/article/view/32043/34198"
        ]

    def test_scrape_venue_year_success(self, scraper):
        """Test successful paper collection from OAI-PMH."""
        # Set batch size to 1 so we stop after first paper
        scraper.config.batch_size = 1

        # Mock XML response
        xml_response = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <responseDate>2025-01-09T19:25:52Z</responseDate>
            <request verb="ListRecords">https://ojs.aaai.org/index.php/AAAI/oai</request>
            <ListRecords>
                <record>
                    <header>
                        <identifier>oai:ojs.aaai.org:article/32043</identifier>
                    </header>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Test Paper Title</dc:title>
                            <dc:creator>Author One</dc:creator>
                            <dc:date>2024-01-01</dc:date>
                            <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/32043</dc:identifier>
                            <dc:identifier>10.1609/aaai.v38i1.32043</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </ListRecords>
        </OAI-PMH>"""

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response

        # Mock only needs to handle first quarter since batch_size=1
        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper.scrape_venue_year("aaai", 2024)

        assert result.success
        assert result.papers_collected == 1

        papers = result.metadata.get("papers", [])
        assert len(papers) == 1

        paper = papers[0]
        assert isinstance(paper, SimplePaper)
        assert paper.title == "Test Paper Title"
        assert paper.authors == ["Author One"]
        assert paper.venue == "AAAI"
        assert paper.year == 2024

    def test_scrape_venue_year_with_date_filtering(self, scraper):
        """Test that date filtering is applied correctly with monthly ranges."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords></ListRecords>
        </OAI-PMH>"""

        with patch.object(
            scraper.session, "get", return_value=mock_response
        ) as mock_get:
            scraper.scrape_venue_year("aaai", 2023)

            # Check that the first request included January date filtering
            args, kwargs = mock_get.call_args_list[0]
            assert "params" in kwargs
            assert "from" in kwargs["params"]
            assert "until" in kwargs["params"]
            assert kwargs["params"]["from"] == "2023-01-01"
            assert kwargs["params"]["until"] == "2023-01-31"

    def test_scrape_venue_year_empty_results(self, scraper):
        """Test handling of empty results."""
        xml_response = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords></ListRecords>
        </OAI-PMH>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper.scrape_venue_year("aaai", 2024)

        assert result.success
        assert result.papers_collected == 0
        assert result.metadata.get("papers", []) == []

    def test_scrape_venue_year_api_error(self, scraper):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper.scrape_venue_year("aaai", 2024)

        assert not result.success
        assert len(result.errors) > 0
        assert "Error fetching AAAI papers" in result.errors[0]

    def test_scrape_venue_year_invalid_venue(self, scraper):
        """Test handling of invalid venue."""
        result = scraper.scrape_venue_year("invalid-venue", 2024)

        assert not result.success
        assert len(result.errors) > 0
        assert "Unsupported venue" in result.errors[0]

    def test_pagination_handling(self, scraper):
        """Test that scraper handles pagination correctly."""
        # First response with resumption token
        xml_response_1 = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords>
                <record>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Paper 1</dc:title>
                            <dc:creator>Author 1</dc:creator>
                            <dc:date>2024-01-01</dc:date>
                            <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/1</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
                <resumptionToken>token123</resumptionToken>
            </ListRecords>
        </OAI-PMH>"""

        # Second response without resumption token
        xml_response_2 = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords>
                <record>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Paper 2</dc:title>
                            <dc:creator>Author 2</dc:creator>
                            <dc:date>2024-01-01</dc:date>
                            <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/2</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </ListRecords>
        </OAI-PMH>"""

        # Set batch size to allow multiple requests
        scraper.config.batch_size = 10

        # Mock responses
        mock_responses = [
            Mock(status_code=200, text=xml_response_1),
            Mock(status_code=200, text=xml_response_2),
        ]

        # Need to add empty responses for the other quarters
        empty_response = Mock(
            status_code=200,
            text="""<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords></ListRecords>
        </OAI-PMH>""",
        )

        with patch.object(
            scraper.session,
            "get",
            side_effect=[
                mock_responses[0],  # Q1 page 1
                mock_responses[1],  # Q1 page 2
                empty_response,  # Q2
                empty_response,  # Q3
                empty_response,  # Q4
            ],
        ):
            result = scraper.scrape_venue_year("aaai", 2024)

        assert result.success
        papers = result.metadata.get("papers", [])
        assert len(papers) == 2
        assert papers[0].title == "Paper 1"
        assert papers[1].title == "Paper 2"

    def test_extract_article_id(self, scraper):
        """Test extraction of article ID from OAI identifier."""
        assert scraper._extract_article_id("oai:ojs.aaai.org:article/32043") == "32043"
        assert scraper._extract_article_id("oai:ojs.aaai.org:article/1234") == "1234"
        assert scraper._extract_article_id("invalid-format") is None

    def test_503_retry_logic(self, scraper):
        """Test that scraper retries on 503 errors."""
        # First response: 503 error with Retry-After
        mock_response_503 = Mock()
        mock_response_503.status_code = 503
        mock_response_503.headers = {"Retry-After": "1"}

        # Second response: Success
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords>
                <record>
                    <metadata>
                        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                                   xmlns:dc="http://purl.org/dc/elements/1.1/">
                            <dc:title>Test Paper</dc:title>
                            <dc:creator>Author</dc:creator>
                            <dc:date>2024-01-01</dc:date>
                            <dc:identifier>https://ojs.aaai.org/index.php/AAAI/article/view/1</dc:identifier>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </ListRecords>
        </OAI-PMH>"""

        # Need 4 sets of responses for 4 quarters - Q1 has retry, others are empty
        empty_response = Mock()
        empty_response.status_code = 200
        empty_response.text = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords></ListRecords>
        </OAI-PMH>"""

        with patch.object(
            scraper.session,
            "get",
            side_effect=[
                mock_response_503,
                mock_response_200,  # Q1: retry then success
                empty_response,  # Q2: empty
                empty_response,  # Q3: empty
                empty_response,  # Q4: empty
            ],
        ):
            with patch("time.sleep"):  # Mock sleep to speed up test
                result = scraper.scrape_venue_year("aaai", 2024)

        assert result.success
        papers = result.metadata.get("papers", [])
        assert len(papers) == 1
        assert papers[0].title == "Test Paper"

    def test_estimate_paper_count_with_identifiers(self, scraper):
        """Test paper count estimation using ListIdentifiers."""
        # Mock response with identifiers
        xml_response = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListIdentifiers>
                <header>
                    <identifier>oai:ojs.aaai.org:article/1</identifier>
                </header>
                <header>
                    <identifier>oai:ojs.aaai.org:article/2</identifier>
                </header>
                <header>
                    <identifier>oai:ojs.aaai.org:article/3</identifier>
                </header>
                <header>
                    <identifier>oai:ojs.aaai.org:article/4</identifier>
                </header>
                <header>
                    <identifier>oai:ojs.aaai.org:article/5</identifier>
                </header>
            </ListIdentifiers>
        </OAI-PMH>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response

        with patch.object(
            scraper.session, "get", return_value=mock_response
        ) as mock_get:
            estimate = scraper.estimate_paper_count("aaai", 2024)

        # Should have called with ListIdentifiers verb
        args, kwargs = mock_get.call_args
        assert "params" in kwargs
        assert kwargs["params"]["verb"] == "ListIdentifiers"
        assert kwargs["params"]["from"] == "2024-02-01"  # AAAI is in February
        assert kwargs["params"]["until"] == "2024-02-28"

        # With 5 papers in February sample, expect ~6 total (5 * 1.2)
        assert estimate == 6

    def test_estimate_paper_count_with_resumption_token(self, scraper):
        """Test estimation when OAI-PMH provides completeListSize."""
        xml_response = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListIdentifiers>
                <header>
                    <identifier>oai:ojs.aaai.org:article/1</identifier>
                </header>
                <resumptionToken completeListSize="1234">token123</resumptionToken>
            </ListIdentifiers>
        </OAI-PMH>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response

        with patch.object(scraper.session, "get", return_value=mock_response):
            estimate = scraper.estimate_paper_count("aaai", 2024)

        # Should use completeListSize * 1.2 for AAAI
        assert estimate == int(1234 * 1.2)

    def test_estimate_paper_count_no_records(self, scraper):
        """Test estimation when no records found."""
        xml_response = """<?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <error code="noRecordsMatch">No records found</error>
        </OAI-PMH>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response

        with patch.object(scraper.session, "get", return_value=mock_response):
            estimate = scraper.estimate_paper_count("aaai", 1990)

        assert estimate == 0

    def test_estimate_paper_count_fallback_to_defaults(self, scraper):
        """Test fallback to defaults on API error."""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch.object(scraper.session, "get", return_value=mock_response):
            # Should fall back to defaults
            assert scraper.estimate_paper_count("aaai", 2024) == 1500
            assert scraper.estimate_paper_count("aies", 2024) == 100
            assert scraper.estimate_paper_count("hcomp", 2024) == 150
            assert scraper.estimate_paper_count("icwsm", 2024) == 300

    def test_estimate_paper_count_invalid_venue(self, scraper):
        """Test estimation returns None for invalid venue."""
        estimate = scraper.estimate_paper_count("invalid-venue", 2024)
        assert estimate is None
