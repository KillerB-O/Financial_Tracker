from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime


class AggregationHelper:
    """Helper functions for data aggregation"""
    
    @staticmethod
    def aggregate_by_category(transactions: List[Any]) -> Dict[str, float]:
        """Aggregate transaction amounts by category"""
        category_totals = defaultdict(float)
        
        for txn in transactions:
            if hasattr(txn, 'category') and hasattr(txn, 'amount'):
                if txn.category:
                    category_totals[txn.category] += txn.amount
        
        return dict(category_totals)
    
    @staticmethod
    def aggregate_by_merchant(transactions: List[Any]) -> Dict[str, float]:
        """Aggregate transaction amounts by merchant"""
        merchant_totals = defaultdict(float)
        
        for txn in transactions:
            if hasattr(txn, 'merchant') and hasattr(txn, 'amount'):
                if txn.merchant:
                    merchant_totals[txn.merchant] += txn.amount
        
        return dict(merchant_totals)
    
    @staticmethod
    def aggregate_by_date(transactions: List[Any]) -> Dict[str, float]:
        """Aggregate transaction amounts by date"""
        date_totals = defaultdict(float)
        
        for txn in transactions:
            if hasattr(txn, 'received_at') and hasattr(txn, 'amount'):
                date_key = txn.received_at.strftime('%Y-%m-%d')
                date_totals[date_key] += txn.amount
        
        return dict(date_totals)
    
    @staticmethod
    def calculate_percentiles(values: List[float]) -> Dict[str, float]:
        """Calculate percentiles (25th, 50th, 75th)"""
        import numpy as np
        
        if not values:
            return {'p25': 0, 'p50': 0, 'p75': 0}
        
        return {
            'p25': float(np.percentile(values, 25)),
            'p50': float(np.percentile(values, 50)),  # Median
            'p75': float(np.percentile(values, 75))
        }
