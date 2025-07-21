"""
Simple data processors for Agent Gamma functionality.
Includes deduplication and citation analysis.
"""

import logging
from typing import List, Dict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from ...pipeline.metadata_collection.models import Paper

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationResult:
    unique_papers: List[Paper]
    duplicate_groups: List[List[Paper]]
    deduplicated_count: int
    original_count: int
    similarity_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class CitationAnalysisReport:
    total_papers: int
    citation_distribution: Dict[str, int]
    high_impact_papers: List[Paper]
    average_citations: float
    median_citations: float
    breakthrough_candidates: List[Paper] = field(default_factory=list)


class SimpleDeduplicator:
    """Simple paper deduplication engine"""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def deduplicate_papers(self, papers: List[Paper]) -> DeduplicationResult:
        """Deduplicate papers based on title and author similarity"""
        if not papers:
            return DeduplicationResult(
                unique_papers=[],
                duplicate_groups=[],
                deduplicated_count=0,
                original_count=0,
            )

        logger.info(f"Deduplicating {len(papers)} papers...")

        unique_papers = []
        duplicate_groups = []
        processed_indices = set()
        similarity_scores = {}

        for i, paper1 in enumerate(papers):
            if i in processed_indices:
                continue

            # Find similar papers
            duplicates = [paper1]
            processed_indices.add(i)

            for j, paper2 in enumerate(papers[i + 1 :], i + 1):
                if j in processed_indices:
                    continue

                similarity = self._calculate_similarity(paper1, paper2)
                similarity_scores[f"{i}_{j}"] = similarity

                if similarity >= self.similarity_threshold:
                    duplicates.append(paper2)
                    processed_indices.add(j)

            # Keep the paper with most citations as the unique one
            best_paper = max(duplicates, key=lambda p: p.citations)
            unique_papers.append(best_paper)

            if len(duplicates) > 1:
                duplicate_groups.append(duplicates)

        result = DeduplicationResult(
            unique_papers=unique_papers,
            duplicate_groups=duplicate_groups,
            deduplicated_count=len(unique_papers),
            original_count=len(papers),
            similarity_scores=similarity_scores,
        )

        logger.info(
            f"Deduplication complete: {len(papers)} -> {len(unique_papers)} papers"
        )
        return result

    def _calculate_similarity(self, paper1: Paper, paper2: Paper) -> float:
        """Calculate similarity between two papers"""
        # Title similarity (most important)
        title_similarity = SequenceMatcher(
            None, paper1.title.lower(), paper2.title.lower()
        ).ratio()

        # Author similarity
        authors1 = {author.name.lower() for author in paper1.authors}
        authors2 = {author.name.lower() for author in paper2.authors}

        if authors1 and authors2:
            author_intersection = len(authors1 & authors2)
            author_union = len(authors1 | authors2)
            author_similarity = (
                author_intersection / author_union if author_union > 0 else 0
            )
        else:
            author_similarity = 0

        # Year similarity (exact match gets bonus)
        year_similarity = 1.0 if paper1.year == paper2.year else 0.5

        # Venue similarity
        venue_similarity = SequenceMatcher(
            None, paper1.venue.lower(), paper2.venue.lower()
        ).ratio()

        # Weighted combination
        overall_similarity = (
            title_similarity * 0.6  # Title is most important
            + author_similarity * 0.2  # Authors are important
            + year_similarity * 0.1  # Year should match
            + venue_similarity * 0.1  # Venue provides context
        )

        return overall_similarity


class SimpleCitationAnalyzer:
    """Simple citation analysis engine"""

    def __init__(self):
        self.high_impact_threshold = 50  # Citations for high impact
        self.breakthrough_threshold = 100  # Citations for breakthrough

    def analyze_citation_distributions(
        self, papers: List[Paper]
    ) -> CitationAnalysisReport:
        """Analyze citation patterns in paper collection"""
        if not papers:
            return CitationAnalysisReport(
                total_papers=0,
                citation_distribution={},
                high_impact_papers=[],
                average_citations=0.0,
                median_citations=0.0,
            )

        logger.info(f"Analyzing citations for {len(papers)} papers...")

        # Calculate citation statistics
        citations = [paper.get_latest_citations_count() for paper in papers]
        total_citations = sum(citations)
        average_citations = total_citations / len(papers) if papers else 0

        sorted_citations = sorted(citations)
        median_citations = (
            sorted_citations[len(sorted_citations) // 2] if sorted_citations else 0
        )

        # Citation distribution
        citation_ranges = {"0-5": 0, "6-20": 0, "21-50": 0, "51-100": 0, "100+": 0}

        for citation_count in citations:
            if citation_count <= 5:
                citation_ranges["0-5"] += 1
            elif citation_count <= 20:
                citation_ranges["6-20"] += 1
            elif citation_count <= 50:
                citation_ranges["21-50"] += 1
            elif citation_count <= 100:
                citation_ranges["51-100"] += 1
            else:
                citation_ranges["100+"] += 1

        # High impact papers
        high_impact_papers = [
            paper for paper in papers if paper.citations >= self.high_impact_threshold
        ]

        # Breakthrough candidates
        breakthrough_candidates = [
            paper for paper in papers if paper.citations >= self.breakthrough_threshold
        ]

        # Sort by citations descending
        high_impact_papers.sort(key=lambda p: p.citations, reverse=True)
        breakthrough_candidates.sort(key=lambda p: p.citations, reverse=True)

        report = CitationAnalysisReport(
            total_papers=len(papers),
            citation_distribution=citation_ranges,
            high_impact_papers=high_impact_papers,
            average_citations=average_citations,
            median_citations=median_citations,
            breakthrough_candidates=breakthrough_candidates,
        )

        logger.info(
            f"Citation analysis complete: avg={average_citations:.1f}, median={median_citations}, high_impact={len(high_impact_papers)}"
        )
        return report

    def filter_papers_by_citations(
        self, papers: List[Paper], min_citations: int
    ) -> List[Paper]:
        """Filter papers by minimum citation count"""
        filtered = [paper for paper in papers if paper.get_latest_citations_count() >= min_citations]
        logger.info(
            f"Citation filter: {len(papers)} -> {len(filtered)} papers (min_citations={min_citations})"
        )
        return filtered

    def identify_breakthrough_papers(
        self, papers: List[Paper], year_thresholds: Dict[int, int]
    ) -> List[Paper]:
        """Identify breakthrough papers based on year-specific thresholds"""
        breakthrough_papers = []

        for paper in papers:
            threshold = year_thresholds.get(paper.year, self.breakthrough_threshold)
            if paper.citations >= threshold:
                paper.breakthrough_score = paper.citations / threshold
                breakthrough_papers.append(paper)

        # Sort by breakthrough score
        breakthrough_papers.sort(key=lambda p: p.breakthrough_score or 0, reverse=True)

        logger.info(f"Identified {len(breakthrough_papers)} breakthrough papers")
        return breakthrough_papers
