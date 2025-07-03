"""
Comprehensive test cases for ComputationalFilter functionality.
"""

from typing import Dict, List, Any
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from compute_forecast.data.models import Paper, Author
from .filter import ComputationalFilter


class FilterTestSuite:
    """Test suite for validating ComputationalFilter functionality"""
    
    def __init__(self):
        self.filter_system = ComputationalFilter()
        
    def create_test_papers(self) -> List[Paper]:
        """Create diverse test papers for filtering"""
        
        papers = [
            # High computational content paper
            Paper(
                title='Large-Scale Transformer Training with 175B Parameters',
                authors=[Author('AI Researcher', 'MIT')],
                venue='NeurIPS',
                year=2023,
                citations=500,
                abstract='''
                We present a large transformer model with 175 billion parameters.
                Training was performed using 1024 V100 GPUs over 2 weeks.
                The model required 16 TB of memory and achieved 20 TFLOPS.
                We used a batch size of 2048 and learning rate of 0.0001.
                Training took 336 hours total with dataset of 500 billion tokens.
                
                Our experimental results demonstrate superior performance on benchmarks.
                We conducted extensive experiments and evaluation on multiple datasets.
                The implementation details include hyperparameter tuning and ablation studies.
                Performance metrics show significant improvements over baselines.
                '''
            ),
            
            # Medium computational content paper  
            Paper(
                title='Efficient Neural Architecture Search',
                authors=[Author('ML Engineer', 'Google')],
                venue='ICML',
                year=2023,
                citations=200,
                abstract='''
                We propose an efficient method for neural architecture search.
                Experiments were conducted on 8 A100 GPUs for 12 hours.
                Our approach uses 50 million parameters and trains for 100 epochs.
                
                Experimental validation shows competitive accuracy with reduced compute.
                We implemented the method and conducted comprehensive evaluation.
                Results demonstrate effectiveness across multiple benchmarks.
                '''
            ),
            
            # Low computational content paper
            Paper(
                title='Survey of Deep Learning Methods',
                authors=[Author('Survey Author', 'Stanford')],
                venue='JMLR',
                year=2023,
                citations=150,
                abstract='''
                This survey reviews recent advances in deep learning.
                We analyze various neural network architectures and training methods.
                The paper discusses computational considerations but presents no experiments.
                '''
            ),
            
            # Theoretical paper
            Paper(
                title='Theoretical Analysis of Gradient Descent',
                authors=[Author('Theory Researcher', 'CMU')],
                venue='STOC',
                year=2023,
                citations=80,
                abstract='''
                We provide theoretical convergence guarantees for gradient descent.
                The analysis uses mathematical tools from optimization theory.
                No computational experiments are performed in this work.
                '''
            )
        ]
        
        return papers
    
    def test_paper_filtering(self) -> Dict[str, bool]:
        """Test paper filtering and categorization"""
        
        papers = self.create_test_papers()
        
        try:
            filtered_papers = self.filter_system.filter_papers_by_computational_content(papers)
            
            results = {
                'filtering_completed': True,
                'all_categories_present': len(filtered_papers) == 4,
                'papers_distributed': sum(len(papers) for papers in filtered_papers.values()) == len(papers),
                'computational_papers_prioritized': len(filtered_papers['medium_priority']) > 0 or len(filtered_papers['high_priority']) > 0,
                'theoretical_separated': len(filtered_papers['theoretical_only']) > 0
            }
            
            return results
            
        except Exception:
            return {'filtering_completed': False}
    
    def test_priority_scoring(self) -> Dict[str, bool]:
        """Test priority scoring and sorting"""
        
        papers = self.create_test_papers()
        
        try:
            filtered_papers = self.filter_system.filter_papers_by_computational_content(papers)
            
            # Test that papers within categories are sorted by priority
            results = {}
            
            for category, paper_list in filtered_papers.items():
                if len(paper_list) > 1:
                    # Check if papers have computational analysis attached
                    has_analysis = all(
                        hasattr(paper, 'computational_analysis') and paper.computational_analysis
                        for paper in paper_list
                    )
                    results[f'{category}_has_analysis'] = has_analysis
                    
                    # Check if papers are sorted (higher richness first)
                    if has_analysis:
                        richness_scores = [
                            paper.computational_analysis['computational_richness']
                            for paper in paper_list
                        ]
                        is_sorted = all(
                            richness_scores[i] >= richness_scores[i+1]
                            for i in range(len(richness_scores)-1)
                        )
                        results[f'{category}_properly_sorted'] = is_sorted
                
            results['priority_scoring_functional'] = True
            return results
            
        except Exception as e:
            return {'priority_scoring_functional': False, 'error': str(e)}
    
    def test_report_generation(self) -> Dict[str, bool]:
        """Test report generation functionality"""
        
        papers = self.create_test_papers()
        
        try:
            filtered_papers = self.filter_system.filter_papers_by_computational_content(papers)
            report = self.filter_system.generate_computational_report(filtered_papers)
            
            required_fields = [
                'total_papers_analyzed',
                'computational_distribution', 
                'resource_projection_quality',
                'dataset_quality_score',
                'recommendations',
                'analysis_summary'
            ]
            
            results = {
                'report_generated': True,
                'has_required_fields': all(field in report for field in required_fields),
                'correct_paper_count': report['total_papers_analyzed'] == len(papers),
                'quality_score_valid': 0 <= report['dataset_quality_score'] <= 1,
                'has_recommendations': len(report['recommendations']) > 0
            }
            
            return results
            
        except Exception:
            return {'report_generated': False}
    
    def test_top_papers_selection(self) -> Dict[str, bool]:
        """Test top papers selection for projection"""
        
        papers = self.create_test_papers()
        
        try:
            filtered_papers = self.filter_system.filter_papers_by_computational_content(papers)
            
            # Test different limits
            top_5 = self.filter_system.get_top_papers_for_projection(filtered_papers, max_papers=5)
            top_2 = self.filter_system.get_top_papers_for_projection(filtered_papers, max_papers=2)
            
            results = {
                'top_papers_selection_works': True,
                'respects_max_limit': len(top_2) <= 2,
                'returns_best_papers': len(top_5) >= len(top_2),
                'no_duplicates': len(set(id(p) for p in top_5)) == len(top_5)
            }
            
            return results
            
        except Exception:
            return {'top_papers_selection_works': False}
    
    def test_error_handling(self) -> Dict[str, bool]:
        """Test error handling with edge cases"""
        
        try:
            # Test with empty list
            empty_result = self.filter_system.filter_papers_by_computational_content([])
            empty_report = self.filter_system.generate_computational_report(empty_result)
            
            # Test with malformed papers
            malformed_paper = Paper(
                title='',
                authors=[],
                venue='',
                year=0,
                citations=0,
                abstract=''
            )
            
            malformed_result = self.filter_system.filter_papers_by_computational_content([malformed_paper])
            
            results = {
                'handles_empty_list': len(empty_result) == 4,  # All categories should exist
                'empty_report_valid': empty_report['total_papers_analyzed'] == 0,
                'handles_malformed_papers': len(malformed_result) == 4
            }
            
            return results
            
        except Exception:
            return {'error_handling_works': False}
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all filter tests and return results"""
        
        results = {
            'filtering': self.test_paper_filtering(),
            'priority_scoring': self.test_priority_scoring(),
            'report_generation': self.test_report_generation(),
            'top_papers_selection': self.test_top_papers_selection(),
            'error_handling': self.test_error_handling()
        }
        
        # Calculate overall success rate
        total_tests = sum(len(test_results) for test_results in results.values())
        passed_tests = sum(
            sum(1 for result in test_results.values() if result is True)
            for test_results in results.values()
        )
        
        results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0.0,
            'all_tests_passed': passed_tests == total_tests
        }
        
        return results


def run_filter_validation() -> Dict[str, Any]:
    """Run comprehensive filter validation"""
    test_suite = FilterTestSuite()
    return test_suite.run_comprehensive_tests()


if __name__ == "__main__":
    results = run_filter_validation()
    
    print("=== COMPUTATIONAL FILTER TEST RESULTS ===")
    print()
    
    for category, tests in results.items():
        if category == 'summary':
            continue
            
        print(f"{category.upper()}:")
        for test_name, passed in tests.items():
            if isinstance(passed, bool):
                status = "✓" if passed else "❌"
                print(f"  {status} {test_name}")
            else:
                print(f"  ⚠️  {test_name}: {passed}")
        print()
    
    summary = results['summary']
    print(f"OVERALL: {summary['passed_tests']}/{summary['total_tests']} tests passed")
    print(f"Success rate: {summary['success_rate']:.1%}")
    
    if summary['all_tests_passed']:
        print("🎉 ALL FILTER TESTS PASSED!")
    else:
        print("⚠️  Some tests failed - review above for details")