"""Integration test for Nature Portfolio scraper with CLI."""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import json
import tempfile
from unittest.mock import patch, Mock

from compute_forecast.cli.main import app


class TestNatureCLIIntegration:
    """Test Nature Portfolio scraper integration with CLI."""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()
    
    def test_list_venues_includes_nature(self, runner):
        """Test that --list-venues includes Nature journals."""
        result = runner.invoke(app, ["collect", "--list-venues"])
        
        assert result.exit_code == 0
        assert "NaturePortfolioScraper" in result.output
        assert "nature" in result.output
        assert "scientific-reports" in result.output
        assert "nature-communications" in result.output
        
    def test_collect_nature_papers(self, runner):
        """Test collecting papers from Nature."""
        # Mock the actual API call
        mock_papers = [
            {
                'DOI': '10.1038/s41586-2024-12345-6',
                'title': ['Test Nature Paper'],
                'author': [{'given': 'John', 'family': 'Doe'}],
                'published-print': {'date-parts': [[2024, 1, 15]]},
                'URL': 'https://doi.org/10.1038/s41586-2024-12345-6',
                'type': 'journal-article'
            }
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {
                'total-results': 1,
                'items': mock_papers
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "nature_papers.json"
            
            with patch('requests.Session.get', return_value=mock_response):
                result = runner.invoke(app, [
                    "collect", 
                    "--venue", "nature",
                    "--year", "2024",
                    "--max-papers", "1",
                    "--output", str(output_file),
                    "--no-progress"
                ])
                
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Check output content
            with open(output_file) as f:
                data = json.load(f)
                
            assert data['collection_metadata']['total_papers'] == 1
            assert 'NATURE' in data['collection_metadata']['venues']
            assert 2024 in data['collection_metadata']['years']
            assert 'paperoni_nature_portfolio' in data['collection_metadata']['scrapers_used']
            
            assert len(data['papers']) == 1
            paper = data['papers'][0]
            assert paper['title'] == 'Test Nature Paper'
            assert paper['venue'] == 'NATURE'
            assert paper['year'] == 2024
            
    def test_collect_multiple_nature_journals(self, runner):
        """Test collecting from multiple Nature journals."""
        # Mock responses for different journals
        def mock_get(url, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200
            
            if '1476-4687' in url:  # Nature
                mock_resp.json.return_value = {
                    'message': {
                        'total-results': 1,
                        'items': [{
                            'DOI': '10.1038/nature-test',
                            'title': ['Nature Test Paper'],
                            'author': [],
                            'published-print': {'date-parts': [[2024, 1, 1]]},
                            'URL': 'https://doi.org/10.1038/nature-test',
                            'type': 'journal-article'
                        }]
                    }
                }
            elif '2045-2322' in url:  # Scientific Reports
                mock_resp.json.return_value = {
                    'message': {
                        'total-results': 1,
                        'items': [{
                            'DOI': '10.1038/s41598-test',
                            'title': ['Sci Reports Test Paper'],
                            'author': [],
                            'published-print': {'date-parts': [[2024, 1, 1]]},
                            'URL': 'https://doi.org/10.1038/s41598-test',
                            'type': 'journal-article'
                        }]
                    }
                }
            else:
                mock_resp.json.return_value = {'message': {'total-results': 0, 'items': []}}
                
            return mock_resp
            
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "multi_nature.json"
            
            with patch('requests.Session.get', side_effect=mock_get):
                result = runner.invoke(app, [
                    "collect",
                    "--venues", "nature,scientific-reports",
                    "--year", "2024", 
                    "--max-papers", "1",
                    "--output", str(output_file),
                    "--no-progress"
                ])
                
            assert result.exit_code == 0
            assert output_file.exists()
            
            with open(output_file) as f:
                data = json.load(f)
                
            assert data['collection_metadata']['total_papers'] == 2
            venues = data['collection_metadata']['venues']
            assert 'NATURE' in venues
            assert 'SCIENTIFIC REPORTS' in venues
            
    def test_nature_year_filtering(self, runner):
        """Test that year filtering works correctly for Nature."""
        # Mock empty response (no papers for the year)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {
                'total-results': 0,
                'items': []
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "nature_1850.json"
            
            with patch('requests.Session.get', return_value=mock_response):
                # Nature started in 1869, so 1850 should have no papers
                result = runner.invoke(app, [
                    "collect",
                    "--venue", "nature", 
                    "--year", "1850",
                    "--output", str(output_file),
                    "--no-progress"
                ])
                
            # Should still succeed but with no papers
            assert result.exit_code == 1  # No papers collected
            assert "No papers collected" in result.output
