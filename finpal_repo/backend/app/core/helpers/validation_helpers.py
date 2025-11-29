import re
from typing import Optional


class ValidationHelper:
    """Helper functions for data validation"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Validate Indian phone number"""
        # Remove spaces, dashes, etc.
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Check if it's a valid Indian number (10 digits or +91 followed by 10 digits)
        patterns = [
            r'^[6-9]\d{9}$',  # 10 digits starting with 6-9
            r'^\+91[6-9]\d{9}$',  # +91 followed by 10 digits
        ]
        
        return any(re.match(pattern, cleaned) for pattern in patterns)
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 500) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1F\x7F]', '', text)
        
        # Limit length
        text = text[:max_length]
        
        # Strip whitespace
        return text.strip()
    
    @staticmethod
    def is_valid_amount(amount: float) -> bool:
        """Validate transaction amount"""
        return 0 < amount < 10_000_000  # Between 0 and 1 crore
