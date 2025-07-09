"""
Comprehensive test cases for computational pattern validation.
"""

from typing import Dict, Any
from .keywords import validate_patterns
from .analyzer import ComputationalAnalyzer


class PatternTestSuite:
    """Test suite for validating regex patterns and normalization"""

    def __init__(self):
        self.analyzer = ComputationalAnalyzer()

    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all pattern tests and return detailed results"""

        results = {
            "basic_validation": self.test_basic_patterns(),
            "edge_cases": self.test_edge_cases(),
            "normalization": self.test_normalization(),
            "error_handling": self.test_error_handling(),
            "real_world_examples": self.test_real_world_examples(),
        }

        # Calculate overall success rate
        total_tests = sum(len(test_results) for test_results in results.values())
        passed_tests = sum(
            sum(1 for result in test_results.values() if result is True)
            for test_results in results.values()
        )

        # Create a separate summary dict with different types
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
            "all_tests_passed": passed_tests == total_tests,
        }
        results["summary"] = summary  # type: ignore

        return results

    def test_basic_patterns(self) -> Dict[str, bool]:
        """Test basic pattern matching functionality"""
        return validate_patterns()

    def test_edge_cases(self) -> Dict[str, bool]:
        """Test edge cases and boundary conditions"""

        edge_cases = {
            "gpu_count_variations": [
                "used 16x GPUs",
                "8 V100s",
                "32 A100 GPUs",
                "1 GPU only",
            ],
            "parameter_count_variations": [
                "1.5 billion parameters",
                "340M parameters",
                "7B parameters",
                "175 billion parameter model",
            ],
            "dataset_size_variations": [
                "10K samples",
                "1.2 million tokens",
                "500B examples",
                "2.5 billion training samples",
            ],
            "time_variations": [
                "trained for 2.5 hours",
                "24 hour training",
                "3 days of training",
                "2 weeks to train",
            ],
        }

        results = {}

        for category, test_cases in edge_cases.items():
            category_results = []

            for test_text in test_cases:
                try:
                    metrics = self.analyzer.extract_resource_metrics(test_text)
                    # Check if any metrics were extracted
                    has_matches = any(
                        len(data.get("raw_matches", [])) > 0
                        for data in metrics.values()
                    )
                    category_results.append(has_matches)
                except Exception:
                    category_results.append(False)

            results[category] = all(category_results)

        return results

    def test_normalization(self) -> Dict[str, bool]:
        """Test metric normalization accuracy"""

        test_cases = {
            "parameter_scaling": {
                "text": "The model has 7 billion parameters",
                "expected_absolute": 7e9,
            },
            "dataset_scaling": {
                "text": "Dataset with 1.5 million samples",
                "expected_absolute": 1.5e6,
            },
            "time_conversion": {"text": "Training took 2 days", "expected_hours": 48},
            "gpu_counting": {"text": "We used 8 GPUs", "expected_count": 8},
        }

        results = {}

        for test_name, test_data in test_cases.items():
            try:
                metrics = self.analyzer.extract_resource_metrics(test_data["text"])

                if "parameter" in test_name and "parameter_count" in metrics:
                    normalized = metrics["parameter_count"]["normalized_values"][0]
                    results[test_name] = (
                        abs(
                            normalized["absolute_value"]
                            - test_data["expected_absolute"]
                        )
                        < 1e6
                    )

                elif "dataset" in test_name and "dataset_size" in metrics:
                    normalized = metrics["dataset_size"]["normalized_values"][0]
                    results[test_name] = (
                        abs(
                            normalized["absolute_value"]
                            - test_data["expected_absolute"]
                        )
                        < 1e3
                    )

                elif "time" in test_name and "training_time" in metrics:
                    normalized = metrics["training_time"]["normalized_values"][0]
                    results[test_name] = (
                        abs(
                            normalized["hours_equivalent"] - test_data["expected_hours"]
                        )
                        < 1
                    )

                elif "gpu" in test_name and "gpu_count" in metrics:
                    normalized = metrics["gpu_count"]["normalized_values"][0]
                    results[test_name] = (
                        normalized["value"] == test_data["expected_count"]
                    )

                else:
                    results[test_name] = False

            except Exception:
                results[test_name] = False

        return results

    def test_error_handling(self) -> Dict[str, bool]:
        """Test error handling for malformed input"""

        error_cases = {
            "empty_string": "",
            "no_numbers": "This text has no computational metrics at all",
            "malformed_numbers": "We used NaN GPUs and infinite parameters",
            "partial_matches": "Training took hours with billion",
            "unicode_text": "Model with ∞ parameters trained on ∅ samples",
        }

        results = {}

        for case_name, test_text in error_cases.items():
            try:
                # Should not crash, even with bad input
                self.analyzer.extract_resource_metrics(test_text)
                self.analyzer.analyze_keywords(test_text)
                results[case_name] = True  # No crash = success

            except Exception:
                results[case_name] = False  # Crash = failure

        return results

    def test_real_world_examples(self) -> Dict[str, bool]:
        """Test with realistic paper abstract examples"""

        examples = {
            "transformer_paper": """
            We present a transformer model with 175 billion parameters trained on 300 billion tokens.
            Training was performed on 1024 V100 GPUs over 2 weeks using a batch size of 1024.
            The model required 8TB of memory and achieved 15 TFLOPS performance.
            """,
            "computer_vision_paper": """
            Our ResNet-152 model was trained on ImageNet containing 1.2 million images.
            Training took 4 days on 8 A100 GPUs with 40GB VRAM each.
            We used a learning rate of 0.001 and trained for 90 epochs.
            """,
            "reinforcement_learning_paper": """
            The agent was trained for 100 million steps using distributed training on 256 CPU cores.
            Training required 72 hours and used approximately $10,000 in compute resources.
            Each environment step processed batches of 512 samples.
            """,
        }

        results = {}

        for paper_type, abstract in examples.items():
            try:
                analysis = self.analyzer.analyze_keywords(abstract)
                metrics = self.analyzer.extract_resource_metrics(abstract)

                # Check if reasonable amount of computational content was detected
                total_matches = sum(cat["matches"] for cat in analysis.values())
                metric_count = len(metrics)

                # Should detect some computational content in these examples
                # More realistic thresholds: at least 2 keywords AND 1 metric
                results[paper_type] = total_matches >= 2 and metric_count >= 1

            except Exception:
                results[paper_type] = False

        return results


def run_pattern_validation() -> Dict[str, Any]:
    """Run comprehensive pattern validation and return results"""
    test_suite = PatternTestSuite()
    return test_suite.run_comprehensive_tests()


if __name__ == "__main__":
    results = run_pattern_validation()

    print("=== COMPREHENSIVE PATTERN TEST RESULTS ===")
    print()

    for category, tests in results.items():
        if category == "summary":
            continue

        print(f"{category.upper()}:")
        for test_name, passed in tests.items():
            status = "✓" if passed else "❌"
            print(f"  {status} {test_name}")
        print()

    summary = results["summary"]
    print(f"OVERALL: {summary['passed_tests']}/{summary['total_tests']} tests passed")
    print(f"Success rate: {summary['success_rate']:.1%}")

    if summary["all_tests_passed"]:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed - review above for details")
