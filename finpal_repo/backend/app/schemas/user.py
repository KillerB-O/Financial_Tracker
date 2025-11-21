from pydantic import BaseModel,EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email:EmailStr
    password:str
    full_name:Optional[str]=None

class UserRead(BaseModel):
    uuid:str
    email: EmailStr
    full_name:Optional[str]=None
    is_active:bool

    class Config:
            orm_model=True

class Token(BaseModel):
     access_token:str
     token_type: str="bearer"
    