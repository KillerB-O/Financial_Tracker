from sqlalchemy import create_engine
from app.core.config import SQLALCHEMY_DATABASE_URL
from app.db.base import Base
from app.db import models  #models to create/register tables

engine=create_engine(SQLALCHEMY_DATABASE_URL)

def init_db():
    Base.metadata.create_all(bind=engine)