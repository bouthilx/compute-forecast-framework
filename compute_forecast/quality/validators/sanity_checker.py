"""Sanity check framework for validating paper collection quality."""

from typing import Dict, List, Any


class SanityChecker:
    """Automated validation of expected institutions, domains, and temporal patterns."""

    def __init__(self):
        """Initialize sanity checker with expected institutions and venues."""
        self.expected_academic_institutions = [
            "MIT",
            "Stanford",
            "CMU",
            "Berkeley",
            "Oxford",
            "Cambridge",
            "ETH Zurich",
            "University of Toronto",
            "NYU",
            "Princeton",
            "Harvard",
            "Yale",
            "University of Washington",
            "EPFL",
            "McGill",
            "Mila",
            "Vector Institute",
        ]

        self.expected_industry_organizations = [
            "Google",
            "Google Research",
            "DeepMind",
            "OpenAI",
            "Microsoft Research",
            "Meta AI",
            "Apple",
            "Amazon",
            "NVIDIA",
            "Anthropic",
            "Cohere",
            "IBM Research",
        ]

        self.expected_venues_by_domain = {
            "Computer Vision": ["CVPR", "ICCV", "ECCV", "MICCAI"],
            "NLP": ["ACL", "EMNLP", "NAACL", "CoNLL"],
            "RL": ["AAMAS", "ICRA", "IROS"],
            "ML General": ["NeurIPS", "ICML", "ICLR"],
        }

    def check_institutional_coverage(
        self, papers: List[Dict[str, Any]], paper_type: str = "academic"
    ) -> Dict[str, Any]:
        """Verify expected institution representation in collected papers."""

        expected_orgs = (
            self.expected_academic_institutions
            if paper_type == "academic"
            else self.expected_industry_organizations
        )

        found_institutions = set()
        institution_paper_counts = {}

        for paper in papers:
            for author in paper.get("authors", []):
                affiliation = author.get("affiliation", "").lower()

                for expected_org in expected_orgs:
                    if expected_org.lower() in affiliation:
                        found_institutions.add(expected_org)
                        institution_paper_counts[expected_org] = (
                            institution_paper_counts.get(expected_org, 0) + 1
                        )

        missing_institutions = set(expected_orgs) - found_institutions
        coverage_percentage = len(found_institutions) / len(expected_orgs)

        return {
            "coverage_percentage": coverage_percentage,
            "found_institutions": list(found_institutions),
            "missing_institutions": list(missing_institutions),
            "institution_paper_counts": institution_paper_counts,
            "quality_flag": "low_coverage"
            if coverage_percentage < 0.3
            else "acceptable",
        }

    def check_domain_balance(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify reasonable distribution across research domains."""

        domain_counts = {}
        for paper in papers:
            domain = paper.get("mila_domain", "Unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        total_papers = len(papers)
        domain_percentages = {
            domain: count / total_papers for domain, count in domain_counts.items()
        }

        # Flag domains with suspicious distributions
        quality_flags = []
        for domain, percentage in domain_percentages.items():
            if percentage > 0.5:  # No domain should dominate >50%
                quality_flags.append(f"domain_imbalance_{domain}")
            elif percentage < 0.05 and total_papers > 100:  # Domains shouldn't be <5%
                quality_flags.append(f"domain_underrepresented_{domain}")

        return {
            "domain_distribution": domain_percentages,
            "domain_counts": domain_counts,
            "total_papers": total_papers,
            "quality_flags": quality_flags,
        }

    def check_temporal_balance(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify reasonable distribution across years 2019-2024."""

        year_counts = {}
        for paper in papers:
            year = paper.get("year", paper.get("collection_year", "Unknown"))
            year_counts[year] = year_counts.get(year, 0) + 1

        expected_years = list(range(2019, 2025))
        missing_years = [year for year in expected_years if year not in year_counts]

        # Check for reasonable year distribution
        total_papers = len(papers)
        year_percentages = {
            year: count / total_papers for year, count in year_counts.items()
        }

        quality_flags = []
        for year in expected_years:
            percentage = year_percentages.get(year, 0)
            if percentage < 0.05:  # Each year should have >5% representation
                quality_flags.append(f"year_underrepresented_{year}")

        return {
            "year_distribution": year_percentages,
            "year_counts": year_counts,
            "missing_years": missing_years,
            "quality_flags": quality_flags,
        }
