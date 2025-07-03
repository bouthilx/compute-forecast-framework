"""Cost tracking system for PDF extraction operations."""

import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class CostTracker:
    """Tracks costs for PDF extraction operations, especially cloud services."""
    
    def __init__(self):
        """Initialize cost tracker."""
        self.cost_records: List[Dict[str, Any]] = []
        self.total_cost: float = 0.0
    
    def record_extraction_cost(self, extractor_name: str, operation: str, 
                             cost: float, details: Dict[str, Any] = None) -> None:
        """Record cost for an extraction operation.
        
        Args:
            extractor_name: Name of the extractor (e.g., 'google_vision', 'claude_vision')
            operation: Type of operation (e.g., 'affiliation_extraction', 'ocr', 'full_text')
            cost: Cost in dollars for this operation
            details: Additional details about the operation (pages, API calls, etc.)
        """
        record = {
            'extractor': extractor_name,
            'operation': operation,
            'cost': cost,
            'timestamp': datetime.now(),
            'details': details or {}
        }
        
        self.cost_records.append(record)
        self.total_cost += cost
        
        if cost > 0:
            logger.info(f"Recorded ${cost:.4f} cost for {extractor_name}/{operation}")
        else:
            logger.debug(f"Recorded free operation: {extractor_name}/{operation}")
    
    def get_costs_by_extractor(self) -> Dict[str, float]:
        """Get total costs grouped by extractor.
        
        Returns:
            Dictionary mapping extractor name to total cost
        """
        costs = defaultdict(float)
        
        for record in self.cost_records:
            costs[record['extractor']] += record['cost']
        
        return dict(costs)
    
    def get_costs_by_operation(self) -> Dict[str, float]:
        """Get total costs grouped by operation type.
        
        Returns:
            Dictionary mapping operation type to total cost
        """
        costs = defaultdict(float)
        
        for record in self.cost_records:
            costs[record['operation']] += record['cost']
        
        return dict(costs)
    
    def get_operations_count(self) -> Dict[str, int]:
        """Get count of operations by type.
        
        Returns:
            Dictionary mapping operation type to count
        """
        counts = defaultdict(int)
        
        for record in self.cost_records:
            counts[record['operation']] += 1
        
        return dict(counts)
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary.
        
        Returns:
            Dictionary with cost breakdown and statistics
        """
        return {
            'total_cost': self.total_cost,
            'total_operations': len(self.cost_records),
            'by_extractor': self.get_costs_by_extractor(),
            'by_operation': self.get_costs_by_operation(),
            'operation_counts': self.get_operations_count(),
            'average_cost_per_operation': (
                self.total_cost / len(self.cost_records) 
                if self.cost_records else 0.0
            )
        }
    
    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent operations.
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of recent operation records
        """
        return sorted(
            self.cost_records, 
            key=lambda x: x['timestamp'], 
            reverse=True
        )[:limit]
    
    def reset(self) -> None:
        """Reset all cost tracking data."""
        self.cost_records.clear()
        self.total_cost = 0.0
        logger.info("Cost tracker reset")
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export all cost data for serialization.
        
        Returns:
            Dictionary containing all cost tracking data
        """
        return {
            'total_cost': self.total_cost,
            'records': [
                {
                    **record,
                    'timestamp': record['timestamp'].isoformat()
                }
                for record in self.cost_records
            ],
            'summary': self.get_cost_summary()
        }