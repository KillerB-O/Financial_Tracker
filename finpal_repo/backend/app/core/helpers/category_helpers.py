from typing import Optional, Dict, List


class CategoryHelper:
    """Helper functions for transaction categorization"""
    
    CATEGORY_KEYWORDS = {
        'food': [
            'swiggy', 'zomato', 'restaurant', 'cafe', 'food', 'pizza', 'burger',
            'mcdonald', 'kfc', 'dominos', 'subway', 'starbucks', 'dunkin',
            'breakfast', 'lunch', 'dinner', 'meal'
        ],
        'transport': [
            'uber', 'ola', 'rapido', 'metro', 'petrol', 'fuel', 'gas', 'parking',
            'toll', 'cab', 'taxi', 'auto', 'bus', 'train', 'flight'
        ],
        'shopping': [
            'amazon', 'flipkart', 'myntra', 'ajio', 'mall', 'store', 'shop',
            'clothing', 'fashion', 'footwear', 'accessories'
        ],
        'groceries': [
            'bigbasket', 'grofers', 'blinkit', 'zepto', 'swiggy instamart',
            'dmart', 'reliance fresh', 'supermarket', 'grocery', 'vegetables',
            'fruits', 'dairy'
        ],
        'entertainment': [
            'netflix', 'prime', 'hotstar', 'spotify', 'youtube', 'movie',
            'theatre', 'pvr', 'inox', 'cinema', 'concert', 'game', 'gaming'
        ],
        'utilities': [
            'electricity', 'water', 'gas', 'mobile', 'recharge', 'airtel',
            'jio', 'vi', 'vodafone', 'broadband', 'internet', 'wifi'
        ],
        'health': [
            'pharmacy', 'medicine', 'hospital', 'clinic', 'doctor', 'apollo',
            'medplus', 'netmeds', '1mg', 'pharmeasy', 'dental', 'medical'
        ],
        'education': [
            'course', 'udemy', 'coursera', 'school', 'college', 'university',
            'tuition', 'books', 'learning', 'training'
        ],
        'insurance': [
            'insurance', 'policy', 'premium', 'lic', 'icici prudential',
            'hdfc life', 'sbi life', 'health insurance'
        ],
        'investment': [
            'mutual fund', 'sip', 'stocks', 'zerodha', 'groww', 'upstox',
            'angel one', 'investment', 'trading'
        ],
    }
    
    ESSENTIAL_CATEGORIES = ['groceries', 'utilities', 'health', 'transport', 'education']
    DISCRETIONARY_CATEGORIES = ['food', 'shopping', 'entertainment']
    
    @classmethod
    def categorize(cls, merchant: str, description: str = "") -> str:
        """Categorize transaction based on merchant and description"""
        text = f"{merchant} {description}".lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        return 'other'
    
    @classmethod
    def is_essential(cls, category: str) -> bool:
        """Check if category is essential spending"""
        return category in cls.ESSENTIAL_CATEGORIES
    
    @classmethod
    def is_discretionary(cls, category: str) -> bool:
        """Check if category is discretionary spending"""
        return category in cls.DISCRETIONARY_CATEGORIES
    
    @classmethod
    def get_category_icon(cls, category: str) -> str:
        """Get emoji icon for category"""
        icons = {
            'food': '🍔',
            'transport': '🚗',
            'shopping': '🛍️',
            'groceries': '🛒',
            'entertainment': '🎬',
            'utilities': '💡',
            'health': '🏥',
            'education': '📚',
            'insurance': '🛡️',
            'investment': '📈',
            'other': '💰'
        }
        return icons.get(category, '💰')
