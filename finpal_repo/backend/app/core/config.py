from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name:str="Finpal_Backend"
    SQLITE_DB_FILE: str="finpal_auth.db"
    secret_key:str="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" 
    algorithm:str="HS256"
    access_token_expire_minutes: int= 60*24*7

    class Config:
            env_file=".env"
            env_file_encoding="utf-8"
    
def Settings_sqlitefile() -> str:
    # this will be called once when the module is loaded
    return "finpal_auth.db"

settings=Settings()

SQLALCHEMY_DATABASE_URL = f"sqlite:///{settings.SQLITE_DB_FILE}"