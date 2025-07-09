"""Tests for BaseExtractor abstract interface."""

import pytest
from abc import ABC
from pathlib import Path
from typing import Dict, List

from compute_forecast.pipeline.content_extraction.parser.core.base_extractor import (
    BaseExtractor,
)


class ConcreteExtractor(BaseExtractor):
    """Concrete implementation for testing."""

    def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
        return {
            "text": "Sample text from pages",
            "method": "test_extractor",
            "confidence": 0.9,
        }

    def extract_full_text(self, pdf_path: Path) -> str:
        return "Full document text"

    def can_extract_affiliations(self) -> bool:
        return True


class TestBaseExtractor:
    """Test BaseExtractor abstract base class."""

    def test_is_abstract_class(self):
        """Test that BaseExtractor is an abstract class."""
        assert issubclass(BaseExtractor, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            BaseExtractor()

    def test_concrete_implementation_works(self):
        """Test that concrete implementation can be instantiated."""
        extractor = ConcreteExtractor()
        assert isinstance(extractor, BaseExtractor)

    def test_extract_first_pages_interface(self):
        """Test extract_first_pages method interface."""
        extractor = ConcreteExtractor()
        pdf_path = Path("/fake/path.pdf")
        pages = [0, 1]

        result = extractor.extract_first_pages(pdf_path, pages)

        assert isinstance(result, dict)
        assert "text" in result
        assert "method" in result
        assert "confidence" in result

    def test_extract_full_text_interface(self):
        """Test extract_full_text method interface."""
        extractor = ConcreteExtractor()
        pdf_path = Path("/fake/path.pdf")

        result = extractor.extract_full_text(pdf_path)

        assert isinstance(result, str)

    def test_can_extract_affiliations_interface(self):
        """Test can_extract_affiliations method interface."""
        extractor = ConcreteExtractor()

        result = extractor.can_extract_affiliations()

        assert isinstance(result, bool)

    def test_missing_abstract_methods_raise_error(self):
        """Test that missing abstract method implementations raise TypeError."""

        class IncompleteExtractor(BaseExtractor):
            def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
                return {}

            # Missing extract_full_text and can_extract_affiliations

        with pytest.raises(TypeError):
            IncompleteExtractor()
