from typing import Optional
from datetime import datetime


class FormattingHelper:
    """Helper functions for data formatting"""
    
    @staticmethod
    def format_currency(amount: float, include_symbol: bool = True) -> str:
        """Format amount as Indian currency"""
        if include_symbol:
            return f"₹{amount:,.2f}"
        return f"{amount:,.2f}"
    
    @staticmethod
    def format_percentage(value: float, decimal_places: int = 1) -> str:
        """Format as percentage"""
        return f"{value:.{decimal_places}f}%"
    
    @staticmethod
    def format_relative_date(date: datetime) -> str:
        """Format date as relative time (e.g., '2 days ago')"""
        now = datetime.utcnow()
        diff = now - date
        
        if diff.days == 0:
            if diff.seconds < 3600:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = diff.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to max length"""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
