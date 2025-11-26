import re
from typing import Optional
from datetime import datetime
import httpx
from ..schemas.sms import ParsedTransaction,TransactionType

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
            r'(?:at|to|from)\s+([A-Z][A-Za-z0-9\s&\-]{2,40})',
            r'(?:merchant|payee):\s*([A-Za-z0-9\s&\-]{2,40})',
        ],
        'account': r'(?:a\/c|account|card)[\s\*]+(?:ending\s+)?(?:x{2,4})?(\d{4})',
        'balance': r'(?:balance|bal|avbl|available)[\s:]*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{2})?)',
        'date': r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
    }

    @classmethod
    def parse(cls,message:str)->ParsedTransaction:
        """Parse SMS message for transaction details"""
        message_lower=message.lower()

        #Initialize result 
        result=ParsedTransaction
        confidence=0.0

        #Detemine Amount
        amount=cls._extract_amount(message)
        if amount:
            result.amount=amount
            confidence +=0.3
        
        #determine transaction time 
        trans_type=cls._extract_transtion_type(message_lower)
        if trans_type:
            result.transaction_type=trans_type
            confidence+=0.2

        #determine merchant
        merchant=cls._extract_merchant(message)
        if merchant:
            result.merchant=merchant
            confidence+=0.2
        
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

        #Categorize transaction
        if result.merchant:
            result.category=cls._categorize_merchant(result.merchant)
            confidence+=0.1
        
        result.confidence=min(confidence,1.0)
        return result
    
    @classmethod
    def _extract_amount(cls,message:str)->Optional[float]:
        for pattern in cls.PATTERNS['amount']:
            match=re.search(pattern,message,re.IGNORECASE)
            if match:
                amount_str=match.group(1).replace(',','')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    @classmethod
    def _extract_transaction_type(cls,message_lower:str)->Optional[TransactionType]:
        if re.search(cls.PATTERNS['transaction_type']['debit'],message_lower):
            return TransactionType.DEBIT
        elif re.search(cls.PATTERNS['transaction_type']['credit'],message_lower):
            return TransactionType.CREDIT
        return TransactionType.UNKNOWN
        
    @classmethod
    def _extract_merchant(cls,message:str)->Optional[str]:
        for pattern in cls.PATTERNS['merchant']:
            match = re.search(pattern,message,re.IGNORECASE)
            if match:
                merchant=match.group(1).strip()

                #Clean up Commmon noise
                merchant=re.sub(r'\s+','',merchant)
                if len(merchant)>3:
                    return merchant
        return None
    
    @classmethod
    def _extract_account(cls,message:str)->Optional[str]:
        match=re.search(cls.PATTERNS['account'],message,re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    @classmethod
    def _extract_balance(cls,message:str)->Optional[float]:
        match=re.search(cls.PATTERNS['balance'],message,re.IGNORECASE)
        if match :
            balance_str=match.group(1).replace(',','')
            try:
                return float(balance_str)
            except ValueError:
                pass
        return None
    
    @classmethod
    def _catogorize_merchant(cls,merchant:str)->str:
        """Simple category detection based on merchant name"""
        merchant_lower = merchant.lower()
        
        categories = {
            'food': ['restaurant', 'cafe', 'swiggy', 'zomato', 'food', 'pizza', 'burger', 'mcdonald', 'kfc'],
            'transport': ['uber', 'ola', 'rapido', 'metro', 'petrol', 'fuel', 'gas', 'parking'],
            'shopping': ['amazon', 'flipkart', 'myntra', 'mall', 'store', 'shop'],
            'utilities': ['electricity', 'water', 'gas', 'mobile', 'recharge', 'airtel', 'jio', 'vi'],
            'entertainment': ['netflix', 'prime', 'hotstar', 'movie', 'theatre', 'spotify', 'youtube'],
            'groceries': ['bigbasket', 'grofers', 'blinkit', 'dmart', 'reliance', 'fresh'],
            'health': ['pharma', 'medicine', 'hospital', 'clinic', 'apollo', 'medplus'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return category
        
        return 'other'

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
