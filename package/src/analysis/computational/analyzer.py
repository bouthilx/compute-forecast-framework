"""
Computational content analysis engine for papers.
"""

import re
from typing import Dict, Any, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.data.models import Paper
from src.analysis.base import BaseAnalyzer
from .keywords import COMPUTATIONAL_INDICATORS, COMPUTATIONAL_PATTERNS


class ComputationalAnalyzer(BaseAnalyzer):
    """Analyzes papers for computational content and resource requirements"""
    
    def __init__(self):
        self.keywords = COMPUTATIONAL_INDICATORS
        self.patterns = COMPUTATIONAL_PATTERNS
        
    def analyze(self, paper: Paper) -> Dict[str, Any]:
        """Comprehensive computational content analysis"""
        
        # Extract text from title, abstract, and full text if available
        text_content = self.extract_paper_text(paper)
        
        # Keyword-based analysis
        keyword_scores = self.analyze_keywords(text_content)
        
        # Pattern-based extraction
        resource_metrics = self.extract_resource_metrics(text_content)
        
        # Computational richness scoring
        richness_score = self.calculate_richness_score(keyword_scores, resource_metrics)
        
        return {
            'computational_richness': richness_score,
            'keyword_matches': keyword_scores,
            'resource_metrics': resource_metrics,
            'experimental_indicators': self.detect_experimental_content(text_content),
            'recommendation': self.make_inclusion_recommendation(richness_score)
        }
    
    def get_confidence_score(self, analysis_result: Dict[str, Any]) -> float:
        """Get confidence score for analysis result"""
        richness = analysis_result['computational_richness']
        has_metrics = len(analysis_result['resource_metrics']) > 0
        is_experimental = analysis_result['experimental_indicators']['is_experimental_paper']
        
        # Base confidence from richness score
        confidence = richness * 0.6
        
        # Boost for specific metrics
        if has_metrics:
            confidence += 0.2
            
        # Boost for experimental content
        if is_experimental:
            confidence += 0.2
            
        return min(confidence, 1.0)
    
    def extract_paper_text(self, paper: Paper) -> str:
        """Extract all available text from paper"""
        text_parts = []
        
        if hasattr(paper, 'title') and paper.title:
            text_parts.append(paper.title)
            
        if hasattr(paper, 'abstract') and paper.abstract:
            text_parts.append(paper.abstract)
            
        if hasattr(paper, 'content') and paper.content:
            text_parts.append(paper.content)
            
        if hasattr(paper, 'full_text') and paper.full_text:
            text_parts.append(paper.full_text)
            
        return ' '.join(text_parts)
    
    def analyze_keywords(self, text: str) -> Dict[str, Dict[str, Any]]:
        """Count computational keyword occurrences by category"""
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.keywords.items():
            matches = 0
            matched_keywords = []
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in text_lower:
                    # Count occurrences of this keyword
                    count = text_lower.count(keyword_lower)
                    matches += count
                    matched_keywords.append((keyword, count))
            
            scores[category] = {
                'matches': matches,
                'unique_keywords': len(matched_keywords),
                'matched_keywords': matched_keywords,
                'density': matches / len(text.split()) if text else 0
            }
        
        return scores
    
    def extract_resource_metrics(self, text: str) -> Dict[str, Dict[str, Any]]:
        """Extract specific computational metrics using regex patterns"""
        metrics = {}
        
        for metric_type, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                metrics[metric_type] = {
                    'raw_matches': matches,
                    'normalized_values': self.normalize_metric_values(metric_type, matches),
                    'count': len(matches)
                }
        
        return metrics
    
    def normalize_metric_values(self, metric_type: str, matches: List[tuple]) -> List[Dict[str, Any]]:
        """Normalize extracted metric values for comparison"""
        normalized = []
        
        for match in matches:
            try:
                if metric_type == 'gpu_count':
                    # Expect 1 group: (count)
                    if isinstance(match, tuple) and len(match) >= 1:
                        normalized.append({'value': int(match[0]), 'unit': 'gpus'})
                    else:
                        normalized.append({'value': int(match), 'unit': 'gpus'})
                        
                elif metric_type == 'training_time':
                    # Expect 2 groups: (value, unit)
                    if isinstance(match, tuple) and len(match) >= 2:
                        value, unit = match[0], match[1]
                        normalized.append({
                            'value': float(value),
                            'unit': unit.lower(),
                            'hours_equivalent': self._convert_to_hours(float(value), unit)
                        })
                    else:
                        # Fallback for unexpected format
                        normalized.append({'value': match, 'unit': 'unknown', 'raw': match})
                        
                elif metric_type == 'parameter_count':
                    # Expect 2 groups: (value, scale)
                    if isinstance(match, tuple) and len(match) >= 2:
                        value, scale = match[0], match[1]
                        multiplier = {'million': 1e6, 'billion': 1e9, 'M': 1e6, 'B': 1e9}.get(scale, 1)
                        normalized.append({
                            'value': float(value),
                            'scale': scale,
                            'absolute_value': float(value) * multiplier
                        })
                    else:
                        # Fallback for unexpected format
                        normalized.append({'value': match, 'scale': 'unknown', 'raw': match})
                        
                elif metric_type == 'dataset_size':
                    # Expect 3 groups: (value, scale, unit)
                    if isinstance(match, tuple) and len(match) >= 3:
                        value, scale, unit = match[0], match[1], match[2]
                        multiplier = {'million': 1e6, 'billion': 1e9, 'M': 1e6, 'B': 1e9, 'K': 1e3}.get(scale, 1)
                        normalized.append({
                            'value': float(value),
                            'scale': scale,
                            'unit': unit,
                            'absolute_value': float(value) * multiplier
                        })
                    else:
                        # Fallback for unexpected format
                        normalized.append({'value': match, 'scale': 'unknown', 'unit': 'unknown', 'raw': match})
                        
                elif metric_type == 'memory_usage':
                    # Expect 2 groups: (value, unit)
                    if isinstance(match, tuple) and len(match) >= 2:
                        value, unit = match[0], match[1]
                        normalized.append({
                            'value': float(value),
                            'unit': unit,
                            'raw': match
                        })
                    else:
                        normalized.append({'value': match, 'unit': 'unknown', 'raw': match})
                        
                elif metric_type == 'flops':
                    # Expect 2 groups: (value, scale)
                    if isinstance(match, tuple) and len(match) >= 2:
                        value, scale = match[0], match[1] if match[1] else ''
                        normalized.append({
                            'value': float(value),
                            'scale': scale,
                            'raw': match
                        })
                    else:
                        normalized.append({'value': match, 'scale': '', 'raw': match})
                        
                else:
                    # Generic handling for other metrics
                    if isinstance(match, tuple):
                        normalized.append({'value': match[0] if match else None, 'raw': match})
                    else:
                        normalized.append({'value': match, 'raw': match})
                        
            except (ValueError, TypeError, IndexError) as e:
                # Log error and continue with fallback handling
                normalized.append({
                    'value': None,
                    'error': f"Normalization failed: {str(e)}",
                    'raw': match
                })
        
        return normalized
    
    def _convert_to_hours(self, value: float, unit: str) -> float:
        """Convert time values to hours for comparison"""
        unit = unit.lower()
        if 'minute' in unit:
            return value / 60
        elif 'hour' in unit:
            return value
        elif 'day' in unit:
            return value * 24
        elif 'week' in unit:
            return value * 24 * 7
        else:
            return value  # Default to hours
    
    def calculate_richness_score(self, keyword_scores: Dict[str, Dict[str, Any]], 
                                resource_metrics: Dict[str, Dict[str, Any]]) -> float:
        """Calculate overall computational richness score (0-1)"""
        
        # Keyword contribution (40% of score)
        keyword_component = 0
        category_weights = {
            'gpu_hardware': 0.3,
            'training_resources': 0.25,
            'model_scale': 0.2,
            'dataset_scale': 0.15,
            'optimization_compute': 0.05,
            'infrastructure': 0.05
        }
        
        for category, scores in keyword_scores.items():
            weight = category_weights.get(category, 0.1)
            # Normalize matches to 0-1 scale, capping at 5 matches for diminishing returns
            category_score = min(scores['matches'] / 5.0, 1.0)
            keyword_component += weight * category_score
        
        # Resource metrics contribution (60% of score)
        metrics_component = 0
        if resource_metrics:
            metrics_weights = {
                'gpu_count': 0.2,
                'training_time': 0.2,
                'parameter_count': 0.2,
                'dataset_size': 0.15,
                'batch_size': 0.1,
                'memory_usage': 0.15
            }
            
            for metric, weight in metrics_weights.items():
                if metric in resource_metrics:
                    metrics_component += weight
        
        final_score = 0.4 * keyword_component + 0.6 * metrics_component
        return min(final_score, 1.0)
    
    def detect_experimental_content(self, text: str) -> Dict[str, Any]:
        """Basic experimental content detection"""
        experimental_indicators = [
            'experiment', 'evaluation', 'benchmark', 'baseline',
            'results', 'performance', 'accuracy', 'precision', 'recall',
            'ablation', 'comparison', 'validation', 'test set',
            'training set', 'dataset', 'implementation', 'code'
        ]
        
        text_lower = text.lower()
        experimental_score = sum(
            1 for indicator in experimental_indicators 
            if indicator in text_lower
        ) / len(experimental_indicators)
        
        # Check for specific experimental sections
        has_results_section = any(
            phrase in text_lower 
            for phrase in ['results section', 'experimental results', 'evaluation results']
        )
        
        has_implementation_details = any(
            phrase in text_lower 
            for phrase in ['implementation details', 'hyperparameters', 'training details']
        )
        
        return {
            'experimental_score': experimental_score,
            'has_results_section': has_results_section,
            'has_implementation_details': has_implementation_details,
            'is_experimental_paper': experimental_score > 0.3 or has_results_section
        }
    
    def make_inclusion_recommendation(self, richness_score: float) -> Dict[str, Any]:
        """Make recommendation for paper inclusion in resource analysis"""
        if richness_score >= 0.7:
            priority = 'high'
            reason = 'Rich computational content with specific metrics'
        elif richness_score >= 0.4:
            priority = 'medium'
            reason = 'Some computational content present'
        elif richness_score >= 0.2:
            priority = 'low'
            reason = 'Minimal computational indicators'
        else:
            priority = 'exclude'
            reason = 'No significant computational content'
        
        return {
            'priority': priority,
            'reason': reason,
            'richness_score': richness_score
        }