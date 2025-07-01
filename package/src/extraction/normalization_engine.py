"""Normalization engine for extracted values."""

from typing import Dict, Any


class NormalizationEngine:
    """Normalize extracted values to standard units."""
    
    def __init__(self):
        self.time_conversions = {
            "minutes": 1/60,
            "hours": 1,
            "days": 24,
            "weeks": 24 * 7
        }
        
        self.memory_conversions = {
            "MB": 1/1024,
            "GB": 1,
            "TB": 1024
        }
        
        self.parameter_conversions = {
            "K": 1e-3,
            "M": 1,
            "B": 1e3,
            "T": 1e6
        }