"""Validators for collection quality assessment."""

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

from compute_forecast.quality.core.interfaces import (
    QualityCheckResult,
    QualityCheckType,
    QualityIssue,
    QualityIssueLevel,
    QualityConfig
)


class BaseValidator(ABC):
    """Base class for all collection validators."""
    
    @abstractmethod
    def validate(self, papers: List[Dict[str, Any]], config: QualityConfig) -> QualityCheckResult:
        """Validate papers and return results."""
        pass
    
    @abstractmethod
    def get_check_type(self) -> QualityCheckType:
        """Return the type of check this validator performs."""
        pass
    
    def _create_issue(
        self,
        level: QualityIssueLevel,
        field: str,
        message: str,
        suggested_action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> QualityIssue:
        """Helper to create quality issues."""
        return QualityIssue(
            check_type=self.get_check_type(),
            level=level,
            field=field,
            message=message,
            suggested_action=suggested_action,
            details=details or {}
        )


class CompletenessValidator(BaseValidator):
    """Validates completeness of required fields and data integrity."""
    
    REQUIRED_FIELDS = ["title", "authors", "venue", "year"]
    OPTIONAL_FIELDS = ["abstract", "pdf_url", "doi", "keywords"]
    
    def get_check_type(self) -> QualityCheckType:
        return QualityCheckType.COMPLETENESS
    
    def validate(self, papers: List[Dict[str, Any]], config: QualityConfig) -> QualityCheckResult:
        """Validate completeness of paper data."""
        issues = []
        
        if not papers:
            issues.append(self._create_issue(
                QualityIssueLevel.CRITICAL,
                "papers",
                "No papers found in collection",
                "Verify collection process completed successfully"
            ))
            return QualityCheckResult(
                check_name="completeness_check",
                check_type=self.get_check_type(),
                passed=False,
                score=0.0,
                issues=issues
            )
        
        # Check required fields
        missing_required = self._check_required_fields(papers, issues)
        
        # Check optional fields availability
        optional_coverage = self._check_optional_fields(papers, issues)
        
        # Calculate score
        total_papers = len(papers)
        papers_with_all_required = total_papers - len(missing_required)
        
        # Score based on required field completeness (80%) + optional coverage (20%)
        required_score = papers_with_all_required / total_papers if total_papers > 0 else 0.0
        optional_score = sum(optional_coverage.values()) / len(optional_coverage) if optional_coverage else 0.0
        overall_score = 0.8 * required_score + 0.2 * optional_score
        
        passed = overall_score >= 0.8 and len([i for i in issues if i.level == QualityIssueLevel.CRITICAL]) == 0
        
        return QualityCheckResult(
            check_name="completeness_check",
            check_type=self.get_check_type(),
            passed=passed,
            score=overall_score,
            issues=issues
        )
    
    def _check_required_fields(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> List[int]:
        """Check for missing required fields."""
        missing_required = []
        
        for i, paper in enumerate(papers):
            missing_fields = []
            for field in self.REQUIRED_FIELDS:
                if field not in paper or not paper[field] or (isinstance(paper[field], str) and not paper[field].strip()):
                    missing_fields.append(field)
            
            if missing_fields:
                missing_required.append(i)
                issues.append(self._create_issue(
                    QualityIssueLevel.CRITICAL,
                    "required_fields",
                    f"Paper {i+1} missing required fields: {', '.join(missing_fields)}",
                    "Ensure all required fields are populated during collection",
                    {"paper_index": i, "missing_fields": missing_fields, "title": paper.get("title", "Unknown")}
                ))
        
        return missing_required
    
    def _check_optional_fields(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> Dict[str, float]:
        """Check coverage of optional fields."""
        coverage = {}
        total_papers = len(papers)
        
        for field in self.OPTIONAL_FIELDS:
            present_count = sum(1 for paper in papers if field in paper and paper[field] and 
                             (not isinstance(paper[field], str) or paper[field].strip()))
            coverage[field] = present_count / total_papers if total_papers > 0 else 0.0
            
            if coverage[field] < 0.5:
                issues.append(self._create_issue(
                    QualityIssueLevel.WARNING,
                    field,
                    f"Low coverage for {field}: {coverage[field]:.1%} ({present_count}/{total_papers})",
                    f"Consider improving {field} extraction in scrapers",
                    {"coverage_rate": coverage[field], "present_count": present_count, "total_papers": total_papers}
                ))
        
        return coverage


class ConsistencyValidator(BaseValidator):
    """Validates consistency of data across papers."""
    
    def get_check_type(self) -> QualityCheckType:
        return QualityCheckType.CONSISTENCY
    
    def validate(self, papers: List[Dict[str, Any]], config: QualityConfig) -> QualityCheckResult:
        """Validate consistency of paper data."""
        issues = []
        
        if not papers:
            return QualityCheckResult(
                check_name="consistency_check",
                check_type=self.get_check_type(),
                passed=True,
                score=1.0,
                issues=[]
            )
        
        # Check for duplicates
        duplicate_score = self._check_duplicates(papers, issues)
        
        # Check venue consistency
        venue_score = self._check_venue_consistency(papers, issues)
        
        # Check year consistency
        year_score = self._check_year_consistency(papers, issues)
        
        # Overall score
        overall_score = (duplicate_score + venue_score + year_score) / 3
        passed = overall_score >= 0.8
        
        return QualityCheckResult(
            check_name="consistency_check",
            check_type=self.get_check_type(),
            passed=passed,
            score=overall_score,
            issues=issues
        )
    
    def _check_duplicates(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Check for duplicate papers."""
        seen_titles = {}
        duplicates = []
        
        for i, paper in enumerate(papers):
            title = paper.get("title", "").strip().lower()
            if title and title in seen_titles:
                duplicates.append((i, seen_titles[title], title))
                issues.append(self._create_issue(
                    QualityIssueLevel.WARNING,
                    "duplicates",
                    f"Possible duplicate: papers {i+1} and {seen_titles[title]+1} have similar titles",
                    "Review and remove duplicate papers",
                    {"paper_indices": [i, seen_titles[title]], "title": paper.get("title", "Unknown")}
                ))
            elif title:
                seen_titles[title] = i
        
        duplicate_rate = len(duplicates) / len(papers) if papers else 0.0
        return max(0.0, 1.0 - duplicate_rate * 2)  # Penalize duplicates heavily
    
    def _check_venue_consistency(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Check venue name consistency."""
        venue_variants = {}
        
        for paper in papers:
            venue = paper.get("venue", "").strip()
            if venue:
                venue_lower = venue.lower()
                if venue_lower not in venue_variants:
                    venue_variants[venue_lower] = []
                venue_variants[venue_lower].append(venue)
        
        inconsistent_venues = []
        for venue_lower, variants in venue_variants.items():
            if len(set(variants)) > 1:
                inconsistent_venues.append((venue_lower, variants))
                issues.append(self._create_issue(
                    QualityIssueLevel.WARNING,
                    "venue_consistency",
                    f"Inconsistent venue naming: {', '.join(set(variants))}",
                    "Standardize venue names during collection",
                    {"venue_variants": list(set(variants))}
                ))
        
        consistency_score = 1.0 - (len(inconsistent_venues) / len(venue_variants)) if venue_variants else 1.0
        return max(0.0, consistency_score)
    
    def _check_year_consistency(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Check year format consistency."""
        invalid_years = []
        current_year = datetime.now().year
        
        for i, paper in enumerate(papers):
            year = paper.get("year")
            if year is not None:
                try:
                    year_int = int(year)
                    if year_int < 1950 or year_int > current_year + 1:
                        invalid_years.append((i, year))
                        issues.append(self._create_issue(
                            QualityIssueLevel.WARNING,
                            "year_validity",
                            f"Paper {i+1} has invalid year: {year}",
                            "Verify year extraction accuracy",
                            {"paper_index": i, "year": year, "title": paper.get("title", "Unknown")}
                        ))
                except (ValueError, TypeError):
                    invalid_years.append((i, year))
                    issues.append(self._create_issue(
                        QualityIssueLevel.WARNING,
                        "year_format",
                        f"Paper {i+1} has invalid year format: {year}",
                        "Ensure year is stored as integer",
                        {"paper_index": i, "year": year, "title": paper.get("title", "Unknown")}
                    ))
        
        year_score = 1.0 - (len(invalid_years) / len(papers)) if papers else 1.0
        return max(0.0, year_score)


class AccuracyValidator(BaseValidator):
    """Validates accuracy of data fields."""
    
    def get_check_type(self) -> QualityCheckType:
        return QualityCheckType.ACCURACY
    
    def validate(self, papers: List[Dict[str, Any]], config: QualityConfig) -> QualityCheckResult:
        """Validate accuracy of paper data."""
        issues = []
        
        if not papers:
            return QualityCheckResult(
                check_name="accuracy_check",
                check_type=self.get_check_type(),
                passed=True,
                score=1.0,
                issues=[]
            )
        
        # Validate author names
        author_score = self._validate_author_names(papers, issues)
        
        # Validate URLs
        url_score = self._validate_urls(papers, issues)
        
        # Validate DOIs
        doi_score = self._validate_dois(papers, issues)
        
        # Overall score
        overall_score = (author_score + url_score + doi_score) / 3
        passed = overall_score >= 0.8
        
        return QualityCheckResult(
            check_name="accuracy_check",
            check_type=self.get_check_type(),
            passed=passed,
            score=overall_score,
            issues=issues
        )
    
    def _validate_author_names(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Validate author name patterns."""
        invalid_authors = []
        
        # Pattern for reasonable author names (allows Unicode for international names)
        author_pattern = re.compile(r'^[A-Za-z\u00C0-\u017F\u0400-\u04FF\s\-\.\']+$')
        
        for i, paper in enumerate(papers):
            authors = paper.get("authors", [])
            if isinstance(authors, str):
                authors = [authors]
            
            for j, author in enumerate(authors):
                if not isinstance(author, str):
                    invalid_authors.append((i, j, author))
                    issues.append(self._create_issue(
                        QualityIssueLevel.WARNING,
                        "author_format",
                        f"Paper {i+1} has non-string author: {author}",
                        "Ensure authors are stored as strings",
                        {"paper_index": i, "author_index": j, "author": str(author)}
                    ))
                elif len(author.strip()) < 2:
                    invalid_authors.append((i, j, author))
                    issues.append(self._create_issue(
                        QualityIssueLevel.WARNING,
                        "author_length",
                        f"Paper {i+1} has suspiciously short author name: '{author}'",
                        "Review author extraction accuracy",
                        {"paper_index": i, "author_index": j, "author": author}
                    ))
                elif not author_pattern.match(author.strip()):
                    invalid_authors.append((i, j, author))
                    issues.append(self._create_issue(
                        QualityIssueLevel.INFO,
                        "author_pattern",
                        f"Paper {i+1} has unusual author name pattern: '{author}'",
                        "Verify author name accuracy",
                        {"paper_index": i, "author_index": j, "author": author}
                    ))
        
        total_authors = sum(len(paper.get("authors", [])) for paper in papers)
        if total_authors == 0:
            return 1.0
        
        accuracy_score = 1.0 - (len(invalid_authors) / total_authors)
        return max(0.0, accuracy_score)
    
    def _validate_urls(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Validate URL formats."""
        invalid_urls = []
        
        for i, paper in enumerate(papers):
            for field in ["pdf_url", "url"]:
                url = paper.get(field)
                if url and isinstance(url, str):
                    try:
                        parsed = urlparse(url)
                        if not parsed.scheme or not parsed.netloc:
                            invalid_urls.append((i, field, url))
                            issues.append(self._create_issue(
                                QualityIssueLevel.WARNING,
                                field,
                                f"Paper {i+1} has invalid URL in {field}: {url}",
                                "Verify URL extraction accuracy",
                                {"paper_index": i, "field": field, "url": url}
                            ))
                    except Exception:
                        invalid_urls.append((i, field, url))
                        issues.append(self._create_issue(
                            QualityIssueLevel.WARNING,
                            field,
                            f"Paper {i+1} has malformed URL in {field}: {url}",
                            "Fix URL format",
                            {"paper_index": i, "field": field, "url": url}
                        ))
        
        total_urls = sum(1 for paper in papers for field in ["pdf_url", "url"] if paper.get(field))
        if total_urls == 0:
            return 1.0
        
        url_score = 1.0 - (len(invalid_urls) / total_urls)
        return max(0.0, url_score)
    
    def _validate_dois(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Validate DOI formats."""
        invalid_dois = []
        
        # Basic DOI pattern
        doi_pattern = re.compile(r'^10\.\d{4,}/[^\s]+$')
        
        for i, paper in enumerate(papers):
            doi = paper.get("doi")
            if doi and isinstance(doi, str):
                doi = doi.strip()
                if doi.startswith("http"):
                    # Extract DOI from URL
                    if "/10." in doi:
                        doi = doi.split("/10.")[1]
                        doi = "10." + doi
                
                if not doi_pattern.match(doi):
                    invalid_dois.append((i, doi))
                    issues.append(self._create_issue(
                        QualityIssueLevel.INFO,
                        "doi_format",
                        f"Paper {i+1} has invalid DOI format: {doi}",
                        "Verify DOI extraction accuracy",
                        {"paper_index": i, "doi": doi}
                    ))
        
        total_dois = sum(1 for paper in papers if paper.get("doi"))
        if total_dois == 0:
            return 1.0
        
        doi_score = 1.0 - (len(invalid_dois) / total_dois)
        return max(0.0, doi_score)


class CoverageValidator(BaseValidator):
    """Validates collection coverage against expectations."""
    
    def get_check_type(self) -> QualityCheckType:
        return QualityCheckType.COVERAGE
    
    def validate(self, papers: List[Dict[str, Any]], config: QualityConfig) -> QualityCheckResult:
        """Validate collection coverage."""
        issues = []
        
        if not papers:
            issues.append(self._create_issue(
                QualityIssueLevel.CRITICAL,
                "coverage",
                "No papers collected",
                "Verify collection process and scraper functionality"
            ))
            return QualityCheckResult(
                check_name="coverage_check",
                check_type=self.get_check_type(),
                passed=False,
                score=0.0,
                issues=issues
            )
        
        # Analyze venue coverage
        venue_score = self._analyze_venue_coverage(papers, issues)
        
        # Analyze year coverage
        year_score = self._analyze_year_coverage(papers, issues)
        
        # Analyze scraper coverage
        scraper_score = self._analyze_scraper_coverage(papers, issues)
        
        # Overall score
        overall_score = (venue_score + year_score + scraper_score) / 3
        passed = overall_score >= 0.6  # Lower threshold for coverage
        
        return QualityCheckResult(
            check_name="coverage_check",
            check_type=self.get_check_type(),
            passed=passed,
            score=overall_score,
            issues=issues
        )
    
    def _analyze_venue_coverage(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Analyze venue coverage distribution."""
        venue_counts = {}
        
        for paper in papers:
            venue = paper.get("venue", "Unknown")
            venue_counts[venue] = venue_counts.get(venue, 0) + 1
        
        if not venue_counts:
            return 0.0
        
        # Check for very uneven distribution
        total_papers = len(papers)
        max_venue_count = max(venue_counts.values())
        min_venue_count = min(venue_counts.values())
        
        if len(venue_counts) > 1:
            imbalance_ratio = max_venue_count / min_venue_count
            if imbalance_ratio > 10:
                issues.append(self._create_issue(
                    QualityIssueLevel.WARNING,
                    "venue_distribution",
                    f"Highly uneven venue distribution: {imbalance_ratio:.1f}x difference between max and min",
                    "Review collection strategy for venue balance",
                    {"venue_counts": venue_counts, "imbalance_ratio": imbalance_ratio}
                ))
        
        # Check for unknown venues
        unknown_count = venue_counts.get("Unknown", 0)
        if unknown_count > 0:
            unknown_rate = unknown_count / total_papers
            if unknown_rate > 0.1:
                issues.append(self._create_issue(
                    QualityIssueLevel.WARNING,
                    "unknown_venues",
                    f"High rate of unknown venues: {unknown_rate:.1%} ({unknown_count}/{total_papers})",
                    "Improve venue extraction in scrapers",
                    {"unknown_count": unknown_count, "total_papers": total_papers, "unknown_rate": unknown_rate}
                ))
        
        # Score based on venue diversity and distribution
        venue_diversity = len(venue_counts) / total_papers if total_papers > 0 else 0.0
        unknown_penalty = unknown_count / total_papers if total_papers > 0 else 0.0
        
        score = min(1.0, venue_diversity * 10) - unknown_penalty
        return max(0.0, score)
    
    def _analyze_year_coverage(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Analyze year coverage distribution."""
        year_counts = {}
        
        for paper in papers:
            year = paper.get("year")
            if year is not None:
                try:
                    year_int = int(year)
                    year_counts[year_int] = year_counts.get(year_int, 0) + 1
                except (ValueError, TypeError):
                    pass
        
        if not year_counts:
            issues.append(self._create_issue(
                QualityIssueLevel.WARNING,
                "year_coverage",
                "No valid years found in papers",
                "Verify year extraction in scrapers"
            ))
            return 0.0
        
        # Check for reasonable year range
        min_year = min(year_counts.keys())
        max_year = max(year_counts.keys())
        current_year = datetime.now().year
        
        if max_year < current_year - 5:
            issues.append(self._create_issue(
                QualityIssueLevel.WARNING,
                "year_recency",
                f"No recent papers found (latest: {max_year})",
                "Verify collection includes recent publications",
                {"latest_year": max_year, "current_year": current_year}
            ))
        
        if min_year > current_year - 2:
            issues.append(self._create_issue(
                QualityIssueLevel.INFO,
                "year_scope",
                f"Limited historical coverage (earliest: {min_year})",
                "Consider expanding year range if needed",
                {"earliest_year": min_year, "current_year": current_year}
            ))
        
        # Score based on year range and distribution
        year_range = max_year - min_year + 1
        expected_range = 5  # Assume 5 years is good coverage
        range_score = min(1.0, year_range / expected_range)
        
        return range_score
    
    def _analyze_scraper_coverage(self, papers: List[Dict[str, Any]], issues: List[QualityIssue]) -> float:
        """Analyze scraper coverage distribution."""
        scraper_counts = {}
        
        for paper in papers:
            scraper = paper.get("scraper_source", "Unknown")
            scraper_counts[scraper] = scraper_counts.get(scraper, 0) + 1
        
        if not scraper_counts:
            return 0.0
        
        # Check for scraper diversity
        total_papers = len(papers)
        unknown_count = scraper_counts.get("Unknown", 0)
        
        if len(scraper_counts) == 1 and "Unknown" in scraper_counts:
            issues.append(self._create_issue(
                QualityIssueLevel.WARNING,
                "scraper_source",
                "All papers have unknown scraper source",
                "Ensure scraper source tracking is implemented"
            ))
            return 0.5
        
        if unknown_count > 0:
            unknown_rate = unknown_count / total_papers
            if unknown_rate > 0.2:
                issues.append(self._create_issue(
                    QualityIssueLevel.INFO,
                    "scraper_tracking",
                    f"Some papers missing scraper source: {unknown_rate:.1%}",
                    "Improve scraper source tracking",
                    {"unknown_count": unknown_count, "total_papers": total_papers}
                ))
        
        # Score based on scraper diversity (more scrapers = better coverage)
        known_scrapers = len([s for s in scraper_counts.keys() if s != "Unknown"])
        scraper_score = min(1.0, known_scrapers / 3)  # Assume 3 scrapers is good
        
        return scraper_score