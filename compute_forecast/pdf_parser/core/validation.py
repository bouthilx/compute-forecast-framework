"""Validation logic for PDF extraction results."""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class AffiliationValidator:
    """Validates affiliation extraction results."""

    def __init__(
        self,
        min_confidence: float = 0.5,
        min_affiliations: int = 1,
        min_text_length: int = 20,
    ):
        """Initialize validator with criteria.

        Args:
            min_confidence: Minimum confidence score to accept
            min_affiliations: Minimum number of affiliations required
            min_text_length: Minimum length of extracted text
        """
        self.min_confidence = min_confidence
        self.min_affiliations = min_affiliations
        self.min_text_length = min_text_length

    def validate_affiliations(
        self, extraction_result: Dict, paper_metadata: Dict
    ) -> bool:
        """Validate extracted affiliations against paper metadata.

        Args:
            extraction_result: Result from extractor containing text, affiliations, etc.
            paper_metadata: Paper metadata for cross-reference

        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Check confidence score
            confidence = extraction_result.get("confidence", 0.0)
            if confidence < self.min_confidence:
                logger.debug(
                    f"Confidence {confidence} below threshold {self.min_confidence}"
                )
                return False

            # Check affiliations count
            affiliations = extraction_result.get("affiliations", [])
            if len(affiliations) < self.min_affiliations:
                logger.debug(
                    f"Only {len(affiliations)} affiliations, need {self.min_affiliations}"
                )
                return False

            # Check text quality
            text = extraction_result.get("text", "")
            if len(text) < self.min_text_length:
                logger.debug(
                    f"Text too short: {len(text)} chars, need {self.min_text_length}"
                )
                return False

            # Check for reasonable affiliation structure
            if not self._validate_affiliation_structure(affiliations):
                logger.debug("Invalid affiliation structure")
                return False

            # Optional: check author name matching
            if "authors" in paper_metadata:
                if not self._validate_author_matching(text, paper_metadata["authors"]):
                    logger.debug("Author name matching failed")
                    # Don't fail validation on this - it's just a warning

            logger.debug("Affiliation validation passed")
            return True

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False

    def _validate_affiliation_structure(self, affiliations: List[Dict]) -> bool:
        """Validate that affiliations have proper structure.

        Args:
            affiliations: List of affiliation dictionaries

        Returns:
            True if structure is valid
        """
        for affiliation in affiliations:
            if not isinstance(affiliation, dict):
                return False

            # Should have at least a name
            if "name" not in affiliation or not affiliation["name"]:
                return False

            # Name should be reasonable length
            if len(affiliation["name"]) < 3:
                return False

        return True

    def _validate_author_matching(
        self, extracted_text: str, author_names: List[str]
    ) -> bool:
        """Check if author names appear in extracted text.

        Args:
            extracted_text: Text extracted from PDF
            author_names: List of author names from metadata

        Returns:
            True if at least one author name is found
        """
        if not author_names:
            return True  # Can't validate if no authors provided

        text_lower = extracted_text.lower()

        # Check if any author name appears in the text
        for author in author_names:
            if author.lower() in text_lower:
                return True

        # Also check for last names only
        for author in author_names:
            if " " in author:
                last_name = author.split()[-1]
                if last_name.lower() in text_lower:
                    return True

        return False

    def get_validation_summary(
        self, extraction_result: Dict, paper_metadata: Dict
    ) -> Dict[str, Any]:
        """Get detailed validation summary.

        Args:
            extraction_result: Result from extractor
            paper_metadata: Paper metadata

        Returns:
            Dictionary with validation details
        """
        summary = {
            "is_valid": self.validate_affiliations(extraction_result, paper_metadata),
            "confidence": extraction_result.get("confidence", 0.0),
            "affiliation_count": len(extraction_result.get("affiliations", [])),
            "text_length": len(extraction_result.get("text", "")),
            "checks": {},
        }

        # Individual check results
        summary["checks"]["confidence_check"] = (
            summary["confidence"] >= self.min_confidence
        )
        summary["checks"]["affiliation_count_check"] = (
            summary["affiliation_count"] >= self.min_affiliations
        )
        summary["checks"]["text_length_check"] = (
            summary["text_length"] >= self.min_text_length
        )
        summary["checks"]["structure_check"] = self._validate_affiliation_structure(
            extraction_result.get("affiliations", [])
        )

        if "authors" in paper_metadata:
            summary["checks"]["author_matching"] = self._validate_author_matching(
                extraction_result.get("text", ""), paper_metadata["authors"]
            )

        return summary
