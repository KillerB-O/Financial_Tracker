from datetime import datetime,timedelta,timezone
from typing import Optional
from jose import jwt  # type: ignore 
from passlib.context import CryptContext
from .config import settings

pwd_cxt=CryptContext(schemes=["bcrypt"],deprecated='auto')

def get_password_hash(password:str)->str:
    return pwd_cxt.hash(password)

def verify_password(plain_password:str,hashed_password:str)->bool:
    return pwd_cxt.verify(plain_password,hashed_password)

def create_access_token(subject:str,expires_delta:Optional[timedelta]=None)->str:
    now=datetime.now(timezone.utc)
    expire=now+(expires_delta if expires_delta else timedelta(minutes=settings.access_token_expire_minutes))
    payload={"sub":str(subject),
             "iat":now.timestamp(),
             "exp":expire.timestamp()}
    token=jwt.encode(payload,settings.secret_key,algorithm=[settings.algorithm])
    return token

def decode_access_token(token:str)->dict:
    return jwt.decode(token,settings.secret_key,algorithms=[settings.algorithm])