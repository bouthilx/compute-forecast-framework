"""Tests for PDF extraction cost tracking system."""

import pytest
from datetime import datetime

from src.pdf_parser.core.cost_tracker import CostTracker


class TestCostTracker:
    """Test cost tracking functionality."""
    
    def test_tracker_initialization(self):
        """Test cost tracker can be initialized."""
        tracker = CostTracker()
        assert tracker.total_cost == 0.0
        assert len(tracker.cost_records) == 0
    
    def test_record_cloud_extraction_cost(self):
        """Test recording cost for cloud-based extractions."""
        tracker = CostTracker()
        
        tracker.record_extraction_cost(
            extractor_name='google_vision',
            operation='affiliation_extraction',
            cost=0.05,
            details={'pages': 2, 'api_calls': 1}
        )
        
        assert tracker.total_cost == 0.05
        assert len(tracker.cost_records) == 1
        
        record = tracker.cost_records[0]
        assert record['extractor'] == 'google_vision'
        assert record['operation'] == 'affiliation_extraction'
        assert record['cost'] == 0.05
        assert record['details']['pages'] == 2
    
    def test_accumulate_multiple_costs(self):
        """Test accumulating costs from multiple operations."""
        tracker = CostTracker()
        
        tracker.record_extraction_cost('claude_vision', 'affiliation', 0.10)
        tracker.record_extraction_cost('google_vision', 'ocr', 0.03)
        tracker.record_extraction_cost('claude_vision', 'full_text', 0.15)
        
        assert tracker.total_cost == 0.28
        assert len(tracker.cost_records) == 3
    
    def test_get_costs_by_extractor(self):
        """Test getting costs grouped by extractor."""
        tracker = CostTracker()
        
        tracker.record_extraction_cost('claude_vision', 'affiliation', 0.10)
        tracker.record_extraction_cost('google_vision', 'ocr', 0.03)
        tracker.record_extraction_cost('claude_vision', 'full_text', 0.15)
        
        costs_by_extractor = tracker.get_costs_by_extractor()
        
        assert costs_by_extractor['claude_vision'] == 0.25
        assert costs_by_extractor['google_vision'] == 0.03
    
    def test_get_cost_summary(self):
        """Test getting comprehensive cost summary."""
        tracker = CostTracker()
        
        tracker.record_extraction_cost('claude_vision', 'affiliation', 0.10, 
                                     details={'pages': 2})
        tracker.record_extraction_cost('google_vision', 'ocr', 0.03,
                                     details={'pages': 10})
        
        summary = tracker.get_cost_summary()
        
        assert summary['total_cost'] == 0.13
        assert summary['total_operations'] == 2
        assert 'by_extractor' in summary
        assert 'by_operation' in summary
    
    def test_record_free_extraction(self):
        """Test recording free extractions (like PyMuPDF)."""
        tracker = CostTracker()
        
        tracker.record_extraction_cost('pymupdf', 'full_text', 0.0)
        
        assert tracker.total_cost == 0.0
        assert len(tracker.cost_records) == 1
        
        # Should still track the operation even if free
        record = tracker.cost_records[0]
        assert record['extractor'] == 'pymupdf'
        assert record['cost'] == 0.0
    
    def test_get_operations_count(self):
        """Test counting operations by type."""
        tracker = CostTracker()
        
        tracker.record_extraction_cost('claude_vision', 'affiliation', 0.10)
        tracker.record_extraction_cost('google_vision', 'affiliation', 0.03)
        tracker.record_extraction_cost('pymupdf', 'full_text', 0.0)
        
        operations = tracker.get_operations_count()
        
        assert operations['affiliation'] == 2
        assert operations['full_text'] == 1
    
    def test_timestamp_recording(self):
        """Test that timestamps are recorded for operations."""
        tracker = CostTracker()
        
        before_time = datetime.now()
        tracker.record_extraction_cost('test_extractor', 'test_op', 0.05)
        after_time = datetime.now()
        
        record = tracker.cost_records[0]
        record_time = record['timestamp']
        
        assert before_time <= record_time <= after_time