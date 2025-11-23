#database models

from typing import Optional
from sqlalchemy import Column,String,Boolean
from sqlalchemy.orm import Mapped,mapped_column
from datetime import datetime,timezone
import uuid
from app.db.base import Base

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
  

