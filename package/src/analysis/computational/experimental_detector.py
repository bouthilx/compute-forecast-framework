"""
Experimental content detection for research papers.
"""

from typing import Dict, Any, List
import re


class ExperimentalDetector:
    """Detects experimental and implementation content in research papers"""
    
    def __init__(self):
        self.experimental_indicators = [
            'experiment', 'evaluation', 'benchmark', 'baseline',
            'results', 'performance', 'accuracy', 'precision', 'recall',
            'ablation', 'comparison', 'validation', 'test set',
            'training set', 'dataset', 'implementation', 'code',
            'empirical', 'empirical study', 'experimental study',
            'case study', 'user study', 'evaluation study'
        ]
        
        self.methodology_indicators = [
            'method', 'approach', 'algorithm', 'technique',
            'architecture', 'model', 'framework', 'system',
            'methodology', 'procedure', 'protocol', 'setup',
            'experimental setup', 'experimental design'
        ]
        
        self.implementation_indicators = [
            'implementation', 'code', 'software', 'library',
            'framework', 'platform', 'tool', 'system',
            'open source', 'github', 'repository', 'source code',
            'programming', 'development', 'built', 'developed'
        ]
        
        self.quantitative_indicators = [
            'metrics', 'measurement', 'quantitative', 'statistical',
            'analysis', 'score', 'rating', 'numerical', 'data',
            'statistics', 'significance', 'correlation', 'regression'
        ]
        
        # Patterns for detecting specific experimental sections
        self.section_patterns = {
            'results': re.compile(r'\b(?:results?|findings?|outcomes?)\b', re.IGNORECASE),
            'experiments': re.compile(r'\b(?:experiments?|experimental)\b', re.IGNORECASE),
            'evaluation': re.compile(r'\b(?:evaluation|evaluating|evaluated)\b', re.IGNORECASE),
            'methodology': re.compile(r'\b(?:methodology|methods?|approach)\b', re.IGNORECASE),
            'implementation': re.compile(r'\b(?:implementation|implementing|implemented)\b', re.IGNORECASE)
        }
    
    def detect_experimental_content(self, text: str) -> Dict[str, Any]:
        """Comprehensive experimental content detection"""
        
        text_lower = text.lower()
        
        # Calculate indicator scores
        experimental_score = self._calculate_indicator_score(text_lower, self.experimental_indicators)
        methodology_score = self._calculate_indicator_score(text_lower, self.methodology_indicators)
        implementation_score = self._calculate_indicator_score(text_lower, self.implementation_indicators)
        quantitative_score = self._calculate_indicator_score(text_lower, self.quantitative_indicators)
        
        # Detect specific sections
        section_presence = self._detect_sections(text)
        
        # Check for specific experimental patterns
        experimental_patterns = self._detect_experimental_patterns(text_lower)
        
        # Calculate overall experimental confidence
        overall_score = self._calculate_overall_experimental_score(
            experimental_score, methodology_score, implementation_score, 
            quantitative_score, section_presence, experimental_patterns
        )
        
        # Determine if this is an experimental paper
        is_experimental = self._determine_experimental_classification(
            overall_score, section_presence, experimental_patterns
        )
        
        return {
            'experimental_score': experimental_score,
            'methodology_score': methodology_score,
            'implementation_score': implementation_score,
            'quantitative_score': quantitative_score,
            'section_presence': section_presence,
            'experimental_patterns': experimental_patterns,
            'overall_experimental_score': overall_score,
            'is_experimental_paper': is_experimental,
            'experimental_confidence': self._calculate_confidence(overall_score, section_presence)
        }
    
    def _calculate_indicator_score(self, text: str, indicators: List[str]) -> float:
        """Calculate normalized score for indicator presence"""
        matches = sum(1 for indicator in indicators if indicator.lower() in text)
        return matches / len(indicators)
    
    def _detect_sections(self, text: str) -> Dict[str, bool]:
        """Detect presence of experimental sections in paper"""
        section_presence = {}
        
        for section_name, pattern in self.section_patterns.items():
            matches = pattern.findall(text)
            section_presence[section_name] = len(matches) > 0
            section_presence[f"{section_name}_count"] = len(matches)
        
        return section_presence
    
    def _detect_experimental_patterns(self, text: str) -> Dict[str, Any]:
        """Detect specific experimental patterns and phrases"""
        patterns = {
            'has_results_section': any(
                phrase in text for phrase in [
                    'results section', 'experimental results', 'evaluation results',
                    'results and discussion', 'findings'
                ]
            ),
            'has_implementation_details': any(
                phrase in text for phrase in [
                    'implementation details', 'hyperparameters', 'training details',
                    'experimental setup', 'implementation notes'
                ]
            ),
            'has_performance_metrics': any(
                phrase in text for phrase in [
                    'performance metrics', 'evaluation metrics', 'accuracy score',
                    'precision recall', 'f1 score', 'auc score'
                ]
            ),
            'has_comparative_analysis': any(
                phrase in text for phrase in [
                    'comparison with', 'compared to', 'baseline comparison',
                    'state-of-the-art', 'outperforms', 'competitive with'
                ]
            ),
            'has_statistical_analysis': any(
                phrase in text for phrase in [
                    'statistical significance', 'p-value', 'confidence interval',
                    'statistical test', 'significance test'
                ]
            ),
            'has_reproducibility_info': any(
                phrase in text for phrase in [
                    'reproducible', 'code available', 'open source',
                    'github repository', 'replication'
                ]
            )
        }
        
        return patterns
    
    def _calculate_overall_experimental_score(self, experimental_score: float, 
                                            methodology_score: float,
                                            implementation_score: float,
                                            quantitative_score: float,
                                            section_presence: Dict[str, Any],
                                            experimental_patterns: Dict[str, bool]) -> float:
        """Calculate weighted overall experimental score"""
        
        # Weight the different components
        score = (
            experimental_score * 0.3 +
            methodology_score * 0.2 +
            implementation_score * 0.2 +
            quantitative_score * 0.15
        )
        
        # Boost for section presence
        section_boost = sum(1 for key, value in section_presence.items() 
                          if not key.endswith('_count') and value) * 0.02
        
        # Boost for experimental patterns
        pattern_boost = sum(experimental_patterns.values()) * 0.01
        
        total_score = score + section_boost + pattern_boost
        return min(total_score, 1.0)
    
    def _determine_experimental_classification(self, overall_score: float,
                                             section_presence: Dict[str, Any],
                                             experimental_patterns: Dict[str, bool]) -> bool:
        """Determine if paper should be classified as experimental"""
        
        # High overall score threshold
        if overall_score >= 0.4:
            return True
        
        # Strong section indicators
        if (section_presence.get('results', False) and 
            section_presence.get('experiments', False)):
            return True
        
        # Strong pattern indicators
        pattern_count = sum(experimental_patterns.values())
        if pattern_count >= 3:
            return True
        
        # Implementation + evaluation combination
        if (experimental_patterns.get('has_implementation_details', False) and
            experimental_patterns.get('has_performance_metrics', False)):
            return True
        
        return False
    
    def _calculate_confidence(self, overall_score: float, 
                            section_presence: Dict[str, Any]) -> float:
        """Calculate confidence in experimental classification"""
        
        base_confidence = overall_score * 0.7
        
        # Boost for clear section structure
        if section_presence.get('results', False):
            base_confidence += 0.15
        if section_presence.get('methodology', False):
            base_confidence += 0.1
        if section_presence.get('evaluation', False):
            base_confidence += 0.05
        
        return min(base_confidence, 1.0)
    
    def get_experimental_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of experimental content analysis"""
        
        classification = "Experimental" if analysis_result['is_experimental_paper'] else "Theoretical"
        confidence = analysis_result['experimental_confidence']
        
        strengths = []
        if analysis_result['experimental_score'] > 0.3:
            strengths.append("Strong experimental indicators")
        if analysis_result['implementation_score'] > 0.2:
            strengths.append("Implementation details present")
        if analysis_result['section_presence'].get('results', False):
            strengths.append("Clear results section")
        if analysis_result['experimental_patterns']['has_performance_metrics']:
            strengths.append("Performance metrics included")
        
        return {
            'classification': classification,
            'confidence': confidence,
            'overall_score': analysis_result['overall_experimental_score'],
            'strengths': strengths,
            'recommendation': self._make_recommendation(analysis_result)
        }
    
    def _make_recommendation(self, analysis_result: Dict[str, Any]) -> str:
        """Make recommendation based on experimental analysis"""
        
        if analysis_result['is_experimental_paper']:
            if analysis_result['experimental_confidence'] > 0.8:
                return "High priority for computational analysis"
            elif analysis_result['experimental_confidence'] > 0.6:
                return "Good candidate for computational analysis"
            else:
                return "Moderate experimental content"
        else:
            return "Primarily theoretical - low priority for resource analysis"