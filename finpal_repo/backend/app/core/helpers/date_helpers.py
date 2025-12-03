from datetime import datetime, timedelta,timezone
from typing import Tuple, List


class DateHelper:
    """Helper functions for date operations"""
    
    @staticmethod
    def get_month_start_end(date: datetime = None) -> Tuple[datetime, datetime]:
        """Get start and end datetime of a month"""
        if date is None:
            date = datetime.now(timezone.utc)
        
        # First day of month
        start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Last day of month
        if date.month == 12:
            end = date.replace(year=date.year + 1, month=1, day=1)
        else:
            end = date.replace(month=date.month + 1, day=1)
        
        end = end - timedelta(microseconds=1)
        
        return start, end
    
    @staticmethod
    def get_week_start_end(date: datetime = None) -> Tuple[datetime, datetime]:
        """Get start and end of current week (Monday-Sunday)"""
        if date is None:
            date = datetime.now(timezone.utc)
        
        # Monday of current week
        start = date - timedelta(days=date.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Sunday of current week
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return start, end
    
    @staticmethod
    def get_last_n_days(days: int, from_date: datetime = None) -> Tuple[datetime, datetime]:
        """Get date range for last N days"""
        if from_date is None:
            from_date = datetime.now(timezone.utc)
        
        end = from_date
        start = from_date - timedelta(days=days)
        
        return start, end
    
    @staticmethod
    def days_until(target_date: datetime) -> int:
        """Calculate days until target date"""
        now = datetime.now(timezone.utc)
        delta = target_date - now
        return max(0, delta.days)
    
    @staticmethod
    def is_same_month(date1: datetime, date2: datetime) -> bool:
        """Check if two dates are in the same month"""
        return date1.year == date2.year and date1.month == date2.month
