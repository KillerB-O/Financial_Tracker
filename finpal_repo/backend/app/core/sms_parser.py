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

            #determine merchant
            merchant=cls._extract_merchant(message)
            if merchant:
                result.merchant =merchant
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
                result.category=cls._catogorize_merchant(result.merchant)
                confidence+=0.1

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

                #Clean up Commmon noise
                    merchant=re.sub(r'\s+','',merchant)
                    if len(merchant)>3:
                        return merchant
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
