
import numpy as np
from typing import List, Tuple
from datetime import datetime, timedelta


class FinancialMathHelper:
    """Helper functions for financial calculations"""
    
    @staticmethod
    def calculate_monthly_average(amounts: List[float], days: int) -> float:
        """Calculate average monthly amount from daily data"""
        if not amounts:
            return 0.0
        
        total = sum(amounts)
        months = days / 30.0
        
        return total / max(1, months)
    
    @staticmethod
    def calculate_growth_rate(old_value: float, new_value: float) -> float:
        """Calculate percentage growth rate"""
        if old_value == 0:
            return 0.0
        
        return ((new_value - old_value) / old_value) * 100
    
    @staticmethod
    def calculate_confidence_score(
        data_points: int,
        variance: float,
        mean: float,
        peer_sample_size: int = 1000
    ) -> float:
        """
        Calculate confidence score using multiple factors
        Returns value between 0 and 1
        """
        # Data quality score (more data = higher confidence)
        c_data = min(1.0, data_points / 180)  # 6 months of daily data
        
        # Pattern consistency score (lower variance = higher confidence)
        if mean > 0:
            cv = variance / mean  # Coefficient of variation
            c_pattern = 1 - min(1.0, cv)
        else:
            c_pattern = 0.5
        
        # Peer data confidence
        c_peer = min(1.0, peer_sample_size / 1000)
        
        # Weighted average
        confidence = (
            0.4 * c_data +
            0.4 * c_pattern +
            0.2 * c_peer
        )
        
        return max(0.0, min(1.0, confidence))
    
    @staticmethod
    def compound_interest(
        principal: float,
        rate: float,
        time_years: float,
        compounds_per_year: int = 12
    ) -> float:
        """Calculate compound interest"""
        return principal * (1 + rate / compounds_per_year) ** (compounds_per_year * time_years)
    
    @staticmethod
    def future_value_of_series(
        monthly_payment: float,
        annual_rate: float,
        months: int
    ) -> float:
        """Calculate future value of a series of payments (annuity)"""
        monthly_rate = annual_rate / 12
        
        if monthly_rate == 0:
            return monthly_payment * months
        
        fv = monthly_payment * (((1 + monthly_rate) ** months - 1) / monthly_rate)
        return fv
    
    @staticmethod
    def calculate_savings_rate(income: float, expenses: float) -> float:
        """Calculate savings rate as percentage"""
        if income == 0:
            return 0.0
        
        savings = income - expenses
        return (savings / income) * 100
