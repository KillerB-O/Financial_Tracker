from pydantic_settings import BaseSettings
from typing import Optional
from functools  import lru_cache


class Settings(BaseSettings):

    project_name:str="Finpal_Backend"
    app_name: str = "FinPal"          
    environment: str = "development"  

    SQLITE_DB_FILE: str="finpal_auth.db"
    DATABASE_URL: Optional[str] = None

    secret_key:str
    algorithm:str ="HS256"
    access_token_expire_minutes: int= 60*24*7

    min_savings_threshold: float        
    min_confidence: float              
    excess_spending_threshold: float      

    
    PENNYWISE_API_URL: Optional[str] = None
    PENNYWISE_API_KEY: Optional[str] = None
    API_URL: str = "http://localhost:8000"
    DEBUG: bool = True

    class Config:
            env_file=".env"
            env_file_encoding="utf-8"
            extra="ignore"
    
def Settings_sqlitefile() -> str:
    # this will be called once when the module is loaded
    return "finpal_auth.db"

settings=Settings()

if settings.DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{settings.SQLITE_DB_FILE}"