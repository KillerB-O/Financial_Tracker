#database models

from typing import Optional
from sqlalchemy import Column,Float,String,Boolean,DateTime,Text,Enum
from sqlalchemy.orm import Mapped,mapped_column
from datetime import datetime,timezone
import uuid
from app.db.base import Base
import enum

class User(Base):
    __tablename__="users"
    
  

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )   
    id:Mapped[str]=mapped_column(
        String,primary_key=True,default=lambda:str(uuid.uuid4())
    )
    email:Mapped[str]=mapped_column(String,nullable=False,unique=True,index=True)
    full_name:Mapped[str]=mapped_column(String)
    hashed_password:Mapped[str]=mapped_column(String)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)

class ParsingStatus(str,enum.Enum):
    PENDING="pending"
    PARSED="parsed"
    FAILED="failed"
    REMOTE_PARSING="remote_parsing"

class TransactionType(str,enum.Enum):
    DEBIT="debit"
    CREDIT="credit"
    UNKNOWN="Unknown"

class SMS(Base):
    __tablename__="sms"

    id=Column(String,primary_key=True,index=True)
    user_id=Column(String,nullable=False,index=True)
    
    # Raw sms data
    phone_number=Column(String,nullable=False)
    raw_message=Column(Text,nullable=True)
    recieved_at=Column(DateTime,default=lambda:datetime.now(timezone.utc),nullable=False)

    # Parsed metadata
    parsed_at=Column(DateTime,nullable=True)
    parsing_status=Column(
        Enum(ParsingStatus),
        default=ParsingStatus.PENDING,
        nullable=False
    )
    error_message=Column(Text,nullable=True)
    remote_parse_requested=Column(Boolean,default=False)

    # Parsed transaction data
    amount=Column(Float,nullable=True)
    transaction_type=Column(Enum(TransactionType),nullable=True)
    merchant=Column(String,nullable=True)
    account_last4=Column(String,nullable=True)
    transaction_date=Column(DateTime,nullable=True)
    balance=Column(Float,nullable=True)
    category=Column(String,nullable=True)
    confidence=Column(Float,default=0.0)

    created_at=Column(DateTime,default=lambda:datetime.now(timezone.utc),nullable=False)    
