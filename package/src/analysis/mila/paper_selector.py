"""Mila paper selection and filtering for computational analysis."""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np
from pathlib import Path


@dataclass
class PaperSelectionCriteria:
    """Criteria for selecting Mila papers."""
    start_year: int = 2019
    end_year: int = 2024
    papers_per_year_min: int = 15
    papers_per_year_max: int = 30
    papers_per_domain_per_year_min: int = 5
    papers_per_domain_per_year_max: int = 10
    domains: List[str] = field(default_factory=lambda: ["NLP", "CV", "RL"])
    min_computational_richness: float = 0.4
    prefer_top_venues: bool = True


class DomainClassifier:
    """Classify papers into ML domains (NLP, CV, RL)."""
    
    def __init__(self):
        # Domain keywords for classification
        self.domain_keywords = {
            "NLP": [
                "language", "nlp", "bert", "gpt", "transformer", "text", "translation",
                "sentiment", "parsing", "question answering", "summarization", "dialogue",
                "named entity", "pos tagging", "tokeniz", "embedding", "word2vec",
                "linguistic", "corpus", "bilingual", "monolingual", "multilingual"
            ],
            "CV": [
                "image", "vision", "visual", "video", "convolution", "cnn", "resnet",
                "detection", "segmentation", "recognition", "classification", "vit",
                "pixel", "object detection", "face", "scene", "imagenet", "coco",
                "yolo", "rcnn", "gan", "generative", "synthesis", "style transfer"
            ],
            "RL": [
                "reinforcement", "rl", "q-learning", "policy", "reward", "agent",
                "environment", "mdp", "markov", "bellman", "actor-critic", "dqn",
                "ppo", "a3c", "sarsa", "monte carlo", "exploration", "exploitation",
                "atari", "mujoco", "gym", "robotic", "control"
            ]
        }
        
        # Compile regex patterns for efficiency
        self.domain_patterns = {
            domain: re.compile(
                r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b',
                re.IGNORECASE
            )
            for domain, keywords in self.domain_keywords.items()
        }
    
    def classify(self, paper: Dict) -> str:
        """Classify paper into primary domain."""
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        text = f"{title} {abstract}"
        
        # Count keyword matches for each domain
        domain_scores = {}
        for domain, pattern in self.domain_patterns.items():
            matches = pattern.findall(text)
            domain_scores[domain] = len(matches)
        
        # Return domain with highest score
        if max(domain_scores.values()) > 0:
            return max(domain_scores, key=domain_scores.get)
        
        return "Other"


class ComputationalContentFilter:
    """Filter papers by computational content richness."""
    
    def __init__(self):
        # Computational indicators
        self.compute_keywords = [
            r'\b\d+\s*(?:gpu|tpu|accelerator)s?\b',
            r'\b\d+\.?\d*[bmk]?\s*(?:parameters?|params?)\b',
            r'\b\d+\s*(?:hours?|days?|weeks?|months?)\s*(?:of\s*)?(?:training|compute)\b',
            r'\b(?:trained?|fine-?tuned?)\s*(?:on|using|with)\b',
            r'\bgpu[\s-]?hours?\b',
            r'\b(?:a100|v100|p100|rtx|titan|tpu)\b',
            r'\b\d+\s*(?:epochs?|iterations?|steps?)\b',
            r'\b(?:flops?|tflops?|pflops?)\b',
            r'\b(?:distributed|parallel|multi-node)\s*training\b'
        ]
        
        # Survey/theory indicators (negative signal)
        self.theory_keywords = [
            r'\bsurvey\b', r'\breview\b', r'\btutorial\b', r'\banalysis\s*of\b',
            r'\btheoretical\b', r'\bproof\b', r'\btheorem\b'
        ]
        
        self.compute_pattern = re.compile('|'.join(self.compute_keywords), re.IGNORECASE)
        self.theory_pattern = re.compile('|'.join(self.theory_keywords), re.IGNORECASE)
    
    def compute_richness_score(self, paper: Dict) -> float:
        """Compute computational richness score for a paper."""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        
        # If no abstract, use title heavily
        if not abstract.strip():
            # Check if title suggests computational work
            title_lower = title.lower()
            ml_keywords = ["training", "learning", "neural", "deep", "model", "transformer",
                          "bert", "gpt", "gan", "vae", "cnn", "rnn", "lstm", "detection",
                          "classification", "segmentation", "reinforcement", "optimization"]
            
            if any(kw in title_lower for kw in ml_keywords):
                # Check for theory/survey indicators
                if any(kw in title_lower for kw in ["survey", "review", "analysis of", "study of"]):
                    return 0.0
                return 0.2  # Base score for ML papers without abstract
            return 0.0
        
        text = f"{title} {abstract}"
        
        # Count computational indicators
        compute_matches = len(self.compute_pattern.findall(text))
        
        # Count theory/survey indicators
        theory_matches = len(self.theory_pattern.findall(text))
        
        # Base score from computational content
        text_length = len(text.split())
        if text_length == 0:
            return 0.0
        
        # Normalize by text length
        compute_density = compute_matches / (text_length / 100)  # per 100 words
        theory_penalty = theory_matches * 0.3
        
        # Score between 0 and 1, with more gradual scaling
        base_score = min(0.6, compute_density * 0.15)  # Cap base at 0.6
        score = max(0.0, base_score - theory_penalty)
        
        # Boost for specific strong indicators
        if re.search(r'\b\d+\s*(?:gpu|tpu)s?\b', text, re.IGNORECASE):
            score = min(1.0, score + 0.2)
        if re.search(r'\b\d+[bmk]\s*parameters?\b', text, re.IGNORECASE):
            score = min(1.0, score + 0.1)
            
        return score
    
    def filter_by_richness(self, papers: List[Dict], min_score: float = 0.4) -> List[Dict]:
        """Filter papers by computational richness score."""
        scored_papers = []
        for paper in papers:
            score = self.compute_richness_score(paper)
            if score >= min_score:
                paper_with_score = paper.copy()
                paper_with_score["computational_richness_score"] = score
                scored_papers.append(paper_with_score)
        
        # Sort by score descending
        scored_papers.sort(key=lambda p: p["computational_richness_score"], reverse=True)
        return scored_papers


class MilaPaperSelector:
    """Select Mila papers for computational analysis."""
    
    def __init__(self):
        self.domain_classifier = DomainClassifier()
        self.content_filter = ComputationalContentFilter()
        
        # Top ML venues
        self.top_venues = {
            "neurips", "icml", "iclr", "cvpr", "eccv", "iccv", "acl", "emnlp", 
            "naacl", "aaai", "ijcai", "uai", "aistats", "jmlr", "tmlr"
        }
    
    def load_papers(self, file_path: str) -> List[Dict]:
        """Load papers from JSON file."""
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def filter_by_year(self, papers: List[Dict], start_year: int, end_year: int) -> List[Dict]:
        """Filter papers by publication year."""
        filtered = []
        for paper in papers:
            year = self._extract_year(paper)
            if year and start_year <= year <= end_year:
                filtered.append(paper)
        return filtered
    
    def _extract_year(self, paper: Dict) -> Optional[int]:
        """Extract publication year from paper."""
        for release in paper.get("releases", []):
            date_text = release.get("venue", {}).get("date", {}).get("text", "")
            if date_text:
                try:
                    return int(date_text[:4])
                except (ValueError, IndexError):
                    pass
        return None
    
    def _extract_venue(self, paper: Dict) -> str:
        """Extract venue name from paper."""
        for release in paper.get("releases", []):
            venue_name = release.get("venue", {}).get("name", "")
            if venue_name:
                return venue_name.lower()
        return ""
    
    def _is_top_venue(self, paper: Dict) -> bool:
        """Check if paper is from a top-tier venue."""
        venue = self._extract_venue(paper)
        return any(top_venue in venue for top_venue in self.top_venues)
    
    def select_papers(self, papers: List[Dict], criteria: PaperSelectionCriteria) -> List[Dict]:
        """Select papers according to criteria with balanced distribution."""
        # Filter by year range
        papers = self.filter_by_year(papers, criteria.start_year, criteria.end_year)
        
        # Filter by computational richness
        papers = self.content_filter.filter_by_richness(
            papers, criteria.min_computational_richness
        )
        
        # Classify papers by domain
        papers_by_year_domain = defaultdict(lambda: defaultdict(list))
        papers_by_year = defaultdict(list)  # All papers by year
        
        for paper in papers:
            year = self._extract_year(paper)
            if year:
                domain = self.domain_classifier.classify(paper)
                papers_by_year[year].append(paper)
                if domain in criteria.domains:
                    papers_by_year_domain[year][domain].append(paper)
        
        # Select papers with balanced distribution
        selected = []
        for year in sorted(papers_by_year.keys()):
            year_papers = []
            
            # First pass: ensure minimum papers per domain
            for domain in criteria.domains:
                domain_papers = papers_by_year_domain[year][domain]
                
                # Sort by venue quality and richness score
                domain_papers.sort(
                    key=lambda p: (
                        self._is_top_venue(p),
                        p.get("computational_richness_score", 0)
                    ),
                    reverse=True
                )
                
                # Select up to max per domain
                n_select = min(
                    len(domain_papers),
                    criteria.papers_per_domain_per_year_max
                )
                year_papers.extend(domain_papers[:n_select])
            
            # Second pass: fill up to year minimum/maximum if needed
            if len(year_papers) < criteria.papers_per_year_min:
                # Need more papers - get from all papers this year
                selected_ids = {p["paper_id"] for p in year_papers}
                remaining_papers = [p for p in papers_by_year[year] 
                                  if p["paper_id"] not in selected_ids]
                
                # Sort by quality
                remaining_papers.sort(
                    key=lambda p: (
                        self._is_top_venue(p),
                        p.get("computational_richness_score", 0)
                    ),
                    reverse=True
                )
                
                needed = criteria.papers_per_year_min - len(year_papers)
                year_papers.extend(remaining_papers[:needed])
            
            # Cap at maximum if exceeded
            if len(year_papers) > criteria.papers_per_year_max:
                year_papers = year_papers[:criteria.papers_per_year_max]
            
            selected.extend(year_papers)
        
        return selected
    
    def generate_selection_summary(self, selected_papers: List[Dict]) -> Dict:
        """Generate summary statistics for selected papers."""
        summary = {
            "total_selected": len(selected_papers),
            "by_year": defaultdict(int),
            "by_domain": defaultdict(int),
            "by_venue_tier": {"top": 0, "other": 0},
            "computational_richness": {
                "scores": [],
                "mean": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0
            }
        }
        
        richness_scores = []
        
        for paper in selected_papers:
            # Year
            year = self._extract_year(paper)
            if year:
                summary["by_year"][year] += 1
            
            # Domain
            domain = self.domain_classifier.classify(paper)
            summary["by_domain"][domain] += 1
            
            # Venue tier
            if self._is_top_venue(paper):
                summary["by_venue_tier"]["top"] += 1
            else:
                summary["by_venue_tier"]["other"] += 1
            
            # Richness score
            score = paper.get("computational_richness_score", 
                           self.content_filter.compute_richness_score(paper))
            richness_scores.append(score)
        
        # Compute richness statistics
        if richness_scores:
            summary["computational_richness"]["scores"] = richness_scores
            summary["computational_richness"]["mean"] = float(np.mean(richness_scores))
            summary["computational_richness"]["std"] = float(np.std(richness_scores))
            summary["computational_richness"]["min"] = float(np.min(richness_scores))
            summary["computational_richness"]["max"] = float(np.max(richness_scores))
        
        # Convert defaultdicts to regular dicts
        summary["by_year"] = dict(summary["by_year"])
        summary["by_domain"] = dict(summary["by_domain"])
        
        return summary