from pydantic import BaseModel,Field
from typing import Optional,List
from datetime import datetime
from enum import Enum


class ParsingStatus(str,Enum):
    PENDING= "pending"
    PARSED="parsed"
    FAILED="failed"
    REMOTE_PARSING="remote_parsing"

class TransactionType(str,Enum):
    DEBIT="debit"
    CREDIT="credit"
    UNKNOWN="Unknown"

class SMSIngestRequest(BaseModel):
    phone_number=str
    message=str
    recieved_at:Optional[datetime]=None
    consent_store_raw:bool =True
    force_remote_parse: bool=False

class SMSParseRequest(BaseModel):
    sms_id:str

class PennyWiseCallback(BaseModel):
    sms_id:str
    succes:bool
    parsed_data:Optional[dict]=None
    error:Optional[str]=None

class ParsedTransaction(BaseModel):
    amount:Optional[float]=None
    transaction_type:Optional[TransactionType]=None
    merchant:Optional[str]=None
    account_last4:Optional[str]=None
    transaction_date:Optional[datetime]=None
    balance:Optional[float]=None
    category:Optional[str]=None
    confidence:float=0.0

class SMSResponse(BaseModel):
    id:str
    user_id:str
    phone_number:str
    raw_message:Optional[str]=None
    recieved_at:datetime
    parsed_at:Optional[datetime]=None
    parsing_status:ParsingStatus
    error_message:Optional[str]=None
    remote_parsing_request:bool=False

    amount:Optional[float]=None
    transaction_type:Optional[TransactionType]=None
    merchant:Optional[str]=None
    account_last4:Optional[str]=None
    transaction_date:Optional[datetime]=None
    balance:Optional[float]=None
    category:Optional[str]=None
    confidence:float=0.0

    created_at:datetime

    class config:
        from_attributes=True

class SMSListResponse(BaseModel):
    items:List[SMSResponse]
    total:int
    skip:int
    limit:int