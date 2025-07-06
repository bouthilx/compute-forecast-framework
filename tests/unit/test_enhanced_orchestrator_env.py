"""Test environment variable support in enhanced orchestrator."""

import os
from unittest.mock import patch
from compute_forecast.data.collectors.enhanced_orchestrator import (
    EnhancedCollectionOrchestrator,
)


class TestEnhancedOrchestratorEnvironment:
    """Test environment variable loading functionality."""

    def test_load_from_env_all_variables(self):
        """Test loading all supported environment variables."""
        env_vars = {
            "SEMANTIC_SCHOLAR_API_KEY": "test_ss_key_123",
            "OPENALEX_EMAIL": "test@example.com",
            "CROSSREF_EMAIL": "crossref@example.com",
            "GOOGLE_SCHOLAR_USE_PROXY": "true",
        }

        with patch.dict(os.environ, env_vars):
            orchestrator = EnhancedCollectionOrchestrator()
            config = orchestrator._load_from_env()

            assert config["semantic_scholar"] == "test_ss_key_123"
            assert config["openalex_email"] == "test@example.com"
            assert config["crossref_email"] == "crossref@example.com"
            assert config["google_scholar_proxy"] is True

    def test_load_from_env_partial_variables(self):
        """Test loading with only some environment variables set."""
        env_vars = {
            "SEMANTIC_SCHOLAR_API_KEY": "partial_key",
            "OPENALEX_EMAIL": "partial@example.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            orchestrator = EnhancedCollectionOrchestrator()
            config = orchestrator._load_from_env()

            assert config["semantic_scholar"] == "partial_key"
            assert config["openalex_email"] == "partial@example.com"
            assert "crossref_email" not in config
            assert "google_scholar_proxy" not in config

    def test_load_from_env_no_variables(self):
        """Test loading with no environment variables set."""
        with patch.dict(os.environ, {}, clear=True):
            orchestrator = EnhancedCollectionOrchestrator()
            config = orchestrator._load_from_env()

            assert config == {}

    def test_google_scholar_proxy_parsing(self):
        """Test various formats for Google Scholar proxy setting."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("invalid", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"GOOGLE_SCHOLAR_USE_PROXY": env_value}):
                orchestrator = EnhancedCollectionOrchestrator()
                config = orchestrator._load_from_env()
                assert config.get("google_scholar_proxy", False) == expected

    def test_env_vars_override_by_init_params(self):
        """Test that init parameters override environment variables."""
        env_vars = {
            "SEMANTIC_SCHOLAR_API_KEY": "env_key",
            "OPENALEX_EMAIL": "env@example.com",
        }

        init_keys = {
            "semantic_scholar": "init_key",
            "crossref_email": "init_crossref@example.com",
        }

        with patch.dict(os.environ, env_vars):
            # Mock the source clients to avoid actual initialization
            with patch(
                "src.data.sources.enhanced_semantic_scholar.EnhancedSemanticScholarClient"
            ) as mock_ss, patch(
                "src.data.sources.enhanced_openalex.EnhancedOpenAlexClient"
            ) as mock_oa, patch(
                "src.data.sources.enhanced_crossref.EnhancedCrossrefClient"
            ) as mock_cr, patch("src.data.sources.google_scholar.GoogleScholarClient"):
                EnhancedCollectionOrchestrator(api_keys=init_keys)

                # Check that init_key overrides env_key for semantic_scholar
                mock_ss.assert_called_with(api_key="init_key")

                # Check that env email is used for openalex (not overridden)
                mock_oa.assert_called_with(email="env@example.com")

                # Check that init email is used for crossref
                mock_cr.assert_called_with(email="init_crossref@example.com")

    def test_api_client_initialization_with_env_vars(self):
        """Test that API clients are properly initialized with environment variables."""
        env_vars = {
            "SEMANTIC_SCHOLAR_API_KEY": "ss_test_key",
            "OPENALEX_EMAIL": "oa_test@example.com",
            "CROSSREF_EMAIL": "cr_test@example.com",
            "GOOGLE_SCHOLAR_USE_PROXY": "yes",
        }

        with patch.dict(os.environ, env_vars):
            with patch(
                "src.data.sources.enhanced_semantic_scholar.EnhancedSemanticScholarClient"
            ) as mock_ss, patch(
                "src.data.sources.enhanced_openalex.EnhancedOpenAlexClient"
            ) as mock_oa, patch(
                "src.data.sources.enhanced_crossref.EnhancedCrossrefClient"
            ) as mock_cr, patch(
                "src.data.sources.google_scholar.GoogleScholarClient"
            ) as mock_gs:
                EnhancedCollectionOrchestrator()

                # Verify each client was initialized with the correct parameters
                mock_ss.assert_called_once_with(api_key="ss_test_key")
                mock_oa.assert_called_once_with(email="oa_test@example.com")
                mock_cr.assert_called_once_with(email="cr_test@example.com")
                mock_gs.assert_called_once_with(use_proxy=True)

    def test_logging_env_var_count(self, caplog):
        """Test that environment variable loading is logged."""
        env_vars = {
            "SEMANTIC_SCHOLAR_API_KEY": "key1",
            "OPENALEX_EMAIL": "email1",
            "CROSSREF_EMAIL": "email2",
        }

        with patch.dict(os.environ, env_vars):
            with caplog.at_level("INFO"):
                EnhancedCollectionOrchestrator()

                # Check that the log message was created
                assert (
                    "Loaded 3 API configurations from environment variables"
                    in caplog.text
                )
