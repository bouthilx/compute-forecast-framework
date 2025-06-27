"""Breakthrough paper detection for identifying high-impact research."""

import json
from datetime import datetime
from typing import List, Set, Tuple
from pathlib import Path

from src.data.models import Paper, Author
from src.data.processors.citation_statistics import BreakthroughPaper


class BreakthroughDetector:
    """Detect papers with breakthrough potential using multiple indicators."""
    
    def __init__(self):
        """Initialize detector with breakthrough keywords and high-impact authors."""
        self.current_year = datetime.now().year
        self.breakthrough_keywords = self._load_breakthrough_keywords()
        self.high_impact_authors = self._load_high_impact_authors()
    
    def _load_breakthrough_keywords(self) -> Set[str]:
        """Load breakthrough keywords from JSON file or use defaults."""
        keywords_file = Path("data/breakthrough_keywords.json")
        
        # Default keywords if file doesn't exist
        default_keywords = [
            # Methodology breakthroughs
            "breakthrough", "novel", "first", "unprecedented", "revolutionary",
            "paradigm", "fundamental", "groundbreaking", "seminal", "pioneering",
            
            # Technical breakthroughs
            "transformer", "attention", "diffusion", "gpt", "llm", "large language",
            "foundation model", "emergent", "scaling law", "in-context learning",
            "few-shot", "zero-shot", "self-supervised", "contrastive", "multimodal",
            "generative", "vision transformer", "bert", "neural architecture",
            
            # Performance breakthroughs  
            "state-of-the-art", "sota", "outperforms", "surpasses", "beats",
            "record", "best", "superior", "exceeds", "achieves new",
            
            # Innovation indicators
            "introduces", "proposes", "presents", "novel approach", "new method",
            "first time", "never before", "unique", "original"
        ]
        
        if keywords_file.exists():
            try:
                with open(keywords_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get("keywords", default_keywords))
            except Exception:
                pass
        
        return set(default_keywords)
    
    def _load_high_impact_authors(self) -> Set[str]:
        """Load high-impact authors from JSON file or use defaults."""
        authors_file = Path("data/high_impact_authors.json")
        
        # Default high-impact authors (can be expanded)
        default_authors = [
            # Deep Learning pioneers
            "Geoffrey Hinton", "Yann LeCun", "Yoshua Bengio", "Andrew Ng",
            "Ian Goodfellow", "Demis Hassabis", "Jürgen Schmidhuber",
            
            # NLP leaders
            "Christopher Manning", "Dan Jurafsky", "Noah Smith", "Percy Liang",
            "Yoav Goldberg", "Jacob Devlin", "Omer Levy",
            
            # Computer Vision experts
            "Fei-Fei Li", "Jitendra Malik", "Andrew Zisserman", "Kaiming He",
            "Ross Girshick", "Ali Farhadi", "Serge Belongie",
            
            # ML Theory
            "Michael Jordan", "Peter Bartlett", "Shai Shalev-Shwartz",
            "Mehryar Mohri", "Robert Schapire", "Vladimir Vapnik",
            
            # Reinforcement Learning
            "Richard Sutton", "David Silver", "Pieter Abbeel", "Sergey Levine",
            "Marc Bellemare", "Doina Precup"
        ]
        
        if authors_file.exists():
            try:
                with open(authors_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get("authors", default_authors))
            except Exception:
                pass
        
        return set(default_authors)
    
    def calculate_breakthrough_score(self, paper: Paper) -> float:
        """Calculate breakthrough potential score (0.0 to 1.0)."""
        score = 0.0
        
        # Factor 1: Citation velocity (30% weight)
        years_since_pub = max(1, self.current_year - paper.year)
        citation_velocity = paper.citations / years_since_pub if paper.citations else 0
        
        # Velocity scoring (non-linear)
        if citation_velocity >= 50:  # Very high velocity
            velocity_score = 1.0
        elif citation_velocity >= 20:  # High velocity
            velocity_score = 0.8
        elif citation_velocity >= 10:  # Good velocity
            velocity_score = 0.6
        elif citation_velocity >= 5:   # Moderate velocity
            velocity_score = 0.4
        elif citation_velocity >= 2:   # Low velocity
            velocity_score = 0.2
        else:
            velocity_score = 0.0
        
        score += velocity_score * 0.3
        
        # Factor 2: Breakthrough keywords (25% weight)
        keyword_score, matched_keywords = self._calculate_keyword_score(paper)
        score += keyword_score * 0.25
        
        # Factor 3: Author reputation (20% weight)
        author_score, high_impact_authors = self._calculate_author_reputation_score(paper.authors)
        score += author_score * 0.2
        
        # Factor 4: Venue prestige (15% weight)
        venue_score = self._calculate_venue_prestige_score(paper.normalized_venue or paper.venue)
        score += venue_score * 0.15
        
        # Factor 5: Recency bonus (10% weight)
        if years_since_pub <= 2:  # Very recent
            recency_score = 1.0
        elif years_since_pub <= 3:  # Recent
            recency_score = 0.8
        elif years_since_pub <= 5:  # Somewhat recent
            recency_score = 0.6
        else:
            recency_score = 0.0
        
        score += recency_score * 0.1
        
        return min(score, 1.0)
    
    def _calculate_keyword_score(self, paper: Paper) -> Tuple[float, List[str]]:
        """Calculate keyword-based breakthrough score."""
        title_lower = paper.title.lower() if paper.title else ""
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        
        matched_keywords = []
        for keyword in self.breakthrough_keywords:
            if keyword in title_lower or keyword in abstract_lower:
                matched_keywords.append(keyword)
        
        # Max score at 5 keywords
        keyword_score = min(len(matched_keywords) / 5.0, 1.0)
        
        return keyword_score, matched_keywords
    
    def _calculate_author_reputation_score(self, authors: List[Author]) -> Tuple[float, List[str]]:
        """Calculate author reputation score."""
        if not authors:
            return 0.0, []
        
        reputation_score = 0.0
        high_impact_authors = []
        
        for author in authors:
            # Check if author is in high-impact list
            if author.name in self.high_impact_authors:
                reputation_score += 0.3
                high_impact_authors.append(author.name)
            
            # Check h-index if available
            if hasattr(author, 'h_index') and author.h_index:
                if author.h_index >= 50:
                    reputation_score += 0.2
                elif author.h_index >= 30:
                    reputation_score += 0.1
        
        return min(reputation_score, 1.0), high_impact_authors
    
    def _calculate_venue_prestige_score(self, venue: str) -> float:
        """Calculate venue prestige score based on tier."""
        # Hardcoded venue tiers (should ideally come from config)
        tier1_venues = {"NeurIPS", "ICML", "ICLR"}
        tier2_venues = {"AAAI", "CVPR", "ICCV", "ECCV", "ACL", "EMNLP", "NAACL"}
        tier3_venues = {"UAI", "AISTATS", "KDD", "WWW", "SIGIR", "WSDM"}
        
        if venue in tier1_venues:
            return 1.0
        elif venue in tier2_venues:
            return 0.8
        elif venue in tier3_venues:
            return 0.6
        else:
            return 0.4
    
    def identify_breakthrough_indicators(self, paper: Paper) -> List[str]:
        """Identify specific indicators of breakthrough potential."""
        indicators = []
        
        # Check citation velocity
        years_since_pub = max(1, self.current_year - paper.year)
        citation_velocity = paper.citations / years_since_pub if paper.citations else 0
        
        if citation_velocity >= 20:
            indicators.append(f"High citation velocity: {citation_velocity:.1f} citations/year")
        elif citation_velocity >= 10:
            indicators.append(f"Good citation velocity: {citation_velocity:.1f} citations/year")
        
        # Check keywords
        _, matched_keywords = self._calculate_keyword_score(paper)
        if matched_keywords:
            indicators.append(f"Breakthrough keywords: {', '.join(matched_keywords[:5])}")
        
        # Check authors
        _, high_impact_authors = self._calculate_author_reputation_score(paper.authors)
        if high_impact_authors:
            indicators.append(f"High-impact authors: {', '.join(high_impact_authors)}")
        
        # Check venue
        venue_score = self._calculate_venue_prestige_score(paper.normalized_venue or paper.venue)
        if venue_score >= 0.8:
            indicators.append(f"Top-tier venue: {paper.normalized_venue or paper.venue}")
        
        # Check recency
        if years_since_pub <= 2:
            indicators.append("Very recent publication")
        
        return indicators
    
    def detect_breakthrough_papers(self, papers: List[Paper]) -> List[BreakthroughPaper]:
        """Identify papers with breakthrough potential from a list."""
        breakthrough_papers = []
        
        for paper in papers:
            score = self.calculate_breakthrough_score(paper)
            
            # Only consider papers with score >= 0.5 as breakthrough candidates
            if score >= 0.5:
                indicators = self.identify_breakthrough_indicators(paper)
                
                # Calculate individual component scores
                years_since_pub = max(1, self.current_year - paper.year)
                citation_velocity = paper.citations / years_since_pub if paper.citations else 0
                
                # Velocity score
                if citation_velocity >= 50:
                    velocity_score = 1.0
                elif citation_velocity >= 20:
                    velocity_score = 0.8
                elif citation_velocity >= 10:
                    velocity_score = 0.6
                elif citation_velocity >= 5:
                    velocity_score = 0.4
                elif citation_velocity >= 2:
                    velocity_score = 0.2
                else:
                    velocity_score = 0.0
                
                # Other scores
                keyword_score, matched_keywords = self._calculate_keyword_score(paper)
                author_score, high_impact_authors = self._calculate_author_reputation_score(paper.authors)
                venue_score = self._calculate_venue_prestige_score(paper.normalized_venue or paper.venue)
                
                # Recency score
                if years_since_pub <= 2:
                    recency_score = 1.0
                elif years_since_pub <= 3:
                    recency_score = 0.8
                elif years_since_pub <= 5:
                    recency_score = 0.6
                else:
                    recency_score = 0.0
                
                breakthrough_paper = BreakthroughPaper(
                    paper=paper,
                    breakthrough_score=score,
                    breakthrough_indicators=indicators,
                    citation_velocity_score=velocity_score,
                    keyword_score=keyword_score,
                    author_reputation_score=author_score,
                    venue_prestige_score=venue_score,
                    recency_bonus=recency_score,
                    matched_keywords=matched_keywords,
                    high_impact_authors=high_impact_authors,
                    citation_velocity=citation_velocity if citation_velocity > 0 else None
                )
                
                breakthrough_papers.append(breakthrough_paper)
        
        # Sort by breakthrough score (highest first)
        breakthrough_papers.sort(key=lambda bp: bp.breakthrough_score, reverse=True)
        
        return breakthrough_papers