from pydantic import BaseModel,Field
from typing import Optional,List



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

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences"""
    monthly_income: Optional[float] = Field(None, ge=0, description="Monthly income in rupees")
    risk_tolerance: Optional[float] = Field(None, ge=0, le=1, description="Risk tolerance (0-1)")
    preferred_categories: Optional[List[str]] = Field(None, description="Preferred spending categories")
    
    class Config:
        schema_extra = {
            "example": {
                "monthly_income": 50000,
                "risk_tolerance": 0.6,
                "preferred_categories": ["food", "transport"]
            }
        }

class UserPreferencesResponse(BaseModel):
    """Response schema for user preferences"""
    monthly_income: Optional[float]
    risk_tolerance: float
    preferred_categories: List[str]
    
    class Config:
        from_attributes = True
