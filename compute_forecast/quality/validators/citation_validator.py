"""Citation verification and validation system."""

from typing import Dict, List, Any


class CitationValidator:
    """Cross-source citation validation and outlier detection."""

    def __init__(self):
        """Initialize citation validator with thresholds."""
        self.citation_thresholds = {
            2024: {"min": 5, "max": 10000},
            2023: {"min": 10, "max": 15000},
            2022: {"min": 20, "max": 20000},
            2021: {"min": 30, "max": 25000},
            2020: {"min": 50, "max": 30000},
            2019: {"min": 75, "max": 35000},
        }

    def validate_citation_counts(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cross-validate citation counts and detect outliers."""

        validation_results = {
            "total_papers": len(papers),
            "citation_issues": [],
            "outliers": [],
            "source_consistency": {},
            "suspicious_patterns": [],
        }

        for paper in papers:
            paper_year = paper.get("year", 2024)
            citations = paper.get("citations", 0)
            sources = paper.get("all_sources", [paper.get("source", "unknown")])

            # Check citation count reasonableness
            thresholds = self.citation_thresholds.get(
                paper_year, {"min": 5, "max": 10000}
            )

            if citations < thresholds["min"]:
                validation_results["citation_issues"].append(
                    {
                        "paper_title": paper.get("title", "Unknown"),
                        "year": paper_year,
                        "citations": citations,
                        "issue": "below_minimum_threshold",
                        "expected_min": thresholds["min"],
                    }
                )

            if citations > thresholds["max"]:
                validation_results["outliers"].append(
                    {
                        "paper_title": paper.get("title", "Unknown"),
                        "year": paper_year,
                        "citations": citations,
                        "issue": "unusually_high_citations",
                        "sources": sources,
                    }
                )

            # Track source consistency
            for source in sources:
                if source not in validation_results["source_consistency"]:
                    validation_results["source_consistency"][source] = {
                        "paper_count": 0,
                        "avg_citations": 0,
                        "citation_sum": 0,
                    }

                source_stats = validation_results["source_consistency"][source]
                source_stats["paper_count"] += 1
                source_stats["citation_sum"] += citations
                source_stats["avg_citations"] = (
                    source_stats["citation_sum"] / source_stats["paper_count"]
                )

        return validation_results

    def detect_suspicious_patterns(
        self, papers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify papers with suspicious citation patterns."""

        suspicious = []

        # Check for identical citation counts (suspicious)
        citation_counts = {}
        for paper in papers:
            citations = paper.get("citations", 0)
            if citations not in citation_counts:
                citation_counts[citations] = []
            citation_counts[citations].append(paper.get("title", "Unknown"))

        # Flag citation counts that appear too frequently
        for citations, titles in citation_counts.items():
            if (
                len(titles) > 5 and citations > 100
            ):  # More than 5 papers with same high citation count
                suspicious.append(
                    {
                        "issue": "identical_citation_counts",
                        "citation_count": citations,
                        "paper_count": len(titles),
                        "papers": titles[:3],  # First 3 examples
                    }
                )

        return suspicious
