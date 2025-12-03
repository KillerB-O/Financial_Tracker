import re
from typing import Optional
from datetime import datetime
import httpx,logging
from ..schemas.sms import ParsedTransaction,TransactionType
from .helpers.sms_helpers import SMSTextHelper  
from .helpers.category_helpers import CategoryHelper

logger=logging.getLogger(__name__)

class LocalSMSParser:
    """Local SMS expense parser with pattern matching"""
    
    # Common patterns for Indian banks and payment apps
    PATTERNS = {
        'amount': [
            r'(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'(?:debited|credited|spent|paid|received)\s+(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{2})?)',
        ],
        'transaction_type': {
            'debit': r'(?:debited|spent|paid|withdrawn|purchase|debit)',
            'credit': r'(?:credited|received|refund|deposit|credit)',
        },
        'merchant': [
            # Pattern 1: "spent on MERCHANT on date" - NEW, FIRST PRIORITY
            r'(?:spent|paid)\s+on\s+([A-Z][A-Z\s&\-]+?)(?:\s+on\s+\d)',

            # Pattern 2: "at MERCHANT"
            r'(?:at|to)\s+([A-Z][A-Z\s&\-]+?)(?:\s+on\s+\d|\.|,|$)',

            # Pattern 3: "for MERCHANT on"
            r'for\s+([A-Z][A-Z\s&\-]+?)(?:\s+on\s+\d)',

            # Pattern 4: "on MERCHANT using"
            r'on\s+([A-Z][A-Z\s&\-]+?)(?:\s+using)'
        ],
        'account': r'(?:a\/c|account|card)[\s\*]+(?:ending\s+)?(?:x{2,4})?(\d{4})',
        'balance': r'(?:balance|bal|avbl|available)[\s:]*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{2})?)',
        'date':r"(\d{1,2}[-/ ](?:\d{1,2}|[A-Za-z]{3,9})[-/ ]\d{2,4})"
    }

    @classmethod
    def parse(cls,message:str)->ParsedTransaction:
        """Parse SMS message for transaction details"""
        if not isinstance(message,str):
            logging.error(f"parse() received non-string input: {type(message)}")
            message=str(message) if message is not None else ""
        
        if not message:
            logging.warning("parse() recieved empty message")
            return ParsedTransaction()
        
        message_lower=message.lower()

        #Initialize result 
        result=ParsedTransaction()
        confidence=0.0
        
        try:
            #Detemine Amount
            amount=cls._extract_amount(message)
            if amount:
                result.amount = amount
                confidence+=0.3        
            #determine transaction time 
            trans_type=cls._extract_transaction_type(message_lower)
            if trans_type:
                result.transaction_type=trans_type
                confidence+=0.2

             # Extract merchant (for debits) or source (for credits)
            if trans_type == TransactionType.DEBIT:
                merchant = cls._extract_merchant(message)
                if merchant:
                    result.merchant = merchant
                    confidence += 0.2
                    # Categorize based on merchant
                    result.category = cls._categorize_merchant(result.merchant)
                    confidence += 0.1

            elif trans_type == TransactionType.CREDIT:
                # For credits, extract the source/reason
                source = cls._extract_credit_source(message)
                if source:
                    result.merchant = source
                    confidence += 0.2
                # Categorize credits separately
                result.category = cls._categorize_credit(message)
                confidence += 0.1

            #Extract account number
            account=cls._extract_account(message)
            if account:
                result.account_last4=account
                confidence+=0.1

            #Extract balance
            balance=cls._extract_balance(message)
            if balance:
                result.balance=balance
                confidence+=0.1

            #Extract transaction date
            trans_date=cls._extract_trans_date(message)
            if trans_date:
                result.transaction_date=trans_date

            result.confidence=min(confidence,1.0)
        except Exception as e:
            logger.error(f"Error parsing SMS: {str(e)}",exc_info=True)
            pass

        return result
    
    @classmethod
    def _extract_amount(cls,message:str)->Optional[float]:

        if not isinstance(message,str):
            message=str(message) if message is not None else ""

        for pattern in cls.PATTERNS['amount']:
            try:
                match=re.search(pattern,message,re.IGNORECASE)
                if match:
                    amount_str=match.group(1).replace(',','')
                    return float(amount_str)
            except (AttributeError,ValueError,TypeError) as e:
                logger.debug(f"Amount extraction error {e}")
                continue
        return None
    
    @classmethod
    def _extract_transaction_type(cls,message_lower:str)->Optional[TransactionType]:
        
        if not isinstance(message_lower,str):
            message_lower=str(message_lower).lower() if message_lower is not None else ""
        try:
            if re.search(cls.PATTERNS['transaction_type']['debit'],message_lower):
                return TransactionType.DEBIT
            elif re.search(cls.PATTERNS['transaction_type']['credit'],message_lower):
                return TransactionType.CREDIT
        except (TypeError,AttributeError) as e:
            logger.debug(f"Transaction type extraction error: {e}")
        
        return TransactionType.UNKNOWN
        
    @classmethod
    def _extract_merchant(cls,message:str)->Optional[str]:

        if not isinstance(message,str):
            message=str(message) if message is not None else ""
        try:
            for pattern in cls.PATTERNS['merchant']:
                match = re.search(pattern,message,re.IGNORECASE)
                if match:
                    merchant=match.group(1).strip()
  
                    # Clean up the merchant name
                    # Remove dates (e.g., "on 28-Nov-24", "on 26-Nov-24")
                    merchant = re.sub(r'\s*on\s+\d{1,2}[-/]\w{3}[-/]\d{2,4}.*', '', merchant, flags=re.IGNORECASE)
                    
                    # Remove "card XX1234 for" type patterns
                    merchant = re.sub(r'card\s+[xX]{2,4}\d{4}\s+for\s+', '', merchant, flags=re.IGNORECASE)
                    
                    # Remove extra whitespace
                    merchant = re.sub(r'\s+', ' ', merchant)
                    
                    # Remove leading/trailing junk
                    merchant = merchant.strip()
                    
                    # Only return if it's a reasonable length and has letters
                    if len(merchant) > 2 and any(c.isalpha() for c in merchant):
                        return merchant.upper() 
        except(AttributeError,TypeError) as e:
            logger.debug(f"Mercahnt extraction error: {e}")
        return None
    
    @classmethod
    def _extract_account(cls,message:str)->Optional[str]:

        if not isinstance(message,str):
            message=str(message) if message is not None else ""

        try:
            match=re.search(cls.PATTERNS['account'],message,re.IGNORECASE)
            if match:
                return match.group(1)
        except (AttributeError,TypeError) as e:
            logger.debug(f"Accouunt extraction error : {e}")
        
        return None
     
    @classmethod
    def _extract_trans_date(cls,message:str)->Optional[datetime]:

        if not isinstance(message,str):
            message=str(message) if message is not None else ""
        try:
            match=re.search(cls.PATTERNS['date'],message,re.IGNORECASE)
            if match:
                date_str=match.group(1).strip()
                normalized = (
                    date_str.replace("/", "-")
                        .replace("  ", " ")
                        .replace(" ", "-")
            )

            # Try multiple possible formats: numeric month and string month
                formats = [
                    "%d-%m-%Y",  # 25-11-2024
                    "%d-%m-%y",  # 25-11-24
                    "%d-%b-%Y",  # 25-Nov-2024
                    "%d-%b-%y",  # 25-Nov-24
                    "%d-%B-%Y",  # 25-November-2024
                    "%d-%B-%y",  # 25-November-24
                ]

                for fmt in formats:
                    try:
                        return datetime.strptime(normalized, fmt)
                    except ValueError:
                        continue

            # If none of the formats worked
                logger.debug(f"Could not parse date '{date_str}' (normalized: '{normalized}')")
                return None
        except (AttributeError,TypeError) as e:
            logger.debug(f"Transaction date extraction error:{e}")
        return None
    
    @classmethod
    def _extract_balance(cls,message:str)->Optional[float]:

        if not isinstance(message,str):
            message=str(message) if message is not None else ""
        
        try:
            match=re.search(cls.PATTERNS['balance'],message,re.IGNORECASE)
            if match :
                balance_str=match.group(1).replace(',','')
                return float(balance_str)
        except (AttributeError,TypeError,ValueError) as e:
            logger.debug(f"Balance Extraction error : {e}")
            
        return None
    
    @classmethod
    def _catogorize_merchant(cls,merchant:str)->str:
        """Simple category detection based on merchant name"""
        
        if not isinstance(merchant,str):
            merchant=str(merchant) if merchant is not None else ""
        
        merchant_lower = merchant.lower()
        
        categories = {
            'food': ['restaurant', 'swiggy instamart','cafe', 'swiggy', 'zomato', 'food', 'pizza', 'burger', 'mcdonald', 'kfc','dominos','subway','starbucks'],
            'transport': ['uber', 'ola', 'rapido', 'metro', 'petrol', 'fuel', 'gas', 'parking','toll','cab','taxi','auto'],
            'shopping': ['amazon', 'flipkart', 'myntra', 'mall', 'store', 'shop'],
            'utilities': ['electricity', 'water', 'gas', 'mobile', 'recharge', 'airtel', 'jio', 'vi','vodaphone','broadband'],
            'entertainment': ['netflix', 'prime', 'hotstar', 'movie', 'theatre', 'spotify', 'youtube','pvr','inox'],
            'groceries': ['bigbasket', 'grofers', 'blinkit', 'dmart', 'reliance', 'fresh','supermarket','instamart'],
            'health': ['pharma','pharmacy','1mg','pharmeasy', 'medicine', 'hospital', 'clinic', 'apollo', 'medplus'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return category
        
        return 'other'
    
    @classmethod
    def _extract_credit_source(cls, message: str) -> Optional[str]:
        """
        Extract source/reason for credit transactions
        Examples: "Salary", "Refund from Amazon", "Transfer from John"
        """
        if not isinstance(message, str):
            message = str(message) if message is not None else ""
        
        # Pattern 1: "- Source for month"
        match = re.search(r'-\s*([A-Za-z\s]+)\s+for\s+\w+\s+\d{4}', message, re.IGNORECASE)
        if match:
            source = match.group(1).strip().title()
            return source
        
        # Pattern 2: "credited - Reason"
        match = re.search(r'credited\s*-?\s*([A-Za-z\s]+)', message, re.IGNORECASE)
        if match:
            source = match.group(1).strip().title()
            # Remove common trailing words
            source = re.sub(r'\s+(for|from|to|on)\s.*', '', source, flags=re.IGNORECASE)
            return source
        
        # Pattern 3: "Refund from MERCHANT"
        match = re.search(r'(refund|cashback|bonus)\s+from\s+([A-Za-z\s]+)', message, re.IGNORECASE)
        if match:
            return f"{match.group(1).title()} from {match.group(2).strip()}"
        
        # Pattern 4: Just look for common income keywords
        income_keywords = {
            'salary': 'Salary',
            'bonus': 'Bonus',
            'incentive': 'Incentive',
            'reimbursement': 'Reimbursement',
            'refund': 'Refund',
            'cashback': 'Cashback',
            'interest': 'Interest',
            'dividend': 'Dividend',
            'transfer': 'Transfer',
        }
        
        message_lower = message.lower()
        for keyword, display_name in income_keywords.items():
            if keyword in message_lower:
                return display_name
        
        return None
    
    @classmethod
    def _categorize_credit(cls, message: str) -> str:
        """
        Categorize credit transactions (income)
        """
        if not isinstance(message, str):
            message = str(message) if message is not None else ""
        
        message_lower = message.lower()
        
        # Income categories
        if any(word in message_lower for word in ['salary', 'wages', 'payroll']):
            return 'income'
        elif any(word in message_lower for word in ['refund', 'return']):
            return 'refund'
        elif any(word in message_lower for word in ['cashback', 'reward', 'bonus']):
            return 'cashback'
        elif any(word in message_lower for word in ['interest', 'dividend']):
            return 'investment'
        elif any(word in message_lower for word in ['transfer', 'upi', 'neft', 'imps']):
            return 'transfer'
        else:
            return 'income'  # Default for credits
   
#PennyWise Parser
async def enqueue_remote_parse(sms, message: str):
    """Send SMS to PennyWise AI for parsing"""
    from ..core.config import settings
    
    pennywise_url = settings.PENNYWISE_API_URL or "https://api.pennywise.ai/v1/sms/parse"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                pennywise_url,
                json={
                    "sms_id": sms.id,
                    "message": message,
                    "callback_url": f"{settings.API_URL}/api/v0/sms/callback"
                },
                headers={
                    "Authorization": f"Bearer {settings.PENNYWISE_API_KEY}"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                sms.remote_parse_requested = True
                sms.parsing_status = "remote_parsing"
    except Exception as e:
        print(f"Failed to enqueue remote parse: {e}")

