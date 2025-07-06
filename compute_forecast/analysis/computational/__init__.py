"""
Computational analysis module for paper resource analysis.
"""

from .keywords import COMPUTATIONAL_INDICATORS, COMPUTATIONAL_PATTERNS
from .analyzer import ComputationalAnalyzer
from .experimental_detector import ExperimentalDetector
from .filter import ComputationalFilter

__all__ = [
    "COMPUTATIONAL_INDICATORS",
    "COMPUTATIONAL_PATTERNS",
    "ComputationalAnalyzer",
    "ExperimentalDetector",
    "ComputationalFilter",
]
