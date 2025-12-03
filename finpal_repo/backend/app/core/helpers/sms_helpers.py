import re
from typing import Optional, Dict, List
from datetime import datetime


class SMSTextHelper:
    """Helper functions for SMS text processing"""
    
    @staticmethod
    def clean_amount(amount_str: str) -> Optional[float]:
        """
        Clean and parse amount from various formats
        Examples: "1,250.00" -> 1250.0, "Rs.500" -> 500.0
        """
        if not amount_str:
            return None
        
        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[Rs\.₹INR\s]', '', amount_str)
        # Remove commas
        cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    @staticmethod
    def extract_date(text: str) -> Optional[datetime]:
        """Extract date from SMS text"""
        date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',  # 25-11-2024
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',  # 25 Nov 2024
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Parse different formats
                for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d %b %Y']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
        
        return None
    
    @staticmethod
    def normalize_merchant_name(merchant: str) -> str:
        """Normalize merchant name for consistency"""
        if not merchant:
            return ""
        
        # Convert to title case
        merchant = merchant.strip().title()
        
        # Remove extra spaces
        merchant = re.sub(r'\s+', ' ', merchant)
        
        # Common replacements
        replacements = {
            'Pvt Ltd': '',
            'Private Limited': '',
            'Pvt. Ltd.': '',
            '  ': ' ',
        }
        
        for old, new in replacements.items():
            merchant = merchant.replace(old, new)
        
        return merchant.strip()
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Detect SMS language (English/Hindi/Kannada/etc)"""
        # Hindi Unicode range
        if re.search(r'[\u0900-\u097F]', text):
            return 'hindi'
        # Kannada Unicode range
        elif re.search(r'[\u0C80-\u0CFF]', text):
            return 'kannada'
        # Tamil Unicode range
        elif re.search(r'[\u0B80-\u0BFF]', text):
            return 'tamil'
        else:
            return 'english'
