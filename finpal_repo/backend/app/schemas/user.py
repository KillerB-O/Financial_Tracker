from pydantic import BaseModel


class UserCreate(BaseModel):
    email:str
    password:str
    full_name:str

class UserRead(BaseModel):
    id:str
    email:str
    full_name:str
    is_active:bool

    class Config:
            from_attributes=True

class Token(BaseModel):
     access_token:str
     token_type: str="bearer"

class UserDelete(BaseModel):
     email:str
    