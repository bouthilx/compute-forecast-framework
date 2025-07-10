"""Formatter registry and base classes for quality reports."""

from abc import ABC, abstractmethod
from typing import Dict, Type, Optional
from pathlib import Path

from .interfaces import QualityReport


class ReportFormatter(ABC):
    """Base formatter for quality reports."""
    
    @abstractmethod
    def format_report(self, report: QualityReport, **kwargs) -> str:
        """Format a quality report."""
        pass


class FormatterRegistry:
    """Registry for report formatters."""
    
    _formatters: Dict[str, Type[ReportFormatter]] = {}
    _stage_formatters: Dict[str, Dict[str, Type[ReportFormatter]]] = {}
    
    @classmethod
    def register(cls, format_name: str, formatter_class: Type[ReportFormatter], stage: Optional[str] = None):
        """Register a formatter."""
        if stage:
            if stage not in cls._stage_formatters:
                cls._stage_formatters[stage] = {}
            cls._stage_formatters[stage][format_name] = formatter_class
        else:
            cls._formatters[format_name] = formatter_class
    
    @classmethod
    def get_formatter(cls, format_name: str, stage: Optional[str] = None) -> Optional[Type[ReportFormatter]]:
        """Get a formatter by name and optional stage."""
        # First check stage-specific formatters
        if stage and stage in cls._stage_formatters:
            if format_name in cls._stage_formatters[stage]:
                return cls._stage_formatters[stage][format_name]
        
        # Fall back to generic formatters
        return cls._formatters.get(format_name)
    
    @classmethod
    def list_formats(cls) -> Dict[str, list]:
        """List all available formats."""
        return {
            "generic": list(cls._formatters.keys()),
            "stage_specific": {
                stage: list(formats.keys()) 
                for stage, formats in cls._stage_formatters.items()
            }
        }


def format_report(report: QualityReport, format_name: str = "text", **kwargs) -> str:
    """Format a quality report using the appropriate formatter."""
    formatter_class = FormatterRegistry.get_formatter(format_name, report.stage)
    
    if not formatter_class:
        raise ValueError(f"No formatter found for format '{format_name}' and stage '{report.stage}'")
    
    formatter = formatter_class()
    return formatter.format_report(report, **kwargs)


def save_report(report: QualityReport, output_path: Path, format_name: str = "text", **kwargs):
    """Save a formatted report to a file."""
    formatted = format_report(report, format_name, **kwargs)
    output_path.write_text(formatted)